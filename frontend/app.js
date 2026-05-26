// App State Management
const state = {
  sessionId: '',
  healthInterval: null,
  isSending: false
};

// DOM Elements
const elements = {
  sessionIdDisplay: document.getElementById('session-id-display'),
  copySessionBtn: document.getElementById('copy-session-btn'),
  resetSessionBtn: document.getElementById('reset-session-btn'),
  kbDocumentList: document.getElementById('kb-document-list'),
  healthBadge: document.getElementById('health-badge'),
  llmBadge: document.getElementById('llm-badge'),
  statLatency: document.getElementById('stat-latency'),
  statTokens: document.getElementById('stat-tokens'),
  statChunks: document.getElementById('stat-chunks'),
  modeBadge: document.getElementById('mode-badge'),
  chatMessages: document.getElementById('chat-messages'),
  suggestionsContainer: document.getElementById('suggestions-container'),
  chatForm: document.getElementById('chat-form'),
  queryInput: document.getElementById('query-input'),
  sendBtn: document.getElementById('send-btn')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  initSession();
  initEventListeners();
  checkSystemHealth();
  // Poll system health every 15 seconds
  state.healthInterval = setInterval(checkSystemHealth, 15000);
});

// Session Management
function initSession() {
  let storedSession = localStorage.getItem('rag_assistant_session');
  if (!storedSession) {
    storedSession = generateUUID();
    localStorage.setItem('rag_assistant_session', storedSession);
  }
  state.sessionId = storedSession;
  elements.sessionIdDisplay.textContent = state.sessionId;
}

function generateUUID() {
  // Simple UUID generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    const icon = elements.copySessionBtn.querySelector('i');
    icon.className = 'fa-solid fa-check';
    icon.style.color = '#10b981';
    
    setTimeout(() => {
      icon.className = 'fa-regular fa-copy';
      icon.style.color = '';
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy session ID: ', err);
  });
}

// Event Listeners Registration
function initEventListeners() {
  // Copy Session ID
  elements.copySessionBtn.addEventListener('click', () => {
    copyToClipboard(state.sessionId);
  });

  // Reset Session
  elements.resetSessionBtn.addEventListener('click', handleResetSession);

  // Chat Form Submit
  elements.chatForm.addEventListener('submit', handleChatSubmit);

  // Click handler for sidebar knowledge directory
  elements.kbDocumentList.addEventListener('click', (e) => {
    const item = e.target.closest('.kb-item');
    if (item) {
      const query = item.getAttribute('data-query');
      populateQuery(query);
    }
  });

  // Click handler for suggestion chips
  elements.suggestionsContainer.addEventListener('click', (e) => {
    const chip = e.target.closest('.suggestion-chip');
    if (chip) {
      const query = chip.getAttribute('data-query');
      populateQuery(query);
    }
  });
}

function populateQuery(queryText) {
  elements.queryInput.value = queryText;
  elements.queryInput.focus();
}

// System Health Checks
async function checkSystemHealth() {
  try {
    const response = await fetch('/health');
    if (response.ok) {
      const data = await response.json();
      
      // Update health status badge
      elements.healthBadge.className = 'badge-online';
      elements.healthBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Healthy';
      
      // Update LLM configuration status badge (if returned by backend)
      if (data.llm_configured) {
        elements.llmBadge.className = 'badge-online';
        elements.llmBadge.textContent = 'Gemini Configured';
        elements.modeBadge.textContent = 'RAG ACTIVE';
        elements.modeBadge.style.background = 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)';
      } else {
        elements.llmBadge.className = 'badge-demo';
        elements.llmBadge.textContent = 'Demo Mode (Mock)';
        elements.modeBadge.textContent = 'DEMO MODE';
        elements.modeBadge.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
      }
    } else {
      setOfflineState();
    }
  } catch (error) {
    console.error('Error checking system status:', error);
    setOfflineState();
  }
}

function setOfflineState() {
  elements.healthBadge.className = 'badge-offline';
  elements.healthBadge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Offline';
  
  elements.llmBadge.className = 'badge-offline';
  elements.llmBadge.textContent = 'Disconnected';
  
  elements.modeBadge.textContent = 'SERVER OFFLINE';
  elements.modeBadge.style.background = '#ef4444';
}

