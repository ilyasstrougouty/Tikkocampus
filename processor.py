import os
import sqlite3
import subprocess
import time

from config import DB_PATH, TEMP_PROCESSING_DIR

# --- Configuration ---
WHISPER_MODEL_SIZE = 'base' 

def extract_audio(video_path, audio_path):
    """
    Uses FFmpeg to strip the audio into a 16kHz mono WAV file.
    This specific format makes Whisper run significantly faster.
    """
    command = [
        'ffmpeg', 
        '-i', video_path, 
        '-vn',                   # Disable video processing
        '-acodec', 'pcm_s16le',  # 16-bit WAV
        '-ar', '16000',          # 16kHz sample rate
        '-ac', '1',              # Mono channel
        audio_path, 
        '-y'                     # Overwrite if file exists
    ]
    
    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def transcribe_local(wav_path):
    """Transcribe using local faster-whisper (CPU). Free but slow."""
    from faster_whisper import WhisperModel
    
    # We lazily load the model and cache it as a function attribute
    if not hasattr(transcribe_local, '_model'):
        print(f"Loading local Whisper '{WHISPER_MODEL_SIZE}' model...")
        transcribe_local._model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    
    segments, info = transcribe_local._model.transcribe(wav_path, beam_size=5)
    return " ".join([segment.text for segment in segments]).strip()

def transcribe_groq(wav_path):
    """Transcribe using Groq's Whisper API. Fast but requires API key."""
    import httpx
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Please save your API key in Settings first.")
    
    with open(wav_path, "rb") as audio_file:
        response = httpx.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (os.path.basename(wav_path), audio_file, "audio/wav")},
            data={"model": "whisper-large-v3", "response_format": "text"},
            timeout=120.0
        )
    
    if response.status_code != 200:
        raise Exception(f"Groq Whisper API error {response.status_code}: {response.text}")
    
    return response.text.strip()

def run_processing_pipeline(status_callback=None, method="local"):
    """
    Processes all un-transcribed videos.
    method: 'local' for faster-whisper on CPU, 'groq_whisper' for Groq cloud API
    """
    method_label = "Local Whisper (CPU)" if method == "local" else "Groq Whisper API (Cloud)"
    msg = f"Using transcription: {method_label}"
    print(msg)
    if status_callback: status_callback(msg)
    
    # 1. FETCH THE QUEUE
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT video_id, file_path FROM videos WHERE transcript IS NULL")
    queue = cursor.fetchall()
    
    if not queue:
        msg = "Queue is empty. No new videos to process."
        print(msg)
        if status_callback: status_callback(msg)
        conn.close()
        return

    total_videos = len(queue)
    # Local is ~15s/video, Groq API is ~3s/video
    est_per_video = 15 if method == "local" else 3
    
    msg = f"Found {total_videos} videos pending transcription."
    print(msg)
    if status_callback: status_callback(msg)

    # 2. PROCESS THE BATCH
    for i, (video_id, file_path) in enumerate(queue):
        remaining = total_videos - i
        eta_seconds = remaining * est_per_video
        eta_str = f"{eta_seconds}s" if eta_seconds < 60 else f"{eta_seconds//60}m {eta_seconds%60}s"
        
        status_msg = f"Transcribing {i+1} of {total_videos} [{method_label}]... (ETA: ~{eta_str})"
        print(f"\n{status_msg}")
        if status_callback: status_callback(status_msg)
        
        if not os.path.exists(file_path):
            print(f"[!] File missing for {video_id}. Skipping...")
            continue
            
        wav_path = file_path.replace('.mp4', '.wav')
        
        # Step A: Extract Audio
        print(f"-> Extracting audio for {video_id}...")
        if not extract_audio(file_path, wav_path):
            print(f"[!] FFmpeg failed for {video_id}.")
            continue
            
        # Delete video file immediately
        os.remove(file_path) 
        
        # Step B: Transcribe
        print(f"-> Transcribing {video_id}...")
        try:
            if method == "groq_whisper":
                transcript_text = transcribe_groq(wav_path)
            else:
                transcript_text = transcribe_local(wav_path)
        except Exception as e:
            print(f"[!] Transcription failed for {video_id}: {e}")
            if os.path.exists(wav_path): os.remove(wav_path)
            continue
        
        # Step C: Database Injection
        cursor.execute("UPDATE videos SET transcript = ? WHERE video_id = ?", (transcript_text, video_id))
        conn.commit()
        
        # Cleanup WAV
        os.remove(wav_path)
        print(f"[SUCCESS] {video_id} transcribed and saved. Temp files deleted.")

    conn.close()
    msg = "Phase 2 pipeline complete."
    print(msg)
    if status_callback: status_callback(msg)

if __name__ == "__main__":
    run_processing_pipeline()
