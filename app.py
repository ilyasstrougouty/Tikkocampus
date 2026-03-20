"""
app.py — FastAPI backend for Tikkocampus.

Uses config for all paths, cookie_manager for cookie I/O,
and logger for all output. No hardcoded paths or print() calls.
"""
import os
import sys

# Fix for PyInstaller --windowed mode where stdout/stderr are None
# This MUST happen before any import that might print.
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

import time
import threading
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import shutil
import argparse
import socket
import json
import signal
import subprocess
from datetime import datetime

import config
import scraper
import processor
import embedder
import chat
import cookie_manager
from logger import get_logger

log = get_logger("app")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global State Tracker ---
task_state = {
    "is_running": False,
    "status": "waiting for input...",
    "error": None,
    "error_code": None,
}


class ProcessRequest(BaseModel):
    target_url: str
    max_videos: int = 10


class ChatRequest(BaseModel):
    query: str
    creator_name: str = None


class CookieSelectRequest(BaseModel):
    filename: str


class SettingsRequest(BaseModel):
    model: str
    api_key: str = ""
    transcription_api_key: str = ""
    transcription_method: str = "local"


# --- Pipeline ---

def run_heavy_pipeline(url: str, max_videos: int = 10):
    """Executes the 3 phases of the pipeline sequentially."""
    global task_state
    try:
        import db
        db.init_db()

        creator_filter = None
        if '@' in url:
            creator_filter = url.split('@')[-1].split('/')[0].split('?')[0]

        task_state["status"] = "Phase 1: Verifying dependencies..."
        install_playwright_if_needed()
        check_ffmpeg()

        task_state["status"] = f"Phase 1: Scraping {max_videos} videos from TikTok..."
        result = scraper.download_profile_videos(url, max_downloads=max_videos)
        
        # Unpack the structured result (4 values now)
        actual_creator, actual_nickname, error_code, error_msg = result

        if error_code and error_code != scraper.OK:
            log.warning(f"Scraper returned error: {error_code} — {error_msg}")
            task_state["error_code"] = error_code
            # Don't abort — continue with whatever we have

        if getattr(config, 'CANCEL_REQUESTED', False):
            task_state["status"] = "Cancelled by user"
            return

        final_creator = actual_creator or creator_filter or "unknown"
        final_nickname = actual_nickname or final_creator

        def status_update_callback(msg):
            task_state["status"] = f"Phase 2: {msg}"

        transcription_method = os.environ.get("TRANSCRIPTION_METHOD", config.TRANSCRIPTION_METHOD)
        if transcription_method == "local":
            if os.environ.get("GROQ_API_KEY"):
                transcription_method = "groq_whisper"

        processor.run_processing_pipeline(
            status_callback=status_update_callback,
            method=transcription_method,
            creator_filter=final_creator
        )

        if getattr(config, 'CANCEL_REQUESTED', False):
            task_state["status"] = "Cancelled by user"
            return

        task_state["status"] = "Phase 3: Chunking text and building Vector DB..."
        embedder.run_embedding_pipeline(creator_filter=final_creator)

        if getattr(config, 'CANCEL_REQUESTED', False):
            task_state["status"] = "Cancelled by user"
            return

        # Save to history
        with db.db_session() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM videos WHERE creator_name = ?', (final_creator,))
            row = c.fetchone()
            final_count = row[0] if row else 0
            db.save_scrape_history(url, final_creator, final_nickname, final_count)

        task_state["creator_name"] = final_creator
        task_state["creator_nickname"] = final_nickname
        task_state["status"] = "completed"
    except Exception as e:
        log.error(f"Pipeline error: {e}", exc_info=True)
        task_state["error"] = str(e)
        task_state["status"] = "Error"
    finally:
        task_state["is_running"] = False


# --- Dependency Checks ---

