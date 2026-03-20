import sys
import os
import socket
import platform
import subprocess

def log(msg):
    print(f"[DIAGNOSTIC] {msg}")

def test_ports():
    log("Testing Port binding...")
    for port in [8000, 0]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                actual_port = s.getsockname()[1]
                log(f"SUCCESS: Bound to 127.0.0.1:{actual_port}")
        except Exception as e:
            log(f"FAILED: Could not bind to port {port}: {e}")

def test_system_browsers():
    log("Testing System Browser discovery...")
    common_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    found = False
    for path in common_paths:
        if os.path.exists(path):
            log(f"FOUND: Browser at {path}")
            found = True
    if not found:
        log("NOT FOUND: No system browsers detected.")

def test_playwright():
    log("Testing Playwright launch (Headless)...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            log("Playwright driver started.")
            try:
                browser = p.chromium.launch(headless=True)
                log("SUCCESS: Launched Chromium bundle.")
                browser.close()
            except Exception as e:
                log(f"INFO: Chromium bundle launch failed: {e}")
                
            log("Testing Edge channel launch...")
            try:
                browser = p.chromium.launch(headless=True, channel="msedge")
                log("SUCCESS: Launched Microsoft Edge via Playwright.")
                browser.close()
            except Exception as e:
                log(f"INFO: Edge launch failed: {e}")
    except Exception as e:
        log(f"CRITICAL: Playwright driver failed to initialize: {e}")

def test_ffmpeg():
    log("Testing FFmpeg availability...")
    try:
        res = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        log(f"SUCCESS: FFmpeg version info found: {res.stdout.splitlines()[0]}")
    except Exception as e:
        log(f"FAILED: FFmpeg check failed: {e}")

if __name__ == "__main__":
    log(f"Starting Diagnostic Test on {platform.system()} {platform.release()}")
    log(f"Frozen: {getattr(sys, 'frozen', False)}")
    log(f"Executable: {sys.executable}")
    log(f"CWD: {os.getcwd()}")
    print("-" * 40)
    
    test_ports()
    test_system_browsers()
    test_playwright()
    test_ffmpeg()
    
    print("-" * 40)
    log("Diagnostic Complete.")
