import os
import sys
import time
import threading
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import webview
import shutil

# Resolve base directory (works both from source and PyInstaller bundle)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEB_DIR = os.path.join(BASE_DIR, "web")

import config
import scraper
import processor
import embedder
import chat

app = FastAPI()

# Mount the web directory for static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# --- Global State Tracker ---
task_state = {
    "is_running": False,
    "status": "waiting for input...",
    "error": None
}

class ProcessRequest(BaseModel):
    target_url: str
    max_videos: int = 10

class ChatRequest(BaseModel):
    query: str
    creator_name: str = None

def run_heavy_pipeline(url: str, max_videos: int = 10):
    """Executes the 3 phases of the pipeline sequentially."""
    global task_state
    try:
        import db
        db.init_db()  # Ensure tables exist
        
        # Determine creator name from URL for filtering
        # URLs are usually like https://www.tiktok.com/@creatorname
        creator_filter = None
        if '@' in url:
            creator_filter = url.split('@')[-1].split('/')[0].split('?')[0]
        
        task_state["status"] = f"Phase 1: Scraping {max_videos} videos from TikTok..."
        # Capture the actual creator name and nickname used by the scraper
        actual_creator, actual_nickname = scraper.download_profile_videos(url, max_downloads=max_videos) 
        
        # If scraper failed to determine a name, fallback to url-based one
        final_creator = actual_creator or creator_filter or "unknown"
        final_nickname = actual_nickname or final_creator
        
        # Pass a callback to processor to update ETA on the frontend
        def status_update_callback(msg):
            task_state["status"] = f"Phase 2: {msg}"
        
        # Default to Groq cloud if they have a API key config, otherwise fallback to local
        transcription_method = os.environ.get("TRANSCRIPTION_METHOD", config.TRANSCRIPTION_METHOD)
        if transcription_method == "local":
            if os.environ.get("GROQ_API_KEY"):
                transcription_method = "groq_whisper"
                
        processor.run_processing_pipeline(
            status_callback=status_update_callback, 
            method=transcription_method,
            creator_filter=final_creator
        )
        
        task_state["status"] = "Phase 3: Chunking text and building Vector DB..."
        embedder.run_embedding_pipeline(creator_filter=final_creator)
        
        # Save to history
        with db.db_session() as conn:
            c = conn.cursor()
            # Use the finalized creator name to get accurate counts
            c.execute('SELECT COUNT(*) FROM videos WHERE creator_name = ?', (final_creator,))
            row = c.fetchone()
            final_count = row[0] if row else 0
            
            db.save_scrape_history(url, final_creator, final_nickname, final_count)
        
        task_state["creator_name"] = final_creator
        task_state["creator_nickname"] = final_nickname
        task_state["status"] = "completed"
    except Exception as e:
        task_state["error"] = str(e)
        task_state["status"] = "Error"
    finally:
        task_state["is_running"] = False

import sys
import subprocess

