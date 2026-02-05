// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const statusText = document.getElementById('status-text');
const clearChatBtn = document.getElementById('clear-chat');
const themeToggle = document.getElementById('theme-toggle');
const chatFileInput = document.getElementById('chat-file-input');
const historyList = document.getElementById('history-list');

// Sidebar user profile (optional, can be hidden)
const userProfile = document.getElementById('user-profile');
if (userProfile) userProfile.style.display = 'none';

// Use empty string for same-origin requests to avoid CORS/localhost issues
const API_BASE_URL = '';

// App State
let chatHistory = JSON.parse(localStorage.getItem('nexara_history')) || [];

// --- THEME LOGIC ---
function initTheme() {
    const savedTheme = localStorage.getItem('nexara_theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
}

themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light-mode');
    const isLight = document.body.classList.contains('light-mode');
    localStorage.setItem('nexara_theme', isLight ? 'light' : 'dark');
    themeToggle.innerHTML = isLight ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
});

// --- CHAT HISTORY LOGIC ---
function saveToHistory(text) {
    if (!text) return;
    const historyItem = {
        id: Date.now(),
        title: text.substring(0, 30) + (text.length > 30 ? '...' : ''),
        timestamp: new Date().toLocaleTimeString()
    };
    chatHistory.unshift(historyItem);
    if (chatHistory.length > 10) chatHistory.pop();
    localStorage.setItem('nexara_history', JSON.stringify(chatHistory));
    loadHistory();
}

function loadHistory() {
    historyList.innerHTML = '';
    chatHistory.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.innerHTML = `<i class="fas fa-comment-dots"></i> ${item.title}`;
        div.onclick = () => {
            userInput.value = item.title.replace('...', '');
            userInput.focus();
        };
        historyList.appendChild(div);
    });
}

// Load History on Init
loadHistory();

// --- FILE UPLOAD LOGIC ---
dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
    dropZone.style.borderColor = 'var(--accent-primary)';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
    dropZone.style.borderColor = 'var(--glass-border)';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    dropZone.style.borderColor = 'var(--glass-border)';
    handleFiles(e.dataTransfer.files);
});

async function handleFiles(files) {
    if (!files || files.length === 0) return;

    // We only support one file at a time effectively
    const file = files[0];

    statusText.innerText = 'Initializing...';
    fileList.innerHTML = `<div class="file-item loading"><i class="fas fa-spinner fa-spin"></i> <span>Processing ${file.name}...</span></div>`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        statusText.innerText = 'Uploading...';
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || 'Upload failed');
        }

        const data = await response.json();

        fileList.innerHTML = `
            <div class="file-item success">
                <i class="fas fa-check-circle"></i> 
                <span>${file.name} (Ready)</span>
            </div>
        `;

        statusText.innerText = 'File Indexed';
        setTimeout(() => {
            if (statusText.innerText === 'File Indexed') statusText.innerText = 'System Ready';
        }, 3000);

        addMessage(`I have successfully processed "${file.name}". You can now ask questions about it!`, 'ai');

    } catch (error) {
        console.error('Upload Error:', error);
        fileList.innerHTML = `
            <div class="file-item error">
                <i class="fas fa-exclamation-triangle"></i> 
                <span>Error: ${error.message}</span>
            </div>
        `;
        statusText.innerText = 'Upload Failed';
        addMessage(`Sorry, I couldn't process the file: ${error.message}`, 'ai');
    }
}

const DEFAULT_PLACEHOLDER = "Ask anything, @ to mention, / for workflows";

// --- TEXTAREA AUTO-RESIZE & ENTER KEY ---
userInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// --- FILE PREVIEW LOGIC (Chat Context) ---
if (primaryUploadBtn) {
    primaryUploadBtn.addEventListener('click', () => chatFileInput.click());
}

chatFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const isImage = file.type.startsWith('image/');
        const reader = new FileReader();

        reader.onload = (e) => {
            let previewHTML = '';
            if (isImage) {
                previewHTML = `<img src="${e.target.result}" alt="Preview">`;
            } else {
                const iconClass = getFileIcon(file.name);
                previewHTML = `<div class="doc-preview-icon"><i class="${iconClass}"></i><span>${file.name}</span></div>`;
            }

            imagePreview.innerHTML = `
                <div class="image-preview-container">
                    ${previewHTML}
                    <button type="button" id="remove-image">×</button>
                </div>
            `;
            imagePreview.style.display = 'block';
            document.getElementById('remove-image').onclick = () => {
                imagePreview.style.display = 'none';
                chatFileInput.value = '';
            };
        };

        if (isImage) {
            reader.readAsDataURL(file);
        } else {
            reader.readAsArrayBuffer(file); // Just to trigger onload
            reader.onload = () => {
                const iconClass = getFileIcon(file.name);
                imagePreview.innerHTML = `
                    <div class="image-preview-container">
                        <div class="doc-preview-icon"><i class="${iconClass}"></i><span>${file.name}</span></div>
                        <button type="button" id="remove-image">×</button>
                    </div>
                `;
                imagePreview.style.display = 'block';
                document.getElementById('remove-image').onclick = () => {
                    imagePreview.style.display = 'none';
                    chatFileInput.value = '';
                };
            }
            reader.readAsText(file.slice(0, 10));
        }
    }
});

function getFileIcon(fileName) {
    const ext = fileName.split('.').pop().toLowerCase();
    switch (ext) {
        case 'pdf': return 'fas fa-file-pdf';
        case 'doc':
        case 'docx': return 'fas fa-file-word';
        case 'xls':
        case 'xlsx':
        case 'csv': return 'fas fa-file-excel';
        case 'ppt':
        case 'pptx': return 'fas fa-file-powerpoint';
        case 'py':
        case 'js':
        case 'css':
        case 'html': return 'fas fa-file-code';
        default: return 'fas fa-file-alt';
    }
}

// --- CHAT LOGIC ---
async function sendMessage(optionalMessage = null) {
    const message = optionalMessage !== null ? optionalMessage : userInput.value.trim();
    const chatFile = chatFileInput.files[0];

    if (!message && !chatFile) return;

    // UI Updates
    addMessage(message, 'user');
    saveToHistory(message);

    // Clear inputs
    userInput.value = '';
    userInput.style.height = 'auto';

    const formData = new FormData();
    formData.append('message', message);
    if (chatFile) {
        formData.append('image', chatFile); // Keeping 'image' key for backend compatibility
        imagePreview.style.display = 'none';
        chatFileInput.value = '';
    }

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        addMessage(data.response, 'ai');
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, something went wrong. Please check your connection.', 'ai');
    }
}

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage();
});

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    avatarDiv.innerText = sender === 'ai' ? 'AI' : 'U';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.innerText = text;

    // Add Actions for AI messages (Copy only)
    if (sender === 'ai') {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'msg-actions';

        // Copy Button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-icon-btn copy-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy Text';
        copyBtn.onclick = () => copyText(text, copyBtn);
        actionsDiv.appendChild(copyBtn);

        contentDiv.appendChild(actionsDiv);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// --- COPY TO CLIPBOARD ---
function copyText(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.style.color = '#10b981';
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.color = '';
        }, 2000);
    });
}

clearChatBtn.addEventListener('click', async () => {
    chatMessages.innerHTML = '';
    try {
        await fetch(`${API_BASE_URL}/clear`);
        statusText.innerText = 'Knowledge Cleared';
        fileList.innerHTML = '';
        setTimeout(() => statusText.innerText = 'System Ready', 2000);
    } catch (e) {
        console.error("Failed to clear backend:", e);
    }
    addMessage("Hello! I'm your advanced RAG assistant. Upload your documents to begin.", 'ai');
});

// Initialize
initTheme();
