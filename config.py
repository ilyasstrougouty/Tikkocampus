import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_PROCESSING_DIR = os.path.join(BASE_DIR, "temp_processing")
DB_PATH = os.path.join(BASE_DIR, "tiktok_data.db")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
MAX_VIDEOS_PER_PROFILE = 5 # Download the latest 5 videos per creator by default

# Ensure the required directories exist
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True)
os.makedirs(COOKIES_DIR, exist_ok=True)
