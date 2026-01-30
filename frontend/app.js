/**
 * WalleTracker Frontend App
 * Connects to Python backend API
 */

// Configuration
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : '';

const REFRESH_INTERVAL = 30000;
const PAGE_SIZE = 10;

// State
let tokens = [];
let signals = [];
let wallets = [];
let news = [];
let currentFilter = 'all';
let currentSort = 'score';
let tokenPage = 1;
let walletPage = 1;

// DOM Elements (Intelligent Detection)
const getEl = (id) => document.getElementById(id);
const elements = {
    tokenList: getEl('token-list'),
    homeTokenList: getEl('home-token-list'),
    signalList: getEl('signal-list'),
    walletList: getEl('wallet-list'),
    newsFeed: getEl('news-feed'),
    walletCount: getEl('wallet-count'),
    tokenCount: getEl('token-count'),
    uploadZone: getEl('upload-zone'),
    fileInput: getEl('file-input'),
    walletInput: getEl('wallet-input'),
    uploadPassword: getEl('upload-password'),
    submitBtn: getEl('submit-wallets'),
    tokenSort: getEl('token-sort'),
    tokenPageInfo: getEl('token-page-info'),
    walletPageInfo: getEl('wallet-page-info')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    startAutoRefresh();
});

async function initializeApp() {
    // Determine which data we need based on present elements
    const tasks = [];
    if (elements.tokenList || elements.homeTokenList || elements.tokenCount) tasks.push(fetchTokens());
    if (elements.signalList) tasks.push(fetchSignals());
    if (elements.walletList || elements.walletCount) tasks.push(fetchWallets());
    if (elements.newsFeed) tasks.push(fetchNews());

    await Promise.all(tasks);
}

function setupEventListeners() {
    // File upload (if present)
    if (elements.uploadZone) {
        elements.uploadZone.addEventListener('click', () => elements.fileInput.click());
        elements.uploadZone.addEventListener('dragover', handleDragOver);
        elements.uploadZone.addEventListener('dragleave', handleDragLeave);
        elements.uploadZone.addEventListener('drop', handleDrop);
        elements.fileInput.addEventListener('change', handleFileSelect);
    }

    if (elements.submitBtn) {
        elements.submitBtn.addEventListener('click', handleWalletSubmit);
    }

    // Filter pills
    document.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentFilter = pill.dataset.filter;
            tokenPage = 1;
            renderTokens();
        });
    });

    // Sorting
    if (elements.tokenSort) {
        elements.tokenSort.addEventListener('change', (e) => {
            currentSort = e.target.value;
            renderTokens();
        });
    }

    // Token Pagination
    getEl('prev-tokens')?.addEventListener('click', () => {
        if (tokenPage > 1) { tokenPage--; renderTokens(); }
    });
    getEl('next-tokens')?.addEventListener('click', () => {
        const totalPages = Math.ceil(tokens.length / PAGE_SIZE);
        if (tokenPage < totalPages) { tokenPage++; renderTokens(); }
    });

    // Wallet Pagination
    getEl('prev-wallets')?.addEventListener('click', () => {
        if (walletPage > 1) { walletPage--; renderWallets(); }
    });
    getEl('next-wallets')?.addEventListener('click', () => {
        const totalPages = Math.ceil(wallets.length / PAGE_SIZE);
        if (walletPage < totalPages) { walletPage++; renderWallets(); }
    });
}

function startAutoRefresh() {
    setInterval(() => {
        if (elements.tokenList || elements.homeTokenList) fetchTokens();
        if (elements.signalList) fetchSignals();
        if (elements.walletList) fetchWallets();
        if (elements.newsFeed) fetchNews();
    }, REFRESH_INTERVAL);
}

// API Functions
async function fetchTokens() {
    try {
        const response = await fetch(`${API_BASE}/api/tokens`);
        if (response.ok) {
            tokens = await response.json();
            renderTokens();
            if (elements.tokenCount) elements.tokenCount.textContent = tokens.length;
        }
    } catch (error) {
        tokens = getMockTokens();
        renderTokens();
    }
}

async function fetchWallets() {
    try {
        const response = await fetch(`${API_BASE}/api/wallets`);
        if (response.ok) {
            wallets = await response.json();
            renderWallets();
            if (elements.walletCount) elements.walletCount.textContent = wallets.length;
        }
    } catch (error) {
        wallets = getMockWallets();
        renderWallets();
    }
}

async function fetchSignals() {
    try {
        const response = await fetch(`${API_BASE}/api/signals`);
        if (response.ok) {
            signals = await response.json();
            renderSignals();
        }
    } catch (error) {
        signals = getMockSignals();
        renderSignals();
    }
}

