import requests
import json

def test_tikwm():
    # Attempt to get user info or user videos
    # TikWM API allows fetching videos if we have the unique_id
    url = "https://tikwm.com/api/user/posts"
    params = {
        "unique_id": "@anass0x0",
        "count": 10,
        "cursor": 0
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, params=params, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Response received!")
        if data.get('code') == 0:
            videos = data.get('data', {}).get('videos', [])
            print(f"Success! Found {len(videos)} videos.")
            if videos:
                v = videos[0]
                print(f"Sample Video metadata - ID: {v.get('video_id')}, Title: {v.get('title')}, URL: {v.get('play')}")
        else:
            print(f"API Error: {data.get('msg')}")

if __name__ == "__main__":
    test_tikwm()
