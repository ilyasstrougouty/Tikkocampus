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
    
    # Session-indicating cookie names
    SESSION_COOKIES = [
        "sessionid", 
        "sessionid_ss", 
        "sid_guard", 
        "sid_tt", 
        "uid_tt", 
        "msToken",
        "tt_chain_token"
    ]

    # Poll for cookies up to 5 minutes
    for i in range(150):
        time.sleep(2)
        try:
            # Check for manual success signal from JS
            try:
                manual_success = window.evaluate_js("window._manual_login_success === true")
                if manual_success:
                    log.info("Manual login success signal received!")
                    logged_in = True
            except:
                pass

            cookies = window.get_cookies()
            if not cookies:
                continue

            has_session = False
            for c in cookies:
                # pywebview returns a list of SimpleCookie objects
                for name, morsel in c.items():
                    if name in SESSION_COOKIES and morsel.value:
                        log.info(f"Found session cookie: {name} (Value length: {len(morsel.value)})")
                        has_session = True
                        break
                if has_session:
                    break

            # Fallback 1: URL Redirect logic
            current_url = window.get_current_url()
            if current_url and "login" not in current_url and ("tiktok.com/foryou" in current_url or "tiktok.com/@" in current_url):
                log.info(f"Login redirect detected to content page! Current URL: {current_url}")
                has_session = True

            # Fallback 2: DOM-based check (looking for profile avatar or logout)
            if not has_session:
                try:
                    is_logged_in_dom = window.evaluate_js("""
                        (function() {
                            // Check for profile icon, logout button, or 'upload' button
                            return !!(
                                document.querySelector('[data-e2e="profile-icon"]') || 
                                document.querySelector('a[href*="/logout"]') ||
                                document.querySelector('a[href*="/@"]') ||
                                document.body.innerText.includes('Logout') ||
                                document.body.innerText.includes('Déconnexion')
                            );
                        })()
                    """)
                    if is_logged_in_dom:
                        log.info("Login detected via Page DOM elements!")
                        has_session = True
                except:
                    pass

            # Fallback 3: Max attempts error detection
            try:
                page_text = window.evaluate_js("document.body.innerText")
                if page_text:
                    p_lower = page_text.lower()
                    if "maximum number of attempts reached" in p_lower or "nombre maximal de tentatives atteint" in p_lower or "too many attempts" in p_lower:
                        log.info("Max attempts error detected! Proceeding to extract available cookies.")
                        has_session = True
                        logged_in = True
            except:
                pass

            if (has_session or logged_in) and not logged_in:
                log.info("Login success detected! Waiting for cookies to settle...")
                logged_in = True
                time.sleep(5) # Give it 5 seconds to finish all redirects and storage writes

            if logged_in:
                final_cookies = window.get_cookies()
                if final_cookies:
                    count = cookie_manager.write_netscape(final_cookies, source="login-flow")
                    log.info(f"Saved {count} cookies to {cookie_manager.get_path()}")
                else:
                    log.warning("Final cookie extraction returned empty list!")

                log.info("Closing window...")
                window.destroy()
                os._exit(0)
                
        except Exception as e:
            if "destroyed" not in str(e).lower() and "closed" not in str(e).lower():
                log.error(f"Polling error (attempt {i}): {e}")
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
            } catch (e) {}

            // 2. Mock Chrome properties
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };

            // 3. Realistic Browser Properties
            const newUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";
            Object.defineProperty(navigator, 'userAgent', { get: () => newUserAgent });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            
            // 4. Improved window.open handling (Keep OAuth in same window)
            const originalOpen = window.open;
            window.open = function(url, name, specs) {
                if (url && (url.includes('google.com') || url.includes('facebook.com') || url.includes('apple.com') || url.includes('twitter.com'))) {
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

            // 6. Manual Fallback Button (Only on TikTok pages)
            if (window.location.href.includes('tiktok.com')) {
                const btn = document.createElement('div');
                btn.innerHTML = "I'm Logged In (Failsafe)";
                btn.style.position = 'fixed';
                btn.style.top = '10px';
                btn.style.right = '70px';
                btn.style.zIndex = '999999';
                btn.style.padding = '8px 16px';
                btn.style.background = '#fe2c55';
                btn.style.color = 'white';
                btn.style.borderRadius = '20px';
                btn.style.cursor = 'pointer';
                btn.style.fontWeight = 'bold';
                btn.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
                btn.style.fontSize = '12px';
                btn.onclick = function() {
                    window._manual_login_success = true;
                    btn.innerHTML = "Processing...";
                    btn.style.background = '#25f4ee';
                };
                document.body.appendChild(btn);
            }

            console.log("Stealth + Manual Fallback initialized");
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
    # Removed private_mode=True to ensure more consistent cookie behavior across Windows machines.
    # WebView2 in non-private mode is generally more reliable for HttpOnly cookie extraction via API.
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

    webview.start()


if __name__ == "__main__":
    run_login_flow()
