import os
from config import TEMP_PROCESSING_DIR, MAX_VIDEOS_PER_PROFILE
from db import insert_video_metadata, db_session

def cleanup_temp_folder(max_age_hours=24):
    """
    Scans the temp_processing folder and deletes files older than max_age_hours.
    """
    print(f"Running garbage collection on {TEMP_PROCESSING_DIR}...")
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
                    print(f"Deleted old file: {filename}")
                except Exception as e:
                    print(f"Failed to delete {filename}: {e}", file=sys.stderr)
                    
    print(f"Garbage collection finished. Deleted {deleted_count} old files.")

import json
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def parse_netscape_cookies(filename):
    cookies = []
    if not os.path.exists(filename):
        return cookies
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookies.append({
                    'name': parts[5],
                    'value': parts[6],
                    'domain': parts[0],
                    'path': parts[2],
                    'secure': parts[3] == 'TRUE',
                    'expires': float(parts[4]) if parts[4] != '0' else -1
                })
    return cookies

def download_video_file(url, video_id, page):
    """Downloads the raw mp4 video to the temp folder via playwright api route to reuse signatures"""
    file_path = os.path.join(TEMP_PROCESSING_DIR, f"{video_id}.mp4")
    
    # Use playwright context to ensure cookies, stealth configs, and headers map
    try:
        response = page.request.get(url, headers={
            "Referer": "https://www.tiktok.com/"
        })
        if response.status == 200:
            with open(file_path, 'wb') as f:
                f.write(response.body())
            return file_path
        else:
            print(f"Failed to download MP4. Status code: {response.status}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Playwright download exception: {e}", file=sys.stderr)
        return None

def download_profile_videos(profile_url, max_downloads=MAX_VIDEOS_PER_PROFILE):
    """
    Downloads the latest videos from a TikTok profile using Playwright.
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
    print(f"Starting Playwright download for {profile_url} (Max {max_downloads} videos)")

    # CLEANUP: Remove any existing PENDING videos for this specific creator 
    # to ensure they don't get mixed in with the new requested batch.
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            
            # We only delete the ones WITHOUT a transcript (ghosts of previous failed scrapes)
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
        print(f"Pre-scrape cleanup error (non-fatal): {e}")

    extracted_count = 0
    found_videos = []
    
    try:
        with Stealth().use_sync(sync_playwright()) as p:
            browser = p.chromium.launch(headless=False)
            # Use a realistic user agent to avoid basic blocks
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Load the authenticated cookies from the native login window
            cookies = parse_netscape_cookies('cookies.txt')
            if not cookies:
                print("Warning: No cookies found or could not parse cookies.txt. Trying anonymously.")
            else:
                context.add_cookies(cookies)

            page = context.new_page()

            creator_nickname = None

            def handle_response(response):
                nonlocal creator_nickname
                if "item_list" in response.url or "post/item_list" in response.url:
                    try:
                        data = response.json()
                        itemList = data.get('itemList', [])
                        for item in itemList:
                            found_videos.append(item)
                            if not creator_nickname:
                                author = item.get('author', {})
                                creator_nickname = author.get('nickname')
                    except Exception as e:
                        pass # Silently fail chunk parses to avoid unhandled exception crashes in bg thread

            page.on("response", handle_response)
            
            print("Navigating to profile to intercept API...")
            try:
                page.goto(profile_url, timeout=60000)
                page.wait_for_timeout(3000)
                
                # Check for "Too many attempts" or basic blocks
                if "verify-login" in page.url or "captcha" in page.url:
                    print("TikTok CAPTCHA or Login wall detected. Falling back to cookies-only scraping.")

                # Scroll to trigger pagination if needed
                last_count = 0
                stale_scrolls = 0
                while len(found_videos) < max_downloads and stale_scrolls < 5:
                    page.keyboard.press("PageDown")
                    page.wait_for_timeout(1500)
                    
                    if len(found_videos) == last_count:
                        stale_scrolls += 1
                        print(f"No new videos found ({last_count} total). Scrolling again... ({stale_scrolls}/5)")
                    else:
                        stale_scrolls = 0
                        last_count = len(found_videos)
                        print(f"Intercepted {last_count} videos so far...")
                        
            except Exception as e:
                print(f"Error navigating the profile: {e}", file=sys.stderr)
                
            print(f"Intercepted {len(found_videos)} video metadata chunks from API.")

            # Deduplicate videos by ID
            unique_videos = {}
            for v in found_videos:
                vid = v.get('id')
                if vid and vid not in unique_videos:
                    unique_videos[vid] = v

            video_list = list(unique_videos.values())
            
            # Process up to max_downloads
            for count, item in enumerate(video_list[:max_downloads]):
                video_id = item.get('id')
                if not video_id:
                    continue
                    
                # Get best quality mp4 url
                video_url = item.get('video', {}).get('playAddr') or item.get('video', {}).get('downloadAddr')
                if not video_url:
                    print(f"Skipping {video_id}: No mp4 URL found.")
                    continue
                    
                upload_date = item.get('createTime', 0)
                # Convert timestamp to YYYYMMDD string for db matching old yt-dlp format
                from datetime import datetime
                if upload_date:
                    upload_date = datetime.fromtimestamp(upload_date).strftime('%Y%m%d')
                else:
                    upload_date = ""
                    
                description = item.get('desc', '')
                creator_name = item.get('author', {}).get('uniqueId') or target_username
                
                print(f"[{count+1}/{max_downloads}] Downloading mp4 for {video_id}...")
                file_path = download_video_file(video_url, video_id, page)
                
                if file_path:
                    print(f"Saving database metadata for video {video_id}")
                    insert_video_metadata(
                        video_id=video_id,
                        upload_date=upload_date,
                        caption=description,
                        creator_name=creator_name,
                        file_path=file_path
                    )
                    extracted_count += 1
                    
            print(f"Successfully processed profile: {profile_url} (Extracted {extracted_count} videos)")
            if extracted_count < max_downloads:
                print(f"\nWarning: Scrape ended early. Only extracted {extracted_count} of {max_downloads} videos.", file=sys.stderr)
                
            browser.close()
            return target_username, creator_nickname
    except Exception as e:
        print(f"Playwright initialization error: {e}", file=sys.stderr)
        return target_username, None

    # The parsing logic has been moved up into the browser context block

if __name__ == "__main__":
    import db
    db.init_db() # Ensure DB exists
    cleanup_temp_folder() # Garbage collection
    
    try:
        with open('targets.txt', 'r') as f:
            targets = [url.strip() for url in f.readlines() if url.strip()]
            
        if not targets:
            print("No targets found in targets.txt.")
            sys.exit(0)

        for target in targets:
            download_profile_videos(target)
            
    except FileNotFoundError:
        print("targets.txt not found. Please create it and add TikTok profile URLs.")
