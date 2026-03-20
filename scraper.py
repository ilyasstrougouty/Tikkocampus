"""
scraper.py — TikTok profile scraper using Playwright + Stealth.

Uses cookie_manager for cookie I/O and logger for all output.
Returns structured results with error codes.
"""
import os
import sys
import time
import json
from config import TEMP_PROCESSING_DIR, MAX_VIDEOS_PER_PROFILE
from db import insert_video_metadata, db_session
from logger import get_logger
import cookie_manager

log = get_logger("scraper")

# --- Error Codes ---
OK = "ok"
ERR_NO_COOKIES = "NO_COOKIES"
ERR_BROWSER_MISSING = "BROWSER_MISSING"
ERR_CAPTCHA_BLOCKED = "CAPTCHA_BLOCKED"
ERR_NETWORK_ERROR = "NETWORK_ERROR"
ERR_NO_VIDEOS_FOUND = "NO_VIDEOS_FOUND"
ERR_PLAYWRIGHT_FAILED = "PLAYWRIGHT_FAILED"


def cleanup_temp_folder(max_age_hours=24):
    """Scans the temp_processing folder and deletes files older than max_age_hours."""
    log.info(f"Running garbage collection on {TEMP_PROCESSING_DIR}...")
    now = time.time()
    deleted_count = 0

    for filename in os.listdir(TEMP_PROCESSING_DIR):
        file_path = os.path.join(TEMP_PROCESSING_DIR, filename)
        if os.path.isfile(file_path):
            file_age_seconds = now - os.path.getmtime(file_path)
            if file_age_seconds > (max_age_hours * 3600):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    log.debug(f"Deleted old file: {filename}")
                except Exception as e:
                    log.error(f"Failed to delete {filename}: {e}")

    log.info(f"Garbage collection finished. Deleted {deleted_count} old files.")


from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


def download_video_file(url, video_id, page):
    """Downloads the raw mp4 video to the temp folder via playwright api route."""
    file_path = os.path.join(TEMP_PROCESSING_DIR, f"{video_id}.mp4")

    try:
        response = page.request.get(url, headers={
            "Referer": "https://www.tiktok.com/"
        })
        if response.status == 200:
            with open(file_path, 'wb') as f:
                f.write(response.body())
            return file_path
        else:
            log.warning(f"Failed to download MP4 for {video_id}. Status: {response.status}")
            return None
    except Exception as e:
        log.error(f"Playwright download exception for {video_id}: {e}")
        return None


