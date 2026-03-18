<div align="center">
  <img src="assets/banner.png" alt="Tikkocampus Banner">
  
  <p><strong>Transform TikTok into your personal knowledge base.</strong></p>
  
  <p><em>Scrape, Transcribe, and Chat with creator content using local or cloud AI.</em></p>

  <div align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/RAG-Powered-FF6F61" alt="RAG">
    <img src="https://img.shields.io/badge/UI-Electron-4786D1?logo=electron&logoColor=white" alt="UI">
  </div>
</div>

---

## 📦 Downloads (Executables)

🚀 **Download the latest v1.0.2 release for your OS:**

- **Windows (.exe)**: [Download Tikkocampus Installer](https://github.com/ilyasstrougouty/Tikkocampus/releases/latest/download/Tikkocampus-v1.0.2-Setup.exe)  
- **macOS (.dmg)**: [Download Tikkocampus DMG](https://github.com/ilyasstrougouty/Tikkocampus/releases/latest/download/Tikkocampus-v1.0.2.dmg)
- **Linux (AppImage)**: [Download Tikkocampus AppImage](https://github.com/ilyasstrougouty/Tikkocampus/releases/latest/download/Tikkocampus-v1.0.2.AppImage)

> [!NOTE]  
> If the links above haven't finished building yet, you can also find them on the [Releases Page](https://github.com/ilyasstrougouty/Tikkocampus/releases).

---

## 🛠️ Next Steps

We're constantly improving Tikkocampus. Here's what's coming next:

1. **Hardware Acceleration**: Better support for Mac Silicon (Metal) and Windows (NVIDIA/AMD) local inference.
2. **Improved Search**: Hybrid search combining BM25 keyword matching with semantic embeddings.
3. **Multi-Platform Scraping**: Expanding beyond TikTok to YouTube Shorts and Instagram Reels.
4. **Desktop UI Polish**: Theme customization and a more refined "Discovery" tab.

---

## ⚙️ What is Tikkocampus?

Tikkocampus is a professional-grade **Retrieval-Augmented Generation (RAG)** pipeline designed for content researchers and fans. It allows you to ingest TikTok profiles and turn them into a searchable, interactive database.

- **Ingestion**: High-speed video and metadata scraping.
- **Intelligence**: High-fidelity transcription (Local or Cloud).
- **Search**: Semantic indexing into ChromaDB for instant contextual retrieval.
- **Chat**: A sleek conversational interface to "talk" to your favorite creators.

---

## 🚀 Dev Setup & Installation

If you prefer to run from source:

### 1. Requirements
- **Node.js 18+**
- **Python 3.10+**
- **FFmpeg** (For audio parsing. [Download](https://www.gyan.dev/ffmpeg/builds/))

### 2. Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Electron dependencies
cd electron-app
npm install
```

### 3. Launch
```bash
# In the electron-app directory:
npm start
```

---

## 🆓 Option 1: 100% Free (Using Groq API)
Groq offers an incredibly fast and **completely free** tier for developers.

1.  **Get a Key**: Register at [console.groq.com](https://console.groq.com/) and create a free API Key.
2.  **Configure**: 
    - Open Tikkocampus and click the **⚙️ Settings** icon.
    - Select `Groq - Llama 3.1 8B` (or 70B) as the model.
    - Set Transcription to `Groq Whisper API` (Fastest).
    - Paste your key and click **Save**.

---

## 💎 Option 2: High Performance (Paid Models)
For the highest accuracy and reasoning capabilities, use OpenAI's flagship models.

1.  **Get a Key**: Obtain an API key from your [OpenAI Dashboard](https://platform.openai.com/).
2.  **Configure**:
    - Select `GPT-4o` or `GPT-4o Mini` in Settings.
    - Paste your OpenAI key and click **Save**.
    - *Note: This requires a paid OpenAI account with available credits.*

---

## 🏠 Option 3: Fully Private & Local (Ollama)
No internet? No problem. Use Ollama to run everything on your own hardware.

1.  **Install**: Download [ollama.com](https://ollama.com/).
2.  **Run**: `ollama run llama3` in your terminal.
3.  **Configure**: Select `Ollama - Llama 3 (Local)` in the app settings.

---

## 📁 Project Structure
- `electron-app/`: Native desktop interface.
- `app.py`: Backend FastAPI server.
- `scraper.py`: TikTok data acquisition.
- `processor.py`: Audio & transcription logic.
- `embedder.py`: Semantic search engine.
- `chat.py`: AI communication layer.

---

<div align="center">
  <p>Built for the open-source community. 🌟 Please star our repo if you find it useful!</p>
</div>