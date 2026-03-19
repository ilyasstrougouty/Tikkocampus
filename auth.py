import os
import time
import threading
import webview

COOKIE_OUTPUT = "cookies.txt"

def convert_pywebview_cookies_to_netscape(cookies_list, output_file=COOKIE_OUTPUT):
    """
    Converts PyWebView's SimpleCookie objects into the Netscape HTTP Cookie File format
    required by yt-dlp.
    """
    with open(output_file, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n")
        f.write("# This is a generated file!  Do not edit.\n\n")

        cookie_count = 0
        for cookie_obj in cookies_list:
            for name, morsel in cookie_obj.items():
                domain = morsel.get("domain", "")
                include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
                path = morsel.get("path", "/")
                secure = "TRUE" if morsel.get("secure", False) else "FALSE"
                
                # Morsel expires is usually a string like "Thu, 01 Jan 1970 00:00:00 GMT" or empty.
                # For yt-dlp, if we don't have a strict integer, we can just use 0 (session cookie).
                # To be safe, we'll set it to 0. 
                expires = "0" 
                
                value = morsel.value

                f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
                cookie_count += 1
                
    return cookie_count

def monitor_login(window):
    print("=" * 50)
    print("Authentication Window Opened!")
    print("Please log into TikTok in the window.")
    print("The window will close automatically when you successfully log in.")
    print("=" * 50)
    
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
                if has_session: break
                
            # Check if URL changed away from login (Google OAuth redirects to homepage)
            current_url = window.get_current_url()
            if current_url and "login" not in current_url and "tiktok.com" in current_url:
                print(f"\nLogin redirect detected! Current URL: {current_url}")
                has_session = True
                
            try:
                page_text = window.evaluate_js("document.body.innerText")
                if page_text:
                    p_lower = page_text.lower()
                    if "maximum number of attempts reached" in p_lower or "nombre maximal de tentatives atteint" in p_lower or "too many attempts" in p_lower:
                        print(f"\nMax attempts error detected! Proceeding to extract cookies and redirect.")
                        has_session = True
                        logged_in = True
                        
                        # Wait just a little bit for any last-minute cookies
                        time.sleep(2)
                        
                        final_cookies = window.get_cookies()
                        if final_cookies:
                            count = convert_pywebview_cookies_to_netscape(final_cookies, COOKIE_OUTPUT)
                            print(f"Saved {count} TikTok cookies to {COOKIE_OUTPUT} (Max Attempts Fallback)!")
                        else:
                            print(f"Warning: No cookies could be extracted after max attempts error.")
                        print("Closing window...")
                        window.destroy()
                        os._exit(0)
            except Exception:
                pass
                
            if has_session and not logged_in:
                print("\nLogin success detected! Waiting for cookies to settle...")
                logged_in = True
                
                # Wait longer (5 seconds) to ensure all OAuth cookies are written to the main domain
                time.sleep(5)
                final_cookies = window.get_cookies()
                
                # Filter to only tiktok cookies and save
                if final_cookies:
                    count = convert_pywebview_cookies_to_netscape(final_cookies, COOKIE_OUTPUT)
                    print(f"Saved {count} TikTok cookies to {COOKIE_OUTPUT}!")
                else:
                    print(f"Warning: No cookies could be extracted after login.")
                
                print("Closing window...")
                window.destroy()
                os._exit(0)
        except Exception as e:
            # get_cookies/get_current_url might throw if window is closed by user early
            if "destroyed" not in str(e).lower() and "closed" not in str(e).lower():
                print(f"Polling error: {e}")
            break
            
    if not logged_in:
        print("\nWARNING: Login not completed within 5 minutes or window closed.")
        
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
            // Google's "One moment please" often happens when the opener-child relationship is broken.
            // We use a slight delay or try to maintain the relationship if possible.
            const originalOpen = window.open;
            window.open = function(url, name, specs) {
                console.log("Attempting to open: " + url);
                if (url && (url.includes('google.com') || url.includes('facebook.com') || url.includes('apple.com'))) {
                    // For OAuth providers, we MUST redirect in the same window because 
                    // pywebview struggles with multi-window session sharing.
                    window.location.href = url;
                    return null;
                }
                return originalOpen(url, name, specs);
            };

            // 5. Intercept target='_blank' links
            document.addEventListener('click', function(e) {
                let target = e.target.closest('a');
                if (target && target.getAttribute('target') === '_blank') {
                    // Only intercept if it's not a download or something specific
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
        print(f"JS Injection failed: {e}")

def run_login_flow():
    """
    Opens a native PyWebView (Edge WebView2) window to TikTok login.
    User logs in manually, we detect the sessionid cookie, and save cookies.txt.
    This bypasses all Playwright bot-detection because it's a real OS browser component.
    """
    # Create the window
    window = webview.create_window(
        'TikTok Authentication (Please Log In)', 
        'https://www.tiktok.com/login',
        width=1000, 
        height=800
    )
    
    # Attach the JS injection to ensure popups stay in this window
    window.events.loaded += lambda: on_loaded(window)
    
    # Start the monitoring thread
    t = threading.Thread(target=monitor_login, args=(window,))
    t.daemon = True
    t.start()
    
    # Start the webview loop (blocks until window is destroyed)
    # Using private_mode=True gives us a fresh browser context every time, bypassing device IP/fingerprint blocks
    webview.start(private_mode=True)

if __name__ == "__main__":
    run_login_flow()
