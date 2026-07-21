const API_BASE_URL = '';

let state = {
  currentUser: null,
  activeTab: 'market',
  portfolios: [],
  tickerData: [],
  token: localStorage.getItem('jwt_token'),
};

let intervals = { ticker: null, tables: null, clock: null };

function getHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (state.token) h['Authorization'] = `Bearer ${state.token}`;
  return h;
}

async function apiGet(path) {
  const res = await fetch(`${API_BASE_URL}${path}`, { headers: getHeaders() });
  if (res.status === 401) { logout(); throw new Error('Session expired'); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function apiPost(path, data) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (res.status === 401) { logout(); throw new Error('Session expired'); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4000);
}

function setConnectionStatus(connected) {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (connected) {
    dot.className = 'status-dot connected';
    text.textContent = 'CONNECTED';
  } else {
    dot.className = 'status-dot disconnected';
    text.textContent = 'DISCONNECTED';
  }
}

function formatCurrency(val) {
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatChange(val) {
  return (val >= 0 ? '+' : '') + val.toFixed(2);
}

function sparkline(values) {
  if (!values || values.length === 0) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const chars = ['▁','▂','▃','▄','▅','▆','▇','█'];
  return values.map(v => chars[Math.min(7, Math.floor(((v - min) / range) * 7))]).join('');
}

function updateMarketClock() {
  const now = new Date();
  const est = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const time = est.toLocaleTimeString('en-US', { hour12: false });
  const date = est.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  const isOpen = est.getHours() >= 9 && est.getHours() < 16 && est.getDay() >= 1 && est.getDay() <= 5;
  const clock = document.getElementById('market-clock');
  if (clock) clock.textContent = `${date} ${time} ET ${isOpen ? '[OPEN]' : '[CLOSED]'}`;
}

async function init() {
  if (state.token) {
    try {
      const me = await apiGet('/api/auth/me');
      state.currentUser = me.username || me.user;
      showDashboard();
    } catch {
      logout();
    }
  } else {
    showLogin();
  }
  updateMarketClock();
  state.clock = setInterval(updateMarketClock, 1000);
}

function showLogin() {
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('dashboard').style.display = 'none';
  clearIntervals();
}

function showDashboard() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('dashboard').style.display = 'flex';
  document.getElementById('nav-user').textContent = state.currentUser || 'USER';
  switchTab('market');
  startIntervals();
}

async function login() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const errorEl = document.getElementById('login-error');
  if (!username || !password) {
    errorEl.textContent = 'Username and password required';
    errorEl.classList.add('show');
    return;
  }
  try {
    const result = await apiPost('/api/auth/login', { username, password });
    state.token = result.access_token || result.token;
    state.currentUser = result.username || username;
    localStorage.setItem('jwt_token', state.token);
    errorEl.classList.remove('show');
    showDashboard();
    showToast('Login successful', 'success');
  } catch (err) {
    errorEl.textContent = err.message || 'Login failed';
    errorEl.classList.add('show');
  }
}

function logout() {
  state.token = null;
  state.currentUser = null;
  localStorage.removeItem('jwt_token');
  clearIntervals();
  showLogin();
  showToast('Logged out', 'info');
}

function clearIntervals() {
  if (intervals.ticker) clearInterval(intervals.ticker);
  if (intervals.tables) clearInterval(intervals.tables);
  if (intervals.clock) clearInterval(intervals.clock);
  intervals.ticker = null;
  intervals.tables = null;
  intervals.clock = null;
}

function startIntervals() {
  if (intervals.ticker) clearInterval(intervals.ticker);
  if (intervals.tables) clearInterval(intervals.tables);
  fetchTicker();
  intervals.ticker = setInterval(fetchTicker, 5000);
  intervals.tables = setInterval(refreshCurrentTab, 15000);
}

function refreshCurrentTab() {
  switch (state.activeTab) {
    case 'market': fetchMarketData(); break;
    case 'portfolio': fetchPortfolios(); break;
    case 'news': fetchNews(); break;
    case 'research': fetchResearch(); break;
    case 'admin': fetchAdminData(); break;
  }
}

