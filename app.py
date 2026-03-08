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
    "status": "Idle",
    "error": None
}

class ProcessRequest(BaseModel):
    target_url: str
    max_videos: int = 10

class ChatRequest(BaseModel):
    query: str

def run_heavy_pipeline(url: str, max_videos: int = 10):
    """Executes the 3 phases of the pipeline sequentially."""
    global task_state
    try:
        task_state["status"] = "Phase 0: Wiping old vector database..."
        import db
        db.reset_database()
        embedder.reset_chroma()
        
        task_state["status"] = f"Phase 1: Scraping {max_videos} videos from TikTok..."
        scraper.download_profile_videos(url, max_downloads=max_videos) 
        
        # Pass a callback to processor to update ETA on the frontend
        def status_update_callback(msg):
            task_state["status"] = f"Phase 2: {msg}"
        
        transcription_method = os.environ.get("TRANSCRIPTION_METHOD", "local")
        processor.run_processing_pipeline(status_callback=status_update_callback, method=transcription_method)
        
        task_state["status"] = "Phase 3: Chunking text and building Vector DB..."
        embedder.run_embedding_pipeline()
        
        # Save to history
        import sqlite3
        conn = sqlite3.connect(db.DB_PATH if hasattr(db, 'DB_PATH') else 'tiktok_data.db')
        c = conn.cursor()
        c.execute('SELECT creator_name, COUNT(*) FROM videos GROUP BY creator_name LIMIT 1')
        row = c.fetchone()
        conn.close()
        creator = row[0] if row else 'unknown'
        count = row[1] if row else 0
        db.save_scrape_history(url, creator, count)
        
        task_state["status"] = "Done"
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
        return {"message": "Cookies extracted."}
    except Exception as e:
        task_state["error"] = str(e)
        task_state["status"] = "Authentication Failed."
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        task_state["is_running"] = False

@app.post("/api/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a .txt file")
    
    try:
        # Save the uploaded file as cookies.txt
        with open("cookies.txt", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "Cookies uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookies: {str(e)}")

@app.get("/api/check-cookies")
async def check_cookies():
    """Check if cookies.txt already exists on disk."""
    exists = os.path.isfile("cookies.txt") and os.path.getsize("cookies.txt") > 0
    return {"exists": exists}

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
        response = chat.get_rag_response(req.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    
    # Persist to .env file
    env_path = ".env"
    env_lines = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    env_lines[key.strip()] = val.strip()
    
    env_lines.update(env_updates)
    
    with open(env_path, "w") as f:
        for key, val in env_lines.items():
            f.write(f"{key}={val}\n")
    
    return {"message": f"Settings saved. Model set to {req.model}"}

@app.get("/api/settings")
async def get_settings():
    """Returns the currently active settings so the UI can display them."""
    import chat
    model = getattr(chat, 'LLM_MODEL', os.environ.get('LLM_MODEL', 'groq/llama-3.1-8b-instant'))
    transcription = os.environ.get("TRANSCRIPTION_METHOD", "local")
    has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
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
    print("\nCtrl+C detected! Shutting down TikTok RAG Engine...")
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
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
        "TikTok RAG Engine", 
        "http://127.0.0.1:8000/", 
        width=1000, 
        height=700, 
        frameless=True, 
        text_select=True,
        js_api=api
    )
    webview.start(icon=os.path.join(WEB_DIR, 'logo.ico'))
