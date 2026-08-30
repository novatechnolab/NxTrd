<script>
  import { onMount, onDestroy } from 'svelte';
  import LeftPanel from './_components/LeftPanel.svelte';
  import TabBar from './_components/TabBar.svelte';
  import EmptyState from './_components/EmptyState.svelte';
  import DetailView from './_components/DetailView.svelte';
  import ToastContainer from './_components/ToastContainer.svelte';

  // ── Search state ────────────────────────────────────────────────────────────
  let searchVal = '';
  let searchResults = [];
  let showSugg = false;
  let symbolListError = '';

  // ── Data state ──────────────────────────────────────────────────────────────
  let spurtData = [];
  let symbolList = [];
  let minPct = 5;
  let prevRankMap = {};
  let oiTimestampMap = {};

  // ── Tab management ──────────────────────────────────────────────────────────
  let watchList = [];
  let activeTab = null;
  let tabTimers = {};
  let prevDetails = {};
  let aiCache = {};

  // ── Status bar state ────────────────────────────────────────────────────────
  let leftCountdown = 60;
  let leftTimer = null;
  let lastUpdateStr = '–';
  let lpTimestamp = '–';
  let sourceMode = 'nse';
  let pulseRed = false;
  let eodSnapshotMode = false;

  // ── Toasts ──────────────────────────────────────────────────────────────────
  let toasts = [];

  // ── Market helpers ──────────────────────────────────────────────────────────
  function isMarketOpen() {
    const now = new Date();
    const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
    const ist = new Date(utcMs + 5.5 * 3600000);
    const day = ist.getDay();
    if (day === 0 || day === 6) return false;
    const mins = ist.getHours() * 60 + ist.getMinutes();
    return mins >= 555 && mins <= 940;
  }
  function fmtTime(d) {
    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }
  function fmt(n, d = 2) {
    if (n === null || n === undefined) return '–';
    return Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  // ── Toast ───────────────────────────────────────────────────────────────────
  function showToast(sym, changes) {
    const parts = [];
    if (changes.ltp) parts.push({ type: 'ltp', dir: changes.ltp.new > changes.ltp.old ? 'pos' : 'neg', arrow: changes.ltp.new > changes.ltp.old ? '▲' : '▼', old: changes.ltp.old, new: changes.ltp.new });
    if (changes.pcr) parts.push({ type: 'pcr', old: changes.pcr.old, new: changes.pcr.new });
    if (changes.max_pain) parts.push({ type: 'max_pain', new: changes.max_pain.new });
    if (!parts.length) return;
    const id = Date.now();
    toasts = [{ id, sym, parts }, ...toasts].slice(0, 5);
    setTimeout(() => dismissToast(id), 5000);
  }
  function dismissToast(id) { toasts = toasts.filter(t => t.id !== id); }

  // ── Symbol list ─────────────────────────────────────────────────────────────
  async function loadSymbolList() {
    try {
      const res = await fetch('/api/equity-list');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const j = await res.json();
      if (j.error) throw new Error(j.error);
      symbolList = (j.stocks || []).map(s => ({ sym: s.tradingsymbol, name: s.name || s.tradingsymbol, tag: 'F&O' }));
      symbolListError = '';
      if (!symbolList.length) {
        symbolListError = '⚠ No instruments found — go to Settings → Sync Instruments.';
      }
    } catch (e) {
      symbolList = [];
      symbolListError = `⚠ Cannot load symbol list — ${e.message}. Go to Settings → Sync Instruments.`;
    }
  }

  // ── Search ──────────────────────────────────────────────────────────────────
  function onSearchInput(e) {
    const q = e.target.value.trim().toUpperCase();
    if (!q) { showSugg = false; return; }
    if (symbolListError) { showSugg = true; searchResults = []; return; }
    searchResults = symbolList.filter(s => s.sym.startsWith(q) || s.name.toUpperCase().includes(q)).slice(0, 12);
    showSugg = true;
  }
  function onSearchKey(e) {
    if (e.key === 'Enter') { showSugg = false; const v = searchVal.trim().toUpperCase(); if (v) selectSymbol(v); }
    else if (e.key === 'Escape') showSugg = false;
  }
  function pickSugg(s) { searchVal = s.sym; showSugg = false; selectSymbol(s.sym); }
  function goSearch() { showSugg = false; if (searchVal.trim()) selectSymbol(searchVal.trim()); }

  // ── Left panel – OI spurt list ──────────────────────────────────────────────
  let _leftDebounce = null;

  async function loadSpurt() {
    try {
      const j = await fetch(`/api/oi/spurt?min_pct=${minPct}`).then(r => r.json());
      const newData = (j.data || j.spurts || []).sort((a, b) => b.oi_change_pct - a.oi_change_pct);
      const newRankMap = {};
      newData.forEach((d, i) => { newRankMap[d.symbol] = i; });

      const now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      newData.forEach(d => {
        const prev = oiTimestampMap[d.symbol];
        if (!prev || Math.abs(d.oi_change_pct - prev.pct) > 0.01) {
          oiTimestampMap[d.symbol] = { pct: d.oi_change_pct, time: now };
        }
        d._ts = d.spurt_time || oiTimestampMap[d.symbol]?.time || now;
      });

      prevRankMap = newRankMap;
      spurtData = newData;
      sourceMode = j.source === 'kite' ? 'kite' : 'nse';
      pulseRed = sourceMode === 'kite';

      const mktOpen = j.market_open !== undefined ? j.market_open : isMarketOpen();
      const tsStr = j.data_as_of ? fmtTime(new Date(j.data_as_of)) : fmtTime(new Date());
      eodSnapshotMode = !mktOpen;

      if (!mktOpen) {
        lastUpdateStr = '🌙 Market Closed';
        lpTimestamp = `EOD ${tsStr} IST`;
        clearInterval(leftTimer); leftTimer = null;
      } else {
        lastUpdateStr = 'L:' + tsStr;
        lpTimestamp = tsStr;
        if (!leftTimer) startLeftCountdown();
      }
    } catch (e) { console.error('loadSpurt', e); }
  }

  function startLeftCountdown() {
    leftCountdown = 60; clearInterval(leftTimer);
    leftTimer = setInterval(() => { leftCountdown--; if (leftCountdown <= 0) { loadSpurt(); leftCountdown = 60; } }, 1000);
  }

  function onSliderChange(e) {
    minPct = e.detail;
    prevRankMap = {};
    clearTimeout(_leftDebounce);
    _leftDebounce = setTimeout(() => loadSpurt(), 300);
  }

  // ── Tab management ──────────────────────────────────────────────────────────
  function selectSymbol(sym) {
    sym = sym.toUpperCase().trim();
    if (!sym) return;
    if (!watchList.includes(sym)) watchList = [...watchList, sym];
    switchTab(sym);
  }

  function switchTab(sym) {
    activeTab = sym;
    watchList = [...watchList];
    if (tabTimers[sym]) clearInterval(tabTimers[sym]);
    fetchDetail(sym);
    if (isMarketOpen()) tabTimers[sym] = setInterval(() => fetchDetail(sym), 15000);
  }

  function closeTab(sym) {
    if (tabTimers[sym]) { clearInterval(tabTimers[sym]); delete tabTimers[sym]; }
    delete prevDetails[sym];
    const idx = watchList.indexOf(sym);
    watchList = watchList.filter(s => s !== sym);
    if (activeTab === sym) {
      activeTab = watchList[Math.min(idx, watchList.length - 1)] || null;
      if (activeTab) switchTab(activeTab);
    }
  }

  // ── Detail fetch ────────────────────────────────────────────────────────────
  async function fetchDetail(sym) {
    if (activeTab !== sym) return;
    try {
      const d = await fetch(`/api/oi/symbol/${encodeURIComponent(sym)}`).then(r => r.json());
      if (d.error && !d.ltp) throw new Error(d.error);
      const mktOpen = d.market_open !== undefined ? d.market_open : isMarketOpen();
      if (!mktOpen && tabTimers[sym]) { clearInterval(tabTimers[sym]); delete tabTimers[sym]; }
      const spurtRow = spurtData.find(s => s.symbol === sym) || {};
      const prev = prevDetails[sym] || {};
      const changes = detectChanges(prev, d, spurtRow);
      if (Object.keys(changes).length && Object.keys(prev).length) showToast(sym, changes);
      prevDetails[sym] = { ...d, ltp: d.ltp || spurtRow.ltp, oi_change_pct: spurtRow.oi_change_pct, arrowState: prev.arrowState || {} };
      prevDetails = { ...prevDetails };
    } catch (e) { console.error('fetchDetail', sym, e); }
  }

  function detectChanges(prev, curr, spurtRow) {
    const changes = {};
    const ltp = spurtRow.ltp || curr.ltp;
    if (prev.ltp && Math.abs(ltp - prev.ltp) > 0.05) changes.ltp = { old: prev.ltp, new: ltp };
    if (prev.pcr && curr.pcr && Math.abs(curr.pcr - prev.pcr) > 0.01) changes.pcr = { old: prev.pcr, new: curr.pcr };
    if (prev.max_pain && curr.max_pain && curr.max_pain !== prev.max_pain) changes.max_pain = { old: prev.max_pain, new: curr.max_pain };
    if (prev.oi_change_pct && spurtRow.oi_change_pct && Math.abs(spurtRow.oi_change_pct - prev.oi_change_pct) > 0.1) changes.oi_change_pct = true;
    if (prev.straddle && curr.straddle && Math.abs(curr.straddle - prev.straddle) > 1.0) changes.straddle = { old: prev.straddle, new: curr.straddle };
    return changes;
  }

  function manualRefresh() { loadSpurt(); if (activeTab) fetchDetail(activeTab); }

  // ── Market lifecycle watcher ─────────────────────────────────────────────────
  let _wasMarketOpen = false;
  let _lifecycleTimer = null;

  // ── Boot ────────────────────────────────────────────────────────────────────
  onMount(() => {
    _wasMarketOpen = isMarketOpen();
    loadSymbolList();
    loadSpurt();
    if (_wasMarketOpen) startLeftCountdown();

    _lifecycleTimer = setInterval(() => {
      const nowOpen = isMarketOpen();
      if (nowOpen && !_wasMarketOpen) {
        _wasMarketOpen = true;
        loadSpurt(); startLeftCountdown();
        if (activeTab) switchTab(activeTab);
      } else if (!nowOpen && _wasMarketOpen) {
        _wasMarketOpen = false;
        clearInterval(leftTimer); leftTimer = null;
        Object.keys(tabTimers).forEach(s => { clearInterval(tabTimers[s]); delete tabTimers[s]; });
      }
    }, 60000);
  });

  onDestroy(() => {
    clearInterval(leftTimer);
    clearInterval(_lifecycleTimer);
    clearTimeout(_leftDebounce);
    Object.keys(tabTimers).forEach(s => clearInterval(tabTimers[s]));
  });
</script>

<svelte:head>
  <title>OI Spurt Scanner — TradeSignal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
</svelte:head>

<ToastContainer {toasts} on:dismiss={e => dismissToast(e.detail)} />

<div class="oi-page">
  <!-- Header -->
  <header class="oi-header">
    <div class="logo">OI<span>Spurt</span></div>

    <!-- Search -->
    <div class="search-wrap">
      <input
        type="text"
        class="search-input"
        placeholder="Search F&O stock or index…"
        autocomplete="off"
        spellcheck="false"
        bind:value={searchVal}
        on:input={onSearchInput}
        on:keydown={onSearchKey}
        on:blur={() => setTimeout(() => { showSugg = false; }, 150)}
      />
      <span class="s-icon">⌕</span>
      {#if showSugg}
        <div class="suggestions">
          {#if symbolListError}
            <div class="si-error">{symbolListError}</div>
          {:else if searchResults.length === 0}
            <div class="si-empty">No matching symbols</div>
          {:else}
            {#each searchResults as s}
              <div class="si" on:mousedown|preventDefault={() => pickSugg(s)} role="option" tabindex="-1">
                <span class="si-sym">{s.sym}</span>
                <span class="si-name">{s.name}</span>
                <span class="si-tag">{s.tag}</span>
              </div>
            {/each}
          {/if}
        </div>
      {/if}
    </div>
    <button class="go-btn" on:click={goSearch}>GO</button>

    <!-- Status bar -->
    <div class="status-bar">
      <span class="source-indicator">
        <span class="src-label" class:src-green={sourceMode === 'nse'} class:src-dim={sourceMode !== 'nse'}>NSE Scraper</span>
        <span class="src-sep">|</span>
        <span class="src-label" class:src-red={sourceMode === 'kite'} class:src-dim={sourceMode !== 'kite'}>Kite API</span>
      </span>
      <span class="last-update">{lastUpdateStr}</span>
      {#if eodSnapshotMode}
        <span class="eod-badge">EOD Snapshot</span>
      {:else}
        <span>Left: <span class="cd">{leftCountdown}</span>s</span>
      {/if}
      <div class="pulse" class:pulse-red={pulseRed}></div>
      <button class="ref-btn" on:click={manualRefresh}>↺ Refresh</button>
    </div>
  </header>

  <!-- Body layout -->
  <div class="layout">
    <LeftPanel
      {spurtData}
      {minPct}
      {activeTab}
      {oiTimestampMap}
      {lpTimestamp}
      on:select={e => selectSymbol(e.detail)}
      on:sliderChange={onSliderChange}
    />

    <main class="right-panel">
      <TabBar
        {watchList}
        {activeTab}
        on:switch={e => switchTab(e.detail)}
        on:close={e => closeTab(e.detail)}
      />

      <div class="rp-content">
        {#if !activeTab || !watchList.length}
          <EmptyState />
        {:else}
          {#each watchList as sym (sym)}
            <div class="det-pane" class:det-visible={sym === activeTab}>
              <DetailView
                {sym}
                detail={prevDetails[sym]}
                spurtRow={spurtData.find(s => s.symbol === sym) || {}}
                {aiCache}
                on:close={() => closeTab(sym)}
                on:aiCache={e => { aiCache = { ...aiCache, [sym]: e.detail }; }}
              />
            </div>
          {/each}
        {/if}
      </div>
    </main>
  </div>
</div>

<style>
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }

  .oi-page {
    --bg: #08090f;
    --surface: #0f1320;
    --surface2: #141928;
    --surface3: #1a2035;
    --border: #1e2a42;
    --border2: #243050;
    --accent: #00e5ff;
    --green: #00e676;
    --red: #ff3d71;
    --orange: #ff9100;
    --yellow: #ffd740;
    --text: #e2e8f0;
    --muted: #4a5a7a;
    --muted2: #6b7a99;
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg);
    color: var(--text);
    display: flex; flex-direction: column;
    height: 100vh; overflow: hidden;
  }

  /* ── Header ── */
  .oi-header {
    height: 50px; background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center;
    padding: 0 14px; gap: 10px; flex-shrink: 0; z-index: 100;
  }
  .logo { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 16px; color: var(--accent); letter-spacing: 1px; white-space: nowrap; flex-shrink: 0; }
  .logo span { color: var(--text); }

  .search-wrap { flex: 1; max-width: 380px; position: relative; }
  .search-input { width: 100%; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 6px 30px 6px 10px; color: var(--text); font-family: inherit; font-size: 11px; outline: none; transition: border-color .2s; }
  .search-input:focus { border-color: var(--accent); }
  .search-input::placeholder { color: var(--muted); }
  .s-icon { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); color: var(--muted); font-size: 12px; pointer-events: none; }

  .suggestions { position: absolute; top: calc(100% + 3px); left: 0; right: 0; background: var(--surface); border: 1px solid var(--border2); border-radius: 8px; max-height: 220px; overflow-y: auto; z-index: 9999; box-shadow: 0 10px 40px rgba(0,0,0,.7); }
  .si { display: flex; align-items: center; gap: 6px; padding: 6px 10px; cursor: pointer; font-size: 11px; border-bottom: 1px solid var(--border); transition: background .1s; }
  .si:last-child { border-bottom: none; }
  .si:hover { background: var(--surface2); }
  .si-sym { font-family: 'Syne', sans-serif; font-weight: 700; color: var(--accent); min-width: 90px; font-size: 11px; }
  .si-name { color: var(--muted2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .si-tag { font-size: 8px; padding: 1px 4px; border-radius: 3px; background: var(--surface3); color: var(--muted2); border: 1px solid var(--border); }
  .si-error { padding: 8px 10px; font-size: 10px; color: var(--red); line-height: 1.5; }
  .si-empty { padding: 8px 10px; font-size: 10px; color: var(--muted); text-align: center; }

  .go-btn { background: var(--accent); color: #000; border: none; border-radius: 6px; padding: 5px 12px; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 11px; cursor: pointer; transition: opacity .15s; }
  .go-btn:hover { opacity: .85; }

  .status-bar { margin-left: auto; display: flex; align-items: center; gap: 8px; font-size: 10px; color: var(--muted2); white-space: nowrap; flex-shrink: 0; }
  .source-indicator { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--border); padding: 2px 6px; border-radius: 4px; background: var(--surface); font-size: 8px; font-weight: 500; margin-right: 4px; }
  .src-sep { opacity: .2; }
  .src-label { transition: all .3s ease; }
  .src-dim { opacity: .4; }
  .src-green { color: var(--green); opacity: 1; font-weight: 700; text-shadow: 0 0 4px rgba(0,230,118,.4); }
  .src-red { color: var(--red); opacity: 1; font-weight: 700; text-shadow: 0 0 4px rgba(255,61,113,.4); }
  .eod-badge { color: var(--yellow); font-weight: 600; font-size: 9px; }
  .cd { color: var(--accent); }
  .last-update { font-size: 10px; }

  .pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
  .pulse-red { background: var(--red) !important; animation: pulse-red 2s infinite !important; }
  @keyframes pulse { 0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(0,230,118,.4)} 50%{opacity:.7;box-shadow:0 0 0 4px rgba(0,230,118,0)} }
  @keyframes pulse-red { 0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(255,61,113,.4)} 50%{opacity:.7;box-shadow:0 0 0 4px rgba(255,61,113,0)} }
  .ref-btn { background: transparent; border: 1px solid var(--border); color: var(--muted2); border-radius: 4px; padding: 2px 8px; font-family: inherit; font-size: 10px; cursor: pointer; transition: all .2s; }
  .ref-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Layout ── */
  .layout { display: flex; flex: 1; overflow: hidden; }

  /* ── Right panel — takes remaining flex space beside the static LeftPanel ── */
  .right-panel {
    --bg: #f0f4f8;
    --surface: #ffffff;
    --surface2: #f8fafc;
    --surface3: #e2e8f0;
    --border: #cbd5e1;
    --border2: #94a3b8;
    --text: #0f172a;
    --muted: #475569;
    --muted2: #64748b;
    --accent: #0284c7;
    --green: #16a34a;
    --red: #dc2626;
    --yellow: #d97706;
    --orange: #ea580c;
    flex: 1; overflow: hidden; background: var(--bg); color: var(--text);
    display: flex; flex-direction: column;
  }
  .rp-content { flex: 1; overflow-y: auto; }
  .rp-content::-webkit-scrollbar { width: 4px; }
  .rp-content::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  .det-pane { display: none; }
  .det-pane.det-visible { display: block; }

  @media (max-width: 768px) {
    .layout { flex-direction: column; }
    .status-bar { gap: 5px; }
    .source-indicator { display: none; }
  }
</style>
