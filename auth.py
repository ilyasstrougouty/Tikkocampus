import os
import time
from logger import get_logger
import cookie_manager
from scraper import _launch_best_browser
from playwright.sync_api import sync_playwright

log = get_logger("auth")

def run_login_flow():
    """
    Opens a native Playwright browser window to TikTok login.
    User logs in manually (including Google/Apple OAuth), we detect the sessionid cookie, and save cookies natively.
    """
    log.info("=" * 50)
    log.info("Authentication Browser Opened!")
    log.info("Please log into TikTok in the new Chrome/Edge window.")
    log.info("The window will close automatically when you successfully log in.")
    log.info("=" * 50)

    try:
        with sync_playwright() as p:
            # Replicating optimal browser detection but injecting Google OAuth bypass args
            import platform
            exe_path = None
            if platform.system() == "Windows":
                for p_path in [
                    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
                    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                    r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
                ]:
                    expanded = os.path.expandvars(p_path)
                    if os.path.exists(expanded):
                        exe_path = expanded
                        break

            # Crucial: Ignore default automation arguments to avoid Google's "Couldn't sign you in" block
            launch_args = {
                "headless": False,
                "args": ["--disable-blink-features=AutomationControlled"],
                "ignore_default_args": ["--enable-automation"]
            }
            if exe_path:
                launch_args["executable_path"] = exe_path

            browser = p.chromium.launch(**launch_args)

            if not browser:
                log.error("CRITICAL: Failed to launch Chromium strictly for authentication.")
                os._exit(1)

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            # Mask Webdriver fingerprint
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            page = context.new_page()
            
            # Apply playwright stealth
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except ImportError:
                log.warning("playwright-stealth not installed, trying to proceed without full stealth.")
            
            try:
                page.goto("https://www.tiktok.com/login", timeout=60000)
            except Exception as e:
                log.error(f"Error navigating to login page: {e}")

            logged_in = False

            # Poll for cookies up to 5 minutes (600 * 0.5s = 300s)
            for _ in range(600):
                time.sleep(0.5)
                
                try:
                    if not browser.is_connected() or not context.pages:
                        log.info("Browser or page closed early by user.")
                        break

                    cookies = context.cookies()
                    if not cookies:
                        continue

                    has_session = False
                    for c in cookies:
                        if c.get("name") == "sessionid" and c.get("value"):
                            has_session = True
                            break

                    # Fallback 1: Check if URL changed away from login (Google OAuth redirects to homepage)
                    current_url = page.url
                    if current_url and "login" not in current_url and "tiktok.com" in current_url:
                        log.info(f"Login redirect detected! Current URL: {current_url}")
                        has_session = True

                    # Fallback 2: Check for Maximum Attempts Error
                    try:
                        page_text = page.locator("body").inner_text()
                        if page_text:
                            p_lower = page_text.lower()
                            if "maximum number of attempts reached" in p_lower or "nombre maximal" in p_lower or "too many attempts" in p_lower:
                                log.info("Max attempts error detected! Proceeding to extract cookies and redirect.")
                                has_session = True
                    except Exception:
                        pass

                    if has_session:
                        log.info("Login success detected! Waiting for cookies to settle...")
                        logged_in = True
                        
                        # Wait slightly to ensure all OAuth side-cookies write
                        time.sleep(1)
                        final_cookies = context.cookies()
                        
                        count = cookie_manager.write_netscape(final_cookies, source="playwright-auth")
                        log.info(f"Saved {count} cookies to {cookie_manager.get_path()}")
                        
                        break

                except Exception as e:
                    if "Target page, context or browser has been closed" not in str(e):
                        log.error(f"Polling error: {e}")
                    break
                    
            if not logged_in:
                log.warning("Login not completed within 5 minutes or window closed.")
                
            browser.close()
            os._exit(0)
            
    except Exception as e:
        log.error(f"Failed to launch authentication window: {e}")
        os._exit(1)

if __name__ == "__main__":
    run_login_flow()
