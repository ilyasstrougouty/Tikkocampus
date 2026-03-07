import os
import time
import threading
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import webview
import shutil
import uvicorn
import webview

import scraper
import processor
import embedder
import chat

app = FastAPI()

# Mount the web directory for static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="web"), name="static")

# --- Global State Tracker ---
task_state = {
    "is_running": False,
    "status": "Idle",
    "error": None
}

class ProcessRequest(BaseModel):
    target_url: str

class ChatRequest(BaseModel):
    query: str

def run_heavy_pipeline(url: str):
    """Executes the 3 phases of the pipeline sequentially."""
    global task_state
    try:
        task_state["status"] = "Phase 0: Wiping old vector database..."
        import db
        db.reset_database()
        embedder.reset_chroma()
        
        task_state["status"] = "Phase 1: Scraping videos from TikTok..."
        scraper.download_profile_videos(url, max_downloads=5) 
        
        # Pass a callback to processor to update ETA on the frontend
        def status_update_callback(msg):
            task_state["status"] = f"Phase 2: {msg}"
            
        processor.run_processing_pipeline(status_callback=status_update_callback)
        
        task_state["status"] = "Phase 3: Chunking text and building Vector DB..."
        embedder.run_embedding_pipeline()
        
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
    background_tasks.add_task(run_heavy_pipeline, req.target_url)
    
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

@app.get("/")
async def serve_index():
    return FileResponse("web/index.html")

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    print("Starting Desktop Interface...")
    # Run the FastAPI server in a background thread
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    
    # Wait a tiny bit for the server to start
    time.sleep(1)
    
    # Open the PyWebView desktop window pointing to our local server
    webview.create_window("TikTok RAG Engine", "http://127.0.0.1:8000/", width=1000, height=700)
    webview.start()
