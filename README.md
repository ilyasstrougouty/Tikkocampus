<div align="center">
  <img src="web/logo.png" alt="Tikkocampus Logo" width="120">
  
  <h1>Tikkocampus 🚀</h1>
  
  <p><strong>Transform TikTok into your personal knowledge base.</strong></p>
  
  <p><em>Scrape, Transcribe, and Chat with creator content using local or cloud AI.</em></p>

  <div align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/RAG-Powered-FF6F61" alt="RAG">
    <img src="https://img.shields.io/badge/UI-PyWebView-6D28D9" alt="UI">
  </div>
</div>

---

## 🎬 Video Tutorial
> [!TIP]
> **New to Tikkocampus?** Watch our [Zero-to-Hero Quickstart Guide](https://link-to-your-video.com) to see how to set up your first local knowledge base in under 5 minutes.

---

## ⚙️ What is Tikkocampus?

Tikkocampus is a professional-grade **Retrieval-Augmented Generation (RAG)** pipeline designed for content researchers, data scientists, and power users. It allows you to ingest TikTok profiles and turn them into a searchable, interactive database.

- **Phase 1: Ingestion** – Automated high-speed downloading with smart IP rotation.
- **Phase 2: Intelligence** – Audio extraction and high-fidelity transcription (Local or Cloud).
- **Phase 3: Synthesis** – Semantic embedding into ChromaDB for instant contextual retrieval.
- **Phase 4: Interaction** – Conversational AI interface for deep content analysis.

---

## 🚀 One-Minute Setup

### 1. Prerequisites
- **Python 3.10+** (Add to PATH)
- **FFmpeg** (Required for audio processing. [Download here](https://www.gyan.dev/ffmpeg/builds/))

### 2. Fast Installation
```bash
# Clone and enter directory
git clone https://github.com/yourusername/tikkocampus.git
cd tikkocampus

# Create environment (Windows)
python -m venv venv
.\venv\Scripts\activate

# Install all components
pip install -r requirements.txt
```

### 3. Launch
```bash
python app.py
```

---

## 🦙 Going Local: Ollama & Llama 3
Tikkocampus is optimized for **100% local privacy**. Here is how to use it without any API keys:

1. **Install Ollama**: Download from [ollama.com](https://ollama.com/).
2. **Pull a Model**: Open your terminal and run:
   ```bash
   ollama run llama3
   ```
3. **Configure Tikkocampus**: 
   - Open the **⚙️ Gear Icon** in the app.
   - Select `Ollama - Llama 3 (Local)` from the dropdown.
   - Click **Save**. *No API key required!*

---

## 🛠️ Configuration Options

| Feature | Local (Free & Private) | Cloud (Fast & Scalable) |
|---|---|---|
| **Transcription** | `Local Whisper` | `Groq Whisper API` |
| **Chat Engine** | `Ollama / Llama 3` | `Groq / OpenAI` |
| **Vector DB** | `ChromaDB` (Local) | - |

---

## 📁 Repository Map
- `app.py`: Desktop interface & server orchestration.
- `scraper.py`: Secure TikTok ingestion engine.
- `processor.py`: Audio analysis & transcription.
- `embedder.py`: Semantic vectorization.
- `chat.py`: RAG logic and LLM integration.

---

## ❓ FAQ & Troubleshooting
- **Refused Connection?** Ensure the Ollama app is running in your taskbar.
- **Scraping Limits?** Use the built-in "Login" button to refresh your TikTok session.
- **FFmpeg Error?** Ensure `ffmpeg` is in your system PATH and try running `ffmpeg -version` in CMD.

---

<div align="center">
  <p>Built for the open-source community. 🌟 Please star our repo if you find it useful!</p>
</div>
