/**
 * WalleTracker Frontend App
 * Connects to Python backend API
 */

// Configuration
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://your-backend-url.onrender.com'; // Update this after deploying backend

const REFRESH_INTERVAL = 30000; // 30 seconds

// State
let tokens = [];
let signals = [];
let wallets = [];
let currentFilter = 'all';

// DOM Elements
const tokenList = document.getElementById('token-list');
const signalList = document.getElementById('signal-list');
const walletList = document.getElementById('wallet-list');
const walletCount = document.getElementById('wallet-count');
const tokenCount = document.getElementById('token-count');
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const walletInput = document.getElementById('wallet-input');
const submitBtn = document.getElementById('submit-wallets');
const toastContainer = document.getElementById('toast-container');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    startAutoRefresh();
});

async function initializeApp() {
    await Promise.all([
        fetchTokens(),
        fetchSignals(),
        fetchWallets()
    ]);
}

function setupEventListeners() {
    // File upload
    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', handleDragOver);
    uploadZone.addEventListener('dragleave', handleDragLeave);
    uploadZone.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileSelect);

    // Submit wallets
    submitBtn.addEventListener('click', handleWalletSubmit);

    // Filter pills
    document.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentFilter = pill.dataset.filter;
            renderTokens();
        });
    });
}

function startAutoRefresh() {
    setInterval(() => {
        fetchTokens();
        fetchSignals();
        fetchWallets();
    }, REFRESH_INTERVAL);
}

// API Functions
async function fetchTokens() {
    try {
        const response = await fetch(`${API_BASE}/api/tokens`);
        if (response.ok) {
            tokens = await response.json();
            renderTokens();
            tokenCount.textContent = tokens.length;
        }
    } catch (error) {
        console.log('Using mock data for tokens');
        tokens = getMockTokens();
        renderTokens();
        tokenCount.textContent = tokens.length;
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
        console.log('Using mock data for signals');
        signals = getMockSignals();
        renderSignals();
    }
}

async function fetchWallets() {
    try {
        const response = await fetch(`${API_BASE}/api/wallets`);
        if (response.ok) {
            wallets = await response.json();
            renderWallets();
            walletCount.textContent = wallets.length;
        }
    } catch (error) {
        console.log('Using mock data for wallets');
        wallets = getMockWallets();
        renderWallets();
        walletCount.textContent = wallets.length;
    }
}

async function uploadWallets(walletData) {
    try {
        const response = await fetch(`${API_BASE}/api/wallets/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wallets: walletData })
        });

        if (response.ok) {
            const result = await response.json();
            showToast(`Added ${result.added} wallets successfully!`, 'success');
            fetchWallets();
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        showToast('Failed to upload wallets. Is the backend running?', 'error');
    }
}

// Render Functions
function renderTokens() {
    const filtered = currentFilter === 'all'
        ? tokens
        : tokens.filter(t => t.category.toLowerCase() === currentFilter);

    if (filtered.length === 0) {
        tokenList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <p>No tokens found. Add wallets to start tracking!</p>
            </div>
        `;
        return;
    }

    tokenList.innerHTML = filtered.map((token, i) => `
        <div class="token-item">
            <div class="token-rank">${i + 1}</div>
            <div class="token-info">
                <div class="token-name">
                    ${token.symbol || 'UNKNOWN'}
                    <span class="badge badge-${token.category.toLowerCase()}">${getCategoryEmoji(token.category)} ${token.category}</span>
                </div>
                <div class="token-mint">${truncateAddress(token.mint_address)}</div>
            </div>
            <div class="token-stats">
                <div class="token-stat">
                    <span class="token-stat-value">${token.wallet_count}</span>
                    <span class="token-stat-label">Wallets</span>
                </div>
                <div class="token-stat">
                    <span class="token-stat-value">${token.hold_ratio}%</span>
                    <span class="token-stat-label">Holding</span>
                </div>
            </div>
            <div class="token-score">
                <span class="score-value">${token.moonshot_score}</span>
                <span class="score-label">Score</span>
            </div>
        </div>
    `).join('');
}

function renderSignals() {
    if (signals.length === 0) {
        signalList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚡</div>
                <p>No signals yet. Tracking in progress...</p>
            </div>
        `;
        return;
    }

    signalList.innerHTML = signals.slice(0, 10).map(signal => `
        <div class="signal-item">
            <div class="signal-icon">${getSignalIcon(signal.level)}</div>
            <div class="signal-content">
                <div class="signal-title">${signal.token_symbol} - ${signal.level} Signal</div>
                <div class="signal-meta">${signal.wallet_count} wallets • Confidence: ${signal.confidence}%</div>
            </div>
            <div class="signal-time">${formatTime(signal.created_at)}</div>
        </div>
    `).join('');
}

function renderWallets() {
    if (wallets.length === 0) {
        walletList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">👛</div>
                <p>No wallets tracked. Upload a wallets.txt to get started!</p>
            </div>
        `;
        return;
    }

    walletList.innerHTML = wallets.slice(0, 12).map(wallet => `
        <div class="wallet-item">
            <div class="wallet-avatar">${getWalletInitial(wallet)}</div>
            <div class="wallet-info">
                <div class="wallet-label">${wallet.label || 'Wallet'}</div>
                <div class="wallet-address">${truncateAddress(wallet.address)}</div>
            </div>
            <div class="wallet-score">${wallet.score.toFixed(0)}</div>
        </div>
    `).join('');
}

// File Handling
function handleDragOver(e) {
    e.preventDefault();
    uploadZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) processFile(file);
}

