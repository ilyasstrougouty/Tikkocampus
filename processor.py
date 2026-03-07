import os
import sqlite3
import subprocess
from faster_whisper import WhisperModel

from config import DB_PATH, TEMP_PROCESSING_DIR

# --- Configuration ---
# 'base' or 'small' are best for local machines. 'large-v3' will require a strong GPU.
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
        # Run the command silently. check=True raises an error if it fails.
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def run_processing_pipeline(status_callback=None):
    # 1. LOAD THE MODEL ONCE
    # Warning: Never put this inside the loop, or you will cause a massive memory leak.
    msg = f"Loading Whisper '{WHISPER_MODEL_SIZE}' model into memory..."
    print(msg)
    if status_callback: status_callback(msg)
    
    # Change device="cuda" if you have an Nvidia GPU setup properly
    model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8") 
    
    # 2. FETCH THE QUEUE
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Only grab videos that haven't been transcribed yet
    cursor.execute("SELECT video_id, file_path FROM videos WHERE transcript IS NULL")
    queue = cursor.fetchall()
    
    if not queue:
        msg = "Queue is empty. No new videos to process."
        print(msg)
        if status_callback: status_callback(msg)
        conn.close()
        return

    total_videos = len(queue)
    msg = f"Found {total_videos} videos pending transcription."
    print(msg)
    if status_callback: status_callback(msg)

    # 3. PROCESS THE BATCH
    for i, (video_id, file_path) in enumerate(queue):
        # Calculate ETA (rough estimate of 15 seconds per video on CPU)
        remaining = total_videos - i
        eta_seconds = remaining * 15
        eta_str = f"{eta_seconds}s" if eta_seconds < 60 else f"{eta_seconds//60}m {eta_seconds%60}s"
        
        status_msg = f"Processing {i+1} of {total_videos}... (ETA: ~{eta_str})"
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
            
        # 🚨 CRITICAL DISK CLEANUP 🚨
        # Delete the massive .mp4 file the exact millisecond the audio is safe.
        os.remove(file_path) 
        
        # Step B: AI Transcription
        print(f"-> Transcribing {video_id}...")
        segments, info = model.transcribe(wav_path, beam_size=5)
        
        # faster-whisper returns a generator. We must iterate through it to get the text.
        transcript_text = " ".join([segment.text for segment in segments]).strip()
        
        # Step C: Database Injection
        cursor.execute("UPDATE videos SET transcript = ? WHERE video_id = ?", (transcript_text, video_id))
        conn.commit()
        
        # 🚨 CRITICAL DISK CLEANUP 🚨
        os.remove(wav_path)
        print(f"[SUCCESS] {video_id} transcribed and saved. Temp files deleted.")

    conn.close()
    msg = "Phase 2 pipeline complete."
    print(msg)
    if status_callback: status_callback(msg)

if __name__ == "__main__":
    run_processing_pipeline()