function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.querySelectorAll('.view-section').forEach(v => v.classList.toggle('active', v.id === `view-${tab}`));
  window.location.hash = `#${tab}`;

  switch (tab) {
    case 'market': fetchMarketData(); break;
    case 'portfolio': fetchPortfolios(); break;
    case 'news': fetchNews(); break;
    case 'research': fetchResearch(); break;
    case 'admin': fetchAdminData(); break;
  }
}

async function fetchTicker() {
  try {
    const data = await apiGet('/api/market/quotes?symbols=AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META');
    state.tickerData = Array.isArray(data) ? data : (data.quotes || []);
    renderTicker();
    setConnectionStatus(true);
  } catch {
    setConnectionStatus(false);
  }
}

function renderTicker() {
  const track = document.getElementById('ticker-track');
  if (!track || state.tickerData.length === 0) return;
  const items = state.tickerData.map(q => {
    const isUp = (q.change || 0) >= 0;
    const arrow = isUp ? '▲' : '▼';
    const cls = isUp ? 'up' : 'down';
    return `<span class="ticker-item">
      <span class="ticker-symbol">${q.symbol}</span>
      <span class="ticker-price">${q.price ? q.price.toFixed(2) : '—'}</span>
      <span class="ticker-arrow ${cls}">${arrow}</span>
      <span class="ticker-change ${cls}">${formatChange(q.change || 0)}</span>
    </span>`;
  }).join('');
  track.innerHTML = items + items;
}

