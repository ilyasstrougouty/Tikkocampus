let pollInterval;
let currentCreator = null;
let apiState = {
    has_groq_key: false,
    has_openai_key: false
};

// --- UI Navigation ---
function setCreator(creatorName) {
    currentCreator = creatorName;
    const chatInput = document.getElementById('chat-input');
    const chatHeader = document.getElementById('active-creator-header');

    if (chatInput) {
        chatInput.placeholder = `Ask about @${creatorName}...`;
    }
    if (chatHeader) {
        chatHeader.innerText = `@${creatorName}`;
    }
}

async function showMainApp() {
    // Validate session before showing the app
    const isValid = await validateSession();
    if (!isValid) return;

    document.getElementById('login-view').style.display = 'none';
    const appContainer = document.getElementById('dashboard-view');
    appContainer.style.display = 'flex';
    appContainer.style.animation = "fadeIn 0.5s ease";
    loadHistory();
    loadSettings();
}

async function validateSession() {
    try {
        const res = await fetch('/api/validate-session');
        const data = await res.json();
        if (!data.valid) {
            console.warn("Session invalid:", data.error || "Redirected to login");
            // Switch back to login view
            document.getElementById('login-view').style.display = 'flex';
            document.getElementById('dashboard-view').style.display = 'none';
            document.getElementById('chat-view').style.display = 'none';
            
            const status = document.getElementById('login-status');
            if (status) {
                status.style.display = "block";
                status.style.color = "#f87171";
                status.innerText = "⚠️ Session expired or invalid. Please log in again.";
            }
            return false;
        }
        return true;
    } catch (e) {
        console.error("Validation failed:", e);
        return false;
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('history-sidebar');
    if (sidebar.style.left === '0px') {
        sidebar.style.left = '-300px';
    } else {
        sidebar.style.left = '0px';
        loadHistory(); // refresh on open
    }
}

function startNewScrape() {
    toggleSidebar();
    showDashboard();
}

async function showDashboard() {
    if (!(await validateSession())) return;
    document.getElementById('dashboard-view').style.display = 'flex';
    document.getElementById('chat-view').style.display = 'none';
    // Update tab styles
    document.getElementById('tab-dashboard').style.background = 'rgba(255,255,255,0.1)';
    document.getElementById('tab-dashboard').style.color = 'white';
    document.getElementById('tab-chat').style.background = 'transparent';
    document.getElementById('tab-chat').style.color = '#a1a1aa';
}

async function showChat() {
    if (!(await validateSession())) return;
    document.getElementById('dashboard-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'flex';
    // Update tab styles
    document.getElementById('tab-chat').style.background = 'rgba(255,255,255,0.1)';
    document.getElementById('tab-chat').style.color = 'white';
    document.getElementById('tab-dashboard').style.background = 'transparent';
    document.getElementById('tab-dashboard').style.color = '#a1a1aa';
}

function toggleSettings() {
    const sidebar = document.getElementById('settings-sidebar');
    if (sidebar.style.right === '0px') {
        sidebar.style.right = '-350px';
    } else {
        sidebar.style.right = '0px';
        updateKeyPlaceholder();
    }
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

        // Store saved state
        apiState.has_groq_key = data.has_groq_key;
        apiState.has_openai_key = data.has_openai_key;

        // Show active config status
        const statusEl = document.getElementById('settings-status');
        const modelLabel = modelSelect.options[modelSelect.selectedIndex].text;
        const transLabel = transcriptionSelect.options[transcriptionSelect.selectedIndex].text;
        const keyStatus = data.has_groq_key ? '🔑 Groq key saved' :
            data.has_openai_key ? '🔑 OpenAI key saved' : '⚠️ No API key set';

        statusEl.innerHTML = `<span style="color: #94a3b8;">Active: <b style="color:#e2e8f0">${modelLabel}</b> · <b style="color:#e2e8f0">${transLabel}</b> · ${keyStatus}</span>`;
        updateKeyPlaceholder();
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
            const creator = item.creator_name || 'unknown';
            return `
            <div onclick="setCreator('${creator}'); showChat(); document.getElementById('history-sidebar').style.left='-300px';" 
                style="display: flex; flex-direction: column; gap: 5px; padding: 12px; margin: 4px 0; 
                border-radius: 12px; background: rgba(255,255,255,0.03); cursor: pointer; transition: 0.2s; border: 1px solid rgba(255,255,255,0.05);"
                onmouseover="this.style.background='rgba(255,255,255,0.08)'" onmouseout="this.style.background='rgba(255,255,255,0.03)'">
                
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color: #f4f4f5; font-weight: 600; font-size: 14px;">@${item.creator_name || 'unknown'}</span>
                        <span style="font-size: 10px; background: rgba(94, 234, 212, 0.1); color: #5eead4; padding: 2px 6px; border-radius: 10px;">Ready</span>
                    </div>
                    <button onclick="event.stopPropagation(); deleteCreator('${creator}')" 
                        style="background: transparent; border: none; font-size: 14px; cursor: pointer; color: #64748b; padding: 4px; border-radius: 4px; display: flex; align-items: center; justify-content: center; transition: 0.2s;"
                        onmouseover="this.style.color='#f87171'; this.style.background='rgba(248, 113, 113, 0.1)'"
                        onmouseout="this.style.color='#64748b'; this.style.background='transparent'" title="Delete Creator">
                        🗑️
                    </button>
                </div>
                <div style="color: #a1a1aa; font-size: 12px; display: flex; justify-content: space-between;">
                    <span>${item.video_count} videos</span>
                    <span>${date}</span>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

async function deleteCreator(creatorName) {
    if (!confirm(`Are you sure you want to permanently delete @${creatorName} and all associated videos?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/history/${creatorName}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            // Optional: If they just deleted the creator they are actively chatting with, clear the chat
            if (currentCreator === creatorName) {
                setCreator("All Data"); // Or however you want to handle default state
                document.getElementById('chat-box').innerHTML = `
                    <div class="message ai" style="max-width: 80%; padding: 16px; border-radius: 16px; border-bottom-left-radius: 4px; line-height: 1.5; font-size: 14px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); color: #d4d4d8; margin-bottom: 20px;">
                        Creator deleted. Select a new creator from the sidebar to continue chatting.
                    </div>`;
            }
            loadHistory(); // Refresh the sidebar
        } else {
            const data = await res.json();
            alert(`Failed to delete: ${data.detail || 'Unknown error'}`);
        }
    } catch (e) {
        console.error("Delete failed:", e);
        alert("Delete failed. See console for details.");
    }
}