def download_profile_videos(profile_url, max_downloads=MAX_VIDEOS_PER_PROFILE):
    """
    Downloads the latest videos from a TikTok profile using Playwright.
    Returns: (creator_username, creator_nickname, error_code, error_message)
    """
    profile_url = profile_url.strip().rstrip('/')

    # Handle bare usernames: "mrbeast" or "@mrbeast"
    if 'tiktok.com' not in profile_url:
        username = profile_url.lstrip('@')
        profile_url = f"https://www.tiktok.com/@{username}"
    elif '@' not in profile_url and 'tiktok.com/' in profile_url:
        username = profile_url.split('/')[-1]
        profile_url = f"https://www.tiktok.com/@{username}"

    target_username = profile_url.split('@')[-1].split('/')[0].split('?')[0]
    log.info(f"Starting scrape for {profile_url} (max {max_downloads} videos)")

    # --- Pre-flight: Check cookies ---
    cookies = cookie_manager.read_netscape()
    if not cookies:
        log.warning(f"No cookies found at {cookie_manager.get_path()}. Scraping anonymously (likely to fail).")
    else:
        log.info(f"Loaded {len(cookies)} cookies from {cookie_manager.get_path()}")

    # --- Pre-scrape cleanup ---
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM videos WHERE creator_name = ? AND transcript IS NULL", (target_username,))
            pending_files = cursor.fetchall()
            for (fpath,) in pending_files:
                if fpath and os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
            cursor.execute("DELETE FROM videos WHERE creator_name = ? AND transcript IS NULL", (target_username,))
            conn.commit()
    except Exception as e:
        log.warning(f"Pre-scrape cleanup error (non-fatal): {e}")

    extracted_count = 0
    found_videos = []

    try:
        with Stealth().use_sync(sync_playwright()) as p:
            import platform
            channel = "msedge" if platform.system() == "Windows" else "chrome"
            
            try:
                browser = p.chromium.launch(headless=False, channel=channel)
                log.info(f"Launched system browser: {channel}")
            except Exception as e:
                log.warning(f"System browser '{channel}' not found ({e}). Falling back to bundled chromium.")
                try:
                    browser = p.chromium.launch(headless=False)
                    log.info("Launched bundled Chromium.")
                except Exception as e2:
                    log.error(f"CRITICAL: Cannot launch any browser: {e2}")
                    return target_username, None, ERR_BROWSER_MISSING, str(e2)

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Load cookies into context
            if cookies:
                context.add_cookies(cookies)

            page = context.new_page()
            creator_nickname = None

            def handle_response(response):
                nonlocal creator_nickname
                if "item_list" in response.url or "post/item_list" in response.url or "api/post" in response.url:
                    log.debug(f"INTERCEPTED API: {response.url} (status={response.status})")
                    try:
                        data = response.json()
                        itemList = data.get('itemList', [])
                        if not itemList:
                            itemList = data.get('data', {}).get('videos', [])

                        if itemList:
                            log.info(f"Found {len(itemList)} videos in API chunk.")
                            for item in itemList:
                                found_videos.append(item)
                                if not creator_nickname:
                                    author = item.get('author', {})
                                    creator_nickname = author.get('nickname')
                        else:
                            log.debug(f"API chunk empty. Keys: {list(data.keys())}")
                    except Exception as e:
                        log.debug(f"Failed to parse API JSON: {e}")

            page.on("response", handle_response)

            log.info("Navigating to profile to intercept API...")
            try:
                page.goto(profile_url, timeout=60000)
                log.info(f"Navigation complete. URL: {page.url}")
                page.wait_for_timeout(5000)

                # Check for blocks
                if "verify-login" in page.url or "captcha" in page.url:
                    log.error(f"BLOCKED: Captcha or login wall detected. URL: {page.url}")
                    browser.close()
                    return target_username, None, ERR_CAPTCHA_BLOCKED, f"Blocked at {page.url}"

                if "notfound" in page.url or "/404" in page.url:
                    log.error(f"Profile not found: {page.url}")
                    browser.close()
                    return target_username, None, ERR_NETWORK_ERROR, "Profile not found"

                # FALLBACK: __NEXT_DATA__ extraction
                if not found_videos:
                    log.info("No videos intercepted. Attempting __NEXT_DATA__ extraction...")
                    try:
                        script_content = page.evaluate("() => document.getElementById('__NEXT_DATA__')?.textContent")
                        if script_content:
                            log.debug("__NEXT_DATA__ script found.")
                            next_data = json.loads(script_content)
                            props = next_data.get('props', {}).get('pageProps', {})
                            itemList = props.get('itemList', [])
                            if itemList:
                                log.info(f"Extracted {len(itemList)} videos from __NEXT_DATA__")
                                for item in itemList:
                                    found_videos.append(item)
                                    if not creator_nickname:
                                        creator_nickname = item.get('author', {}).get('nickname')
                    except Exception as e:
                        log.debug(f"__NEXT_DATA__ extraction failed: {e}")

                # Scroll to trigger pagination
                last_count = 0
                stale_scrolls = 0
                while len(found_videos) < max_downloads and stale_scrolls < 5:
                    import config
                    if getattr(config, 'CANCEL_REQUESTED', False):
                        log.info("Scraping cancelled by user during scroll.")
                        break

                    page.evaluate("window.scrollBy(0, 1500)")
                    page.wait_for_timeout(2000)

                    if len(found_videos) == last_count:
                        stale_scrolls += 1
                        log.debug(f"No new videos ({last_count} total). Stale scroll {stale_scrolls}/5")
                    else:
                        stale_scrolls = 0
                        last_count = len(found_videos)
                        log.info(f"Intercepted {last_count} videos so far...")

            except Exception as e:
                log.error(f"Error navigating profile: {e}")

            log.info(f"Intercepted {len(found_videos)} video metadata chunks total.")

            # Deduplicate
            unique_videos = {}
            for v in found_videos:
                vid = v.get('id')
                if vid and vid not in unique_videos:
                    unique_videos[vid] = v

            video_list = list(unique_videos.values())

            # Download
            for count, item in enumerate(video_list[:max_downloads]):
                import config
                if getattr(config, 'CANCEL_REQUESTED', False):
                    log.info("Scraping cancelled by user during download.")
                    break

                video_id = item.get('id')
                if not video_id:
                    continue

                video_url = item.get('video', {}).get('playAddr') or item.get('video', {}).get('downloadAddr')
                if not video_url:
                    log.debug(f"Skipping {video_id}: No mp4 URL found.")
                    continue

                upload_date = item.get('createTime', 0)
                from datetime import datetime
                if upload_date:
                    upload_date = datetime.fromtimestamp(upload_date).strftime('%Y%m%d')
                else:
                    upload_date = ""

                description = item.get('desc', '')
                creator_name = item.get('author', {}).get('uniqueId') or target_username

                log.info(f"[{count + 1}/{max_downloads}] Downloading {video_id}...")
                file_path = download_video_file(video_url, video_id, page)

                if file_path:
                    insert_video_metadata(
                        video_id=video_id,
                        upload_date=upload_date,
                        caption=description,
                        creator_name=creator_name,
                        file_path=file_path
                    )
                    extracted_count += 1

            log.info(f"Scrape complete: {extracted_count}/{max_downloads} videos from {profile_url}")

            if extracted_count == 0 and len(found_videos) == 0:
                error_code = ERR_NO_COOKIES if not cookies else ERR_NO_VIDEOS_FOUND
                error_msg = "No cookies available" if not cookies else "API returned no video data"
                return target_username, creator_nickname, error_code, error_msg

            return target_username, creator_nickname, OK, None

    except Exception as e:
        log.error(f"Playwright error during scrape: {e}")
        return target_username, None, ERR_PLAYWRIGHT_FAILED, str(e)
    finally:
        try:
            if 'browser' in locals() and browser:
                browser.close()
            log.info("Playwright session cleaned up.")
        except Exception:
            pass


if __name__ == "__main__":
    import db
    db.init_db()
    cleanup_temp_folder()

    try:
        with open('targets.txt', 'r') as f:
            targets = [url.strip() for url in f.readlines() if url.strip()]

        if not targets:
            log.info("No targets found in targets.txt.")
            sys.exit(0)

        for target in targets:
            download_profile_videos(target)

    except FileNotFoundError:
        log.error("targets.txt not found. Please create it and add TikTok profile URLs.")
