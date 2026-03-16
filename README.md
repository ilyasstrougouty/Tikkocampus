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

## ⚙️ What is Tikkocampus?

Tikkocampus is a professional-grade **Retrieval-Augmented Generation (RAG)** pipeline designed for content researchers and fans. It allows you to ingest TikTok profiles and turn them into a searchable, interactive database.

- **Ingestion**: High-speed video and metadata scraping.
- **Intelligence**: High-fidelity transcription (Local or Cloud).
- **Search**: Semantic indexing into ChromaDB for instant contextual retrieval.
- **Chat**: A sleek conversational interface to "talk" to your favorite creators.

---

## 🚀 Easy Launch (Get started in 3 steps)

### 1. Requirements
- **Python 3.10+**
- **FFmpeg** (For audio parsing. [Download](https://www.gyan.dev/ffmpeg/builds/))

### 2. Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

### 3. Start
```bash
python app.py
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
- `app.py`: Main application launcher.
- `scraper.py`: TikTok data acquisition.
- `processor.py`: Audio & transcription logic.
- `embedder.py`: Semantic search engine.
- `chat.py`: AI communication layer.

---

<div align="center">
  <p>Built for the open-source community. 🌟 Please star our repo if you find it useful!</p>
</div>