// Reset Chat Session Handler
async function handleResetSession() {
  if (confirm('Are you sure you want to clear the conversation memory and start a new session?')) {
    try {
      // Trigger API to reset session backend-side
      const response = await fetch(`/api/chat/session/${state.sessionId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        // Generate new session token local-side
        localStorage.removeItem('rag_assistant_session');
        initSession();
        
        // Reset UI chat log
        elements.chatMessages.innerHTML = `
          <div class="message assistant-msg">
            <div class="message-avatar">
              <i class="fa-solid fa-robot"></i>
            </div>
            <div class="message-content-wrapper">
              <div class="message-bubble">
                <p>Hello! I have cleared our chat memory and generated a fresh session.</p>
                <p>What can I help you search in the company knowledge base today?</p>
              </div>
              <span class="message-time">Just now</span>
            </div>
          </div>
        `;
        
        // Clear metrics panel
        elements.statLatency.textContent = '-';
        elements.statTokens.textContent = '-';
        elements.statChunks.textContent = '-';
        
        // Show suggestions again
        elements.suggestionsContainer.style.display = 'flex';
        
        console.log('Session reset successfully.');
      } else {
        alert('Failed to reset conversation history on server.');
      }
    } catch (err) {
      console.error('Error resetting session:', err);
      alert('Error communicating with backend server.');
    }
  }
}

// Submit Chat Query Handler
async function handleChatSubmit(e) {
  e.preventDefault();
  
  const query = elements.queryInput.value.trim();
  if (!query || state.isSending) return;
  
  state.isSending = true;
  elements.queryInput.value = '';
  
  // Hide suggestions once chat starts
  elements.suggestionsContainer.style.display = 'none';
  
  // 1. Display user message bubble
  appendUserMessage(query);
  
  // 2. Append temporary bot typing bubble
  const loaderId = appendBotLoader();
  
  const startTime = performance.now();
  
  try {
    // 3. Post query payload to backend
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sessionId: state.sessionId,
        message: query
      })
    });
    
    const endTime = performance.now();
    const latencyMs = Math.round(endTime - startTime);
    
    // Remove bot loader bubble
    removeBotLoader(loaderId);
    
    if (response.ok) {
      const data = await response.json();
      
      // Update sidebar metrics panel
      elements.statLatency.textContent = `${(latencyMs / 1000).toFixed(2)}s`;
      elements.statTokens.textContent = data.tokensUsed;
      elements.statChunks.textContent = data.retrievedChunks;
      
      // Display completed bot response
      appendBotResponse(data);
      
      // Update UI mode badges based on LLM configuration
      if (data.mocked) {
        elements.llmBadge.className = 'badge-demo';
        elements.llmBadge.textContent = 'Demo Mode (Mock)';
        elements.modeBadge.textContent = 'DEMO MODE';
        elements.modeBadge.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
      } else {
        elements.llmBadge.className = 'badge-online';
        elements.llmBadge.textContent = 'Gemini Configured';
        elements.modeBadge.textContent = 'RAG ACTIVE';
        elements.modeBadge.style.background = 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)';
      }
    } else {
      const errData = await response.json().catch(() => ({}));
      const errMsg = errData.detail || 'An unexpected server error occurred.';
      appendErrorResponse(errMsg);
    }
  } catch (err) {
    console.error('Fetch error:', err);
    removeBotLoader(loaderId);
    appendErrorResponse('Could not connect to the backend server. Please verify it is running.');
  } finally {
    state.isSending = false;
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  }
}

// UI Dom Manipulation helpers
function appendUserMessage(text) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const html = `
    <div class="message user-msg">
      <div class="message-avatar">
        <i class="fa-solid fa-user"></i>
      </div>
      <div class="message-content-wrapper">
        <div class="message-bubble">
          <p>${escapeHTML(text)}</p>
        </div>
        <span class="message-time">${time}</span>
      </div>
    </div>
  `;
  elements.chatMessages.insertAdjacentHTML('beforeend', html);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function appendBotLoader() {
  const loaderId = `loader-${Date.now()}`;
  const html = `
    <div class="message assistant-msg" id="${loaderId}">
      <div class="message-avatar">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="message-content-wrapper">
        <div class="message-bubble">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
  `;
  elements.chatMessages.insertAdjacentHTML('beforeend', html);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return loaderId;
}

function removeBotLoader(loaderId) {
  const loader = document.getElementById(loaderId);
  if (loader) loader.remove();
}

function appendBotResponse(data) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  // Format reply markdown
  const formattedReply = formatMarkdown(data.reply);
  
  // Build sources segment if chunks are present
  let sourcesHTML = '';
  if (data.sources && data.sources.length > 0) {
    const sourcesListId = `sources-${Date.now()}`;
    const sourcesHeaderId = `header-${Date.now()}`;
    
    const itemsHTML = data.sources.map(src => `
      <div class="source-item">
        <div class="source-title-row">
          <span>${escapeHTML(src.title)}</span>
          <span class="source-match">${(src.similarity * 100).toFixed(1)}% match</span>
        </div>
        <div class="source-snippet" title="${escapeHTML(src.text)}">
          "${escapeHTML(src.text)}"
        </div>
      </div>
    `).join('');

    sourcesHTML = `
      <div class="sources-container">
        <div class="sources-header" id="${sourcesHeaderId}">
          <span><i class="fa-solid fa-magnifying-glass-chart"></i> Grounded Sources (${data.sources.length})</span>
          <i class="fa-solid fa-chevron-down"></i>
        </div>
        <div class="sources-list" id="${sourcesListId}">
          ${itemsHTML}
        </div>
      </div>
    `;
    
    // Attach lazy toggle script logic right after rendering
    setTimeout(() => {
      const header = document.getElementById(sourcesHeaderId);
      const list = document.getElementById(sourcesListId);
      if (header && list) {
        header.addEventListener('click', () => {
          header.classList.toggle('open');
          list.classList.toggle('open');
          elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        });
      }
    }, 0);
  }

  // Render response HTML
  const html = `
    <div class="message assistant-msg">
      <div class="message-avatar">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="message-content-wrapper">
        <div class="message-bubble">
          <div>${formattedReply}</div>
          ${sourcesHTML}
          <div class="stat-tag">
            <i class="fa-solid fa-microchip"></i> <span>Tokens: ${data.tokensUsed}</span>
          </div>
        </div>
        <span class="message-time">${time}</span>
      </div>
    </div>
  `;
  
  elements.chatMessages.insertAdjacentHTML('beforeend', html);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function appendErrorResponse(errorText) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const html = `
    <div class="message assistant-msg">
      <div class="message-avatar" style="background: var(--color-error)">
        <i class="fa-solid fa-triangle-exclamation"></i>
      </div>
      <div class="message-content-wrapper">
        <div class="message-bubble" style="border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.05)">
          <p style="color: #f87171; font-weight: 600;">System Error</p>
          <p style="font-size: 12.5px;">${escapeHTML(errorText)}</p>
        </div>
        <span class="message-time">${time}</span>
      </div>
    </div>
  `;
  elements.chatMessages.insertAdjacentHTML('beforeend', html);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// Security sanitization helper
function escapeHTML(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Lightweight Custom Markdown Formatter
function formatMarkdown(text) {
  let escaped = escapeHTML(text);
  
  // Format bold (**bold**)
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Format code blocks
  escaped = escaped.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  
  // Format inline code
  escaped = escaped.replace(/`(.*?)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 11.5px;">$1</code>');
  
  // Format bullet points
  const lines = escaped.split('\n');
  let inList = false;
  const formattedLines = [];
  
  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      if (!inList) {
        formattedLines.push('<ul style="margin-left: 20px; margin-top: 6px; margin-bottom: 6px; display: flex; flex-direction: column; gap: 4px;">');
        inList = true;
      }
      formattedLines.push(`<li style="list-style-type: disc;">${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        formattedLines.push('</ul>');
        inList = false;
      }
      formattedLines.push(line);
    }
  }
  if (inList) {
    formattedLines.push('</ul>');
  }
  
  return formattedLines.join('\n').replace(/\n/g, '<br>');
}