@app.post("/api/auth")
async def trigger_auth():
    global task_state
    if task_state["is_running"]:
        raise HTTPException(status_code=400, detail="A process is already running.")
    
    task_state["is_running"] = True
    task_state["status"] = "Waiting for user to login via Chromium..."
    task_state["error"] = None
    
    try:
        # Run the Playwright auth flow in an isolated subprocess to prevent asyncio loop clashes
        subprocess.run([sys.executable, "auth.py"], check=True)
        task_state["status"] = "Authentication Successful!"
        
        # Save a copy to the cookies history directory
        if os.path.exists("cookies.txt"):
            from config import COOKIES_DIR
            from datetime import datetime
            import shutil
            os.makedirs(COOKIES_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"cookie_{timestamp}.txt"
            shutil.copyfile("cookies.txt", os.path.join(COOKIES_DIR, unique_filename))
            enforce_cookie_limit()
            
        return {"message": "Cookies extracted."}
    except Exception as e:
        task_state["error"] = str(e)
        task_state["status"] = "Authentication Failed."
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        task_state["is_running"] = False

def install_playwright_if_needed():
    """Checks for Playwright Chromium and installs it if missing."""
    print("Checking Playwright Chromium...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                # Try to launch headless to verify existence
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("Playwright Chromium is correctly installed.")
            except Exception as e:
                if "Executable doesn't exist" in str(e) or "not found" in str(e):
                    print("Playwright Chromium missing. Starting automatic installation...")
                    # In a frozen bundle, sys.executable is the .exe
                    # We use it to run the playwright module installer
                    import subprocess
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                    print("Playwright Chromium installed successfully!")
                else:
                    print(f"Playwright check info: {e}")
                    # If it's another error, we don't necessarily want to block startup
                    # but we also don't want to try to install if it's a driver error
    except Exception as e:
        print(f"Failed to check/install Playwright: {e}")

from config import COOKIES_DIR
from datetime import datetime

class CookieSelectRequest(BaseModel):
    filename: str

@app.delete("/api/history/{creator_name}")
async def delete_history_creator(creator_name: str):
    """Hard-deletes a creator and all their vectors from the system."""
    try:
        import db
        import embedder
        db.delete_creator(creator_name)
        embedder.delete_creator(creator_name)
        return {"message": f"Successfully deleted {creator_name} and all associated data."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a .txt file")
    
    try:
        # Generate a unique filename based on the current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"cookie_{timestamp}.txt"
        save_path = os.path.join(COOKIES_DIR, unique_filename)
        
        # Save to the history folder
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Immediately set it as the active cookie
        shutil.copyfile(save_path, "cookies.txt")
        enforce_cookie_limit()
        
        return {"message": "Cookies uploaded successfully", "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookies: {str(e)}")

@app.get("/api/list-cookies")
async def list_cookies():
    """Returns a list of all saved cookie profiles."""
    enforce_cookie_limit()
    cookies = []
    if os.path.exists(COOKIES_DIR):
        for filename in os.listdir(COOKIES_DIR):
            if filename.endswith(".txt"):
                file_path = os.path.join(COOKIES_DIR, filename)
                # Get file creation/modification time for display
                mtime = os.path.getmtime(file_path)
                created_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                cookies.append({
                    "filename": filename,
                    "created_at": created_str,
                    "timestamp": mtime
                })
        # Sort newest first
        cookies.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"cookies": cookies}

@app.post("/api/select-cookie")
async def select_cookie(req: CookieSelectRequest):
    """Sets a historical cookie file as the active cookies.txt."""
    source_path = os.path.join(COOKIES_DIR, req.filename)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="Cookie file not found")
    
    try:
        shutil.copyfile(source_path, "cookies.txt")
        return {"message": f"Successfully loaded {req.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cookies/{filename}")
async def delete_cookie_file(filename: str):
    """Deletes a historical cookie file from the disk."""
    file_path = os.path.join(COOKIES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Cookie file not found")
    
    try:
        os.remove(file_path)
        return {"message": f"Deleted {filename} successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/check-cookies")
async def check_cookies():
    """Check if cookies.txt already exists on disk."""
    exists = os.path.isfile("cookies.txt") and os.path.getsize("cookies.txt") > 0
    return {"exists": exists}

@app.get("/api/validate-session")
async def validate_session():
    """Checks if the current cookies are actually valid for TikTok."""
    if not os.path.exists("cookies.txt"):
        return {"valid": False, "error": "No cookies found"}
    
    import httpx
    try:
        from scraper import parse_netscape_cookies
        raw_cookies = parse_netscape_cookies("cookies.txt")
        # Extract name=value pairs for httpx
        cookies = {c['name']: c['value'] for c in raw_cookies}
        
        async with httpx.AsyncClient(cookies=cookies, follow_redirects=True, timeout=10.0) as client:
            # Check TikTok home page with more realistic headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.tiktok.com/"
            }
            resp = await client.get("https://www.tiktok.com/", headers=headers)
            
            # Check for redirect to login or presence of login markers
            final_url = str(resp.url)
            page_text = resp.text.lower()
            
            if "/login" in final_url.lower() or "passport.tiktok.com" in final_url or "verify-login" in page_text:
                print(f"Session invalidated: Redirected to {final_url}")
                return {"valid": False}
                
            return {"valid": True}
    except Exception as e:
        print(f"Session validation error: {str(e)}")
        return {"valid": False, "error": str(e)}

def enforce_cookie_limit():
    """Ensures there are never more than 4 cookie files in the directory."""
    try:
        if not os.path.exists(COOKIES_DIR):
            return
            
        files = [f for f in os.listdir(COOKIES_DIR) if f.endswith(".txt")]
        if len(files) <= 4:
            return
            
        # Sort by modification time (descending)
        file_paths = [os.path.join(COOKIES_DIR, f) for f in files]
        file_paths.sort(key=os.path.getmtime, reverse=True)
        
        # Keep the top 4, delete the rest
        to_delete = file_paths[4:]
        for path in to_delete:
            try:
                os.remove(path)
                print(f"Enforced limit: Deleted old cookie file {os.path.basename(path)}")
            except Exception as e:
                print(f"Failed to delete {path}: {e}")
    except Exception as e:
        print(f"Error enforcing cookie limit: {e}")

@app.post("/api/process")
async def trigger_pipeline(req: ProcessRequest, background_tasks: BackgroundTasks):
    global task_state
    if task_state["is_running"]:
        raise HTTPException(status_code=400, detail="A process is already running.")
    
    # Lock the state
    task_state["is_running"] = True
    task_state["status"] = "Starting..."
    task_state["error"] = None
    
    # Hand the heavy function to FastAPI to run in the background
    background_tasks.add_task(run_heavy_pipeline, req.target_url, req.max_videos)
    
    # Immediately return a success message so the browser doesn't timeout
    return {"message": "Job started in the background."}

@app.get("/api/status")
async def get_status():
    """The frontend will poll this endpoint every few seconds."""
    return task_state

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Endpoint for the JS frontend to ask questions."""
    try:
        response = chat.get_rag_response(req.query, req.creator_name)
        return {"response": response}
    except Exception as e:
        # Return error as a chat message so the user sees what went wrong
        return {"response": f"❌ Error: {str(e)}"}

class SettingsRequest(BaseModel):
    model: str
    api_key: str = ""
    transcription_method: str = "local"

@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    """Save the user's LLM model and API key to memory AND to .env file."""
    env_updates = {"LLM_MODEL": req.model, "TRANSCRIPTION_METHOD": req.transcription_method}
    os.environ["TRANSCRIPTION_METHOD"] = req.transcription_method
    
    # Set the correct environment variable based on the model provider
    if req.api_key:
        if req.model.startswith("groq/"):
            os.environ["GROQ_API_KEY"] = req.api_key
            env_updates["GROQ_API_KEY"] = req.api_key
        elif req.model.startswith("gpt") or req.model.startswith("openai"):
            os.environ["OPENAI_API_KEY"] = req.api_key
            env_updates["OPENAI_API_KEY"] = req.api_key
    
    # Update the active model in the chat module
    chat.LLM_MODEL = req.model
    
    # Persist to .env file safely
    try:
        update_env_file(env_updates)
    except Exception as e:
        print(f"Failed to update .env: {e}")
    
    return {"message": f"Settings saved. Model set to {req.model}"}

def update_env_file(updates: dict):
    """Safely updates the .env file with new key-value pairs."""
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    new_lines = []
    keys_updated = set()
    
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                keys_updated.add(key)
                continue
        new_lines.append(line)
    
    for key, value in updates.items():
        if key not in keys_updated:
            new_lines.append(f"{key}={value}\n")
            
    with open(env_path, "w") as f:
        f.writelines(new_lines)

@app.get("/api/settings")
async def get_settings():
    """Returns the currently active settings so the UI can display them."""
    import chat
    model = getattr(chat, 'LLM_MODEL', os.environ.get('LLM_MODEL', 'groq/llama-3.1-8b-instant'))
    has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
    
    transcription = os.environ.get("TRANSCRIPTION_METHOD", config.TRANSCRIPTION_METHOD)
    if not transcription or transcription == "local":
        transcription = "groq_whisper" if has_groq_key else "local"
    return {
        "model": model,
        "transcription_method": transcription,
        "has_groq_key": has_groq_key,
        "has_openai_key": has_openai_key
    }

@app.get("/api/history")
async def get_history():
    """Returns the list of previously scraped profiles."""
    import db
    db.init_db()  # Ensure the table exists
    history = db.get_scrape_history()
    return {"history": history}

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

class WindowAPI:
    def __init__(self):
        pass

    def close(self):
        import os
        os._exit(0)

    def minimize(self):
        webview.windows[0].minimize()

    def toggle_maximize(self):
        webview.windows[0].toggle_fullscreen()

import signal
import sys
import os

def sigint_handler(signum, frame):
    print("\nCtrl+C detected! Shutting down Tikkocampus...")
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    
    # Ensure Playwright is ready before starting anything else
    install_playwright_if_needed()
    
    print("Starting Desktop Interface...")
    
    # Run the FastAPI server in a background thread
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    
    # Wait a tiny bit for the server to start
    time.sleep(1)
    
    # Create the frameless PyWebView desktop window
    api = WindowAPI()
    window = webview.create_window(
        "", 
        "http://127.0.0.1:8000/", 
        width=850, 
        height=650, 
        frameless=True, 
        easy_drag=False,
        text_select=True,
        js_api=api
    )
    webview.start(icon=os.path.join(WEB_DIR, 'logo.ico'))
