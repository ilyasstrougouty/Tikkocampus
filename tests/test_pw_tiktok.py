import asyncio
from playwright.async_api import async_playwright
import json

def parse_netscape_cookies(filename):
    cookies = []
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

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Load cookies
        cookies = parse_netscape_cookies('cookies.txt')
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        # Intercept network responses
        found_videos = []
        async def handle_response(response):
            if "item_list" in response.url or "post/item_list" in response.url:
                try:
                    data = await response.json()
                    itemList = data.get('itemList', [])
                    print(f"Intercepted API! Found {len(itemList)} videos.")
                    for item in itemList:
                        # Extract video URL and metadata
                        video_url = item.get('video', {}).get('playAddr') or item.get('video', {}).get('downloadAddr')
                        if video_url:
                            found_videos.append(video_url)
                except Exception as e:
                    print(f"Error parsing API response: {e}")

        page.on("response", handle_response)
        
        print("Navigating to TikTok...")
        await page.goto("https://www.tiktok.com/@anass0x0")
        await page.wait_for_timeout(5000)
        
        # Scroll down a few times to trigger API calls
        for _ in range(3):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(2000)
            
        print(f"Total intercepted videos: {len(found_videos)}")
        if found_videos:
            print(f"Sample video URL: {found_videos[0][:100]}...")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