def check_system_browsers():
    """Checks if common system browsers are available on Windows."""
    import platform
    if platform.system() != "Windows":
        return None
    common_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def install_playwright_if_needed():
    """Checks for Playwright Chromium and installs it if missing."""
    log.info("Phase 1: Verifying dependencies...")

    log.info("Phase 1: Checking for system browsers (Edge/Chrome)...")
    system_browser = check_system_browsers()
    if system_browser:
        log.info(f"Phase 1: Found system browser: {system_browser}")
        return

    log.info("Phase 1: No system browser found. Checking Playwright bundle...")
    try:
        from playwright.sync_api import sync_playwright
        log.info("Phase 1: Playwright imported successfully.")

        with sync_playwright() as p:
            log.info("Phase 1: Playwright driver initialized.")
            try:
                browser = p.chromium.launch(headless=True)
                log.info("Phase 1: Bundled Chromium OK.")
                browser.close()
            except Exception as e:
                if "Executable doesn't exist" in str(e) or "not found" in str(e):
                    log.warning(f"Phase 1: Chromium missing ({e})")
                    if getattr(sys, 'frozen', False):
                        log.warning("Phase 1: Frozen mode — skipping auto-install.")
                        return
                    log.info("Phase 1: Attempting auto-install...")
                    try:
                        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, timeout=120)
                        log.info("Phase 1: Chromium installed!")
                    except Exception as ie:
                        log.error(f"Phase 1: Install failed: {ie}")
                else:
                    log.info(f"Phase 1: Playwright check note: {e}")
    except Exception as e:
        log.error(f"Phase 1: Dependency verification error: {e}")