async function fetchMarketData() {
  const container = document.getElementById('view-market');
  if (!container) return;

  const searchQuery = document.getElementById('market-search')?.value?.trim() || '';

  try {
    container.innerHTML = `<div class="loading-matrix">█ LOADING MARKET DATA █</div>`;

    let quotes = [];
    let gainers = [];
    let losers = [];

    if (searchQuery) {
      const searchRes = await apiGet(`/api/market/search?q=${encodeURIComponent(searchQuery)}`);
      if (searchRes.results && searchRes.results.length > 0) {
        const symbols = searchRes.results.slice(0, 5).map(r => r.symbol);
        const qData = await apiGet(`/api/market/quotes?symbols=${symbols.join(',')}`);
        quotes = Array.isArray(qData) ? qData : (qData.quotes || []);
      }
    } else {
      const [qData, movers] = await Promise.all([
        apiGet('/api/market/quotes?symbols=AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,BRK.B,JPM,V,PG,JNJ,UNH,HD,XOM,KO,PEP,MRK,BA,DIS,INTC,AMD,NFLX,ADBE,CRM,PYPL'),
        apiGet('/api/market/movers').catch(() => ({ gainers: [], losers: [] })),
      ]);
      quotes = Array.isArray(qData) ? qData : (qData.quotes || []);
      gainers = movers.gainers || [];
      losers = movers.losers || [];
    }

    let html = `<h2>▌MARKET OVERVIEW</h2>`;
    html += `<div class="search-bar">
      <input type="text" class="form-input" id="market-search" placeholder="SEARCH SYMBOL..." value="${searchQuery}">
      <button class="btn btn-amber" onclick="fetchMarketData()">SEARCH</button>
    </div>`;

    if (quotes.length > 0) {
      html += `<table class="data-table" id="market-table">
        <thead><tr><th>Symbol</th><th>Name</th><th>Price</th><th>Change</th><th>Change %</th><th>Volume</th><th>Trend</th></tr></thead>
        <tbody>`;
      quotes.forEach(q => {
        const isUp = (q.change || 0) >= 0;
        const changeCls = isUp ? 'up' : 'down';
        const arrow = isUp ? '▲' : '▼';
        const sp = sparkline(q.sparkline || q.history || []);
        html += `<tr>
          <td class="symbol-cell">${q.symbol}</td>
          <td>${q.name || '—'}</td>
          <td class="price-cell">${q.price ? q.price.toFixed(2) : '—'}</td>
          <td class="change-cell ${changeCls}">${arrow} ${formatChange(q.change || 0)}</td>
          <td class="change-cell ${changeCls}">${q.change_pct ? q.change_pct.toFixed(2) + '%' : '—'}</td>
          <td class="num-cell">${q.volume ? q.volume.toLocaleString() : '—'}</td>
          <td style="font-size:14px;letter-spacing:1px;color:var(--green)">${sp || '—'}</td>
        </tr>`;
      });
      html += `</tbody></table>`;
    }

    if (gainers.length > 0) {
      html += `<h3>▌TOP GAINERS</h3><table class="data-table">
        <thead><tr><th>Symbol</th><th>Price</th><th>Change %</th></tr></thead><tbody>`;
      gainers.forEach(g => {
        html += `<tr><td class="symbol-cell">${g.symbol}</td><td class="price-cell">${g.price ? g.price.toFixed(2) : '—'}</td>
          <td class="change-cell up">▲ ${(g.change_pct || 0).toFixed(2)}%</td></tr>`;
      });
      html += `</tbody></table>`;
    }

    if (losers.length > 0) {
      html += `<h3>▌TOP LOSERS</h3><table class="data-table">
        <thead><tr><th>Symbol</th><th>Price</th><th>Change %</th></tr></thead><tbody>`;
      losers.forEach(l => {
        html += `<tr><td class="symbol-cell">${l.symbol}</td><td class="price-cell">${l.price ? l.price.toFixed(2) : '—'}</td>
          <td class="change-cell down">▼ ${(l.change_pct || 0).toFixed(2)}%</td></tr>`;
      });
      html += `</tbody></table>`;
    }

    if (quotes.length === 0 && !searchQuery) {
      html += `<div class="empty-state"><div class="empty-state-text">⚠ NO MARKET DATA AVAILABLE</div>
        <div class="empty-state-hint">Configure API keys or check backend connection</div></div>`;
    }

    container.innerHTML = html;
    document.getElementById('market-search')?.addEventListener('keydown', e => { if (e.key === 'Enter') fetchMarketData(); });
  } catch (err) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-state-text">⚠ ERROR LOADING MARKET DATA</div>
      <div class="empty-state-hint">${err.message}</div>
    </div>`;
    showToast(err.message, 'error');
  }
}

async function fetchPortfolios() {
  const container = document.getElementById('view-portfolio');
  if (!container) return;

  try {
    container.innerHTML = `<div class="loading-matrix">█ LOADING PORTFOLIO █</div>`;

    const portfolios = await apiGet('/api/portfolio/list');
    state.portfolios = Array.isArray(portfolios) ? portfolios : [];

    let html = `<h2>▌PORTFOLIO</h2>`;

    if (state.portfolios.length === 0) {
      html += `<div class="empty-state"><div class="empty-state-text">NO PORTFOLIOS FOUND</div>
        <div class="empty-state-hint">Create a portfolio to start trading</div>
        <button class="btn btn-green" onclick="createPortfolio()" style="margin-top:16px">+ CREATE PORTFOLIO</button>
      </div>`;
      container.innerHTML = html;
      return;
    }

    const pf = state.portfolios[0];
    const detail = await apiGet(`/api/portfolio/${pf.id}`);

    const pnlClass = (detail.pnl || 0) >= 0 ? 'positive' : 'negative';
    html += `<div class="portfolio-summary">
      <div class="portfolio-card"><div class="portfolio-card-value">$${formatCurrency(detail.total_value || 0)}</div>
        <div class="portfolio-card-label">Total Value</div></div>
      <div class="portfolio-card"><div class="portfolio-card-value">$${formatCurrency(detail.cash || 0)}</div>
        <div class="portfolio-card-label">Cash</div></div>
      <div class="portfolio-card"><div class="portfolio-card-value">$${formatCurrency(detail.total_position_value || 0)}</div>
        <div class="portfolio-card-label">Positions</div></div>
      <div class="portfolio-card"><div class="portfolio-card-value ${pnlClass}">${(detail.pnl || 0) >= 0 ? '+' : ''}$${formatCurrency(detail.pnl || 0)}</div>
        <div class="portfolio-card-label">P&L</div></div>
    </div>`;

    html += `<div style="display:flex;gap:8px;margin-bottom:16px">
      <button class="btn btn-green" onclick="showBuyModal()">+ BUY</button>
      <button class="btn btn-red" onclick="showSellModal()">- SELL</button>
    </div>`;

    if (detail.positions && detail.positions.length > 0) {
      html += `<table class="data-table">
        <thead><tr><th>Symbol</th><th>Quantity</th><th>Avg Cost</th><th>Current Value</th><th>Unrealized P&L</th></tr></thead>
        <tbody>`;
      detail.positions.forEach(p => {
        const cost = p.avg_cost * p.quantity;
        const pnl = p.current_value - cost;
        const pnlCls = pnl >= 0 ? 'positive' : 'negative';
        html += `<tr>
          <td class="symbol-cell">${p.symbol}</td>
          <td class="num-cell">${p.quantity}</td>
          <td class="price-cell">$${p.avg_cost.toFixed(2)}</td>
          <td class="price-cell">$${p.current_value.toFixed(2)}</td>
          <td class="num-cell pnl-cell ${pnlCls}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
        </tr>`;
      });
      html += `</tbody></table>`;
    } else {
      html += `<div class="empty-state"><div class="empty-state-text">NO POSITIONS</div>
        <div class="empty-state-hint">Buy securities to build your portfolio</div></div>`;
    }

    try {
      const trades = await apiGet(`/api/portfolio/trades/${pf.id}`);
      if (trades && trades.length > 0) {
        html += `<h3 style="margin-top:20px">▌TRADE HISTORY</h3><table class="data-table">
          <thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Quantity</th><th>Price</th><th>Status</th></tr></thead>
          <tbody>`;
        trades.slice(0, 20).forEach(t => {
          const sideCls = t.side === 'buy' ? 'up' : 'down';
          html += `<tr>
            <td style="font-size:11px;color:var(--text-dim)">${t.timestamp ? new Date(t.timestamp).toLocaleString() : '—'}</td>
            <td class="symbol-cell">${t.symbol}</td>
            <td class="change-cell ${sideCls}">${t.side.toUpperCase()}</td>
            <td class="num-cell">${t.quantity}</td>
            <td class="price-cell">$${(t.price || 0).toFixed(2)}</td>
            <td>${t.status || 'filled'}</td>
          </tr>`;
        });
        html += `</tbody></table>`;
      }
    } catch {}

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-state-text">⚠ ERROR LOADING PORTFOLIO</div>
      <div class="empty-state-hint">${err.message}</div>
    </div>`;
    showToast(err.message, 'error');
  }
}

