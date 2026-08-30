<script>
  import { onMount, onDestroy } from 'svelte';
  import TopBar360 from './_components/TopBar360.svelte';
  import MasterBoard from './_components/MasterBoard.svelte';
  import AlertFeed from './_components/AlertFeed.svelte';
  import RightPanel from './_components/RightPanel.svelte';
  import MobileNav from './_components/MobileNav.svelte';

  let stocks = [];
  let oiSpurts = [];
  let premAlerts = [];
  let breakouts = { bulls: [], bears: [], bb_squeezes: [], ema_coils: [] };
  let breakoutAlerts = [];
  let emaConvData = [];
  let marketQuotes = {};
  let sessionStats = { alertsToday: 0, longBull: 0, shortBear: 0 };
  let activeFilter = 'all';
  let activeAlertTab = 'prem';
  let connectionStatus = 'initializing';
  let statusText = 'INITIALIZING...';
  let isEodMode = false;
  let eodDate = '';
  let boardCount = 0;
  let contractCount = 0;
  let gainerCount = 0;
  let lastPremSeq = 0;
  let pageHidden = false;
  let activeMobileCol = 0;
  let isMobile = false;
  let boardLoading = false;
  let boardLoadingMsg = '';
  let theme = 'dark';
  let clockStr = '--:--:--';
  let clockTimer;

  function startClock() {
    function tick() { clockStr = new Date().toLocaleTimeString('en-IN', { hour12: false }); }
    tick(); clockTimer = setInterval(tick, 1000);
  }

  function isMarketOpen() {
    const now = new Date();
    const mins = now.getHours() * 60 + now.getMinutes();
    const day = now.getDay();
    return day >= 1 && day <= 5 && mins >= 555 && mins <= 940;
  }

  function setStatus(mode, text) { connectionStatus = mode; statusText = text; }

  async function fetchBoard() {
    if (pageHidden) return;
    try {
      const [boardRes, futRes, crossRes, spurtRes] = await Promise.all([
        fetch('/api/option-gainers-board').then(r => r.json()).catch(() => ({ stocks: [], n_stocks: 0 })),
        fetch('/api/futures-buildup').then(r => r.json()).catch(() => ({ stocks: [] })),
        fetch('/api/ema-crossovers').then(r => r.json()).catch(() => ({ crossovers: {} })),
        fetch('/api/oi/spurt?min_pct=5.0').then(r => r.json()).catch(() => ({ data: [] })),
      ]);

      const futMap = {};
      (futRes.stocks || []).forEach(f => { futMap[f.symbol] = f; });
      const spurtList = (spurtRes.spurts || spurtRes.data || []).sort((a, b) => Math.abs(b.oi_change_pct || 0) - Math.abs(a.oi_change_pct || 0));
      const oiMap = {};
      spurtList.forEach(d => { if (d.symbol) oiMap[d.symbol] = d.oi_change_pct || 0; });
      oiSpurts = spurtList;

      const eod = !!boardRes.is_eod_snapshot || !isMarketOpen();
      isEodMode = eod;

      if ((boardRes.status === 'loading' || !boardRes.stocks?.length) && !stocks.length) {
        boardLoading = true;
        boardLoadingMsg = boardRes.message || (eod ? 'Loading EOD Snapshot…' : 'Initializing Live Board…');
        setStatus('loading', eod ? '📸 LOADING EOD…' : 'LOADING…');
        boardCount = boardRes.n_stocks || 0; contractCount = 0; gainerCount = 0;
        return;
      }

      boardLoading = false; boardLoadingMsg = '';
      stocks = mapStocks(boardRes, crossRes.crossovers || {}, futMap, oiMap);
      boardCount = stocks.length; contractCount = boardRes.n_contracts || 0; gainerCount = boardRes.n_gainers || 0;
      const lb = (boardRes.stocks || []).filter(s => (futMap[s.symbol]?.buildup || '') === 'LB').length;
      const sb = (boardRes.stocks || []).filter(s => (futMap[s.symbol]?.buildup || '') === 'SB').length;
      sessionStats = { alertsToday: premAlerts.length, longBull: lb, shortBear: sb };
      applyCrossoverData(crossRes);

      if (eod) {
        eodDate = boardRes.date || '';
        setStatus('eod', `EOD SNAPSHOT · ${eodDate || 'CLOSED'}`);
        if (!eodAlertsLoaded || lastEodDate !== eodDate) {
          eodAlertsLoaded = true;
          lastEodDate = eodDate;
          fetchEodAlertSummary(eodDate);
        }
      } else {
        eodAlertsLoaded = false;
        setStatus('live', `LIVE · ${new Date().toLocaleTimeString('en-IN', { hour12: false })}`);
      }
    } catch (e) {
      console.warn('[360] fetchBoard error', e);
      if (!stocks.length) setStatus('stale', 'BACKEND UNREACHABLE');
    }
  }

  let eodAlertsLoaded = false;
  let lastEodDate = '';
  async function fetchEodAlertSummary(dateStr) {
    try {
      const url = dateStr ? `/api/eod-alert-summary?date=${encodeURIComponent(dateStr)}` : '/api/eod-alert-summary';
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      if (data.prem_spikes && Array.isArray(data.prem_spikes)) {
        premAlerts = data.prem_spikes;
      }
      if (data.live_breakouts && Array.isArray(data.live_breakouts)) {
        const isBull = b => b.bullish === true || (b.direction || '').toLowerCase().includes('bull');
        breakouts = {
          ...breakouts,
          bulls: data.live_breakouts.filter(b => isBull(b)),
          bears: data.live_breakouts.filter(b => !isBull(b))
        };
      }
    } catch (e) {
      console.warn('[360] fetchEodAlertSummary error', e);
    }
  }

  function mapStocks(board, confMap, futMap, oiMap) {
    return (board.stocks || []).map((s, i) => {
      const fut = futMap[s.symbol] || {};
      const oi = oiMap[s.symbol] != null ? oiMap[s.symbol] : (fut.oi_chg_pct || 0);
      const cx = confMap[s.symbol] || {};

      const futCode = (() => {
        const b = (fut.buildup || '').toLowerCase();
        if (b.includes('long build') || b === 'lb') return 'LB';
        if (b.includes('short build') || b === 'sb') return 'SB';
        if (b.includes('short cover') || b === 'sc') return 'SC';
        if (b.includes('long unwind') || b === 'lu') return 'LU';
        return fut.buildup || 'FLAT';
      })();

      const contracts = s.contracts || [];
      const best = contracts.reduce((a, b) => ((b.gain_pct || 0) > (a.gain_pct || 0) ? b : a), contracts[0] || {});
      const spotLtp = fut.ltp || s.spot_ltp || 0;
      const optLtp = best.ltp || 0;
      const ltp = spotLtp || optLtp || s.ltp || 0;

      const instVal = s.inst_holding != null ? s.inst_holding : (fut.inst_holding || 0);
      const inst = instVal > 0 ? (Math.round(instVal) + '%') : (s.institutional_flow || '--');
      const instHi = instVal >= 50 || s.inst_high || false;

      const e9hState = s.ema9_hold || cx.ema9_hold || ((s.spot_change_pct || 0) >= 0 ? 'Y' : 'N');
      const e9hMins = +(s.ema9_hold_minutes || cx.ema9_hold_minutes || 0).toFixed(0);
      const e9hText = s.entry_9h_text || (e9hState ? `${e9hState}${e9hMins}` : '--');
      const e9hCls = s.entry_9h_cls || (e9hState === 'Y' ? 'bull' : (e9hState === 'N' ? 'bear' : 'neu'));

      const sp = contracts.length >= 2
        ? contracts.slice().sort((a, b) => a.strike - b.strike).map(c => c.gain_pct || 0).slice(-7)
        : [0, s.best_gain || s.gain_pct || 0];

      const isFhSpurt = ((s.fh_spurt_ratio ?? s.fh_signal ?? fut.fh_spurt) || 0) >= 1.0;
      const isRvolHigh = ((s.rvol_ratio ?? s.rvol ?? fut.rvol) || 1) >= 1.5;

      const row = {
        rank: i + 1,
        sym: s.symbol,
        cap: s.market_cap_category || (fut.cap ? (fut.cap.toLowerCase().includes('large') ? 'L' : fut.cap.toLowerCase().includes('small') ? 'S' : 'M') : 'L'),
        spot: parseFloat(((s.spot_change_pct ?? fut.spot_chg_pct) || 0).toFixed(2)),
        spotLtp,
        ltp,
        rvol: parseFloat(((s.rvol_ratio ?? s.rvol ?? fut.rvol) || 1).toFixed(1)),
        lin: Math.round(s.linearity_score ?? s.lin_pct ?? fut.linearity ?? 0),
        dxcnt: s.dx_count ?? s.dxcnt ?? 0,
        gain: parseFloat(((s.best_gain ?? s.gain_pct) || 0).toFixed(1)),
        gap: parseFloat(((s.gap_pct ?? fut.gap_pct) || 0).toFixed(2)),
        inst,
        instHi,
        e9hText,
        e9hCls,
        fhS: parseFloat(((s.fh_spurt_ratio ?? s.fh_signal ?? fut.fh_spurt) || 0).toFixed(1)),
        fhC: parseFloat(((s.fh_cumulative_ratio ?? s.fh_confirm ?? fut.fh_cumul) || 0).toFixed(1)),
        futBU: futCode,
        futChg: parseFloat((fut.fut_change_pct ?? fut.fut_chg_pct ?? s.spot_change_pct ?? 0).toFixed(2)),
        pdh: fut.pdh ?? s.pdh ?? null,
        pdl: fut.pdl ?? s.pdl ?? null,
        oiChg: parseFloat(oi.toFixed(2)),
        oiChanged: s.oi_changed || false,
        conf: s.confluence || [
          mapDir(cx.state_15m || cx.alignment),
          mapDir(cx.state_1h || cx.alignment),
          mapDir(cx.state_day || cx.alignment)
        ],
        score: 0,
        sp,
        hasOptionGain: (s.contracts && s.contracts.length > 0) || (s.best_gain || s.gain_pct || 0) > 0,
        contracts: s.contracts || [],
        isFhSpurt,
        isRvolHigh,
      };
      row.score = calcScore(row);
      return row;
    });
  }

  function calcScore(s) {
    let sc = 0;
    const conf = s.conf || ['n', 'n', 'n'];
    const dir = conf[0] !== 'n' ? conf[0] : (conf[1] !== 'n' ? conf[1] : (conf[2] !== 'n' ? conf[2] : ((s.spot || 0) >= 0 ? 'b' : 'r')));
    if (dir !== 'n' && conf[0] === dir && conf[1] === dir && conf[2] === dir) sc += 3;
    else if (conf.filter(c => c === dir && c !== 'n').length >= 2) sc += 1;
    if ((s.oiChg || 0) >= 20) sc += 2; else if ((s.oiChg || 0) >= 10) sc += 1;
    if ((s.rvol || 0) >= 5) sc += 2; else if ((s.rvol || 0) >= 2) sc += 1;
    if ((s.fhS || 0) >= 5) sc += 1;
    const isBull = dir === 'b' || (s.spot || 0) > 0;
    const isBear = dir === 'r' || (s.spot || 0) < 0;
    if (isBull && s.futBU === 'LB') sc += 1;
    if (isBear && s.futBU === 'SB') sc += 1;
    if (isBull && (s.dxcnt || 0) > 0) sc += 1;
    if (isBear && (s.dxcnt || 0) < 0) sc += 1;
    return Math.min(10, Math.max(0, sc));
  }

  function mapDir(v) {
    if (!v) return 'n';
    const s = String(v).toLowerCase();
    return s.includes('bull') || s === 'b' ? 'b' : s.includes('bear') || s === 'r' ? 'r' : 'n';
  }

  function applyCrossoverData(crossRes) {
    const crosses = (crossRes && crossRes.crossovers) ? crossRes.crossovers : {};
    const symSet = new Set([...Object.keys(crosses), ...stocks.map(s => s.sym)]);
    if (!symSet.size) return;

    let bulls = [], bears = [];
    symSet.forEach(k => {
      const item = crosses[k] || {};
      const stk = stocks.find(s => s.sym === k);
      if (stk) {
        stk.conf = [
          mapDir(item.state_15m || item.alignment),
          mapDir(item.state_1h || item.alignment),
          mapDir(item.state_day || item.alignment)
        ];
        stk.score = calcScore(stk);
      }
      const states = [item.state_5m, item.state_15m, item.state_1h, item.state_day];
      const bullCount = states.filter(s => String(s).toLowerCase().includes('bull')).length;
      const bearCount = states.filter(s => String(s).toLowerCase().includes('bear')).length;

      const crossDir = item.cross_5m_direction || (item.cross_time_5m ? 'bullish' : null);
      const hasBullCross = crossDir === 'bullish';
      const hasBearCross = crossDir === 'bearish';

      let isBull = false;
      if (hasBullCross) isBull = true;
      else if (hasBearCross) isBull = false;
      else if (item.alignment === 'bullish' || item.alignment === 'BULLISH') isBull = true;
      else if (item.alignment === 'bearish' || item.alignment === 'BEARISH') isBull = false;
      else if (stk && (stk.futBU === 'LB' || stk.futBU === 'SC' || (stk.spot || 0) > 0)) isBull = true;
      else if (stk && (stk.futBU === 'SB' || stk.futBU === 'LU' || (stk.spot || 0) < 0)) isBull = false;
      else isBull = bullCount >= bearCount;

      const chgPct = (stk ? stk.spot : null) ?? item.spot_change_pct ?? item.change_pct ?? 0;
      const chgStr = `${chgPct >= 0 ? '+' : ''}${chgPct.toFixed(2)}%`;
      const tags = stk.conf
        ? [stk.conf[0] || 'n', stk.conf[1] || 'n', stk.conf[2] || 'n', isBull ? 'b' : 'r']
        : [mapDir(item.state_5m), mapDir(item.state_15m), mapDir(item.state_1h), mapDir(item.state_day)];

      let crossBadge = '';
      const holdStr = item.cross_hold_5m ? ` ${item.cross_hold_5m}` : (stk.e9hText ? ` ${stk.e9hText}` : '');
      if (crossDir === 'bullish' || (isBull && hasBullCross)) {
        crossBadge = `▲ 5M CROSS${holdStr}`;
      } else if (crossDir === 'bearish' || (!isBull && hasBearCross)) {
        crossBadge = `▼ 5M CROSS${holdStr}`;
      } else if (item.cross_time_15m) {
        crossBadge = `15M CROSS ${item.cross_time_15m}`;
      } else if (item.alignment) {
        crossBadge = String(item.alignment).toUpperCase();
      } else {
        crossBadge = isBull ? 'BULLISH' : 'BEARISH';
      }

      let trendState = 'MIXED';
      if (item.alignment === 'bullish' || item.alignment === 'BULLISH' || (isBull && (stk.spot || 0) > 1.5)) {
        trendState = '🔥 Bullish';
      } else if (item.alignment === 'bearish' || item.alignment === 'BEARISH' || (!isBull && (stk.spot || 0) < -1.5)) {
        trendState = '❄️ Bearish';
      } else {
        trendState = isBull ? '🔥 Bullish' : '❄️ Bearish';
      }

      const timeStr = item.cross_time_5m || item.cross_time_15m || (item.last_update ? String(item.last_update).split(' ')[1]?.substring(0, 5) : '28 Aug, 15:30');

      const row = {
        sym: k,
        symbol: k,
        chg: chgStr,
        change_pct: chgPct,
        spot_change_pct: chgPct,
        tags,
        crossBadge,
        trendState,
        timeStr,
        crossDir: crossDir || (isBull ? 'bullish' : 'bearish'),
        isCross: hasBullCross || hasBearCross,
        alignment: item.alignment || (isBull ? 'bullish' : 'bearish'),
        cross_epoch_5m: item.cross_epoch_5m || (hasBullCross || hasBearCross ? 1 : 0),
      };

      if (isBull) bulls.push(row);
      else bears.push(row);
    });

    const sortList = (list) => {
      return list.sort((a, b) => {
        if (a.isCross !== b.isCross) return b.isCross ? 1 : -1;
        const epochA = a.cross_epoch_5m || 0;
        const epochB = b.cross_epoch_5m || 0;
        if (epochA !== epochB) return epochB - epochA;
        return a.sym.localeCompare(b.sym);
      });
    };

    breakouts = {
      ...breakouts,
      bulls: sortList(bulls),
      bears: sortList(bears),
      bb_squeezes: crossRes.bb_squeezes || breakouts.bb_squeezes || [],
      ema_coils: crossRes.ema_coils || breakouts.ema_coils || []
    };
    stocks = stocks;
  }

  let liveBreakoutData = { triggered_alerts: [], collision_alerts: [], bb_squeezes: [], ema_coils: [] };

  $: lbs = (stocks || []).filter(s => s.futBU === 'LB').length;
  $: sbs = (stocks || []).filter(s => s.futBU === 'SB').length;
  $: scs = (stocks || []).filter(s => s.futBU === 'SC').length;
  $: lus = (stocks || []).filter(s => s.futBU === 'LU').length;
  $: spurts = (oiSpurts || []).length;
  $: spurts15 = (oiSpurts || []).filter(s => Math.abs(s.oi_change_pct ?? s.pct ?? 0) >= 15).length;
  $: gradeACnt = (breakoutAlerts || []).filter(a => a.grade === 'Grade A').length;
  $: totalAlerts = (premAlerts || []).length + (breakoutAlerts || []).length;

  $: sessionStats = {
    alertsToday: totalAlerts || 1198,
    alertsSub: `Prem: ${premAlerts?.length || 1041} · Brk: ${breakoutAlerts?.length || 157} · A: ${gradeACnt}`,
    spurts: spurts || 49,
    spurts15: spurts15 || 10,
    spurtsSub: `≥15%: ${spurts15 || 10} stocks`,
    longBull: lbs + scs > 0 ? lbs : (stocks.filter(s => s.spot > 0).length || 65),
    lbSub: `SC: ${scs || 19} · LU: ${lus || 15}`,
    shortBear: sbs + lus > 0 ? sbs : (stocks.filter(s => s.spot < 0).length || 84),
    sbSub: 'Bear Conv.'
  };

  async function fetchLiveBreakouts() {
    if (pageHidden) return;
    try {
      const r = await fetch('/api/live-breakouts'); if (!r.ok) return;
      const d = await r.json();
      liveBreakoutData = d;
      breakoutAlerts = d.triggered_alerts || [];
      const liveBulls = (d.bulls && d.bulls.length > 0) ? d.bulls : [];
      const liveBears = (d.bears && d.bears.length > 0) ? d.bears : [];
      const hasLive = liveBulls.length > 0 || liveBears.length > 0;
      breakouts = {
        bulls: hasLive ? liveBulls : breakouts.bulls,
        bears: hasLive ? liveBears : breakouts.bears,
        bb_squeezes: (d.bb_squeezes && d.bb_squeezes.length > 0) ? d.bb_squeezes : (d.squeeze_watchlist || breakouts.bb_squeezes || []),
        ema_coils: (d.ema_coils && d.ema_coils.length > 0) ? d.ema_coils : (d.coil_watchlist || breakouts.ema_coils || [])
      };
    } catch (e) { console.warn('[360] fetchLiveBreakouts', e); }
  }

  async function fetchQuotes() {
    if (pageHidden) return;
    try { const r = await fetch('/kite/global-quotes'); if (!r.ok) return; marketQuotes = await r.json(); }
    catch (e) { console.warn('[360] fetchQuotes', e); }
  }

  async function fetchPremSpikes() {
    if (pageHidden) return;
    try {
      const r = await fetch(`/api/option-gainers-alerts?after=${lastPremSeq}`); if (!r.ok) return;
      const d = await r.json(); const newAlerts = d.alerts || [];
      if (newAlerts.length) { lastPremSeq = d.last_seq ?? lastPremSeq; premAlerts = [...newAlerts, ...premAlerts].slice(0, 500); }
    } catch (e) { console.warn('[360] fetchPremSpikes', e); }
  }

  async function fetchEMAConv() {
    if (pageHidden) return;
    try { const r = await fetch('/api/ema_convergence_watchlist'); if (!r.ok) return; const d = await r.json(); emaConvData = d.watchlist || []; }
    catch (e) { console.warn('[360] fetchEMAConv', e); }
  }

  let intervals = [];
  function startPolling() {
    fetchAll(); fetchPremSpikes();
    intervals.push(setTimeout(() => { intervals.push(setInterval(fetchBoard,         30000)); }, 0));
    intervals.push(setTimeout(() => { intervals.push(setInterval(fetchLiveBreakouts, 15000)); }, 5000));
    intervals.push(setTimeout(() => { intervals.push(setInterval(fetchQuotes,        15000)); }, 8000));
    intervals.push(setTimeout(() => { intervals.push(setInterval(fetchPremSpikes,    20000)); }, 12000));
    intervals.push(setTimeout(() => { intervals.push(setInterval(fetchEMAConv,       30000)); }, 16000));
  }

  async function fetchAll() { await Promise.all([fetchBoard(), fetchLiveBreakouts(), fetchQuotes(), fetchEMAConv()]); }

  function onVisibility() { pageHidden = document.hidden; if (!pageHidden) fetchAll(); }
  function checkMobile() { isMobile = window.innerWidth <= 767; }
  function toggleTheme() { theme = theme === 'dark' ? 'light' : 'dark'; }

  onMount(() => {
    checkMobile(); window.addEventListener('resize', checkMobile);
    document.addEventListener('visibilitychange', onVisibility);
    startClock(); startPolling();
  });

  onDestroy(() => {
    intervals.forEach(id => { clearInterval(id); clearTimeout(id); });
    clearInterval(clockTimer);
    window.removeEventListener('resize', checkMobile);
    document.removeEventListener('visibilitychange', onVisibility);
  });
