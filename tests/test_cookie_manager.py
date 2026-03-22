import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.cookies import SimpleCookie
import cookie_manager

def test_cookie_write():
    # Simulate pywebview's get_cookies() return value
    # Pywebview returns a list of SimpleCookie objects.
    # A single SimpleCookie object contains multiple Morsels.
    c = SimpleCookie()
    c["sessionid"] = "123456789"
    c["sessionid"]["domain"] = ".tiktok.com"
    c["sessionid"]["path"] = "/"
    c["sessionid"]["secure"] = True

    c2 = SimpleCookie()
    c2["tt_webid_v2"] = "abcdef"
    c2["tt_webid_v2"]["domain"] = "www.tiktok.com"
    c2["tt_webid_v2"]["path"] = "/"

    # Mock the COOKIE_FILE path to a test file
    cookie_manager.COOKIE_FILE = "test_cookies_output.txt"
    
    count = cookie_manager.write_netscape([c, c2], source="test")
    print(f"Wrote {count} cookies")

def test_cookie_write_dict():
    # Simulate Playwright context.cookies() format
    dict_cookies = [
        {
            "name": "sessionid",
            "value": "playwright_session_123",
            "domain": ".tiktok.com",
            "path": "/",
            "expires": 1700000000,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        },
        {
            "name": "tt_webid_v2",
            "value": "playwright_webid",
            "domain": "www.tiktok.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax"
        }
    ]

    # Mock the COOKIE_FILE path to a test file
    cookie_manager.COOKIE_FILE = "test_playwright_cookies.txt"
    count = cookie_manager.write_netscape(dict_cookies, source="test-playwright")
    print(f"Wrote {count} Playwright cookies:")
    with open("test_playwright_cookies.txt", "r") as f:
        print(f.read())

if __name__ == "__main__":
    test_cookie_write()
    test_cookie_write_dict()
