import os
import sys
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    # In a frozen bundle, the base dir should be the directory where the executable lives
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load variables from .env in the base directory
load_dotenv(os.path.join(BASE_DIR, ".env"))

TEMP_PROCESSING_DIR = os.path.join(BASE_DIR, "temp_processing")
DB_PATH = os.path.join(BASE_DIR, "tiktok_data.db")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")

# Defaults
MAX_VIDEOS_PER_PROFILE = int(os.environ.get("MAX_VIDEOS_PER_PROFILE", 5))
LLM_MODEL = os.environ.get("LLM_MODEL", "groq/llama-3.1-8b-instant")
TRANSCRIPTION_METHOD = os.environ.get("TRANSCRIPTION_METHOD", "local")

# Global state for interrupting background threads
CANCEL_REQUESTED = False

# Ensure the required directories exist
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True)
os.makedirs(COOKIES_DIR, exist_ok=True)
