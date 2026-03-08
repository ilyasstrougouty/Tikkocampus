let pollInterval;

// --- UI Navigation ---
function showMainApp() {
    document.getElementById('login-view').style.display = 'none';
    document.getElementById('dashboard-view').style.display = 'flex';
    document.getElementById('chat-view').style.display = 'none';
    loadHistory();
    loadSettings();
}

function showDashboard() {
    document.getElementById('dashboard-view').style.display = 'flex';
    document.getElementById('chat-view').style.display = 'none';
    // Update tab styles
    document.getElementById('tab-dashboard').style.background = 'rgba(255,255,255,0.1)';
    document.getElementById('tab-dashboard').style.color = '#e2e8f0';
    document.getElementById('tab-dashboard').style.borderBottom = '2px solid #4ade80';
    document.getElementById('tab-chat').style.background = 'transparent';
    document.getElementById('tab-chat').style.color = '#64748b';
    document.getElementById('tab-chat').style.borderBottom = '2px solid transparent';
}

function showChat() {
    document.getElementById('dashboard-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'flex';
    // Update tab styles on chat view
    document.getElementById('tab-chat-2').style.background = 'rgba(255,255,255,0.1)';
    document.getElementById('tab-chat-2').style.color = '#e2e8f0';
    document.getElementById('tab-chat-2').style.borderBottom = '2px solid #4ade80';
    document.getElementById('tab-dashboard-2').style.background = 'transparent';
    document.getElementById('tab-dashboard-2').style.color = '#64748b';
    document.getElementById('tab-dashboard-2').style.borderBottom = '2px solid transparent';
}

// --- Load Saved Settings ---
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();

        // Pre-select the saved model
        const modelSelect = document.getElementById('model-select');
        if (data.model) {
            for (let opt of modelSelect.options) {
                if (opt.value === data.model) { opt.selected = true; break; }
            }
        }

        // Pre-select the saved transcription method
        const transcriptionSelect = document.getElementById('transcription-method');
        if (data.transcription_method) {
            for (let opt of transcriptionSelect.options) {
                if (opt.value === data.transcription_method) { opt.selected = true; break; }
            }
        }

        // Show active config status
        const statusEl = document.getElementById('settings-status');
        const modelLabel = modelSelect.options[modelSelect.selectedIndex].text;
        const transLabel = transcriptionSelect.options[transcriptionSelect.selectedIndex].text;
        const keyStatus = data.has_groq_key ? '🔑 Groq key saved' :
            data.has_openai_key ? '🔑 OpenAI key saved' : '⚠️ No API key set';

        statusEl.innerHTML = `<span style="color: #94a3b8;">Active: <b style="color:#e2e8f0">${modelLabel}</b> · <b style="color:#e2e8f0">${transLabel}</b> · ${keyStatus}</span>`;
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

// --- History ---
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const list = document.getElementById('history-list');

        if (!data.history || data.history.length === 0) {
            list.innerHTML = '<p style="color: #64748b; font-size: 13px; margin: 5px 0;">No previous scrapes yet.</p>';
            return;
        }

        list.innerHTML = data.history.map(item => {
            const date = new Date(item.scraped_at).toLocaleDateString();
            return `<div onclick="showChat()" 
                style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; margin: 4px 0; 
                border-radius: 8px; background: rgba(255,255,255,0.04); cursor: pointer; transition: 0.2s; border: 1px solid rgba(255,255,255,0.06);"
                onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.04)'">
                <span style="color: #e2e8f0; font-size: 13px;">@${item.creator_name || 'unknown'}</span>
                <span style="color: #64748b; font-size: 12px;">${item.video_count} videos · ${date}</span>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

// --- Method 1: App Login Flow ---
async function startAuthFlow() {
    const authBtn = document.getElementById('auth-btn');
    const statusText = document.getElementById('auth-status');

    authBtn.innerText = "Waiting for Login...";
    authBtn.disabled = true;
    statusText.innerText = "Please log in using the popup window...";
    statusText.style.color = "#fbbf24";

    try {
        const startResponse = await fetch('/api/auth', { method: 'POST' });

        if (!startResponse.ok) {
            const err = await startResponse.json();
            throw new Error(err.detail || "Authentication failed.");
        }

        statusText.innerText = "✅ Authentication Complete!";
        statusText.style.color = "#4ade80";
        authBtn.innerText = "Logged In";

        // Transition to main app
        setTimeout(showMainApp, 1000);

    } catch (error) {
        statusText.innerText = `❌ Auth Error: ${error.message}`;
        statusText.style.color = "#f87171";
        authBtn.innerText = "Login to TikTok";
        authBtn.disabled = false;
    }
}

// --- Method 2: Drag & Drop Cookies ---
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('cookie-file');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#4ade80';
    dropZone.style.background = 'rgba(74, 222, 128, 0.1)';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = 'rgba(255,255,255,0.2)';
    dropZone.style.background = 'transparent';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'rgba(255,255,255,0.2)';
    dropZone.style.background = 'transparent';

    if (e.dataTransfer.files.length) {
        handleFileUpload(e.dataTransfer.files[0]);
    }
});

async function handleFileUpload(file) {
    const statusText = document.getElementById('upload-status');

    if (!file || !file.name.endsWith('.txt')) {
        statusText.innerText = "❌ Please upload a valid cookies.txt file";
        statusText.style.color = "#f87171";
        return;
    }

    statusText.innerText = `Uploading ${file.name}...`;
    statusText.style.color = "#fbbf24";

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload-cookies', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Upload failed.");

        statusText.innerText = "✅ Cookies uploaded successfully!";
        statusText.style.color = "#4ade80";
        document.getElementById('drop-text').innerText = file.name;

        // Transition to main app
        setTimeout(showMainApp, 1000);
    } catch (error) {
        statusText.innerText = `❌ Error: ${error.message}`;
        statusText.style.color = "#f87171";
    }
}

async function startProcessing() {
    const target = document.getElementById('tiktok-url').value;
    const videoCount = parseInt(document.getElementById('video-count').value) || 10;
    const statusText = document.getElementById('process-status');
    const scrapeBtn = document.getElementById('scrape-btn');

    if (!target) return alert("Please enter a TikTok URL.");

    // Lock UI
    scrapeBtn.innerText = "Processing...";
    scrapeBtn.disabled = true;
    statusText.style.color = "#fbbf24";

    try {
        // 1. Tell the server to start the job
        const startResponse = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_url: target, max_videos: videoCount })
        });

        if (!startResponse.ok) {
            const err = await startResponse.json();
            throw new Error(err.detail || "Could not start job.");
        }

        // 2. Start Polling the Status every 2 seconds
        pollInterval = setInterval(async () => {
            const statusRes = await fetch('/api/status');
            const state = await statusRes.json();

            // Update the UI with real-time logs from the server
            statusText.innerText = state.status;

            // 3. Check if the job finished
            if (!state.is_running && state.status !== "Starting...") {
                if (state.error) {
                    clearInterval(pollInterval);
                    statusText.innerText = `❌ Error: ${state.error}`;
                    statusText.style.color = "#f87171";
                } else if (state.status === "failed") {
                    clearInterval(pollInterval);
                    statusText.innerText = `❌ Error: ${state.error}`;
                    statusText.style.color = "#f87171";
                } else if (state.status === "completed") {
                    clearInterval(pollInterval);
                    statusText.innerText = "✅ Processing Complete! Data ready.";
                    statusText.style.color = "#4ade80";
                    // Unlock the chat interface
                    document.getElementById('chat-input').disabled = false;
                    document.getElementById('send-btn').disabled = false;
                    loadHistory(); // Refresh history with the new scrape
                    // Auto-switch to chat page
                    setTimeout(() => showChat(), 1500);
                }

                // Unlock the scrape button
                scrapeBtn.innerText = "1. Scrape & Process Data";
                scrapeBtn.disabled = false;
            }
        }, 2000); // 2000 milliseconds = 2 seconds

    } catch (error) {
        statusText.innerText = `❌ API Error: ${error.message}`;
        statusText.style.color = "#f87171";
        scrapeBtn.disabled = false;
        scrapeBtn.innerText = "1. Scrape & Process Data";
    }
}

async function sendMessage() {
    const inputElement = document.getElementById("chat-input");
    const text = inputElement.value;

    if (text.trim() === "") return;

    const chatBox = document.getElementById("chat-box");

    // 1. Create and append the User's message bubble
    const userMsg = document.createElement("div");
    userMsg.className = "message user";
    userMsg.innerText = text;
    chatBox.appendChild(userMsg);

    // Clear the input
    inputElement.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // 2. Create a temporary "loading" bubble for the AI
    const loadingMsg = document.createElement("div");
    loadingMsg.className = "message ai glass-panel";
    loadingMsg.innerText = "Searching database...";
    chatBox.appendChild(loadingMsg);
    chatBox.scrollTop = chatBox.scrollHeight;

    // 3. Call the Python backend logic via standard REST!
    try {
        const fetchRes = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text })
        });

        if (!fetchRes.ok) throw new Error("Could not fetch response from AI.");

        const data = await fetchRes.json();
        const response = data.response;

        // 4. Update the loading bubble with the actual LLM response
        loadingMsg.innerText = response;
    } catch (e) {
        loadingMsg.innerText = `❌ Error: ${e.message}`;
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Allow pressing 'Enter' to send
document.getElementById("chat-input").addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

// --- LLM Settings ---
async function saveSettings() {
    const modelSelection = document.getElementById('model-select').value;
    const apiKey = document.getElementById('api-key-input').value;
    const transMethod = document.getElementById('transcription-method').value;
    const statusEl = document.getElementById('settings-status');

    try {
        const modelSelect = document.getElementById('model-select');
        const transcriptionSelect = document.getElementById('transcription-method');
        const modelLabel = modelSelect.options[modelSelect.selectedIndex].text;
        const transLabel = transcriptionSelect.options[transcriptionSelect.selectedIndex].text;

        if ((transMethod === 'groq_whisper' || modelSelection.startsWith('groq/') || modelSelection.startsWith('gpt')) && !apiKey) {
            statusEl.innerText = "⚠️ Please enter an API key.";
            statusEl.style.color = "#fbbf24";
            return;
        }

        statusEl.innerText = "Saving settings...";
        statusEl.style.color = "#fbbf24";

        const payload = {
            model: modelSelection,
            transcription_method: transMethod,
            api_key: apiKey
        };

        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Failed to save settings");

        statusEl.innerHTML = `✅ <b>Saved!</b> Chat: <b>${modelLabel}</b> · Transcription: <b>${transLabel}</b> · 🔑 Key stored`;
        statusEl.style.color = "#4ade80";

    } catch (e) {
        statusEl.innerText = `❌ Error: ${e.message}`;
        statusEl.style.color = "#f87171";
    }
}
