let pollInterval;
let deleteModalResolve;
let currentCreator = null;
let apiState = {
    has_groq_key: false,
    has_openai_key: false,
    has_transcription_key: false
};

const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const originalIcon = btn.innerHTML;
        btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = originalIcon;
            btn.classList.remove('copied');
        }, 2000);
    });
}

// --- Custom Modal Logic ---
function showDeleteModal(creatorName, message = null) {
    const modal = document.getElementById('delete-modal');
    const nameSpan = document.getElementById('delete-creator-name');
    const msgPara = modal.querySelector('p.text-sm');
    
    if (nameSpan) nameSpan.innerText = `@${creatorName}`;
    
    if (message) {
        msgPara.innerHTML = message;
    } else {
        msgPara.innerHTML = `Are you sure you want to delete <span id="delete-creator-name" class="text-brand font-bold">@${creatorName}</span>? Please know that you cannot restore this action once confirmed.`;
    }

    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('show'), 10);

    return new Promise((resolve) => {
        deleteModalResolve = resolve;
    });
}

function closeDeleteModal(confirmed) {
    const modal = document.getElementById('delete-modal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.classList.add('hidden');
        if (deleteModalResolve) {
            deleteModalResolve(confirmed);
            deleteModalResolve = null;
        }
    }, 300);
}

