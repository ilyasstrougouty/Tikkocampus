<div align="center">
  <img src="web/logo.png" alt="TikTok RAG Engine" width="80">
  
  <h1>TikTok RAG Engine</h1>
  <p><em>Scrape any TikTok creator's videos, transcribe them with AI, and chat with the content using any LLM.</em></p>
</div>

---

## ⚙️ What It Does

This is a full **Retrieval-Augmented Generation (RAG)** pipeline for TikTok. Point it at any creator, and it will:

1. **Download** their recent videos using `yt-dlp`
2. **Transcribe** the audio using `faster-whisper` (local) or Groq Whisper API
3. **Embed & Index** the transcripts into a local ChromaDB vector database
4. **Let you chat** with the content using any LLM (Groq, OpenAI, Ollama, etc.)

### Key Features

| Feature | Description |
|---|---|
| **Smart Scraping** | Uses `yt-dlp` with randomized delays (5–15s) to avoid IP bans |
| **Local Transcription** | `faster-whisper` runs entirely on your machine — no API needed |
| **Cloud Transcription** | Optional Groq Whisper API for ~2s/video processing |
| **Vector Search** | ChromaDB stores semantic embeddings for instant retrieval |
| **BYOK (Bring Your Own Key)** | `LiteLLM` supports Groq, OpenAI, Ollama, and more |
| **Desktop App** | Native window powered by `pywebview` with a dark glassmorphism UI |
| **Auto Cleanup** | Deletes `.mp4` and `.wav` files immediately after processing |

---

## 🛠️ Prerequisites

You need two things installed **before** setting up the project:

### 1. Python 3.10+