function processFile(file) {
    if (!file.name.endsWith('.txt')) {
        showToast('Please upload a .txt file', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        walletInput.value = e.target.result;
        showToast('File loaded! Click "Add Wallets" to submit.', 'info');
    };
    reader.readAsText(file);
}

function handleWalletSubmit() {
    const text = walletInput.value.trim();
    if (!text) {
        showToast('Please enter wallet addresses', 'error');
        return;
    }

    const walletData = parseWalletInput(text);
    if (walletData.length === 0) {
        showToast('No valid wallet addresses found', 'error');
        return;
    }

    uploadWallets(walletData);
    walletInput.value = '';
}

function parseWalletInput(text) {
    const lines = text.split('\n').filter(line => {
        const trimmed = line.trim();
        return trimmed && !trimmed.startsWith('#');
    });

    return lines.map(line => {
        const parts = line.split(',').map(p => p.trim());
        const address = parts[0];
        const label = parts[1] || null;

        // Basic Solana address validation (base58, ~44 chars)
        if (address.length >= 32 && address.length <= 44 && /^[1-9A-HJ-NP-Za-km-z]+$/.test(address)) {
            return { address, label };
        }
        return null;
    }).filter(Boolean);
}

// Utility Functions
function truncateAddress(address) {
    if (!address) return '...';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function getCategoryEmoji(category) {
    const emojis = {
        'MOONSHOT': '🚀',
        'RISING': '📈',
        'WATCHLIST': '👀',
        'DEAD': '💀'
    };
    return emojis[category] || '🪙';
}

function getSignalIcon(level) {
    const icons = {
        'STRONG': '🔥',
        'MODERATE': '⚡',
        'WEAK': '💫'
    };
    return icons[level] || '📊';
}

function getWalletInitial(wallet) {
    if (wallet.label) return wallet.label[0].toUpperCase();
    return wallet.address.slice(0, 2).toUpperCase();
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span>${getToastIcon(type)}</span>
        <span>${message}</span>
    `;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getToastIcon(type) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    return icons[type] || 'ℹ️';
}

// Mock Data (used when backend is not available)
function getMockTokens() {
    return [
        { mint_address: '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr', symbol: '$POPCAT', category: 'MOONSHOT', moonshot_score: 92, wallet_count: 18, hold_ratio: 85 },
        { mint_address: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', symbol: '$BONK', category: 'RISING', moonshot_score: 78, wallet_count: 24, hold_ratio: 72 },
        { mint_address: 'MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5', symbol: '$MEW', category: 'RISING', moonshot_score: 71, wallet_count: 15, hold_ratio: 68 },
        { mint_address: 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm', symbol: '$WIF', category: 'WATCHLIST', moonshot_score: 55, wallet_count: 9, hold_ratio: 45 },
        { mint_address: 'ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82', symbol: '$BOME', category: 'WATCHLIST', moonshot_score: 48, wallet_count: 7, hold_ratio: 38 }
    ];
}

function getMockSignals() {
    return [
        { token_symbol: '$NEWMEME', level: 'STRONG', wallet_count: 7, confidence: 85, created_at: new Date(Date.now() - 300000).toISOString() },
        { token_symbol: '$TRENDING', level: 'MODERATE', wallet_count: 4, confidence: 62, created_at: new Date(Date.now() - 1800000).toISOString() },
        { token_symbol: '$EARLY', level: 'WEAK', wallet_count: 2, confidence: 45, created_at: new Date(Date.now() - 7200000).toISOString() }
    ];
}

function getMockWallets() {
    return [
        { address: '9ZPsRWGkJsKxN3yzV5tVmQeXdExdB3sZ5o7z8qXnvW4D', label: 'WhaleAlpha', score: 87.5 },
        { address: 'ASTyfSim4Bk3p6SbPQdTDqNbJR8e3LxPvPbNwcQxJq9A', label: 'PumpTrader', score: 82.1 },
        { address: 'u6PJ8DtQuPFnfmwHbGFULQ4u4mrmwaQEV7xAZt4W8wX', label: 'EarlyBuyer', score: 76.8 },
        { address: 'HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH', label: null, score: 71.2 }
    ];
}