def check_ffmpeg():
    """Checks if ffmpeg is available in the system path."""
    log.info("Phase 1: Checking for FFmpeg...")
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        log.info("Phase 1: FFmpeg is available.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.warning("Phase 1: FFmpeg not found. Audio extraction may fail.")
        return False


# --- Auth ---

@app.post("/api/auth")
async def trigger_auth():
    global task_state
    if task_state["is_running"]:
        raise HTTPException(status_code=400, detail="A process is already running.")

    task_state["is_running"] = True
    task_state["status"] = "Waiting for user to login via Chromium..."
    task_state["error"] = None

    try:
        if getattr(sys, 'frozen', False):
            subprocess.run([sys.executable, "auth"], check=True)
        else:
            backend_script = os.path.join(config.BASE_DIR, "backend.py")
            subprocess.run([sys.executable, backend_script, "auth"], check=True)

        task_state["status"] = "Authentication Successful!"
        cookie_manager.copy_to_history()
        return {"message": "Cookies extracted."}
    except Exception as e:
        task_state["error"] = str(e)
        task_state["status"] = "Authentication Failed."
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        task_state["is_running"] = False


# --- Cookie Endpoints ---

@app.post("/api/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a .txt file")
    try:
        filename = cookie_manager.save_uploaded(file.file)
        return {"message": "Cookies uploaded successfully", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookies: {str(e)}")


@app.get("/api/list-cookies")
async def list_cookies():
    return {"cookies": cookie_manager.list_history()}


@app.post("/api/select-cookie")
async def select_cookie(req: CookieSelectRequest):
    try:
        cookie_manager.select_from_history(req.filename)
        return {"message": f"Successfully loaded {req.filename}"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cookie file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cookies/{filename}")
async def delete_cookie_file(filename: str):
    try:
        cookie_manager.delete_from_history(filename)
        return {"message": f"Deleted {filename} successfully."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cookie file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logout")
async def logout():
    try:
        cookie_manager.delete()
        return {"message": "Logged out successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/check-cookies")
async def check_cookies():
    return {"exists": cookie_manager.exists()}


@app.get("/api/validate-session")
async def validate_session():
    if not cookie_manager.exists():
        return {"valid": False, "error": "No cookies found"}

    import httpx
    try:
        raw_cookies = cookie_manager.read_netscape()
        cookies_dict = {c['name']: c['value'] for c in raw_cookies}

        async with httpx.AsyncClient(cookies=cookies_dict, follow_redirects=True, timeout=10.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.tiktok.com/"
            }
            resp = await client.get("https://www.tiktok.com/", headers=headers)
            final_url = str(resp.url)

            if "/login" in final_url.lower() or "passport.tiktok.com" in final_url:
                log.info(f"Session invalid: redirected to {final_url}")
                return {"valid": False}

            return {"valid": True}
    except Exception as e:
        log.error(f"Session validation error: {e}")
        return {"valid": False, "error": str(e)}


# --- Pipeline Control ---

@app.post("/api/process")
async def trigger_pipeline(req: ProcessRequest, background_tasks: BackgroundTasks):
    global task_state
    if task_state["is_running"]:
        raise HTTPException(status_code=400, detail="A process is already running.")

    config.CANCEL_REQUESTED = False
    task_state["is_running"] = True
    task_state["status"] = "Starting..."
    task_state["error"] = None
    task_state["error_code"] = None

    background_tasks.add_task(run_heavy_pipeline, req.target_url, req.max_videos)
    return {"message": "Job started in the background."}


@app.post("/api/process/cancel")
async def cancel_process():
    global task_state
    if task_state["is_running"]:
        config.CANCEL_REQUESTED = True
        return {"message": "Cancellation requested."}
    return {"message": "No process is currently running."}


@app.get("/api/status")
async def get_status():
    return task_state


# --- History ---

@app.delete("/api/history/{creator_name}")
async def delete_history_creator(creator_name: str):
    try:
        import db
        db.delete_creator(creator_name)
        embedder.delete_creator(creator_name)
        return {"message": f"Successfully deleted {creator_name} and all associated data."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    import db
    db.init_db()
    history = db.get_scrape_history()
    return {"history": history}


# --- Chat ---

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    import db
    db.init_db()

    if req.creator_name and req.creator_name != "All Data":
        db.save_chat_message(req.creator_name, "user", req.query)

    def generate():
        full_response = ""
        try:
            for chunk in chat.get_rag_response_generator(req.query, req.creator_name):
                yield chunk
                try:
                    data = json.loads(chunk)
                    if "chunk" in data:
                        full_response += data["chunk"]
                    elif "response" in data:
                        full_response += data["response"]
                except Exception:
                    pass
        except Exception as e:
            if type(e).__name__ != 'GeneratorExit':
                yield json.dumps({"response": f"❌ Error: {str(e)}"}) + "\n"
        finally:
            if req.creator_name and req.creator_name != "All Data" and full_response:
                db.save_chat_message(req.creator_name, "ai", full_response)

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/api/chat/history/{creator_name}")
async def get_chat_history_endpoint(creator_name: str):
    import db
    db.init_db()
    messages = db.get_chat_history(creator_name)
    return {"messages": messages}


# --- Settings ---

@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    env_updates = {"LLM_MODEL": req.model, "TRANSCRIPTION_METHOD": req.transcription_method}
    os.environ["TRANSCRIPTION_METHOD"] = req.transcription_method

    if req.api_key:
        if req.model.startswith("groq/"):
            os.environ["GROQ_API_KEY"] = req.api_key
            env_updates["GROQ_API_KEY"] = req.api_key
        elif req.model.startswith("gpt") or req.model.startswith("openai"):
            os.environ["OPENAI_API_KEY"] = req.api_key
            env_updates["OPENAI_API_KEY"] = req.api_key

    if req.transcription_api_key:
        os.environ["TRANSCRIPTION_API_KEY"] = req.transcription_api_key
        env_updates["TRANSCRIPTION_API_KEY"] = req.transcription_api_key

    chat.LLM_MODEL = req.model

    try:
        update_env_file(env_updates)
    except Exception as e:
        log.error(f"Failed to update .env: {e}")

    return {"message": f"Settings saved. Model set to {req.model}"}


def update_env_file(updates: dict):
    """Safely updates the .env file with new key-value pairs."""
    lines = []
    if os.path.exists(config.ENV_FILE):
        with open(config.ENV_FILE, "r") as f:
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

    with open(config.ENV_FILE, "w") as f:
        f.writelines(new_lines)


@app.get("/api/settings")
async def get_settings():
    model = getattr(chat, 'LLM_MODEL', os.environ.get('LLM_MODEL', 'groq/llama-3.1-8b-instant'))
    has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
    has_transcription_key = bool(os.environ.get("TRANSCRIPTION_API_KEY"))

    transcription = os.environ.get("TRANSCRIPTION_METHOD", config.TRANSCRIPTION_METHOD)
    if not transcription or transcription == "local":
        transcription = "groq_whisper" if has_groq_key else "local"
    return {
        "model": model,
        "transcription_method": transcription,
        "has_groq_key": has_groq_key,
        "has_openai_key": has_openai_key,
        "has_transcription_key": has_transcription_key
    }


# --- Server ---

def run_server(host="127.0.0.1", port=8000):
    actual_port = port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            actual_port = s.getsockname()[1]
    except OSError:
        log.info(f"Port {port} is busy, falling back to an available port...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            actual_port = s.getsockname()[1]

    # This line is parsed by Electron's main.js
    print(f"BACKEND_PORT: {actual_port}")
    log.info(f"Server starting on http://{host}:{actual_port}")

    uvicorn.run(app, host=host, port=actual_port, log_config=None)


# Mount the web directory LAST so it doesn't shadow /api/* routes
app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tikkocampus Backend Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args, unknown = parser.parse_known_args()

    log.info(f"Starting Tikkocampus Backend on port {args.port}...")
    run_server(host=args.host, port=args.port)
