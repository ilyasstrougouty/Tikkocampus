"""
config.py — Single source of truth for all application paths and settings.

In frozen mode (PyInstaller), BASE_DIR is the directory containing the executable.
In dev mode, BASE_DIR is the project root.
"""
import os
import sys
import platform
from dotenv import load_dotenv

# --- Path Management (THE single source of truth) ---
if getattr(sys, 'frozen', False):
    app_name = "tikkocampus"
    if platform.system() == "Windows":
        app_data = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
        BASE_DIR = os.path.join(app_data, app_name, 'backend_data')
    elif platform.system() == "Darwin":
        BASE_DIR = os.path.join(os.path.expanduser('~/Library/Application Support'), app_name, 'backend_data')
    else:
        BASE_DIR = os.path.join(os.path.expanduser('~/.config'), app_name, 'backend_data')
    os.makedirs(BASE_DIR, exist_ok=True)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Resolve the internal assets directory (PyInstaller temp extraction folder)
# Used ONLY for bundled read-only assets like the web/ folder.
if getattr(sys, 'frozen', False):
    INTERNAL_DIR = sys._MEIPASS
else:
    INTERNAL_DIR = BASE_DIR

# --- File Paths (all absolute, no relative paths anywhere) ---
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")
ENV_FILE = os.path.join(BASE_DIR, ".env")
LOG_FILE = os.path.join(BASE_DIR, "backend.log")
DB_PATH = os.path.join(BASE_DIR, "tiktok_data.db")
TEMP_PROCESSING_DIR = os.path.join(BASE_DIR, "temp_processing")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
WEB_DIR = os.path.join(INTERNAL_DIR, "web")

# --- Load .env from BASE_DIR ---
load_dotenv(ENV_FILE)

# --- Application Settings ---
MAX_VIDEOS_PER_PROFILE = int(os.environ.get("MAX_VIDEOS_PER_PROFILE", 5))
LLM_MODEL = os.environ.get("LLM_MODEL", "groq/llama-3.1-8b-instant")
TRANSCRIPTION_METHOD = os.environ.get("TRANSCRIPTION_METHOD", "local")

# --- Global State ---
CANCEL_REQUESTED = False

# --- Ensure required directories exist ---
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True)
os.makedirs(COOKIES_DIR, exist_ok=True)
