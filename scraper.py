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
    profile_url = profile_url.rstrip('/')
    if '@' not in profile_url and 'tiktok.com/' in profile_url:
        username = profile_url.split('/')[-1]
        profile_url = f"https://www.tiktok.com/@{username}"

    target_username = profile_url.split('@')[-1].split('/')[0]

    def profile_match_filter(info_dict, **kwargs):
        if target_username:
            uploader = info_dict.get('uploader')
            if uploader and uploader.lower() != target_username.lower():
                return f"Skipping {uploader} (target is {target_username})"
        return None

    extracted_count = 0
    def post_extraction_hook(d):
        nonlocal extracted_count
        if d['status'] == 'finished' or d['status'] == 'already_downloaded':
            # Extract metadata from the completed download dict
            info = d.get('info_dict', {})
            video_id = info.get('id')
            
            if not video_id:
                return

            upload_date = info.get('upload_date')
            title = info.get('title', '')
            description = info.get('description', '')
            caption = title if title else description
            creator_name = info.get('uploader') or info.get('channel') or 'unknown'
            file_path = d.get('filename') # Absolute path to the saved/cached file
            
            print(f"Saving database metadata for video {video_id}")
            insert_video_metadata(
                video_id=video_id,
                upload_date=upload_date,
                caption=caption,
                creator_name=creator_name,
                file_path=file_path
            )
            extracted_count += 1

    ydl_opts = {
        'outtmpl': f'{TEMP_PROCESSING_DIR}/%(id)s.%(ext)s',
        'max_downloads': max_downloads,
        'quiet': False,
        'cookiefile': 'cookies.txt',        # Use a dedicated cookies file
        'sleep_interval': 5,                # rate limiting: pause randomly 
        'max_sleep_interval': 15,           # for 5 to 15 seconds
        'match_filter': profile_match_filter,
        'socket_timeout': 60,              # Increase timeout from 20s default to 60s
        'retries': 5,                       # Retry failed downloads up to 5 times
        'extractor_retries': 3,             # Retry failed extractions up to 3 times
        'progress_hooks': [post_extraction_hook], # Runs after every single video
    }

    print(f"Starting download for {profile_url} (Max {max_downloads} videos)")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # We just trigger the download and let the `progress_hooks` handle the DB insertion instantly
            ydl.download([profile_url])
            
            print(f"Successfully processed profile: {profile_url} (Extracted {extracted_count} videos)")
            
            if extracted_count < max_downloads:
                print(f"\nWarning: Scrape ended early. Only extracted {extracted_count} of {max_downloads} videos.", file=sys.stderr)
            
        except yt_dlp.utils.MaxDownloadsReached:
             print(f"Reached max downloads limit ({max_downloads}).")
        except yt_dlp.utils.DownloadError as e:
            print(f"Error scraping {profile_url}: {e}", file=sys.stderr)
            raise e 
        except Exception as e:
            print(f"Error scraping {profile_url}: {e}", file=sys.stderr)
            raise e

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