// --- UI Navigation ---
async function setCreator(creatorName, creatorNickname = null) {
    currentCreator = creatorName;
    const chatInput = document.getElementById('chat-input');
    const chatTitle = document.getElementById('chat-title');
    const chatSubtitle = document.getElementById('chat-subtitle');
    const headerName = document.getElementById('active-creator-header');
    const chatBox = document.getElementById('chat-box');
    
    const displayName = creatorNickname || creatorName;

    // Reset chat box for a fresh experience
    if (chatBox) {
        chatBox.innerHTML = `
            <div id="chat-placeholder" class="font-typewriter text-lg opacity-30 select-none">
                Hey, ask about ${displayName}
            </div>
        `;
    }

    if (chatInput) {
        chatInput.classList.remove('shrunk');
        chatInput.placeholder = `Ask @${creatorName}...`;
    }
    document.body.classList.remove('chat-active');
    
    if (chatTitle) {
        chatTitle.innerText = displayName;
    }

    if (headerName) {
        headerName.innerText = `@${creatorName}`;
        if (chatSubtitle) chatSubtitle.classList.remove('hidden');
    }

    // Load Chat History
    if (creatorName !== "All Data") {
        try {
            const res = await fetch(`${API_BASE}/api/chat/history/${creatorName}`);
            const data = await res.json();
            if (data.messages && data.messages.length > 0) {
                // Clear the placeholder
                document.getElementById('chat-placeholder')?.remove();
                
                // Add chat active classes
                if (chatInput) chatInput.classList.add('shrunk');
                document.body.classList.add('chat-active');

                // Render history
                data.messages.forEach(msg => {
                    const msgDiv = document.createElement("div");
                    if (msg.role === "user") {
                        msgDiv.className = "message user";
                        msgDiv.innerText = msg.content;
                        chatBox.appendChild(msgDiv);
                    } else if (msg.role === "ai") {
                        const loadingMsgContainer = document.createElement("div");
                        loadingMsgContainer.className = "message ai";
                        
                        const textCont = document.createElement("div");
                        textCont.className = "markdown-content"; 
                        textCont.innerHTML = marked.parse(msg.content);
                        loadingMsgContainer.appendChild(textCont);
                        
                        const copyBtn = document.createElement("button");
                        copyBtn.className = "copy-btn";
                        copyBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>`;
                        copyBtn.onclick = () => copyToClipboard(textCont.innerText, copyBtn);
                        loadingMsgContainer.appendChild(copyBtn);

                        chatBox.appendChild(loadingMsgContainer);
                    }
                });
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        } catch (e) {
            console.error("Failed to load chat history", e);
        }
    }
}

async function showMainApp() {
    // Validate session before showing the app
    const isValid = await validateSession();
    if (!isValid) return;

    document.getElementById('login-view').style.display = 'none';
    showDashboard(); // Default view
    loadSettings();
}

let lastValidationTime = 0;
const VALIDATION_CACHE_MS = 30000; // 30 seconds cache

async function validateSession(force = false) {
    const now = Date.now();
    if (!force && (now - lastValidationTime < VALIDATION_CACHE_MS)) {
        return true; 
    }

    try {
        const res = await fetch(`${API_BASE}/api/validate-session`);
        const data = await res.json();
        if (!data.valid) {
            console.warn("Session invalid:", data.error || "Redirected to login");
            
            // Revert UI to login
            document.getElementById('login-view').style.display = 'flex';
            document.getElementById('dashboard-view').classList.add('hidden');
            document.getElementById('chat-view').classList.add('hidden');
            
            const status = document.getElementById('login-status');
            if (status) {
                status.style.display = "block";
                status.style.color = "#f87171";
                status.innerText = "⚠️ Session expired or invalid. Please log in again.";
            }
            return false;
        }
        lastValidationTime = now;
        return true;
    } catch (e) {
        console.error("Validation failed:", e);
        return false;
    }
}

function updateNavStates(activeId) {
    const navItems = {
        'nav-home': 'nav-home',
        'nav-chat': 'nav-chat'
    };

    Object.entries(navItems).forEach(([key, navId]) => {
        const navEl = document.getElementById(navId);
        if (!navEl) return;
        
        if (navId === activeId) {
            navEl.classList.add('nav-active');
            navEl.classList.remove('nav-inactive');
        } else {
            navEl.classList.add('nav-inactive');
            navEl.classList.remove('nav-active');
        }
    });
}

function showDashboard() {
    // Optimistic UI update
    document.getElementById('dashboard-view').classList.remove('hidden');
    document.getElementById('chat-view').classList.add('hidden');
    document.getElementById('creators-view').classList.add('hidden');
    updateNavStates('nav-home');
    
    // Background tasks
    validateSession(); 
    loadHistory();
}

async function showCreators() {
    // Optimistic UI update
    document.getElementById('dashboard-view').classList.add('hidden');
    document.getElementById('chat-view').classList.add('hidden');
    document.getElementById('creators-view').classList.remove('hidden');
    updateNavStates('nav-chat');
    
    // Background tasks
    validateSession();
    renderCreatorsGrid();
}

async function renderCreatorsGrid() {
    const grid = document.getElementById('creators-grid');
    grid.innerHTML = '<div class="col-span-full text-center py-20 opacity-50 font-typewriter">Loading creators...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/api/history`);
        const data = await res.json();
        
        if (!data.history || data.history.length === 0) {
            grid.innerHTML = '<div class="col-span-full text-center py-20 opacity-50 font-typewriter">No creators indexed yet. Start by scraping a profile!</div>';
            return;
        }

        grid.innerHTML = data.history.map(item => {
            const creator = item.creator_name || 'unknown';
            const nickname = item.creator_nickname || creator;
            const initial = nickname.charAt(0).toUpperCase();
            
            return `
            <div class="creator-card" onclick="setCreator('${creator}', '${nickname.replace(/'/g, "\\'")}'); showChat();">
                <button onclick="event.stopPropagation(); deleteCreator('${creator}')" class="creator-delete-btn" title="Delete Data">
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                </button>
                <div class="creator-avatar">${initial}</div>
                <div class="creator-handle">@${creator}</div>
                <div class="creator-nickname">${nickname}</div>
                <div class="creator-stats">
                    <span class="stat-pill">${item.video_count} Videos</span>
                    <span class="stat-pill">Ready</span>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load creators grid:', e);
        grid.innerHTML = '<div class="col-span-full text-center py-20 text-brand">Error loading creators.</div>';
    }
}

function showChat() {
    // Optimistic UI update
    document.getElementById('dashboard-view').classList.add('hidden');
    document.getElementById('creators-view').classList.add('hidden');
    document.getElementById('chat-view').classList.remove('hidden');
    updateNavStates('nav-chat');
    
    // Background tasks
    validateSession();
}

function toggleSettings() {
    const sidebar = document.getElementById('settings-sidebar');
    sidebar.classList.toggle('show');
    if (sidebar.classList.contains('show')) {
        updateKeyPlaceholder();
    }
}

// --- Reset Scraper UI ---
function resetScraper() {
    const formArea = document.getElementById('scraper-form-area');
    const successArea = document.getElementById('scraper-success-area');
    if (formArea) formArea.classList.remove('hidden');
    if (successArea) successArea.classList.add('hidden');
    
    // Clear URL but DO NOT reset video count so user's preference is saved
    const targetUrl = document.getElementById('tiktok-url');
    if (targetUrl) targetUrl.value = '';
    
    const scrapeBtn = document.getElementById('scrape-btn');
    if (scrapeBtn) {
        scrapeBtn.disabled = false;
        scrapeBtn.innerHTML = '<i class="fa-solid fa-bolt mr-2"></i> 1. Scrape & Process Data';
        scrapeBtn.classList.remove('bg-red-500', 'hover:bg-red-600');
        scrapeBtn.classList.add('bg-brand', 'hover:bg-brandHover');
        scrapeBtn.onclick = startProcessing;
    }
    
    const term = document.getElementById('process-status');
    if (term) {
        term.innerText = "Status: waiting for input...";
        term.style.color = "inherit";
    }
}

// --- Load Saved Settings ---
async function loadSettings() {
    try {
        const res = await fetch(`${API_BASE}/api/settings`);
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
        apiState.has_transcription_key = data.has_transcription_key;

        // Show active config status
        const statusEl = document.getElementById('settings-status');
        const modelLabel = modelSelect.options[modelSelect.selectedIndex].text;
        const transLabel = transcriptionSelect.options[transcriptionSelect.selectedIndex].text;
        const keyStatus = data.has_groq_key ? '🔑 Groq key saved' :
            data.has_openai_key ? '🔑 OpenAI key saved' : '⚠️ No API key set';

        statusEl.innerHTML = `Active: <b>${modelLabel}</b> · <b>${transLabel}</b> · ${keyStatus}`;
        updateKeyPlaceholder();
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

// --- History ---
async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/history`);
        const data = await res.json();
        const list = document.getElementById('history-list');

        if (!data.history || data.history.length === 0) {
            list.innerHTML = '<p style="color: #64748b; font-size: 13px; margin: 5px 0;">No previous scrapes yet.</p>';
            return;
        }

        list.innerHTML = data.history.map(item => {
            const date = new Date(item.scraped_at).toLocaleDateString();
            const creator = item.creator_name || 'unknown';
            const nickname = item.creator_nickname || creator;
            return `
            <div class="history-item border border-borderDark rounded-lg p-3 bg-white/5 hover:bg-white/10 transition-colors cursor-pointer group" onclick="setCreator('${creator}', '${nickname.replace(/'/g, "\\'")}'); showChat();">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-sm font-medium text-white">${nickname}</span>
                    <button onclick="event.stopPropagation(); deleteCreator('${creator}')" 
                        class="text-textMuted opacity-0 group-hover:opacity-100 transition-opacity hover:text-brand">
                        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path>
                        </svg>
                    </button>
                </div>
                <div class="text-[10px] text-textMuted mb-2">@${creator} · ${item.video_count} VIDEOS</div>
                <div class="flex justify-between items-center text-xs text-textMuted">
                    <span class="opacity-60">${date}</span>
                    <span class="bg-badgeBg text-badgeText px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide">Ready</span>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

async function deleteCreator(creatorName) {
    const confirmed = await showDeleteModal(creatorName);
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/api/history/${creatorName}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            // Optional: If they just deleted the creator they are actively chatting with, clear the chat
            if (currentCreator === creatorName) {
                setCreator("All Data"); // Or however you want to handle default state
                document.getElementById('chat-box').innerHTML = `
                    <div class="message ai flex gap-4 max-w-[85%] font-typewriter">
                        <div class="w-8 h-8 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0 border border-brand/20 text-brand">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </div>
                        <div class="bg-card p-5 rounded-2xl rounded-tl-none border border-borderDark text-sm leading-relaxed shadow-sm">
                            Creator data purged. Select another creator from the history to continue analysis.
                        </div>
                    </div>`;
            }
            loadHistory(); // Refresh the sidebar
            renderCreatorsGrid(); // Refresh the grid
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
        const res = await fetch(`${API_BASE}/api/list-cookies`);
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
                btn.className = "flex justify-between items-center p-4 bg-sidebar/50 border border-borderDark rounded-xl cursor-pointer transition-all hover:border-brand/50 hover:bg-brand/5 group";
                
                btn.onclick = () => selectCookie(cookie.filename);

                btn.innerHTML = `
                    <div class="flex items-center gap-4">
                        <div class="w-10 h-10 rounded-lg bg-brand/10 flex items-center justify-center border border-brand/20 group-hover:bg-brand/20 transition-colors">
                            <svg class="h-6 w-6 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                            </svg>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-white font-bold text-sm">Session</span>
                            <span class="text-[10px] text-textMuted uppercase tracking-wider font-typewriter">${cookie.created_at}</span>
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <span class="text-[10px] font-bold text-brand opacity-0 group-hover:opacity-100 transition-opacity uppercase tracking-widest">CONTINUE ➔</span>
                        <button onclick="event.stopPropagation(); deleteCookie('${cookie.filename}')" 
                                class="w-8 h-8 rounded-lg flex items-center justify-center text-textMuted hover:text-white hover:bg-white/10 transition-colors" title="Delete Session">
                            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
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
    const confirmed = await showDeleteModal(filename, `Permanently delete this session file (<span class="text-brand font-bold">${filename}</span>)? This will remove your stored login cookies.`);
    if (!confirmed) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/cookies/${filename}`, { method: 'DELETE' });
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
        const res = await fetch(`${API_BASE}/api/select-cookie`, {
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
        const res = await fetch(`${API_BASE}/api/auth`, { method: 'POST' });
        
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

// --- Startup Animation (Dot Matrix Logo) ---
async function startLogoAnimation() {
    const canvas = document.getElementById('logo-canvas');
    if (!canvas) return;
    
    // Retina-ready Setup
    canvas.width = 800; 
    canvas.height = 800;
    canvas.style.width = '200px';
    canvas.style.height = '200px';
    const ctx = canvas.getContext('2d');
    
    // High-resolution grid
    const dotRadius = 3.5; // Slightly smaller dots
    const gap = 2.0; // Crisper gap for LED definition
    const gridSize = (dotRadius * 2) + gap;
    
    // Load and sample the logo
    const img = new Image();
    img.src = 'logo.png';
    await new Promise(resolve => img.onload = resolve);
    
    const cols = Math.floor(canvas.width / gridSize);
    const rows = Math.floor(canvas.height / gridSize);
    
    const offCanvas = document.createElement('canvas');
    offCanvas.width = cols;
    offCanvas.height = rows;
    const offCtx = offCanvas.getContext('2d');
    
    // Center logo on sampling canvas
    const ratio = Math.min(cols / img.width, rows / img.height) * 0.85;
    const w = img.width * ratio;
    const h = img.height * ratio;
    offCtx.drawImage(img, (cols - w) / 2, (rows - h) / 2, w, h);
    
    const imgData = offCtx.getImageData(0, 0, cols, rows).data;
    const brandColor = '#ff3b66'; // High-fidelity vibrant pinkish-red
    
    const dots = [];
    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            const idx = (y * cols + x) * 4;
            const r = imgData[idx];
            const g = imgData[idx + 1];
            const b = imgData[idx + 2];
            
            if (r + g + b > 30) { // Threshold for the bright logo dots
                dots.push({ 
                    x: x * gridSize + dotRadius, 
                    y: y * gridSize + dotRadius, 
                    baseAlpha: 0.8 + Math.random() * 0.2, // Higher base alpha so it matches original brightness
                    phase: Math.random() * Math.PI * 2,
                    shimmer: Math.random() * 0.1
                });
            }
        }
    }
    
    let startTime = Date.now();
    function animate() {
        if (!document.getElementById('startup-loader')) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const time = (Date.now() - startTime) / 1000;
        
        dots.forEach(dot => {
            // Combine multiple sine waves at erratic fractional frequencies to create fluid, non-looping organic motion
            const w1 = Math.sin(time * 1.7 + dot.phase);
            const w2 = Math.sin(time * 2.3 - dot.phase * 1.5);
            const w3 = Math.sin(time * 3.1 + dot.phase * 0.8);
            
            const fluidWave = (w1 + w2 + w3) / 3;
            const pulse = fluidWave * 0.5 + 0.5; // Smooth pulse from 0.0 to 1.0
            
            const shimmer = Math.sin(time * 12 + dot.phase) * dot.shimmer;
            const alpha = Math.max(0.1, (dot.baseAlpha * pulse) + shimmer);
            
            // Randomly distribute dots between Neon Pink (345) and Pure Red (360) based on their fixed phase
            const blend = (Math.sin(dot.phase) + 1) / 2;
            const hue = 345 + (blend * 15);
            const dotColor = `hsl(${hue}, 100%, 70%)`; // Brighter core
            const glowColor = `hsl(${hue}, 100%, 60%)`; // Brighter glow
            
            // Layer 1: Core Glow (Bloom)
            ctx.shadowBlur = 15; 
            ctx.shadowColor = glowColor;
            ctx.globalAlpha = alpha; 
            ctx.fillStyle = glowColor;
            
            ctx.beginPath();
            // Optional fallback to arc if roundRect unsupported, but modern Chromium handles it perfectly
            if (ctx.roundRect) {
                ctx.roundRect(dot.x - dotRadius * 1.1, dot.y - dotRadius * 1.1, dotRadius * 2.2, dotRadius * 2.2, 2.5);
            } else {
                ctx.arc(dot.x, dot.y, dotRadius * 1.2, 0, Math.PI * 2);
            }
            ctx.fill();
            
            // Layer 2: Main Dot
            ctx.shadowBlur = 0;
            ctx.globalAlpha = alpha;
            ctx.fillStyle = dotColor;
            
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(dot.x - dotRadius, dot.y - dotRadius, dotRadius * 2, dotRadius * 2, 2);
            } else {
                ctx.arc(dot.x, dot.y, dotRadius, 0, Math.PI * 2);
            }
            ctx.fill();
        });
        
        ctx.globalAlpha = 1.0;
        requestAnimationFrame(animate);
    }
    animate();
    
    // Progress bar simulation
    return new Promise(resolve => {
        const progressBar = document.getElementById('loader-progress');
        const statusText = document.getElementById('loader-status');
        const states = ["Loading .", "Loading ..", "Loading ...", "Loading .", "Loading ..", "Loading ...", "Loading ."];
        let progress = 0;
        const interval = setInterval(() => {
            if (progress >= 99 && !window.backendConnected) {
                // Hold at 99% until backend signals readiness
                return;
            }
            
            if (window.backendConnected || progress >= 100) { 
                progress = 100;
                if (progressBar) progressBar.style.width = `100%`;
                if (statusText) statusText.innerText = "System Ready";
                clearInterval(interval); 
                setTimeout(resolve, 500); // Give user a moment to see 100%
                return; 
            }

            // Variable speed for more natural feeling
            const increment = progress < 70 ? (Math.random() * 8 + 2) : (Math.random() * 2 + 0.5);
            progress += increment;
            
            if (progress > 99) progress = 99; // Cap at 99 until backendConnected
            
            if (progressBar) progressBar.style.width = `${progress}%`;
            if (statusText) {
                const stateIdx = Math.floor((progress / 100) * (states.length - 1));
                statusText.innerText = states[stateIdx];
            }
        }, 120);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    const logoAnimPromise = startLogoAnimation();
    const appInitPromise = initApp();
    
    // Wait for BOTH backend to be ready AND animation to finish
    await Promise.all([logoAnimPromise, appInitPromise]);
    
    // Final transition
    const loader = document.getElementById('startup-loader');
    const loginCard = document.getElementById('login-card');
    if (loader) {
        loader.classList.add('fade-out'); // Use a CSS class for smoother fade
        setTimeout(() => {
            loader.style.display = 'none';
            loader.remove();
        }, 800);
    }
    // Delete Modal Listeners
    document.getElementById('cancel-delete-btn')?.addEventListener('click', () => closeDeleteModal(false));
    document.getElementById('confirm-delete-btn')?.addEventListener('click', () => closeDeleteModal(true));
    document.getElementById('delete-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'delete-modal') closeDeleteModal(false);
    });

    if (loginCard) {
        loginCard.classList.add('show');
    }
});

async function initApp(retries = 15) {
    for (let i = 0; i < retries; i++) {
        console.log(`Connecting to backend... (${i + 1}/${retries})`);
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000); // 2s timeout per request
            
            const resCheck = await fetch(`${API_BASE}/api/status`, { signal: controller.signal });
            clearTimeout(timeoutId);

            if (resCheck.ok || resCheck.status === 404) {
                console.log("Connected to backend!");
                window.backendConnected = true; 
                loadCookieSessions();
                
                // Settings Listeners
                const modelSelect = document.getElementById('model-select');
                const transSelect = document.getElementById('transcription-method');
                if (modelSelect) modelSelect.addEventListener('change', updateKeyPlaceholder);
                if (transSelect) transSelect.addEventListener('change', updateKeyPlaceholder);

                // Check active session
                const resCookies = await fetch(`${API_BASE}/api/check-cookies`);
                const data = await resCookies.json();
                if (data.exists) {
                    const isValid = await validateSession();
                    if (isValid) showMainApp();
                }
                return true;
            }
        } catch (e) {
            console.warn("Backend connection attempt failed...");
        }
        await new Promise(r => setTimeout(r, 800)); 
    }
    
    // Explicit failure state
    console.error("Failed to connect to backend.");
    const statusText = document.getElementById('loader-status');
    if (statusText) {
        statusText.innerText = "Error: Backend unreachable. Please restart.";
        statusText.style.color = "#f87171";
    }
    window.backendConnected = false;
    return false;
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
        const response = await fetch(`${API_BASE}/api/upload-cookies`, {
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

async function cancelProcessing() {
    const scrapeBtn = document.getElementById('scrape-btn');
    if (scrapeBtn) {
        scrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Cancelling...';
        scrapeBtn.disabled = true;
    }
    try {
        await fetch(`${API_BASE}/api/process/cancel`, { method: 'POST' });
    } catch (e) {
        console.error("Cancel failed", e);
    }
}

async function startProcessing() {
    const target = document.getElementById('tiktok-url').value;
    const videoCount = parseInt(document.getElementById('video-count').value) || 10;
    const statusText = document.getElementById('process-status');
    const scrapeBtn = document.getElementById('scrape-btn');

    if (!target) return alert("Please enter a TikTok URL.");

    // Transform UI into a Stop Button and lock inputs
    scrapeBtn.innerHTML = '<i class="fa-solid fa-stop mr-2"></i> Stop Scrape';
    scrapeBtn.classList.remove('bg-brand', 'hover:bg-brandHover');
    scrapeBtn.classList.add('bg-red-500', 'hover:bg-red-600');
    scrapeBtn.onclick = cancelProcessing;
    
    document.getElementById('tiktok-url').disabled = true;
    document.getElementById('video-count').disabled = true;

    statusText.style.color = "#fbbf24";
    statusText.innerText = "Starting...";

    try {
        // 1. Tell the server to start the job
        const startResponse = await fetch(`${API_BASE}/api/process`, {
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
            const statusRes = await fetch(`${API_BASE}/api/status`);
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
                        setCreator(state.creator_name, state.creator_nickname);
                    } else {
                        // Fallback only if server didn't report it
                        let extracted = target.split('@').pop().split(/[\/\?]/)[0] || target;
                        setCreator(extracted);
                    }

                    // Unlock the chat interface
                    document.getElementById('chat-input').disabled = false;
                    document.getElementById('send-btn').disabled = false;
                    loadHistory(); // Refresh history with the new scrape
                    // Provide visual indication they can proceed to chat
                    statusText.innerHTML = '✅ Processing Complete! <a href="#" onclick="showChat()" class="underline text-brand">Go to Chat</a>';
                }

                // Restore the scrape button and unlock inputs
                scrapeBtn.innerHTML = '<i class="fa-solid fa-bolt mr-2"></i> 1. Scrape & Process Data';
                scrapeBtn.classList.remove('bg-red-500', 'hover:bg-red-600');
                scrapeBtn.classList.add('bg-brand', 'hover:bg-brandHover');
                scrapeBtn.onclick = startProcessing;
                scrapeBtn.disabled = false;
                
                document.getElementById('tiktok-url').disabled = false;
                document.getElementById('video-count').disabled = false;
            }
        }, 2000); // 2000 milliseconds = 2 seconds

    } catch (error) {
        statusText.innerText = `❌ API Error: ${error.message}`;
        statusText.style.color = "#f87171";
        scrapeBtn.disabled = false;
        
        document.getElementById('tiktok-url').disabled = false;
        document.getElementById('video-count').disabled = false;
    }
}

let currentAbortController = null;

function setStopButton() {
    const btnText = document.getElementById('send-btn-text');
    const btnIcon = document.getElementById('send-btn-icon');
    if (btnText) btnText.style.display = 'none';
    if (btnIcon) {
        btnIcon.innerHTML = `<rect x="6" y="6" width="12" height="12"></rect>`;
        btnIcon.setAttribute("viewBox", "0 0 24 24");
        btnIcon.setAttribute("stroke-width", "2");
        btnIcon.setAttribute("fill", "currentColor");
    }
}

function resetSendButton() {
    const btnText = document.getElementById('send-btn-text');
    const btnIcon = document.getElementById('send-btn-icon');
    if (btnText) btnText.style.display = 'inline';
    if (btnIcon) {
        btnIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>`;
        btnIcon.setAttribute("fill", "none");
    }
    const inputElement = document.getElementById('chat-input');
    if (inputElement) {
        inputElement.disabled = false;
        inputElement.focus();
    }
}

function sendOrStopMessage() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
        resetSendButton();
        return;
    }
    sendMessage();
}

async function sendMessage() {
    const inputElement = document.getElementById("chat-input");
    const text = inputElement.value;

    if (text.trim() === "") return;
    
    currentAbortController = new AbortController();
    setStopButton();
    inputElement.disabled = true;

    const chatBox = document.getElementById("chat-box");
    
    // Hide placeholder once a message is sent
    const placeholder = document.getElementById('chat-placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    // Shrink the input box and hide suggestions once a message is sent
    inputElement.classList.add('shrunk');
    document.body.classList.add('chat-active');

    // 1. Create and append the User's message bubble
    const userMsg = document.createElement("div");
    userMsg.className = "message user";
    userMsg.innerText = text;
    chatBox.appendChild(userMsg);

    // Clear the input
    inputElement.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // 2. Create a temporary "loading" bubble for the AI
    const loadingMsgContainer = document.createElement("div");
    loadingMsgContainer.className = "message ai italic text-brand font-typewriter animate-pulse";
    
    const loadingMsg = document.createElement("div");
    loadingMsg.className = "markdown-content"; // Container for actual text
    loadingMsgContainer.appendChild(loadingMsg);
    
    const copyBtn = document.createElement("button");
    copyBtn.className = "copy-btn";
    copyBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>`;
    copyBtn.onclick = () => copyToClipboard(loadingMsg.innerText, copyBtn);
    loadingMsgContainer.appendChild(copyBtn);

    chatBox.appendChild(loadingMsgContainer);
    chatBox.scrollTop = chatBox.scrollHeight;

    const loadingStates = ["Thinking...", "Searching database...", "Analyzing Creator Data...", "Planning...", "Formatting..."];
    let stateIdx = 0;
    loadingMsg.innerText = loadingStates[0];

    // 3. Call the Python backend logic via standard REST using a stream reader
    try {
        const fetchRes = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: text,
                creator_name: currentCreator
            }),
            signal: currentAbortController.signal
        });

        if (!fetchRes.ok) throw new Error("Could not fetch response from AI.");

        const reader = fetchRes.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullResponse = "";
        let isGenerating = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete line in buffer

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    if (data.state) {
                        if (data.state === "Generating...") {
                            isGenerating = true;
                            loadingMsg.innerHTML = "";
                            loadingMsgContainer.classList.remove('italic', 'text-brand', 'font-typewriter', 'animate-pulse');
                        } else if (data.state !== "Done" && !isGenerating) {
                            loadingMsg.innerText = data.state;
                        }
                    } else if (data.chunk) {
                        fullResponse += data.chunk;
                        // Parse as it comes in
                        loadingMsg.innerHTML = marked.parse(fullResponse);
                        chatBox.scrollTop = chatBox.scrollHeight;
                    } else if (data.response) {
                        // Error or one-shot responses
                        loadingMsg.innerHTML = marked.parse(data.response);
                        loadingMsgContainer.classList.remove('italic', 'text-brand', 'font-typewriter', 'animate-pulse');
                    }
                } catch (err) {
                    console.error("Error parsing NDJSON line:", line, err);
                }
            }
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            loadingMsg.innerHTML += "<br><em class='text-textMuted'>[Generation stopped by user]</em>";
        } else {
            loadingMsg.innerText = `❌ Error: ${e.message}`;
        }
        loadingMsgContainer.classList.remove('italic', 'text-brand', 'font-typewriter', 'animate-pulse');
    } finally {
        currentAbortController = null;
        resetSendButton();
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// Allow pressing 'Enter' to send
document.getElementById("chat-input").addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

// Toggle nav on start
showDashboard();
function updateKeyPlaceholder() {
    const model = document.getElementById('model-select').value;
    const trans = document.getElementById('transcription-method').value;
    const input = document.getElementById('api-key-input');
    const statusEl = document.getElementById('settings-status');

    let needsGroq = model.startsWith('groq/') || trans === 'groq_whisper';
    let needsOpenAI = model.startsWith('gpt') || model.startsWith('openai');

    if ((needsGroq && apiState.has_groq_key) || (needsOpenAI && apiState.has_openai_key)) {
        input.placeholder = "🔑 Brain API Key Saved (Enter new to overwrite)";
    } else if (needsGroq || needsOpenAI) {
        input.placeholder = "Paste Groq/OpenAI key...";
    } else {
        input.placeholder = "No key required for local models";
        statusEl.innerText = ""; // Clear warning if we switch to local
    }
    
    const transInput = document.getElementById('transcription-api-key-input');
    if (transInput) {
        if (apiState.has_transcription_key) {
            transInput.placeholder = "🔑 Transcription Key Saved (Enter to overwrite)";
        } else {
            transInput.placeholder = "Enter Transcription API key...";
        }
    }
}

async function saveSettings() {
    const modelSelection = document.getElementById('model-select').value;
    const apiKey = document.getElementById('api-key-input').value;
    const transApiKey = document.getElementById('transcription-api-key-input').value;
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
            api_key: apiKey,
            transcription_api_key: transApiKey
        };

        const res = await fetch(`${API_BASE}/api/settings`, {
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
        if (transApiKey) {
            apiState.has_transcription_key = true;
            document.getElementById('transcription-api-key-input').value = "";
        }

        statusEl.innerHTML = `✅ <b>Saved!</b> Chat: <b>${modelLabel}</b> · Transcription: <b>${transLabel}</b> · 🔑 Key stored`;
        statusEl.style.color = "#4ade80";
        updateKeyPlaceholder();

    } catch (e) {
        statusEl.innerText = `❌ Error: ${e.message}`;
        statusEl.style.color = "#f87171";
    }
}

function quickAction(type) {
    const input = document.getElementById('chat-input');
    const prompts = {
        'Summarize': 'Please summarize the main themes and topics covered by this creator.',
        'Notes': 'Can you provide detailed notes on the key points mentioned in these videos?',
        'Advices': 'Please extract and list all of the specific advice, tips, and insights mentioned by the creator across all of their videos.',
        'Recommendations': 'What top 3 videos would you recommend me to watch first, and why?'
    };
    
    if (prompts[type]) {
        input.value = prompts[type];
        sendMessage();
    }
}