// --- Session Management ---
async function loadCookieSessions() {
    try {
        const res = await fetch('/api/list-cookies');
        const data = await res.json();

        const container = document.getElementById('existing-sessions-container');
        const list = document.getElementById('cookie-list');

        if (data.cookies && data.cookies.length > 0) {
            container.style.display = 'block';
            list.innerHTML = '';

            // LIMIT TO 4 MOST RECENT
            const recentCookies = data.cookies.slice(0, 4);

            recentCookies.forEach(cookie => {
                const btn = document.createElement('div');
                btn.style.cssText = `
                    display: flex; justify-content: space-between; align-items: center; 
                    padding: 12px 15px; background: rgba(0,0,0,0.2); 
                    border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; 
                    cursor: pointer; transition: all 0.2s;
                `;
                btn.onmouseover = () => {
                    btn.style.background = 'rgba(94, 234, 212, 0.05)';
                    btn.style.borderColor = 'rgba(94, 234, 212, 0.3)';
                };
                btn.onmouseout = () => {
                    btn.style.background = 'rgba(0,0,0,0.2)';
                    btn.style.borderColor = 'rgba(255,255,255,0.05)';
                };
                
                // Clicking the main body selects the cookie
                btn.onclick = () => selectCookie(cookie.filename);

                btn.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 18px;">🍪</span>
                        <div style="display: flex; flex-direction: column;">
                            <span style="color: #f4f4f5; font-size: 14px; font-weight: 500;">Session</span>
                            <span style="color: #a1a1aa; font-size: 12px;">${cookie.created_at}</span>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="color: #5eead4; font-size: 12px; font-weight: 600;">Select ➔</span>
                        <button onclick="event.stopPropagation(); deleteCookie('${cookie.filename}')" 
                                style="background: transparent; border: none; font-size: 14px; cursor: pointer; color: #64748b; padding: 4px; border-radius: 4px; display: flex; align-items: center; justify-content: center; transition: 0.2s;"
                                onmouseover="this.style.color='#f87171'; this.style.background='rgba(248, 113, 113, 0.1)'"
                                onmouseout="this.style.color='#64748b'; this.style.background='transparent'" title="Delete Session">
                            🗑️
                        </button>
                    </div>
                `;
                list.appendChild(btn);
            });
        } else {
            container.style.display = 'none';
        }
    } catch (e) {
        console.error('Could not load cookie sessions:', e);
    }
}

async function deleteCookie(filename) {
    if (!confirm(`Permanently delete this session file (${filename})?`)) return;
    
    try {
        const res = await fetch(`/api/cookies/${filename}`, { method: 'DELETE' });
        if (res.ok) {
            loadCookieSessions();
        } else {
            const data = await res.json();
            alert(`Delete failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (e) {
        console.error('Delete error:', e);
    }
}

async function selectCookie(filename) {
    try {
        const res = await fetch('/api/select-cookie', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });

        if (res.ok) {
            showMainApp();
        } else {
            console.error('Failed to select cookie');
        }
    } catch (e) {
        console.error('API error selecting cookie:', e);
    }
}

// --- Native TikTok Login Flow ---
async function triggerLogin() {
    const btn = document.getElementById('native-login-btn');
    const status = document.getElementById('login-status');
    btn.disabled = true;
    btn.innerText = "Waiting for Login Window...";
    status.style.display = "block";
    status.style.color = "#fbbf24";
    status.innerText = "Please complete the login in the pop-up window...";

    try {
        const res = await fetch('/api/auth', { method: 'POST' });
        
        if (res.ok) {
            status.innerText = "✅ Successfully logged in!";
            status.style.color = "#4ade80";
            
            // Wait for 1 second, then reload sessions
            setTimeout(loadCookieSessions, 1000);
            
            // Auto redirect to main app immediately as per request
            setTimeout(showMainApp, 1500);
        } else {
            const data = await res.json();
            throw new Error(data.detail || "Login failed");
        }
    } catch (e) {
        status.innerText = `❌ Error: ${e.message}`;
        status.style.color = "#f87171";
    } finally {
        btn.disabled = false;
        btn.innerText = "Log In with TikTok";
    }
}

// Run on page load
async function initApp() {
    // 1. Initial Load of sessions
    loadCookieSessions();
    
    // 2. Settings Listeners
    document.getElementById('model-select').addEventListener('change', updateKeyPlaceholder);
    document.getElementById('transcription-method').addEventListener('change', updateKeyPlaceholder);

    // 3. Check if we already have an active cookies.txt session AND if it's valid
    try {
        const res = await fetch('/api/check-cookies');
        const data = await res.json();
        if (data.exists) {
            console.log("Active session found. Validating...");
            const isValid = await validateSession();
            if (isValid) {
                showMainApp();
            }
        }
    } catch (e) {
        console.error("Check cookies failed:", e);
    }
}

document.addEventListener('DOMContentLoaded', initApp);

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

        // Refresh the list instead of skipping straight to the app
        setTimeout(loadCookieSessions, 500);
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

                    // Use the creator name reported by the server
                    if (state.creator_name) {
                        setCreator(state.creator_name);
                    } else {
                        // Fallback only if server didn't report it
                        let extracted = target.split('@').pop().split(/[\/\?]/)[0] || target;
                        setCreator(extracted);
                    }

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
            body: JSON.stringify({
                query: text,
                creator_name: currentCreator
            })
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
function updateKeyPlaceholder() {
    const model = document.getElementById('model-select').value;
    const trans = document.getElementById('transcription-method').value;
    const input = document.getElementById('api-key-input');
    const statusEl = document.getElementById('settings-status');

    let needsGroq = model.startsWith('groq/') || trans === 'groq_whisper';
    let needsOpenAI = model.startsWith('gpt') || model.startsWith('openai');

    if ((needsGroq && apiState.has_groq_key) || (needsOpenAI && apiState.has_openai_key)) {
        input.placeholder = "🔑 API Key Saved (Enter new to overwrite)";
    } else if (needsGroq || needsOpenAI) {
        input.placeholder = "Paste Groq/OpenAI key...";
    } else {
        input.placeholder = "No key required for local models";
        statusEl.innerText = ""; // Clear warning if we switch to local
    }
}

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

        let needsGroq = modelSelection.startsWith('groq/') || transMethod === 'groq_whisper';
        let needsOpenAI = modelSelection.startsWith('gpt') || modelSelection.startsWith('openai');

        // Smarter validation: only block if NO key exists (neither in input nor on server)
        if (needsGroq && !apiKey && !apiState.has_groq_key) {
            statusEl.innerText = "⚠️ Please enter a Groq API key.";
            statusEl.style.color = "#fbbf24";
            return;
        }
        if (needsOpenAI && !apiKey && !apiState.has_openai_key) {
            statusEl.innerText = "⚠️ Please enter an OpenAI API key.";
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

        // Update local state if a new key was provided
        if (apiKey) {
            if (needsGroq) apiState.has_groq_key = true;
            if (needsOpenAI) apiState.has_openai_key = true;
            document.getElementById('api-key-input').value = ""; // Clear input after successful save
        }

        statusEl.innerHTML = `✅ <b>Saved!</b> Chat: <b>${modelLabel}</b> · Transcription: <b>${transLabel}</b> · 🔑 Key stored`;
        statusEl.style.color = "#4ade80";
        updateKeyPlaceholder();

    } catch (e) {
        statusEl.innerText = `❌ Error: ${e.message}`;
        statusEl.style.color = "#f87171";
    }
}
