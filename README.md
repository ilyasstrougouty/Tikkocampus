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

You need **Python 3.10+** and **FFmpeg** installed before starting.

### Install FFmpeg

| OS | Command |
|---|---|
| **Windows** | Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) → add to System PATH |
| **macOS** | `brew install ffmpeg` |
| **Linux** | `sudo apt install ffmpeg` |

To verify: run `ffmpeg -version` in your terminal.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/tiktok-rag-engine.git
cd tiktok-rag-engine
```

```bash
python -m venv venv
```

Activate the virtual environment:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### 2. Get Your TikTok Cookies

TikTok blocks unauthenticated scraping after ~5 videos. You **must** provide a logged-in session via cookies.

1. Install the **"Get cookies.txt LOCALLY"** browser extension ([Chrome](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) / Firefox / Edge)
2. Go to [tiktok.com](https://www.tiktok.com/) and make sure you're **logged in**
3. Click the extension icon → **Export** cookies
4. You'll upload this file in the app (see step 4 below)

### 3. Launch the App

```bash
python app.py
```

A desktop window will open automatically.

### 4. Upload Cookies

On first launch you'll see the **Welcome** screen. Drag and drop your `cookies.txt` file (or click to browse). The file is saved permanently — you won't need to upload it again on future launches.

### 5. Configure Your LLM

Click the **⚙️ gear icon** (top-right corner) to open the Settings panel:

- **Transcription Method** — Choose between local Whisper or Groq Whisper API
- **Chat Model** — Select your preferred LLM (Groq, OpenAI, Ollama)
- **API Key** — Paste your Groq or OpenAI API key

Click **Save Configuration** to persist your settings.

### 6. Scrape & Chat

1. On the **🔍 Scraper** tab, enter a TikTok username (e.g. `@mrbeast`)
2. Set the number of videos to download (default: 10)
3. Click **Scrape Data** — the pipeline will download, transcribe, and index everything
4. Switch to the **💬 Chat** tab and ask questions about the videos!

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
├── web/                # Frontend (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── logo.png
│   └── logo.ico
├── requirements.txt
├── cookies.txt         # Your TikTok session (created on upload)
├── tiktok_data.db      # SQLite scrape history
├── chroma_db/          # Vector database storage
└── .env                # Saved API keys & model preferences
```

---

## 🔑 Supported LLM Providers

| Provider | Model Examples | API Key Required |
|---|---|---|
| **Groq** | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `gemma2-9b-it` | Yes (free tier available) |
| **OpenAI** | `gpt-4o-mini`, `gpt-4o` | Yes |
| **Ollama** | `llama3` (runs locally) | No |

Get a free Groq API key at [console.groq.com](https://console.groq.com/).

---

## 🧪 Running Tests

```bash
pytest
```

---

## ⚠️ Disclaimer

This tool is for **educational and research purposes only**. Respect TikTok's Terms of Service and the content creators whose data you scrape. Do not use this tool for commercial purposes without proper authorization.