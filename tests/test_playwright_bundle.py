import sys
import subprocess
import os

def install_playwright_if_needed():
    print("Checking Playwright dependencies...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                # Try to launch headless to verify existence
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("Playwright Chromium is already installed.")
            except Exception as e:
                if "Executable doesn't exist" in str(e) or "not found" in str(e):
                    print("Playwright Chromium missing. Starting automatic installation...")
                    # In a frozen bundle, sys.executable is the .exe
                    # We can use it to run the playwright module installer
                    env = os.environ.copy()
                    # Optional: Set custom storage path to keep it local to the app
                    # env["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), "browsers")
                    
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                                   env=env, check=True)
                    print("Playwright Chromium installed successfully!")
                else:
                    print(f"Unexpected Playwright error: {e}")
                    raise
    except ImportError:
        print("Playwright module not found in environment.")

if __name__ == "__main__":
    install_playwright_if_needed()