async function createPortfolio() {
  const name = prompt('Enter portfolio name:');
  if (!name) return;
  try {
    await apiPost('/api/portfolio/create', { name, initial_cash: 100000 });
    showToast('Portfolio created', 'success');
    fetchPortfolios();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

let tradeSymbol = '';
function showBuyModal() { showTradeModal('buy'); }
function showSellModal() { showTradeModal('sell'); }

function showTradeModal(side) {
  const modal = document.getElementById('trade-modal');
  document.getElementById('trade-modal-title').textContent = side === 'buy' ? 'BUY SECURITIES' : 'SELL SECURITIES';
  document.getElementById('trade-side').value = side;
  document.getElementById('trade-symbol').value = tradeSymbol || '';
  document.getElementById('trade-quantity').value = '';
  document.getElementById('trade-price').value = '';
  document.getElementById('trade-error').style.display = 'none';
  modal.classList.add('active');
  setTimeout(() => document.getElementById('trade-symbol').focus(), 100);
}

function closeTradeModal() {
  document.getElementById('trade-modal').classList.remove('active');
}

async function submitTrade() {
  const side = document.getElementById('trade-side').value;
  const symbol = document.getElementById('trade-symbol').value.trim().toUpperCase();
  const quantity = parseFloat(document.getElementById('trade-quantity').value);
  const price = parseFloat(document.getElementById('trade-price').value);
  const errorEl = document.getElementById('trade-error');

  if (!symbol || !quantity || !price) {
    errorEl.textContent = 'All fields required';
    errorEl.style.display = 'block';
    return;
  }

  if (state.portfolios.length === 0) {
    errorEl.textContent = 'No portfolio available';
    errorEl.style.display = 'block';
    return;
  }

  try {
    const pfId = state.portfolios[0].id;
    const endpoint = `/api/portfolio/${pfId}/${side}`;
    await apiPost(endpoint, { symbol, quantity, price });
    closeTradeModal();
    showToast(`${side.toUpperCase()} ${quantity} ${symbol} @ $${price.toFixed(2)}`, 'success');
    fetchPortfolios();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
  }
}

async function fetchNews() {
  const container = document.getElementById('view-news');
  if (!container) return;

  const activeFilter = document.querySelector('.filter-btn.active')?.dataset?.filter || 'all';

  try {
    container.innerHTML = `<div class="loading-matrix">█ LOADING NEWS █</div>`;

    let news;
    if (activeFilter === 'all') {
      news = await apiGet('/api/news');
    } else {
      news = await apiGet(`/api/news?source=${encodeURIComponent(activeFilter)}`);
    }

    const articles = Array.isArray(news) ? news : (news.articles || []);

    let html = `<h2>▌MARKET NEWS</h2>`;
    html += `<div class="filter-bar">
      <button class="filter-btn ${activeFilter === 'all' ? 'active' : ''}" data-filter="all" onclick="setNewsFilter(this)">ALL</button>
      <button class="filter-btn ${activeFilter === 'Reuters' ? 'active' : ''}" data-filter="Reuters" onclick="setNewsFilter(this)">REUTERS</button>
      <button class="filter-btn ${activeFilter === 'Bloomberg' ? 'active' : ''}" data-filter="Bloomberg" onclick="setNewsFilter(this)">BLOOMBERG</button>
      <button class="filter-btn ${activeFilter === 'CNBC' ? 'active' : ''}" data-filter="CNBC" onclick="setNewsFilter(this)">CNBC</button>
      <button class="filter-btn ${activeFilter === 'MarketWatch' ? 'active' : ''}" data-filter="MarketWatch" onclick="setNewsFilter(this)">MARKETWATCH</button>
    </div>`;

    if (articles.length === 0) {
      html += `<div class="empty-state"><div class="empty-state-text">NO NEWS ARTICLES</div>
        <div class="empty-state-hint">Check back later for updates</div></div>`;
    } else {
      articles.forEach(a => {
        const ts = a.datetime || a.published_at || '';
        const timeStr = ts ? new Date(ts).toLocaleString() : '';
        html += `<div class="news-card" onclick="window.open('${a.url || a.link || '#'}','_blank')">
          <div class="news-source">${a.source || '—'} ${timeStr ? '· ' + timeStr : ''}</div>
          <div class="news-title">${a.title || 'Untitled'}</div>
          <div class="news-summary">${(a.summary || a.description || '').substring(0, 200)}</div>
        </div>`;
      });
    }

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-state-text">⚠ ERROR LOADING NEWS</div>
      <div class="empty-state-hint">${err.message}</div>
    </div>`;
    showToast(err.message, 'error');
  }
}

function setNewsFilter(el) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  fetchNews();
}

async function fetchResearch() {
  const container = document.getElementById('view-research');
  if (!container) return;

  const searchQuery = document.getElementById('research-search')?.value?.trim() || '';

  try {
    container.innerHTML = `<div class="loading-matrix">█ LOADING RESEARCH █</div>`;

    let papers;
    if (searchQuery) {
      papers = await apiGet(`/api/research/search?q=${encodeURIComponent(searchQuery)}`);
    } else {
      papers = await apiGet('/api/research');
    }

    const paperList = Array.isArray(papers) ? papers : (papers.papers || []);

    let html = `<h2>▌RESEARCH</h2>`;
    html += `<div class="search-bar">
      <input type="text" class="form-input" id="research-search" placeholder="SEARCH PAPERS..." value="${searchQuery}">
      <button class="btn btn-amber" onclick="fetchResearch()">SEARCH</button>
    </div>`;

    if (paperList.length === 0) {
      html += `<div class="empty-state"><div class="empty-state-text">NO PAPERS FOUND</div>
        <div class="empty-state-hint">Try a different search term</div></div>`;
    } else {
      paperList.forEach(p => {
        const authors = Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || '');
        const cats = Array.isArray(p.categories) ? p.categories : [];
        html += `<div class="paper-card" onclick="toggleAbstract(this)">
          <div class="paper-title">${p.title || 'Untitled'}</div>
          <div class="paper-authors">${authors}</div>
          ${cats.length > 0 ? `<div class="paper-categories">${cats.map(c => `<span class="paper-cat">${c}</span>`).join('')}</div>` : ''}
          <div class="paper-abstract">${p.abstract || 'No abstract available'}</div>
        </div>`;
      });
    }

    container.innerHTML = html;
    document.getElementById('research-search')?.addEventListener('keydown', e => { if (e.key === 'Enter') fetchResearch(); });
  } catch (err) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-state-text">⚠ ERROR LOADING RESEARCH</div>
      <div class="empty-state-hint">${err.message}</div>
    </div>`;
    showToast(err.message, 'error');
  }
}

function toggleAbstract(el) {
  const abs = el.querySelector('.paper-abstract');
  if (abs) abs.classList.toggle('show');
}

async function fetchAdminData() {
  const container = document.getElementById('view-admin');
  if (!container) return;

  try {
    container.innerHTML = `<div class="loading-matrix">█ LOADING ADMIN █</div>`;

    const [audit, health] = await Promise.all([
      apiGet('/api/admin/audit').catch(() => ({ logs: [] })),
      apiGet('/api/admin/health').catch(() => ({ status: 'unknown' })),
    ]);

    const logs = Array.isArray(audit) ? audit : (audit.logs || []);
    const healthData = health;

    let html = `<h2>▌ADMIN</h2><div class="admin-grid">`;

    html += `<div class="card"><div class="card-title">SYSTEM HEALTH</div>`;
    const checks = {
      'API Server': healthData.api || healthData.status || 'ok',
      'Database': healthData.database || healthData.db || 'ok',
      'Market Data': healthData.market || healthData.market_data || 'ok',
      'News Feed': healthData.news || healthData.news_feed || 'ok',
    };
    Object.entries(checks).forEach(([k, v]) => {
      const statusClass = v === 'ok' || v === true ? 'ok' : (v === 'warn' ? 'warn' : 'error');
      html += `<div class="health-item"><span class="health-label">${k}</span>
        <span class="health-status ${statusClass}">${String(v).toUpperCase()}</span></div>`;
    });
    html += `</div>`;

    html += `<div class="card"><div class="card-title">AUDIT LOG</div>`;
    if (logs.length === 0) {
      html += `<div class="empty-state"><div class="empty-state-text">NO AUDIT LOGS</div></div>`;
    } else {
      html += `<table class="data-table">
        <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Details</th></tr></thead>
        <tbody>`;
      logs.slice(0, 25).forEach(l => {
        html += `<tr>
          <td style="font-size:10px;color:var(--text-dim);white-space:nowrap">${l.timestamp ? new Date(l.timestamp).toLocaleString() : '—'}</td>
          <td style="font-size:11px">${l.user || '—'}</td>
          <td style="font-size:11px;color:var(--amber)">${l.action || '—'}</td>
          <td style="font-size:10px;color:var(--text-dim);max-width:200px;overflow:hidden;text-overflow:ellipsis">${l.details || '—'}</td>
        </tr>`;
      });
      html += `</tbody></table>`;
    }
    html += `</div></div>`;

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-state-text">⚠ ERROR LOADING ADMIN</div>
      <div class="empty-state-hint">${err.message}</div>
    </div>`;
    showToast(err.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  init();

  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  document.getElementById('login-btn')?.addEventListener('click', login);
  document.getElementById('login-password')?.addEventListener('keydown', e => { if (e.key === 'Enter') login(); });
  document.getElementById('login-username')?.addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('login-password').focus(); });
  document.getElementById('logout-btn')?.addEventListener('click', logout);

  const hash = window.location.hash.replace('#', '');
  if (hash && ['market', 'portfolio', 'news', 'research', 'admin'].includes(hash) && state.token) {
    state.activeTab = hash;
  }
});