async function fetchNews() {
    try {
        const response = await fetch(`${API_BASE}/api/news`);
        if (response.ok) {
            news = await response.json();
            renderNews();
        }
    } catch (error) {
        news = [{ id: 1, title: 'Trending Meta', summary: 'AI tokens are surging.', trend: 'AI', created_at: new Date() }];
        renderNews();
    }
}

// Render Functions
function renderTokens() {
    // Filter
    let filtered = currentFilter === 'all'
        ? tokens
        : tokens.filter(t => t.category.toLowerCase() === currentFilter);

    // Sort
    filtered.sort((a, b) => {
        if (currentSort === 'score') return b.moonshot_score - a.moonshot_score;
        if (currentSort === 'age') return new Date(a.first_seen_at || 0) - new Date(b.first_seen_at || 0);
        if (currentSort === 'volume') return (b.wallet_count || 0) - (a.wallet_count || 0);
        return 0;
    });

    // Handle Home Page (Top 5)
    if (elements.homeTokenList) {
        const top5 = filtered.slice(0, 5);
        elements.homeTokenList.innerHTML = top5.map((t, i) => renderTokenItem(t, i)).join('');
    }

    // Handle Tokens Page (Pagination)
    if (elements.tokenList) {
        const start = (tokenPage - 1) * PAGE_SIZE;
        const end = start + PAGE_SIZE;
        const paginated = filtered.slice(start, end);
        const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;

        if (elements.tokenPageInfo) elements.tokenPageInfo.textContent = `Page ${tokenPage} of ${totalPages}`;
        getEl('prev-tokens').disabled = tokenPage === 1;
        getEl('next-tokens').disabled = tokenPage === totalPages;

        elements.tokenList.innerHTML = paginated.map((t, i) => renderTokenItem(t, start + i)).join('');
    }
}

function renderTokenItem(token, rank) {
    const age = formatAge(token.first_seen_at);
    const isNew = isTokenNew(token.first_seen_at);
    return `
        <div class="token-item">
            <div class="token-rank">${rank + 1}</div>
            <div class="token-info">
                <div class="token-name">
                    ${token.symbol || 'UNKNOWN'}
                    ${isNew ? '<span class="badge badge-new">🔥 NEW</span>' : ''}
                    <span class="badge badge-${token.category.toLowerCase()}">${token.category}</span>
                </div>
                <div class="token-mint">
                    ${truncateAddress(token.mint_address)}
                    <span class="copy-icon" onclick="copyToClipboard('${token.mint_address}')">📋</span>
                </div>
                <div class="token-age" style="font-size: 0.75rem; color: var(--text-muted); margin-top: 5px;">
                    Launched: ${age}
                </div>
                <a href="research.html?mint=${token.mint_address}" target="_blank" class="research-link">🔍 Deep Research</a>
            </div>
            <div class="token-stats">
                <div class="token-stat">
                    <span class="token-stat-value">${token.wallet_count}</span> 
                    <span class="token-stat-label">Wallets</span>
                </div>
                <div class="token-stat">
                    <span class="token-stat-value">${token.volume_pct}%</span> 
                    <span class="token-stat-label">Vol Share</span>
                </div>
            </div>
            <div class="token-score"><span class="score-value">${token.moonshot_score}</span> <span class="score-label">Score</span></div>
        </div>
    `;
}

