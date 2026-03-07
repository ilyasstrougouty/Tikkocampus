<div align="center">
  <img src="assets/banner.png" alt="TikTok RAG Engine Banner" width="100%">
  
  <p><em>An open-source pipeline to scrape, transcribe, and chat with TikTok videos locally.</em></p>
</div>

---

## ⚙️ Features

This project is a complete Retrieval-Augmented Generation (RAG) pipeline designed specifically for TikTok. It allows you to download a creator's archive, transcribe their audio locally, and query their knowledge base using the LLM of your choice.

* **Resilient Scraping Engine:** Uses `yt-dlp` to bypass brittle HTML selectors, with built-in rate limiting (randomized 5-15s delays) to prevent IP bans.
* **Local AI Transcription:** Automatically strips audio and uses `faster-whisper` to generate highly accurate text transcripts locally.
* **Vector Search:** Chunks and embeds transcripts into a local **ChromaDB** instance for instant semantic retrieval.
* **Bring Your Own Key (BYOK):** Powered by `LiteLLM`, allowing you to chat with the data using local models (Ollama), fast cloud APIs (Groq), or standard providers (OpenAI/Anthropic).
* **Modern Web UI:** A sleek, glassmorphism FastAPI web interface to control the scraping pipeline and chat with your data.
* **Aggressive Garbage Collection:** Automatically deletes massive `.mp4` and `.wav` files the millisecond they are processed, preventing disk bloat.

---

## 🚨 IMPORTANT: Browser Cookies Required

TikTok heavily restricts unauthenticated scraping. To pull more than the first ~5 videos off a profile, **you MUST provide a logged-in TikTok session.**

We rely on a `cookies.txt` file to authenticate the scraper instead of attempting automated browser extraction, which often fails or gets locked by modern OS encryption (like Windows DPAPI).

1.  Download the **"Get cookies.txt LOCALLY"** extension for your browser (Chrome/Firefox/Edge).
2.  Go to [tiktok.com](https://www.tiktok.com/) and ensure you are logged in.
3.  Click the extension and export your cookies.
4.  Save the downloaded file as exactly `cookies.txt` into the root of this project folder.

---

## 🛠️ Prerequisites

Before installing the Python packages, you **must** have FFmpeg installed on your system. The AI transcription model requires it to process the audio files.

* **Windows:** Download the pre-compiled binaries from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add them to your System PATH.
* **macOS:** `brew install ffmpeg`
* **Linux:** `sudo apt install ffmpeg`

---

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/tiktok-rag-engine.git](https://github.com/yourusername/tiktok-rag-engine.git)
   cd tiktok-rag-engine