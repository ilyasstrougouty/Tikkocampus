import webview
import threading
import time
import sys
import os

def test_cookies(window):
    print("\n[STEP 2] Window loaded. Navigating to Google to test cookie extraction...")
    time.sleep(5)
    try:
        cookies = window.get_cookies()
        if not cookies:
            print("[-] RESULT: No cookies found. Potential causes:")
            print("    1. WebView2 version is too old.")
            print("    2. 'private_mode=True' is preventing access on this PC.")
            print("    3. Security software is blocking the embedded browser.")
        else:
            print(f"[+] RESULT: Successfully extracted {len(cookies)} cookies!")
            for i, c in enumerate(cookies[:5]):
                # SimpleCookie structure
                for name, morsel in c.items():
                    print(f"    - Found cookie: {name} (Value length: {len(morsel.value)})")
    except Exception as e:
        print(f"[-] RESULT: Error getting cookies: {e}")
    
    print("\nDiagnostic complete. You can close the window now.")

def run_diagnostic():
    print("==========================================")
    print("   Tikkocampus Login Diagnostic Tool")
    print("==========================================")
    print(f"OS: {sys.platform}")
    print(f"Python: {sys.version.split()[0]}")
    
    print("\n[STEP 1] Testing PyWebView (WebView2) launch...")
    
    try:
        # Create a window to a simple site
        window = webview.create_window(
            'Tikkocampus Diagnostic (Google Test)',
            'https://www.google.com',
            width=1000,
            height=800
        )
        
        # Start monitoring thread
        t = threading.Thread(target=test_cookies, args=(window,))
        t.daemon = True
        t.start()
        
        # Start the GUI
        # If this fails, it's usually a missing WebView2 runtime on Windows
        webview.start(private_mode=True)
        
    except Exception as e:
        print(f"\n[-] CRITICAL ERROR: Failed to even open the window.")
        print(f"    Details: {e}")
        if "WebView2" in str(e) or "DLL" in str(e):
            print("\n[!] CAUSE: The WebView2 Runtime is likely missing or corrupted on this PC.")
            print("    Fix: Download the 'Evergreen Bootstrapper' from Microsoft's WebView2 page.")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