Download from [python.org](https://www.python.org/downloads/). During installation on Windows, **check "Add Python to PATH"**.

To verify:
```bash
python --version
```

### 2. FFmpeg

The AI transcription model requires FFmpeg to process audio files.

| OS | How to Install |
|---|---|
| **Windows** | Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/). Extract the zip, then add the `bin/` folder to your System PATH ([guide](https://www.architectryan.com/2018/03/17/add-to-the-path-on-windows-10/)) |
| **macOS** | Run `brew install ffmpeg` in Terminal |
| **Linux** | Run `sudo apt install ffmpeg` in Terminal |

To verify:
```bash
ffmpeg -version
```

---

## 🚀 Quick Start (Run from Source)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/yourusername/tiktok-rag-engine.git
cd tiktok-rag-engine
```

### Step 2 — Create a Virtual Environment

```bash
python -m venv venv
```

### Step 3 — Activate the Virtual Environment

**Windows (PowerShell):**
```powershell
venv\Scripts\activate
```

**Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required Python packages including `yt-dlp`, `faster-whisper`, `chromadb`, `litellm`, `fastapi`, `pywebview`, and more.

### Step 5 — Get Your TikTok Cookies

TikTok blocks unauthenticated scraping after ~5 videos. You **must** provide a logged-in session via a cookies file.

1. Install the **"Get cookies.txt LOCALLY"** browser extension:
   - [Chrome](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/) / Edge
2. Go to [tiktok.com](https://www.tiktok.com/) and make sure you are **logged in**
3. Click the extension icon → click **Export** to download your cookies
4. Keep the downloaded file — you'll upload it in the app

### Step 6 — Launch the App

```bash
python app.py
```

A native desktop window will open after ~2 seconds.

### Step 7 — Upload Your Cookies

On first launch you'll see the **Welcome** screen:

1. **Drag and drop** your downloaded `cookies.txt` file onto the upload area (or click to browse)
2. The app saves this file permanently — you **won't need to re-upload** on future launches
3. After upload, you'll be taken to the main dashboard automatically

### Step 8 — Configure Your LLM (API Settings)

Click the **⚙️ gear icon** in the **top-right corner** to open the Settings panel:

| Setting | What to Choose |
|---|---|
| **Transcription Method** | `Local Whisper` (free, ~15s/video) or `Groq Whisper API` (fast, ~2s/video) |
| **Chat Model** | Pick any model from the dropdown (see table below) |
| **API Key** | Paste your **Groq** or **OpenAI** API key |

Click **Save Configuration** when done. Settings are saved to `.env` and persist across restarts.

### Step 9 — Scrape a TikTok Creator

1. Make sure you're on the **🔍 Scraper** tab (top center)
2. Enter a TikTok username in the input field (e.g. `@mrbeast`)
3. Set the number of videos to download (1–100, default: 10)
4. Click **Scrape Data**
5. Wait for the pipeline to finish — it will:
   - Download the videos
   - Extract and transcribe the audio
   - Embed the transcripts into the vector database
   - Auto-delete the video/audio files to save disk space

The scrape history appears in the **left sidebar**.

### Step 10 — Chat with the Data

1. Switch to the **💬 Chat** tab (top center)
2. Type a question about the scraped videos (e.g. *"What topics does this creator talk about?"*)
3. Press **Send** — the AI will search the vector database and answer using the transcripts as context

---

## 📦 Build as Executable (.exe)

You can package the app into a standalone `.exe` so it runs without Python installed.

### Build Steps

```bash
# Make sure you're in the project root with venv activated
pip install pyinstaller

# Run the build
python -m PyInstaller build.spec --noconfirm
```

### Output

```
dist/TikTokRAG/
├── TikTokRAG.exe     ← Double-click to run
└── _internal/        ← Required dependencies (keep next to .exe)
```

### Distributing

1. Zip the entire `dist/TikTokRAG/` folder
2. Share the zip file
3. The recipient must still have **FFmpeg** installed on their machine
4. On first run, the user will upload their `cookies.txt` through the app

> **Note:** The `_internal/` folder must always be in the same directory as `TikTokRAG.exe`.

---

## 📁 Project Structure

```
tiktok-rag-engine/
├── app.py              # FastAPI server + PyWebView desktop app
├── scraper.py          # yt-dlp video downloader
├── processor.py        # Audio extraction + transcription pipeline
├── embedder.py         # ChromaDB vector embedding
├── chat.py             # LiteLLM chat with RAG context
├── db.py               # SQLite database for scrape history
├── auth.py             # TikTok authentication helpers
├── config.py           # Configuration constants
├── build.spec          # PyInstaller build configuration
├── web/                # Frontend (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── logo.png
│   └── logo.ico
├── requirements.txt
├── cookies.txt         # Your TikTok session (created on upload)
├── tiktok_data.db      # SQLite scrape history (auto-created)
├── chroma_db/          # Vector database storage (auto-created)
└── .env                # Saved API keys & model preferences (auto-created)
```

---

## 🔑 Supported LLM Providers

| Provider | Model Examples | API Key Required | Notes |
|---|---|---|---|
| **Groq** | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `gemma2-9b-it` | Yes | [Free tier available](https://console.groq.com/) |
| **OpenAI** | `gpt-4o-mini`, `gpt-4o` | Yes | [Get key](https://platform.openai.com/api-keys) |
| **Ollama** | `llama3` | No | Runs 100% locally, [install Ollama](https://ollama.com/) first |

**Recommended for beginners:** Sign up at [console.groq.com](https://console.groq.com/) for a free API key, then select `Groq - Llama 3.1 8B` in the settings.

---

## 🧪 Running Tests

```bash
pytest
```

---

## ❓ Troubleshooting

| Problem | Solution |
|---|---|
| `ffmpeg not found` | Make sure FFmpeg is installed and added to your system PATH |
| Scraping stops at ~5 videos | Your cookies are expired — re-export from the browser extension |
| `ModuleNotFoundError` | Make sure your virtual environment is activated (`venv\Scripts\activate`) |
| Window doesn't open | Check if port 8000 is already in use by another app |
| `.exe` won't start | Make sure `_internal/` folder is next to `TikTokRAG.exe` |

---

## ⚠️ Disclaimer

This tool is for **educational and research purposes only**. Respect TikTok's Terms of Service and the content creators whose data you scrape. Do not use this tool for commercial purposes without proper authorization.