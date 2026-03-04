import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_PROCESSING_DIR = os.path.join(BASE_DIR, "temp_processing")
DB_PATH = os.path.join(BASE_DIR, "tiktok_data.db")
MAX_VIDEOS_PER_PROFILE = 5 # Download the latest 5 videos per creator by default

# Ensure the temp processing directory exists
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True)
