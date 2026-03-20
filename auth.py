import os
import time
import threading
import webview
import cookie_manager
from logger import get_logger

log = get_logger("auth")


def monitor_login(window):
    log.info("=" * 50)
    log.info("Authentication Window Opened!")
    log.info("Please log into TikTok in the window.")
    log.info("The window will close automatically when you successfully log in.")
    log.info("=" * 50)

    logged_in = False

    # Poll for cookies up to 5 minutes
    for _ in range(150):
        time.sleep(2)
        try:
            cookies = window.get_cookies()
            if not cookies:
                continue

            has_session = False
            for c in cookies:
                for name, morsel in c.items():
                    if name == "sessionid" and morsel.value:
                        has_session = True
                        break
                if has_session:
                    break

            # Check if URL changed away from login (Google OAuth redirects to homepage)
            current_url = window.get_current_url()
            if current_url and "login" not in current_url and "tiktok.com" in current_url:
                log.info(f"Login redirect detected! Current URL: {current_url}")
                has_session = True

            try:
                page_text = window.evaluate_js("document.body.innerText")
                if page_text:
                    p_lower = page_text.lower()
                    if "maximum number of attempts reached" in p_lower or "nombre maximal de tentatives atteint" in p_lower or "too many attempts" in p_lower:
                        log.info("Max attempts error detected! Proceeding to extract cookies and redirect.")
                        has_session = True
                        logged_in = True

                        time.sleep(2)

                        final_cookies = window.get_cookies()
                        if final_cookies:
                            count = cookie_manager.write_netscape(final_cookies, source="max-attempts-fallback")
                            log.info(f"Saved {count} cookies to {cookie_manager.get_path()} (Max Attempts Fallback)")
                        else:
                            log.warning("No cookies could be extracted after max attempts error.")
                        log.info("Closing window...")
                        window.destroy()
                        os._exit(0)
            except Exception:
                pass

            if has_session and not logged_in:
                log.info("Login success detected! Waiting for cookies to settle...")
                logged_in = True

                # Wait longer (5 seconds) to ensure all OAuth cookies are written
                time.sleep(5)
                final_cookies = window.get_cookies()

                if final_cookies:
                    count = cookie_manager.write_netscape(final_cookies, source="login-flow")
                    log.info(f"Saved {count} cookies to {cookie_manager.get_path()}")
                else:
                    log.warning("No cookies could be extracted after login.")

                log.info("Closing window...")
                window.destroy()
                os._exit(0)
        except Exception as e:
            if "destroyed" not in str(e).lower() and "closed" not in str(e).lower():
                log.error(f"Polling error: {e}")
            break

    if not logged_in:
        log.warning("Login not completed within 5 minutes or window closed.")

    window.destroy()
    os._exit(0)


def on_loaded(window):
    """
    Inject JS into every page load to bypass bot detection and trap popups.
    """
    js = """
        (function() {
            // 1. Mask webdriver safely
            try {
                if (Object.getOwnPropertyDescriptor(navigator, 'webdriver')) {
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                }
            } catch (e) {
                console.warn("Could not mask webdriver:", e);
            }

            // 2. Mock Chrome properties more fully
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // 3. Realistic Browser Properties
            const newUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";
            Object.defineProperty(navigator, 'userAgent', { get: () => newUserAgent });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            
            // Mock plugins to look less like a headless/embedded browser
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

            // 4. Improved window.open handling
            const originalOpen = window.open;
            window.open = function(url, name, specs) {
                console.log("Attempting to open: " + url);
                if (url && (url.includes('google.com') || url.includes('facebook.com') || url.includes('apple.com'))) {
                    window.location.href = url;
                    return null;
                }
                return originalOpen(url, name, specs);
            };

            // 5. Intercept target='_blank' links
            document.addEventListener('click', function(e) {
                let target = e.target.closest('a');
                if (target && target.getAttribute('target') === '_blank') {
                    if (target.href && !target.href.startsWith('javascript:')) {
                        e.preventDefault();
                        window.location.href = target.href;
                    }
                }
            }, true);

            console.log("Advanced Stealth initialized");
        })();
    """
    try:
        window.evaluate_js(js)
    except Exception as e:
        log.error(f"JS Injection failed: {e}")


def run_login_flow():
    """
    Opens a native PyWebView (Edge WebView2) window to TikTok login.
    User logs in manually, we detect the sessionid cookie, and save cookies.
    """
    window = webview.create_window(
        'TikTok Authentication (Please Log In)',
        'https://www.tiktok.com/login',
        width=1000,
        height=800
    )

    window.events.loaded += lambda: on_loaded(window)

    t = threading.Thread(target=monitor_login, args=(window,))
    t.daemon = True
    t.start()

    webview.start(private_mode=True)


if __name__ == "__main__":
    run_login_flow()
