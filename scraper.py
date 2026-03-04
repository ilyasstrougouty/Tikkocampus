import sys
import os
import time
import yt_dlp
from config import TEMP_PROCESSING_DIR, MAX_VIDEOS_PER_PROFILE
from db import insert_video_metadata

def cleanup_temp_folder(max_age_hours=24):
    """
    Scans the temp_processing folder and deletes files older than max_age_hours.
    """
    print(f"Running garbage collection on {TEMP_PROCESSING_DIR}...")
    now = time.time()
    deleted_count = 0
    
    for filename in os.listdir(TEMP_PROCESSING_DIR):
        file_path = os.path.join(TEMP_PROCESSING_DIR, filename)
        if os.path.isfile(file_path):
            file_age_seconds = now - os.path.getmtime(file_path)
            if file_age_seconds > (max_age_hours * 3600):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"Deleted old file: {filename}")
                except Exception as e:
                    print(f"Failed to delete {filename}: {e}", file=sys.stderr)
                    
    print(f"Garbage collection finished. Deleted {deleted_count} old files.")

def download_profile_videos(profile_url, max_downloads=MAX_VIDEOS_PER_PROFILE):
    """
    Downloads the latest videos from a TikTok profile and extracts metadata.
    """
    target_username = profile_url.rstrip('/').split('@')[-1].split('/')[0] if '@' in profile_url else None

    def profile_match_filter(info_dict, **kwargs):
        if target_username:
            uploader = info_dict.get('uploader')
            if uploader and uploader.lower() != target_username.lower():
                return f"Skipping {uploader} (target is {target_username})"
        return None

    ydl_opts = {
        'outtmpl': f'{TEMP_PROCESSING_DIR}/%(id)s.%(ext)s',
        'max_downloads': max_downloads,
        'quiet': False,
        'cookiefile': 'cookies.txt',        # Use a dedicated cookies file instead
        'sleep_interval': 5,                # rate limiting: pause randomly 
        'max_sleep_interval': 15,           # for 5 to 15 seconds
        'match_filter': profile_match_filter,
    }

    print(f"Starting download for {profile_url} (Max {max_downloads} videos)")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(profile_url, download=True)
            
            # If it's a playlist/profile, iterate over entries
            entries = info.get('entries', [info])
            
            
            extracted_count = 0
            for entry in entries:
                if not entry:
                    continue
                
                video_id = entry.get('id')
                upload_date = entry.get('upload_date')
                title = entry.get('title', '')
                description = entry.get('description', '')
                caption = title if title else description
                creator_name = entry.get('uploader') or entry.get('channel') or 'unknown'
                
                # The final filename yt-dlp saves
                ext = entry.get('ext', 'mp4')
                file_path = f"{TEMP_PROCESSING_DIR}/{video_id}.{ext}"
                
                # Check if it was actually downloaded (could be skipped by filter or max_downloads)
                if not os.path.exists(file_path):
                    continue
                
                print(f"Saving database metadata for video {video_id}")
                insert_video_metadata(
                    video_id=video_id,
                    upload_date=upload_date,
                    caption=caption,
                    creator_name=creator_name,
                    file_path=file_path
                )
                extracted_count += 1
                
            print(f"Successfully processed profile: {profile_url} (Extracted {extracted_count} videos)")
            
            if extracted_count < max_downloads:
                print(f"\nWarning: Scrape ended early. Only extracted {extracted_count} of {max_downloads} videos.", file=sys.stderr)
                print("Your TikTok cookies may be expired, or you hit a rate limit.\n", file=sys.stderr)
            
        except Exception as e:
            print(f"Error scraping {profile_url}: {e}", file=sys.stderr)

if __name__ == "__main__":
    import db
    db.init_db() # Ensure DB exists
    cleanup_temp_folder() # Garbage collection
    
    
    try:
        with open('targets.txt', 'r') as f:
            targets = [url.strip() for url in f.readlines() if url.strip()]
            
        if not targets:
            print("No targets found in targets.txt.")
            sys.exit(0)

        for target in targets:
            download_profile_videos(target)
            
    except FileNotFoundError:
        print("targets.txt not found. Please create it and add TikTok profile URLs.")
