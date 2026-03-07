let pollInterval;

// --- UI Navigation ---
function showMainApp() {
    document.getElementById('login-view').style.display = 'none';
    document.getElementById('main-view').style.display = 'flex';
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
            body: JSON.stringify({ target_url: target })
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
                clearInterval(pollInterval); // Stop polling

                if (state.error) {
                    statusText.innerText = `❌ Error: ${state.error}`;
                    statusText.style.color = "#f87171";
                } else {
                    statusText.innerText = "✅ Processing Complete! Data ready.";
                    statusText.style.color = "#4ade80";
                    // Unlock the chat interface
                    document.getElementById('chat-input').disabled = false;
                    document.getElementById('send-btn').disabled = false;
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