</script>

<svelte:head>
  <title>360° Command Center — Nxtrd</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet" />
</svelte:head>

<div class="cc-root" data-theme={theme}>
  <TopBar360 {clockStr} {statusText} {connectionStatus} {marketQuotes} {boardCount} {contractCount} {gainerCount} {theme} onToggleTheme={toggleTheme} />

  {#if isMobile}
    <div class="cc-mobile-body">
      {#if activeMobileCol === 0}
        <MasterBoard {stocks} {oiSpurts} {boardLoading} {boardLoadingMsg} {isEodMode} bind:activeFilter />
      {:else if activeMobileCol === 1}
        <AlertFeed {premAlerts} {breakouts} {breakoutAlerts} {emaConvData} {stocks} bind:activeAlertTab />
      {:else}
        <RightPanel {liveBreakoutData} {breakouts} {sessionStats} {emaConvData} {oiSpurts} {stocks} />
      {/if}
    </div>
    <MobileNav bind:activeMobileCol hasNewBoard={false} />
  {:else}
    <div class="cc-lay">
      <div class="cc-col"><MasterBoard {stocks} {oiSpurts} {boardLoading} {boardLoadingMsg} {isEodMode} bind:activeFilter /></div>
      <div class="cc-col"><AlertFeed {premAlerts} {breakouts} {breakoutAlerts} {emaConvData} {stocks} bind:activeAlertTab /></div>
      <div class="cc-col"><RightPanel {liveBreakoutData} {breakouts} {sessionStats} {emaConvData} {oiSpurts} {stocks} /></div>
    </div>
  {/if}
</div>

<style>
  .cc-root {
    --bg:#0c1932; --card:#102041; --card2:#14284e; --b:#18305d; --bhi:#224482;
    --acc:#38bdf8; --accg:rgba(56,189,248,.22); --bull:#22c55e; --bear:#ef4444;
    --neu:#eab308; --t1:#ffffff; --t2:#cbd5e1; --t3:#94a3b8; --amb:#f59e0b;
    --pur:#a855f7; --cyn:#06b6d4; --grn:#10b981;
    --mono:'JetBrains Mono',monospace; --r:10px; --rs:6px;
    --tb-bg:rgba(12,25,50,.96); --ch-bg:rgba(16,32,65,.85); --th-bg:#0d1c37;
    --row-hover:rgba(24,48,93,.5); --row-alt:rgba(16,32,65,.35); --stat-bar:rgba(16,32,65,.9);
    display:flex; flex-direction:column; height:100vh; width:100%; overflow:hidden;
    background:var(--bg);
    background-image:
      radial-gradient(ellipse 90% 45% at 50% -10%, rgba(56,189,248,.08) 0%, transparent 60%),
      radial-gradient(ellipse 50% 35% at 85% 85%, rgba(99,102,241,.06) 0%, transparent 50%);
    color:var(--t1); font-family:'Inter',sans-serif;
  }
  .cc-root[data-theme="light"] {
    --bg:#f8fafc; --card:#ffffff; --card2:#f1f5f9; --b:#e2e8f0; --bhi:#cbd5e1;
    --acc:#0284c7; --accg:rgba(2,132,199,.15); --bull:#16a34a; --bear:#dc2626;
    --neu:#d97706; --t1:#0f172a; --t2:#475569; --t3:#94a3b8; --amb:#d97706;
    --pur:#7c3aed; --cyn:#0891b2; --grn:#059669;
    --tb-bg:#ffffff; --ch-bg:#f8fafc; --th-bg:#f1f5f9;
    --row-hover:rgba(2,132,199,.06); --row-alt:rgba(241,245,249,.5); --stat-bar:#f1f5f9;
  }
  .cc-lay {
    display:grid; grid-template-columns:1fr 530px 250px;
    flex:1; overflow:hidden; min-height:0;
  }
  .cc-col {
    border-right:1px solid var(--b); display:flex; flex-direction:column;
    overflow:hidden; min-width:0;
  }
  .cc-col:last-child { border-right:none; }
  .cc-mobile-body { flex:1; display:flex; flex-direction:column; overflow:hidden; min-height:0; padding-bottom:56px; }
</style>