function renderWallets() {
    if (!elements.walletList) return;

    const start = (walletPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const paginated = wallets.slice(start, end);
    const totalPages = Math.ceil(wallets.length / PAGE_SIZE) || 1;

    if (elements.walletPageInfo) elements.walletPageInfo.textContent = `Page ${walletPage} of ${totalPages}`;
    getEl('prev-wallets').disabled = walletPage === 1;
    getEl('next-wallets').disabled = walletPage === totalPages;

    elements.walletList.innerHTML = paginated.map((w, i) => `
        <div class="wallet-item">
            <div class="wallet-rank">${start + i + 1}</div>
            <div class="wallet-info">
                <div class="wallet-label">${w.label || truncateAddress(w.address)}</div>
                <div class="wallet-address">
                    ${truncateAddress(w.address)}
                    <span class="copy-icon" onclick="copyToClipboard('${w.address}')">📋</span>
                </div>
            </div>
            <div class="wallet-score">
                <span class="score-value">${Math.round(w.score)}</span>
                <span class="score-label">Score</span>
            </div>
        </div>
    `).join('');
}

function renderSignals() {
    if (!elements.signalList) return;
    elements.signalList.innerHTML = signals.map(sig => `
        <div class="signal-item">
            <div class="signal-icon">${sig.level === 'STRONG' ? '🔴' : '🟡'}</div>
            <div class="signal-info">
                <div class="signal-token">${sig.token_symbol}</div>
                <div class="signal-meta">${sig.level} | ${sig.wallet_count} Wallets</div>
            </div>
            <div class="signal-time">${formatTime(sig.created_at)}</div>
        </div>
    `).join('');
}

function renderNews() {
    if (!elements.newsFeed) return;

    if (news.length === 0) {
        elements.newsFeed.innerHTML = `
            <div class="empty-state">
                <p>Waiting for market alpha... 📡</p>
            </div>
        `;
        return;
    }

    elements.newsFeed.innerHTML = news.map(item => `
        <div class="news-item ${item.importance_score > 80 ? 'priority' : ''}" 
             ${item.source_url ? `onclick="window.open('${item.source_url}', '_blank')"` : ''}
             style="${item.source_url ? 'cursor: pointer;' : ''}">
            <div class="news-header">
                <span class="news-badge badge-${item.category.toLowerCase()}">
                    ${getNewsIcon(item.category)} ${item.category}
                </span>
                <span class="news-time">${formatTime(item.created_at)}</span>
            </div>
            <div class="news-title">${item.title}</div>
            <div class="news-summary">${item.summary}</div>
            ${item.source_url ? `<div class="news-source-link">🔗 View Full Alpha Source</div>` : ''}
        </div>
    `).join('');
}

function getNewsIcon(category) {
    const icons = {
        'Whale': '🐋',
        'Influencer': '👤',
        'Alpha': '💎',
        'Market': '📈',
        'Narrative': '🎭'
    };
    return icons[category] || '🗞️';
}

// Utility Functions
function truncateAddress(addr) {
    if (!addr) return '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

function formatAge(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diffHours = Math.floor((now - date) / 3600000);
    if (diffHours < 1) return '< 1h';
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function isTokenNew(timestamp) {
    if (!timestamp) return false;
    return (Date.now() - new Date(timestamp).getTime()) < 86400000;
}

window.copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard ✔️', 'success');
    });
};

function showToast(msg, type) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    getEl('toast-container')?.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Wallet Upload Handlers
function handleDragOver(e) { e.preventDefault(); elements.uploadZone.classList.add('dragover'); }
function handleDragLeave() { elements.uploadZone.classList.remove('dragover'); }
function handleDrop(e) {
    e.preventDefault();
    elements.uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
}
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) handleFile(file);
}
function handleFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => elements.walletInput.value = e.target.result;
    reader.readAsText(file);
}

async function handleWalletSubmit() {
    const input = elements.walletInput.value.trim();
    const password = elements.uploadPassword ? elements.uploadPassword.value : '';

    if (!input) {
        showToast('Please enter wallet addresses', 'error');
        return;
    }

    if (!password) {
        showToast('Security password required', 'error');
        return;
    }

    const lines = input.split('\n');
    let walletData = lines.map(line => {
        const parts = line.split(',').map(p => p.trim());
        return { address: parts[0], label: parts[1] || null };
    }).filter(w => w.address.length >= 32);

    // Local Deduplication
    const seen = new Set();
    walletData = walletData.filter(w => {
        if (seen.has(w.address)) return false;
        seen.add(w.address);
        return true;
    });

    try {
        const response = await fetch(`${API_BASE}/api/wallets/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wallets: walletData,
                password: password
            })
        });

        const result = await response.json();

        if (response.ok) {
            showToast(`Success! Added: ${result.added}, Skipped: ${result.skipped}`, 'success');
            elements.walletInput.value = '';
            if (elements.uploadPassword) elements.uploadPassword.value = '';
            fetchWallets();
        } else {
            showToast(result.detail || 'Upload failed', 'error');
        }
    } catch (e) {
        showToast('Upload server error', 'error');
    }
}

// Mock Data
function getMockTokens() {
    return [
        { symbol: 'PENGUIN', mint_address: '9ZPsRWGkJsKxN3yzV5tVmQe...', moonshot_score: 92, wallet_count: 45, category: 'MOONSHOT', first_seen_at: new Date() },
        { symbol: 'GROK', mint_address: 'ASTyfSim4Bk3p6SbPQdTDq...', moonshot_score: 85, wallet_count: 32, category: 'MOONSHOT', first_seen_at: new Date() }
    ];
}
function getMockWallets() {
    return [{ address: 'Whale1...', label: 'Whale Alpha', score: 98 }];
}
function getMockSignals() {
    return [{ token_symbol: 'PENGUIN', level: 'STRONG', wallet_count: 5, created_at: new Date() }];
}

// End of App Logic
