# TikTok RAG Pipeline

This project implements a robust scraper and data ingestion pipeline for TikTok profiles using `yt-dlp` and `SQLite`.

## Quick Start

### 🚨 IMPORTANT: Browser Cookies Required 🚨
TikTok heavily restricts unauthenticated scrape scraping. To pull more than the first ~5 videos off a profile, **you MUST provide a logged-in TikTok session.**

We rely on a `cookies.txt` file to authenticate `yt-dlp` instead of attempting automated browser extraction, which often fails or gets locked by the OS.

1. Download the **"Get cookies.txt LOCALLY"** extension for your browser (Chrome/Firefox/Edge).
2. Go to [tiktok.com](https://www.tiktok.com/) and ensure you are logged in.
3. Click the extension and export your cookies.
4. Save the downloaded file as exactly `cookies.txt` into the root of this project folder (the same directory as `scraper.py`).

### Setup
1. Clone the repository.
2. Create targeted profiles list: Add TikTok profile URLs to `targets.txt`, one url per line.
   ```text
   https://www.tiktok.com/@tiktok
   ```
3. Initialize the environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Run the scraper:
   ```bash
   python scraper.py
   ```

## Server Deployments
If you are deploying this to Docker or a server, ensure the `cookies.txt` file is mounted into the container or uploaded to the server directory alongside the code.

## Features
- **Rate Limiting**: Built-in randomized 5-15 second delays to prevent IP bans.
- **Garbage Collection**: Automatically cleans up media files older than 24 hours in `/temp_processing` to prevent disk bloat.
- **SQLite Persistence**: Saves all metadata (`video_id`, `upload_date`, `caption`, `creator`) into a lightweight local DB for downstream RAG processing.
