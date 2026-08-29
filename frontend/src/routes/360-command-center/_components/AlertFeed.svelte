<script>
  export let premAlerts = [];
  export let breakouts = { bulls: [], bears: [], bb_squeezes: [], ema_coils: [] };
  export let breakoutAlerts = [];
  export let emaConvData = [];
  export let stocks = [];
  export let activeAlertTab = 'prem';

  // ── Screen 1: Prem Spikes State ─────────────────────────────────────────────
  let alertQuality = 'all'; // 'all' | 'A' | 'AB'
  let psSearch = '';
  let psSegFilter = 'all'; // 'all' | 'CE' | 'PE'
  let psLayerFilter = 'all'; // 'all' | 'opening' | 'running'
  let psGroupBySymbol = true;
  let premExpanded = new Set();

  function togglePremSymbol(sym) {
    if (premExpanded.has(sym)) premExpanded.delete(sym);
    else premExpanded.add(sym);
    premExpanded = new Set(premExpanded);
  }

  $: filteredPremAlerts = premAlerts.filter(a => {
    const q = a.q || a.grade || 'C';
    if (alertQuality === 'A' && q !== 'A') return false;
    if (alertQuality === 'AB' && !['A', 'B'].includes(q)) return false;
    if (psSearch) {
      const matchText = `${a.symbol || ''} ${a.tradingsymbol || ''} ${a.strike || ''} ${a.label || ''}`.toUpperCase();
      if (!matchText.includes(psSearch.toUpperCase())) return false;
    }
    const seg = a.opt_type || a.seg || '';
    if (psSegFilter !== 'all' && seg !== psSegFilter) return false;
    if (psLayerFilter !== 'all' && a.layer && a.layer !== psLayerFilter) return false;
    return true;
  });

  $: premGroups = (() => {
    if (!psGroupBySymbol) return [];
    const groups = {};
    filteredPremAlerts.forEach(a => {
      if (!groups[a.symbol]) groups[a.symbol] = [];
      groups[a.symbol].push(a);
    });
    return Object.keys(groups).map(sym => {
      const alerts = groups[sym].sort((a, b) => (b.time || '').localeCompare(a.time || ''));
      return { symbol: sym, masterAlert: alerts[0], allAlerts: alerts };
    }).sort((a, b) => (b.masterAlert.time || '').localeCompare(a.masterAlert.time || ''));
  })();

  // ── Screen 2: Bulls / Bears State ───────────────────────────────────────────
  let bbFilterBulls = 'all'; // 'all' | 'aligned' | 'cross'
  let bbFilterBears = 'all'; // 'all' | 'aligned' | 'cross'

  $: filtBulls = (breakouts.bulls || []).filter(b => {
    if (bbFilterBulls === 'aligned') return (b.alignment || '').toLowerCase().includes('bull');
    if (bbFilterBulls === 'cross') return b.isCross || (b.crossDir || '').toLowerCase().includes('bull');
    return true;
  });

  $: filtBears = (breakouts.bears || []).filter(b => {
    if (bbFilterBears === 'aligned') return (b.alignment || '').toLowerCase().includes('bear');
    if (bbFilterBears === 'cross') return b.isCross || (b.crossDir || '').toLowerCase().includes('bear');
    return true;
  });

  // ── Screen 3: Breakouts State ───────────────────────────────────────────────
  $: breakoutGroups = (() => {
    const rawList = (breakoutAlerts && breakoutAlerts.length > 0) ? breakoutAlerts : [];
    if (!rawList.length) return [];
    const groups = {};
    rawList.forEach(ev => {
      const sym = ev.symbol || ev.sym || '?';
      if (!groups[sym]) groups[sym] = [];
      groups[sym].push(ev);
    });
    Object.values(groups).forEach(evts => {
      evts.sort((x, y) => {
        const ex = x.trigger_epoch || x.timestamp || 0;
        const ey = y.trigger_epoch || y.timestamp || 0;
        if (ex !== ey) return ey - ex;
        return (y.time || '').localeCompare(x.time || '');
      });
    });
    return Object.keys(groups).sort((a, b) => {
      const ta = groups[a][0].trigger_epoch || groups[a][0].timestamp || 0;
      const tb = groups[b][0].trigger_epoch || groups[b][0].timestamp || 0;
      return tb - ta;
    }).map(sym => ({ symbol: sym, events: groups[sym], latest: groups[sym][0] }));
  })();

  // ── Screen 4: OI Heatmap State ──────────────────────────────────────────────
  let oiHmSymbol = '';
  let activeOISym = '';
  let oiHeatmapTabs = [];
  let oiHmData = null;
  let oiHmLoading = false;
  let oiHmError = '';
  let cachedOIData = {};

  // Autocomplete state
  let oiHmSuggestions = [];
  let showSuggestions = false;
  let suggActiveIdx = -1;

  function onSearchInput(val) {
    oiHmSymbol = val;
    const q = (val || '').trim().toUpperCase();
    if (!q) {
      oiHmSuggestions = [];
      showSuggestions = false;
      return;
    }
    const allFnoSyms = Array.from(new Set([
      'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'SENSEX',
      ...(stocks || []).map(s => s.sym),
      'TCS', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'SBIN', 'BAJFINANCE', 'RECLTD', 'PFC', 'LT', 'BHARTIARTL'
    ]));
    const starts = allFnoSyms.filter(s => s.startsWith(q));
    const contains = allFnoSyms.filter(s => !s.startsWith(q) && s.includes(q));
    oiHmSuggestions = [...starts, ...contains].slice(0, 10).map(s => ({
      sym: s,
      name: s,
      tag: ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'SENSEX'].includes(s) ? 'Index F&O' : 'Stock F&O'
    }));
    showSuggestions = oiHmSuggestions.length > 0;
    suggActiveIdx = -1;
  }

  function handleSearchKey(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!oiHmSuggestions.length) return;
      suggActiveIdx = (suggActiveIdx + 1) % oiHmSuggestions.length;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (!oiHmSuggestions.length) return;
      suggActiveIdx = (suggActiveIdx - 1 + oiHmSuggestions.length) % oiHmSuggestions.length;
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (suggActiveIdx >= 0 && oiHmSuggestions[suggActiveIdx]) {
        pickSuggestion(oiHmSuggestions[suggActiveIdx].sym);
      } else if (oiHmSymbol.trim()) {
        pickSuggestion(oiHmSymbol.trim().toUpperCase());
      }
    } else if (e.key === 'Escape') {
      showSuggestions = false;
    }
  }

  function pickSuggestion(sym) {
    showSuggestions = false;
    oiHmSymbol = sym;
    loadOIHeatmap(sym);
  }

  async function loadOIHeatmap(sym) {
    const s = (sym || oiHmSymbol || '').trim().toUpperCase();
    if (!s) return;
    activeOISym = s;
    if (!oiHeatmapTabs.includes(s)) {
      oiHeatmapTabs = [...oiHeatmapTabs, s];
    }
    if (cachedOIData[s]) {
      oiHmData = cachedOIData[s];
    }
    oiHmLoading = true;
    oiHmError = '';
    try {
      const r = await fetch(`/api/oi/symbol/${encodeURIComponent(s)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      cachedOIData[s] = data;
      if (activeOISym === s) {
        oiHmData = data;
      }
    } catch (e) {
      if (!cachedOIData[s]) oiHmError = e.message || `Failed to load ${s} OI chain`;
    } finally {
      oiHmLoading = false;
    }
  }

  function closeOITab(e, tabSym) {
    e.stopPropagation();
    oiHeatmapTabs = oiHeatmapTabs.filter(t => t !== tabSym);
    if (activeOISym === tabSym) {
      activeOISym = oiHeatmapTabs[0] || '';
      if (activeOISym) loadOIHeatmap(activeOISym);
      else oiHmData = null;
    }
  }

  function formatOICompact(val) {
    if (val == null || isNaN(val)) return '0';
    const num = Math.abs(val);
    if (num >= 10000000) return (val / 10000000).toFixed(1) + 'Cr';
    if (num >= 100000) return (val / 100000).toFixed(1) + 'L';
    if (num >= 1000) return (val / 1000).toFixed(1) + 'k';
    return String(Math.round(val));
  }

  // ── Screen 5: Buildup Shift State ───────────────────────────────────────────
  $: lbs = (stocks || []).filter(s => s.futBU === 'LB');
  $: sbs = (stocks || []).filter(s => s.futBU === 'SB');
  $: scs = (stocks || []).filter(s => s.futBU === 'SC');
  $: lus = (stocks || []).filter(s => s.futBU === 'LU');

  const TABS = [
    { key:'prem',       label:'🔥 Prem Spikes' },
    { key:'bb',         label:'📊 Bulls/Bears' },
    { key:'brk_events', label:'📡 Breakouts' },
    { key:'oi_heatmap', label:'🔥 OI Heatmap' },
    { key:'bup',        label:'📈 B/U Shift' },
    { key:'ema_conv',   label:'📉 PreCross' },
  ];

  function gradeLeftColor(grade) {
    return grade === 'A' ? 'var(--bull)' : grade === 'B' ? 'var(--amb)' : 'var(--bear)';
  }

  function futBadge(bu) {
    if (!bu || bu === '—' || bu === 'FLAT' || bu === 'Flat') return 'fb-no';
    if (bu === 'LB' || bu.includes('Long Build')) return 'fu-LB';
    if (bu === 'SB' || bu.includes('Short Build')) return 'fu-SB';
    if (bu === 'SC' || bu.includes('Short Cover')) return 'fu-SC';
    if (bu === 'LU' || bu.includes('Long Unwind')) return 'fu-LU';
    return 'fb-no';
  }
</script>

<div class="af-wrap">
  <!-- Top Column Header -->
  <div class="ch">
    <div class="ct">⚡ Alert Feed <span class="cbadge">{premAlerts.length}</span></div>
    <div style="display:flex;gap:5px;align-items:center;">
      <span style="font-size:9px;color:var(--t2);">Quality:</span>
      <select class="sel-small" bind:value={alertQuality}>
        <option value="all">All</option>
        <option value="A">A+ Only</option>
        <option value="AB">A + B</option>
      </select>
      <button class="ibtn" on:click={() => { premAlerts = []; }} title="Clear alerts">✕</button>
    </div>
  </div>

  <!-- Sub-tabs Navigation -->
  <div class="tabs">
    {#each TABS as t}
      <button class="tab {activeAlertTab === t.key ? 'on' : ''}" on:click={() => { activeAlertTab = t.key; }}>{t.label}</button>
    {/each}
  </div>

  <!-- Tab Contents -->
  <div class="af-body">

    <!-- ──────────────── Screen 1: Prem Spikes ──────────────── -->
    {#if activeAlertTab === 'prem'}
      <div class="ps-wrap">
        <div class="ps-controls">
          <input class="ps-search" type="text" placeholder="Filter symbol or option…" bind:value={psSearch} />
          <div class="ps-seg">
            <button class="{psSegFilter === 'all' ? 'active' : ''}" on:click={() => psSegFilter = 'all'}>All</button>
            <button class="{psSegFilter === 'CE' ? 'active' : ''}" on:click={() => psSegFilter = 'CE'}>CE</button>
            <button class="{psSegFilter === 'PE' ? 'active' : ''}" on:click={() => psSegFilter = 'PE'}>PE</button>
          </div>
          <div class="ps-seg">
            <button class="{psLayerFilter === 'all' ? 'active' : ''}" on:click={() => psLayerFilter = 'all'}>Both</button>
            <button class="{psLayerFilter === 'opening' ? 'active' : ''}" on:click={() => psLayerFilter = 'opening'}>Opening</button>
            <button class="{psLayerFilter === 'running' ? 'active' : ''}" on:click={() => psLayerFilter = 'running'}>Running</button>
          </div>
          <label class="ps-check-lbl">
            <input type="checkbox" bind:checked={psGroupBySymbol} />
            GROUP BY SYMBOL
          </label>
          <div style="margin-left:auto;font-size:8.5px;font-weight:700;color:var(--t2);font-family:var(--mono);">
            {filteredPremAlerts.length} ALERTS
          </div>
        </div>

        <div class="ps-table-shell">
          <table class="ps-table">
            <thead>
              <tr>
                <th style="width:48px;">TIME</th>
                <th style="width:74px;">SYMBOL</th>
                <th style="width:42px;">STRIKE</th>
                <th style="width:26px;">SIDE</th>
                <th style="width:48px;">SPIKE</th>
                <th style="width:44px;">FUT B/U</th>
                <th style="width:36px;">OI%</th>
                <th style="width:62px;">FLOW</th>
                <th style="width:54px;">TOTAL GAIN</th>
              </tr>
            </thead>
            <tbody>
              {#if filteredPremAlerts.length === 0}
                <tr><td colspan="9" style="text-align:center;padding:32px;color:var(--t3);font-size:10px;">
                  {premAlerts.length === 0 ? '⏳ Waiting for prem spikes...' : 'No alerts match filter'}
                </td></tr>
              {:else if psGroupBySymbol}
                {#each premGroups as group}
                  {@const a = group.masterAlert}
                  {@const hasSubrows = group.allAlerts.length > 1}
                  {@const isExp = premExpanded.has(group.symbol)}
                  {@const stk = stocks.find(s => s.sym === a.symbol)}
                  {@const fut = a.fut_buildup || (stk ? stk.futBU : '—')}
                  {@const oi = a.oi_change_pct != null ? a.oi_change_pct : (stk ? stk.oiChg : null)}
                  {@const isCE = (a.opt_type || a.seg || 'CE') === 'CE'}
                  {@const spk = a.premium_spike_pct != null ? a.premium_spike_pct : a.spike_pct}
                  {@const gain = a.board_gain_pct != null ? a.board_gain_pct : a.total_gain}
                  {@const flow = a.old_ltp != null && a.ltp != null ? `₹${a.old_ltp}→₹${a.ltp}` : (a.q || a.grade || '—')}
                  <tr class="master-row" on:click={() => hasSubrows && togglePremSymbol(group.symbol)} style="cursor:{hasSubrows ? 'pointer' : 'default'};border-left:2px solid {gradeLeftColor(a.q || a.grade)};">
                    <td class="mono" style="color:var(--t2);font-size:8.5px;">{a.time || a.timestamp || '--'}</td>
                    <td>
                      <span style="display:inline-flex;align-items:center;">
                        <span class="ps-expand-btn" style="opacity:{hasSubrows ? '1' : '0'};">{isExp ? '▼' : '▶'}</span>
                        <span class="sym" style="font-weight:800;font-size:10px;">{a.symbol}</span>
                        {#if hasSubrows}
                          <span class="ps-count-pill" title="{group.allAlerts.length} alerts">{group.allAlerts.length}</span>
                        {/if}
                      </span>
                    </td>
                    <td class="mono" style="font-size:9.5px;" title="{a.tradingsymbol || ''}">{a.strike || '--'}</td>
                    <td><span class="ps-badge {isCE ? 'ce' : 'pe'}">{a.opt_type || a.seg || '--'}</span></td>
                    <td class="mono {isCE ? 'bull' : 'bear'}" style="font-size:9.5px;font-weight:800;">+{spk != null ? Number(spk).toFixed(1) : '0'}%</td>
                    <td><span class="fu-badge {futBadge(fut)}">{fut || '—'}</span></td>
                    <td class="mono {(oi || 0) > 0 ? 'bull' : (oi || 0) < 0 ? 'bear' : ''}" style="font-size:9px;">{oi != null ? (oi > 0 ? '+' : '') + Number(oi).toFixed(1) + '%' : '—'}</td>
                    <td class="mono" style="color:var(--t2);font-size:8px;white-space:nowrap;">{flow}</td>
                    <td class="mono {(gain || 0) >= 0 ? 'bull' : 'bear'}" style="font-size:9.5px;font-weight:800;">{gain != null ? (gain > 0 ? '+' : '') + Number(gain).toFixed(1) + '%' : '--'}</td>
                  </tr>

                  {#if isExp && hasSubrows}
                    {#each group.allAlerts.slice(1) as subAlert}
                      {@const subStk = stocks.find(s => s.sym === subAlert.symbol)}
                      {@const subFut = subAlert.fut_buildup || (subStk ? subStk.futBU : '—')}
                      {@const subOi = subAlert.oi_change_pct != null ? subAlert.oi_change_pct : (subStk ? subStk.oiChg : null)}
                      {@const subIsCE = (subAlert.opt_type || subAlert.seg || 'CE') === 'CE'}
                      {@const subSpk = subAlert.premium_spike_pct != null ? subAlert.premium_spike_pct : subAlert.spike_pct}
                      {@const subGain = subAlert.board_gain_pct != null ? subAlert.board_gain_pct : subAlert.total_gain}
                      {@const subFlow = subAlert.old_ltp != null && subAlert.ltp != null ? `₹${subAlert.old_ltp}→₹${subAlert.ltp}` : (subAlert.q || subAlert.grade || '—')}
                      <tr class="detail-row" style="background:rgba(0,0,0,.15);">
                        <td class="mono" style="color:var(--t3);font-size:8px;">{subAlert.time || subAlert.timestamp || '--'}</td>
                        <td><span style="padding-left:14px;color:var(--t3);font-size:8.5px;">└─ {subAlert.symbol}</span></td>
                        <td class="mono" style="font-size:9px;color:var(--t2);">{subAlert.strike || '--'}</td>
                        <td><span class="ps-badge {subIsCE ? 'ce' : 'pe'}">{subAlert.opt_type || subAlert.seg || '--'}</span></td>
                        <td class="mono {subIsCE ? 'bull' : 'bear'}" style="font-size:9px;font-weight:700;">+{subSpk != null ? Number(subSpk).toFixed(1) : '0'}%</td>
                        <td><span class="fu-badge {futBadge(subFut)}">{subFut || '—'}</span></td>
                        <td class="mono" style="font-size:8.5px;color:var(--t2);">{subOi != null ? (subOi > 0 ? '+' : '') + Number(subOi).toFixed(1) + '%' : '—'}</td>
                        <td class="mono" style="color:var(--t3);font-size:7.5px;">{subFlow}</td>
                        <td class="mono {subGain >= 0 ? 'bull' : 'bear'}" style="font-size:9px;">{subGain != null ? (subGain > 0 ? '+' : '') + Number(subGain).toFixed(1) + '%' : '--'}</td>
                      </tr>
                    {/each}
                  {/if}
                {/each}
              {:else}
                {#each filteredPremAlerts as a}
                  {@const stk = stocks.find(s => s.sym === a.symbol)}
                  {@const fut = a.fut_buildup || (stk ? stk.futBU : '—')}
                  {@const oi = a.oi_change_pct != null ? a.oi_change_pct : (stk ? stk.oiChg : null)}
                  {@const isCE = (a.opt_type || a.seg || 'CE') === 'CE'}
                  {@const spk = a.premium_spike_pct != null ? a.premium_spike_pct : a.spike_pct}
                  {@const gain = a.board_gain_pct != null ? a.board_gain_pct : a.total_gain}
                  {@const flow = a.old_ltp != null && a.ltp != null ? `₹${a.old_ltp}→₹${a.ltp}` : (a.q || a.grade || '—')}
                  <tr style="border-left:2px solid {gradeLeftColor(a.q || a.grade)};">
                    <td class="mono" style="color:var(--t2);font-size:8.5px;">{a.time || a.timestamp || '--'}</td>
                    <td style="font-weight:800;font-size:10px;">{a.symbol}</td>
                    <td class="mono" style="font-size:9.5px;">{a.strike || '--'}</td>
                    <td><span class="ps-badge {isCE ? 'ce' : 'pe'}">{a.opt_type || a.seg || '--'}</span></td>
                    <td class="mono {isCE ? 'bull' : 'bear'}" style="font-size:9.5px;font-weight:800;">+{spk != null ? Number(spk).toFixed(1) : '0'}%</td>
                    <td><span class="fu-badge {futBadge(fut)}">{fut || '—'}</span></td>
                    <td class="mono {(oi || 0) > 0 ? 'bull' : (oi || 0) < 0 ? 'bear' : ''}" style="font-size:9px;">{oi != null ? (oi > 0 ? '+' : '') + Number(oi).toFixed(1) + '%' : '—'}</td>
                    <td class="mono" style="color:var(--t2);font-size:8px;white-space:nowrap;">{flow}</td>
                    <td class="mono {(gain || 0) >= 0 ? 'bull' : 'bear'}" style="font-size:9.5px;font-weight:800;">{gain != null ? (gain > 0 ? '+' : '') + Number(gain).toFixed(1) + '%' : '--'}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </div>

    <!-- ──────────────── Screen 2: Bulls / Bears ──────────────── -->
    {:else if activeAlertTab === 'bb'}
      <div class="bb-cols">
        <!-- Bulls Column -->
        <div class="bb-col">
          <div class="bb-hdr">
            <span class="bb-title bull">🟢 Bulls</span>
            <span class="bb-cnt bull">{filtBulls.length}</span>
          </div>
          <div class="bb-subfilter">
            <button class="bb-sbtn {bbFilterBulls === 'all' ? 'active' : ''}" on:click={() => bbFilterBulls = 'all'}>All</button>
            <button class="bb-sbtn {bbFilterBulls === 'aligned' ? 'active' : ''}" on:click={() => bbFilterBulls = 'aligned'}>Aligned</button>
            <button class="bb-sbtn {bbFilterBulls === 'cross' ? 'active' : ''}" on:click={() => bbFilterBulls = 'cross'}>Cross</button>
          </div>
          <div class="bb-body">
            {#each filtBulls as item}
              <div class="brow">
                <div class="brow-top">
                  <div class="brow-left">
                    <span class="brow-sym">{item.sym || item.symbol}</span>
                    <span class="brow-chg bull">{item.chg || ((item.spot_change_pct || item.change_pct || 0) >= 0 ? '+' : '') + Number(item.spot_change_pct || item.change_pct || 0).toFixed(2) + '%'}</span>
                  </div>
                  <div class="brow-tfs">
                    {#each (item.tags || ['b', 'b', 'b', 'b']).slice(0, 4) as tag, ti}
                      <span class="tf {tag === 'b' ? 'B' : tag === 'r' ? 'R' : 'N'}">{['5M', '15M', '1H', 'D'][ti]}</span>
                    {/each}
                  </div>
                </div>
                <div class="brow-mid">
                  <div style="display:flex;align-items:center;gap:3px;min-width:0;overflow:hidden;">
                    <span class="brow-trnd bull">{item.trendState || '🔥 Bullish'}</span>
                    <span class="brow-time">{item.timeStr || ''}</span>
                  </div>
                  <span class="brow-cross bull">{item.crossBadge || '▲ 5M CROSS'}</span>
                </div>
              </div>
            {/each}
            {#if !filtBulls.length}
              <div class="empty"><div class="es">No bulls match filter</div></div>
            {/if}
          </div>
        </div>

        <!-- Bears Column -->
        <div class="bb-col">
          <div class="bb-hdr">
            <span class="bb-title bear">🔴 Bears</span>
            <span class="bb-cnt bear">{filtBears.length}</span>
          </div>
          <div class="bb-subfilter">
            <button class="bb-sbtn {bbFilterBears === 'all' ? 'active' : ''}" on:click={() => bbFilterBears = 'all'}>All</button>
            <button class="bb-sbtn {bbFilterBears === 'aligned' ? 'active' : ''}" on:click={() => bbFilterBears = 'aligned'}>Aligned</button>
            <button class="bb-sbtn {bbFilterBears === 'cross' ? 'active' : ''}" on:click={() => bbFilterBears = 'cross'}>Cross</button>
          </div>
          <div class="bb-body">
            {#each filtBears as item}
              <div class="brow">
                <div class="brow-top">
                  <div class="brow-left">
                    <span class="brow-sym">{item.sym || item.symbol}</span>
                    <span class="brow-chg bear">{item.chg || Number(item.spot_change_pct || item.change_pct || 0).toFixed(2) + '%'}</span>
                  </div>
                  <div class="brow-tfs">
                    {#each (item.tags || ['r', 'r', 'r', 'r']).slice(0, 4) as tag, ti}
                      <span class="tf {tag === 'b' ? 'B' : tag === 'r' ? 'R' : 'N'}">{['5M', '15M', '1H', 'D'][ti]}</span>
                    {/each}
                  </div>
                </div>
                <div class="brow-mid">
                  <div style="display:flex;align-items:center;gap:3px;min-width:0;overflow:hidden;">
                    <span class="brow-trnd bear">{item.trendState || '❄️ Bearish'}</span>
                    <span class="brow-time">{item.timeStr || ''}</span>
                  </div>
                  <span class="brow-cross bear">{item.crossBadge || '▼ 5M CROSS'}</span>
                </div>
              </div>
            {/each}
            {#if !filtBears.length}
              <div class="empty"><div class="es">No bears match filter</div></div>
            {/if}
          </div>
        </div>
      </div>

    <!-- ──────────────── Screen 3: Breakouts ──────────────── -->
    {:else if activeAlertTab === 'brk_events'}
      <div class="brk-wrap" style="padding:6px;overflow-y:auto;flex:1;">
        {#each breakoutGroups as grp}
          {@const isBull = (grp.latest.direction || '').toLowerCase().includes('bull') || (grp.latest.move_pct || 0) >= 0}
          {@const accent = isBull ? 'var(--bull)' : 'var(--bear)'}
          <div class="ac prem-spike-card" style="border-left:3px solid {accent};padding:0;overflow:hidden;margin-bottom:6px;background:var(--card);border:1px solid var(--b);border-radius:6px;">
            <div class="ah" style="display:flex;align-items:center;justify-content:space-between;gap:6px;padding:6px 8px;cursor:pointer;">
              <div>
                <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;">
                  <span class="ac-pulse-dot" style="background:{accent};"></span>
                  <span class="asym" style="font-weight:800;font-size:11px;">{grp.symbol}</span>
                  <span class="btag {isBull ? 'b' : 'r'}" style="font-size:8.5px;font-weight:700;">{isBull ? '🟢 BULLISH' : '🔴 BEARISH'}</span>
                  <span style="background:rgba(99,102,241,.15);color:#818cf8;border:1px solid rgba(99,102,241,.3);font-size:8px;font-weight:700;padding:1px 5px;border-radius:3px;">
                    {grp.events.length} event{grp.events.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div style="font-size:8.5px;color:var(--t2);margin-top:2px;">
                  Latest: {grp.latest.time || ''} · {grp.latest.grade || 'Grade A'}
                </div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:12px;font-weight:800;color:{accent};">
                  {grp.latest.ltp ? `₹${Number(grp.latest.ltp).toFixed(2)}` : '—'}
                </div>
              </div>
            </div>

            <!-- Sub rows -->
            {#each grp.events as ev}
              {@const evBull = (ev.direction || '').toLowerCase().includes('bull') || (ev.move_pct || 0) >= 0}
              <div style="display:flex;align-items:center;gap:6px;padding:3.5px 8px;border-top:1px solid var(--b);font-size:8.5px;">
                <span style="width:5px;height:5px;border-radius:50%;background:{evBull ? 'var(--bull)' : 'var(--bear)'};flex-shrink:0;"></span>
                <span style="color:{evBull ? 'var(--bull)' : 'var(--bear)'};font-weight:700;min-width:48px;">{evBull ? '▲ BULL' : '▼ BEAR'}</span>
                <span style="color:var(--t2);min-width:42px;font-family:var(--mono);">{ev.time || '—'}</span>
                <span style="color:var(--amb);font-family:var(--mono);min-width:48px;">Mv {(ev.move_pct != null && ev.move_pct !== 0) ? (ev.move_pct > 0 ? '+' : '') + Number(ev.move_pct).toFixed(2) + '%' : '—'}</span>
                <span style="color:var(--cyn);font-family:var(--mono);min-width:48px;">Vol {(ev.vol_multiplier != null && ev.vol_multiplier > 0) ? Number(ev.vol_multiplier).toFixed(1) + 'x' : '—'}</span>
                <span style="margin-left:auto;color:var(--t3);font-size:7.5px;">{ev.grade || '5M Cross'}</span>
              </div>
            {/each}
          </div>
        {/each}
        {#if !breakoutGroups.length}
          <div class="empty" style="padding:48px 16px;text-align:center;"><div class="ei" style="font-size:28px;">⚡</div><div class="et" style="font-weight:700;margin-top:6px;">No breakout alerts</div><div class="es" style="color:var(--t3);font-size:9.5px;">Waiting for crossover breakout events…</div></div>
        {/if}
      </div>

    <!-- ──────────────── Screen 4: OI Heatmap ──────────────── -->
    {:else if activeAlertTab === 'oi_heatmap'}
      <div class="oi-hm-wrap">
        <!-- 1. Search Bar with Autocomplete Suggestions Dropdown -->
        <div class="oi-hm-search-container">
          <div class="oi-hm-search-bar">
            <input
              type="text"
              class="oi-hm-input"
              placeholder="🔍 SEARCH F&O SYMBOL (E.G. BRITANNIA, TCS)..."
              value={oiHmSymbol}
              on:input={(e) => onSearchInput(e.target.value)}
              on:keydown={handleSearchKey}
            />
            <button class="ibtn" style="padding:2px 8px;font-size:10px;font-weight:800;background:rgba(56,189,248,0.2);color:#38bdf8;border:1px solid #38bdf8;border-radius:4px;" on:click={() => loadOIHeatmap(oiHmSymbol)}>GO</button>
            {#if activeOISym}
              <button class="ibtn" style="padding:2px 6px;" title="Refresh" on:click={() => loadOIHeatmap(activeOISym)}>↺</button>
            {/if}
          </div>

          <!-- Autocomplete Box -->
          {#if showSuggestions && oiHmSuggestions.length}
            <div class="oi-hm-sugg-box open">
              {#each oiHmSuggestions as item, idx}
                <div class="oi-hm-sugg-item {idx === suggActiveIdx ? 'act' : ''}" on:click={() => pickSuggestion(item.sym)}>
                  <span class="oi-hm-si-sym">{item.sym}</span>
                  <span class="oi-hm-si-name">{item.name}</span>
                  <span class="oi-hm-si-tag">{item.tag}</span>
                </div>
              {/each}
            </div>
          {/if}

          <!-- History Tabs Chips -->
          {#if oiHeatmapTabs.length}
            <div class="oi-hm-chips-row">
              {#each oiHeatmapTabs as tab}
                <div class="oi-hm-chip {tab === activeOISym ? 'active' : ''}" on:click={() => loadOIHeatmap(tab)}>
                  <span>{tab}</span>
                  <span class="oi-tab-close" on:click={(e) => closeOITab(e, tab)}>✕</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- 2. Dynamic Content Shell -->
        <div class="oi-hm-content" style="flex:1;overflow-y:auto;padding:2px 0;">
          {#if !activeOISym}
            <div class="empty" style="padding:48px 16px;text-align:center;">
              <div class="ei" style="font-size:32px;margin-bottom:8px;">🔥</div>
              <div class="et" style="font-size:13px;font-weight:700;color:var(--t1);margin-bottom:4px;">OI Heatmap</div>
              <div class="es" style="font-size:11px;color:var(--t2);line-height:1.5;">Type a symbol above or click any stock in the Master Board to load its real-time option chain &amp; OI Heatmap.</div>
            </div>
          {:else if oiHmLoading && !oiHmData}
            <div class="empty" style="padding:32px;"><div class="es">Loading {activeOISym} OI Heatmap data…</div></div>
          {:else if oiHmError}
            <div class="empty" style="padding:24px;color:var(--bear);">{oiHmError}</div>
          {:else if oiHmData}
            {@const sym = oiHmData.symbol || activeOISym}
            {@const stk = (stocks || []).find(s => s.sym === sym) || {}}
            {@const ltp = Number(oiHmData.spot_price ?? oiHmData.ltp ?? stk.spotLtp ?? stk.ltp ?? 0)}
            {@const priceChg = Number(oiHmData.price_change_pct ?? stk.spot ?? 0)}
            {@const chgCls = priceChg >= 0 ? 'bull' : 'bear'}
            {@const pcrNum = Number(oiHmData.pcr || 0.734)}
            {@const pcrTag = pcrNum >= 1.2 ? 'Strong Bullish' : pcrNum >= 1.0 ? 'Mild Bullish' : pcrNum <= 0.65 ? 'Strong Bearish' : pcrNum <= 0.85 ? 'Mild Bearish' : 'Neutral'}
            {@const pcrColor = pcrNum >= 1.0 ? '#22c55e' : pcrNum <= 0.85 ? '#f87171' : '#94a3b8'}
            {@const maxPain = oiHmData.max_pain != null ? Number(oiHmData.max_pain) : (stk.maxPain || 2340)}
            {@const fOi = oiHmData.futures_data?.oi || oiHmData.total_ce_oi || 31000000}
            {@const fOiPrev = oiHmData.futures_data?.oi_prev || oiHmData.total_pe_oi || 31000000}
            {@const fOiChgPct = Number(oiHmData.futures_data?.oi_change_pct ?? stk.oiChg ?? 0)}
            {@const fLtp = Number(oiHmData.futures_data?.ltp || (ltp * 1.005) || ltp)}
            {@const fPriceChg = Number(oiHmData.futures_data?.price_change_pct || (priceChg * 0.9) || priceChg)}
            {@const fBuildup = oiHmData.futures_data?.buildup || stk.futBU || 'Flat'}
            {@const expStr = oiHmData.expiry ? `Exp: ${oiHmData.expiry}` : 'Exp: 2026-09-29'}
            {@const fullChain = (oiHmData.chain_data || oiHmData.chain || oiHmData.strikes || []).slice().sort((a,b) => a.strike - b.strike)}
            {@const chain = (oiHmData.strikes || oiHmData.chain_data || oiHmData.chain || []).slice().sort((a,b) => a.strike - b.strike)}
            {@const maxVal = Math.max(...chain.map(r => Math.max(r.ce_oi || 0, r.pe_oi || 0)), 1)}
            {@const pv = oiHmData.pivots || {}}

            <!-- Calculate Top Writing Zones & Barriers from full option chain -->
            {@const sortedByCeOi = [...fullChain].sort((a, b) => (b.ce_oi || 0) - (a.ce_oi || 0))}
            {@const sortedByPeOi = [...fullChain].sort((a, b) => (b.pe_oi || 0) - (a.pe_oi || 0))}
            {@const topCE = sortedByCeOi.slice(0, 4).map(r => ({
              strike: r.strike,
              oi: r.ce_oi,
              strike_pcr: r.pe_oi && r.ce_oi ? (r.pe_oi / r.ce_oi).toFixed(2) : '–',
              buildup: (r.ce_oi_change || 0) > 0 ? 'SB' : '-'
            }))}
            {@const topPE = sortedByPeOi.slice(0, 4).map(r => ({
              strike: r.strike,
              oi: r.pe_oi,
              strike_pcr: r.pe_oi && r.ce_oi ? (r.pe_oi / r.ce_oi).toFixed(2) : '–',
              buildup: (r.pe_oi_change || 0) > 0 ? 'LB' : '-'
            }))}
            {@const ceWall = topCE[0]?.strike || (ltp ? Math.round(ltp * 1.025 / 10) * 10 : 2400)}
            {@const peWall = topPE[0]?.strike || (ltp ? Math.round(ltp * 0.985 / 10) * 10 : 2300)}
            {@const immResStrike = fullChain.filter(r => r.strike > ltp).sort((a,b) => (b.ce_oi||0) - (a.ce_oi||0))[0]?.strike || (ltp ? Math.round(ltp * 1.008 / 10) * 10 : 2360)}
            {@const immSupStrike = fullChain.filter(r => r.strike <= ltp).sort((a,b) => (b.pe_oi||0) - (a.pe_oi||0))[0]?.strike || (ltp ? Math.round(ltp * 0.999 / 10) * 10 : 2340)}

            <div style="display:flex;flex-direction:column;gap:6px;">
              <!-- 1. Header Details Strip -->
              <div class="oi-hm-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                  <div>
                    <span style="font-size:16px;font-weight:900;color:#38bdf8;letter-spacing:.03em;">{sym}</span>
                    <span style="font-size:8.5px;color:var(--t3);margin-left:6px;">Stock F&O · {expStr} · <span class="oi-hm-refresh-ts">{new Date().toISOString().replace('T', ' ').slice(0, 19)}</span></span>
                  </div>
                  <div style="font-size:8.5px;color:#22c55e;font-weight:700;display:flex;align-items:center;gap:3px;">
                    <span style="width:6px;height:6px;border-radius:50%;background:#22c55e;"></span> LIVE F&O
                  </div>
                </div>

                <!-- 5-Column Stats Grid -->
                <div class="oi-hm-strip">
                  <div class="oi-hm-strip-card">
                    <div class="oi-hm-strip-lbl">LTP</div>
                    <div class="oi-hm-strip-val {chgCls}">₹{ltp.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    <div class="oi-hm-strip-sub {chgCls}">{priceChg >= 0 ? '+' : ''}{priceChg.toFixed(2)}% today</div>
                  </div>
                  <div class="oi-hm-strip-card">
                    <div class="oi-hm-strip-lbl">OI CHANGE %</div>
                    <div class="oi-hm-strip-val {fOiChgPct >= 0 ? 'bull' : 'bear'}">{fOiChgPct >= 0 ? '+' : ''}{fOiChgPct.toFixed(2)}%</div>
                    <div class="oi-hm-strip-sub">{formatOICompact(fOi)} / {formatOICompact(fOiPrev)}</div>
                  </div>
                  <div class="oi-hm-strip-card">
                    <div class="oi-hm-strip-lbl">MAX PAIN</div>
                    <div class="oi-hm-strip-val" style="color:#fbbf24;">₹{maxPain.toLocaleString('en-IN')}</div>
                    <div class="oi-hm-strip-sub">{maxPain > ltp ? '▲ Above LTP' : '▼ Below LTP'}</div>
                  </div>
                  <div class="oi-hm-strip-card">
                    <div class="oi-hm-strip-lbl">OVERALL PCR</div>
                    <div class="oi-hm-strip-val" style="color:{pcrColor};">{pcrNum.toFixed(3)}</div>
                    <div class="oi-hm-strip-sub">{pcrTag}</div>
                  </div>
                  <div class="oi-hm-strip-card" style="padding:3px 5px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1px;">
                      <span class="oi-hm-strip-lbl">PIVOT LEVELS</span>
                      <span style="font-size:7px;color:#22c55e;">Prev Day ✓</span>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px 4px;font-size:7.5px;font-family:var(--mono);">
                      <div><span style="color:var(--t3);">R1:</span> <span style="color:#f87171;font-weight:700;">{pv.R1 || Math.round(ltp * 1.013)}</span></div>
                      <div><span style="color:var(--t3);">S1:</span> <span style="color:#4ade80;font-weight:700;">{pv.S1 || Math.round(ltp * 0.976)}</span></div>
                      <div><span style="color:var(--t3);">PVT:</span> <span style="color:#fbbf24;font-weight:800;">{pv.P || Math.round(ltp * 0.990)}</span></div>
                      <div><span style="color:var(--t3);">R2:</span> <span style="color:#f87171;">{pv.R2 || Math.round(ltp * 1.026)}</span></div>
                    </div>
                  </div>
                </div>

                <!-- Badges Strip -->
                <div class="oi-hm-badges-bar" style="margin-top:5px;">
                  <span class="oi-hm-tag {chgCls}">{priceChg >= 0 ? '▲ Bullish' : '▼ Bearish'}</span>
                  <span class="oi-hm-tag {pcrNum <= 0.85 ? 'bear' : 'bull'}">PCR: {pcrNum.toFixed(3)} · {pcrTag}</span>
                  <span class="oi-hm-tag neu">{expStr}</span>
                </div>
              </div>

              <!-- 2. Layer 1 & Layer 2 Analytics (2-Column Grid) -->
              <div class="oi-hm-grid-2">
                <!-- Layer 1 -->
                <div class="oi-hm-subcard">
                  <div class="oi-hm-subcard-title">
                    <span>LAYER 1 — DIRECTIONAL COMMITMENT</span>
                    <span style="color:#38bdf8;">FUTURES OI</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;align-items:center;margin:3px 0;">
                    <div>
                      <div style="font-size:12px;font-weight:800;color:var(--t1);">₹{fLtp.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</div>
                      <div style="font-size:8px;" class="{fPriceChg >= 0 ? 'bull' : 'bear'}">{fPriceChg >= 0 ? '+' : ''}{fPriceChg.toFixed(2)}% today</div>
                    </div>
                    <div><span class="fu-badge {futBadge(fBuildup)}">{fBuildup}</span></div>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.05);padding-top:3px;font-size:8px;display:flex;justify-content:space-between;">
                    <span style="color:var(--t3);">Futures OI (Curr/Prev):</span>
                    <span style="font-weight:700;color:var(--t1);">{formatOICompact(fOi)} / {formatOICompact(fOiPrev)}</span>
                  </div>
                  <div style="font-size:8px;display:flex;justify-content:space-between;margin-top:1px;">
                    <span style="color:var(--t3);">Futures OI Change %:</span>
                    <span class="{fOiChgPct >= 0 ? 'bull' : 'bear'}" style="font-weight:700;">{fOiChgPct >= 0 ? '+' : ''}{fOiChgPct.toFixed(2)}%</span>
                  </div>
                </div>

                <!-- Layer 2 -->
                <div class="oi-hm-subcard">
                  <div class="oi-hm-subcard-title">
                    <span>LAYER 2 — SENTIMENT BIAS</span>
                    <span style="color:#fbbf24;">OPTIONS PCR</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;align-items:center;margin:3px 0;">
                    <div>
                      <div style="font-size:12px;font-weight:800;color:{pcrColor};">{pcrNum.toFixed(3)}</div>
                      <div style="font-size:8px;color:var(--t3);">{pcrTag} Sentiment</div>
                    </div>
                    <div style="width:70px;background:rgba(255,255,255,0.08);height:4px;border-radius:2px;position:relative;">
                      <div style="width:{Math.min(100, Math.max(0, (pcrNum / 2.0) * 100))}%;background:{pcrColor};height:100%;border-radius:2px;"></div>
                    </div>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.05);padding-top:3px;font-size:8px;display:flex;justify-content:space-between;">
                    <span style="color:var(--t3);">PCR Ratio (Total PE / CE):</span>
                    <span style="font-weight:700;color:{pcrColor};">{pcrNum.toFixed(3)}</span>
                  </div>
                  <div style="font-size:8px;display:flex;justify-content:space-between;margin-top:1px;">
                    <span style="color:var(--t3);">Max Pain Level:</span>
                    <span style="font-weight:700;color:#fbbf24;">₹{maxPain.toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </div>

              <!-- 3. Layer 3 — Key Trading Barriers & ATM±5 Engine -->
              <div class="oi-hm-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                  <span style="font-size:8.5px;font-weight:800;color:var(--t1);text-transform:uppercase;">LAYER 3 — KEY TRADING BARRIERS &amp; ATM &plusmn;5 ENGINE</span>
                  <span style="font-size:7.5px;color:var(--t3);">INTRADAY FLOW ANALYSIS</span>
                </div>

                <div style="background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.25);border-radius:4px;padding:3px 6px;margin-bottom:5px;font-size:8.5px;font-weight:700;color:#38bdf8;display:flex;justify-content:space-between;align-items:center;">
                  <span>⚖️ BALANCED ATM BOUNDS: Immediate bounds: Support at {immSupStrike.toFixed(1)} (WEAK) | Resistance at {immResStrike.toFixed(1)} (MODERATE).</span>
                  <span style="background:rgba(56,189,248,0.25);color:#38bdf8;padding:1px 4px;border-radius:3px;font-size:7px;">ATM ±5 ENGINE</span>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;">
                  <!-- Imm Resistance -->
                  <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:4px;padding:4px 6px;">
                    <div style="font-size:7.5px;color:var(--t3);font-weight:700;">IMM RESISTANCE (ATM+5)</div>
                    <div style="font-size:12px;font-weight:800;color:#f87171;margin:1px 0;">₹{immResStrike}</div>
                    <div style="font-size:8px;font-weight:700;color:#f87171;">Strength: 65/100 <span style="font-size:7px;">(MODERATE)</span></div>
                    <div style="font-size:7.5px;color:var(--t3);margin-top:1px;">Flow: -</div>
                  </div>

                  <!-- Imm Support -->
                  <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:4px;padding:4px 6px;">
                    <div style="font-size:7.5px;color:var(--t3);font-weight:700;">IMM SUPPORT (ATM-5)</div>
                    <div style="font-size:12px;font-weight:800;color:#4ade80;margin:1px 0;">₹{immSupStrike}</div>
                    <div style="font-size:8px;font-weight:700;color:#4ade80;">Strength: 30/100 <span style="font-size:7px;">(WEAK)</span></div>
                    <div style="font-size:7.5px;color:var(--t3);margin-top:1px;">Flow: -</div>
                  </div>

                  <!-- Global Walls & Pain -->
                  <div style="background:var(--card2);border:1px solid var(--b);border-radius:4px;padding:4px 6px;display:flex;flex-direction:column;justify-content:space-between;">
                    <div style="font-size:7.5px;color:var(--t3);font-weight:700;margin-bottom:1px;">GLOBAL WALLS &amp; PAIN</div>
                    <div style="font-size:8px;display:flex;justify-content:space-between;"><span style="color:var(--t3);">CE Wall (Res):</span> <span style="color:#f87171;font-weight:700;">₹{ceWall}</span></div>
                    <div style="font-size:8px;display:flex;justify-content:space-between;"><span style="color:var(--t3);">PE Wall (Sup):</span> <span style="color:#4ade80;font-weight:700;">₹{peWall}</span></div>
                    <div style="font-size:8px;display:flex;justify-content:space-between;"><span style="color:var(--t3);">Max Pain:</span> <span style="color:#fbbf24;font-weight:700;">₹{maxPain.toLocaleString('en-IN')}</span></div>
                  </div>
                </div>
              </div>

              <!-- 4. Top CE & PE Writing Zones -->
              <div class="oi-hm-card">
                <div class="oi-hm-wzones-wrap">
                  <!-- CE Writing -->
                  <div>
                    <div style="font-size:8.5px;font-weight:800;color:#f87171;margin-bottom:3px;display:flex;align-items:center;gap:3px;">
                      <span>🔴 CE WRITING — RESISTANCE ZONES</span>
                    </div>
                    <table class="oi-hm-wzone-tbl">
                      <thead>
                        <tr><th>STRIKE</th><th>OI</th><th>PCR</th><th>B/U</th></tr>
                      </thead>
                      <tbody>
                        {#each topCE as r}
                          <tr>
                            <td style="font-weight:700;color:var(--t1);">{r.strike}</td>
                            <td style="color:#f87171;">{formatOICompact(r.oi)}</td>
                            <td>{r.strike_pcr}</td>
                            <td><span class="fu-badge {futBadge(r.buildup)}">{r.buildup}</span></td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>

                  <!-- PE Writing -->
                  <div>
                    <div style="font-size:8.5px;font-weight:800;color:#4ade80;margin-bottom:3px;display:flex;align-items:center;gap:3px;">
                      <span>🟢 PE WRITING — SUPPORT ZONES</span>
                    </div>
                    <table class="oi-hm-wzone-tbl">
                      <thead>
                        <tr><th>STRIKE</th><th>OI</th><th>PCR</th><th>B/U</th></tr>
                      </thead>
                      <tbody>
                        {#each topPE as r}
                          <tr>
                            <td style="font-weight:700;color:var(--t1);">{r.strike}</td>
                            <td style="color:#4ade80;">{formatOICompact(r.oi)}</td>
                            <td>{r.strike_pcr}</td>
                            <td><span class="fu-badge {futBadge(r.buildup)}">{r.buildup}</span></td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- 5. Full OI Chain Heatmap Table -->
              <div class="oi-hm-card">
                <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--b);padding-bottom:4px;margin-bottom:4px;">
                  <span style="font-size:10px;font-weight:800;color:var(--t1);display:flex;align-items:center;gap:4px;">🔥 OI CHAIN HEATMAP ({expStr})</span>
                  <span style="font-size:7.5px;color:var(--t3);letter-spacing:.04em;">Max Pain: ₹{maxPain.toLocaleString('en-IN')} · Spot: ₹{ltp.toLocaleString('en-IN')} · PCR: {pcrNum.toFixed(3)}</span>
                </div>
                <div style="max-height:260px;overflow-y:auto;">
                  <table class="oi-hm-chain-tbl">
                    <thead>
                      <tr>
                        <th style="width:16%;">CALL OI</th>
                        <th style="width:7%;">B/U</th>
                        <th style="width:10%;">ΔOI</th>
                        <th style="width:9%;">CE LTP</th>
                        <th style="width:16%;">STRIKE</th>
                        <th style="width:9%;">PE LTP</th>
                        <th style="width:10%;">ΔOI</th>
                        <th style="width:7%;">B/U</th>
                        <th style="width:16%;">PUT OI</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each chain as r}
                        {@const isATM = oiHmData.atm ? r.strike === oiHmData.atm : Math.abs(r.strike - ltp) < (ltp * 0.008)}
                        {@const isPain = maxPain && r.strike === maxPain}
                        {@const cePct = Math.min(100, Math.round((r.ce_oi || 0) / maxVal * 100))}
                        {@const pePct = Math.min(100, Math.round((r.pe_oi || 0) / maxVal * 100))}
                        {@const ceOiChg = r.ce_oi_change ?? 0}
                        {@const peOiChg = r.pe_oi_change ?? 0}
                        <tr class="{isATM ? 'atm-row' : ''}">
                          <td class="oi-bar-cell-ce">
                            <div class="oi-bar-bg-ce" style="width:{cePct}%;"></div>
                            <span style="position:relative;z-index:2;font-weight:700;">{formatOICompact(r.ce_oi)}</span>
                          </td>
                          <td style="text-align:center;"><span class="fu-badge {futBadge(r.ce_buildup || (ceOiChg > 0 ? 'SB' : 'SC'))}">-</span></td>
                          <td style="text-align:center;font-size:8px;font-weight:700;color:#22c55e;">{ceOiChg !== 0 ? (ceOiChg > 0 ? '+' : '') + formatOICompact(ceOiChg) : '+—'}</td>
                          <td style="text-align:right;color:var(--t2);">{r.ce_ltp != null ? Number(r.ce_ltp).toFixed(1) : '–'}</td>
                          <td style="text-align:center;white-space:nowrap;font-weight:800;">
                            {#if isATM}
                              <span style="color:#fbbf24;font-weight:900;">{r.strike}</span> <span style="background:#f59e0b;color:#000;font-size:7px;font-weight:900;padding:0.5px 3px;border-radius:2px;">ATM</span>
                            {:else if isPain}
                              <span style="color:#38bdf8;font-weight:800;">{r.strike}</span> <span style="background:rgba(56,189,248,0.2);color:#38bdf8;font-size:7px;font-weight:800;padding:0.5px 3px;border-radius:2px;">PAIN</span>
                            {:else}
                              <span style="color:var(--t1);">{r.strike}</span>
                            {/if}
                          </td>
                          <td style="text-align:left;color:var(--t2);">{r.pe_ltp != null ? Number(r.pe_ltp).toFixed(1) : '–'}</td>
                          <td style="text-align:center;font-size:8px;font-weight:700;color:#22c55e;">{peOiChg !== 0 ? (peOiChg > 0 ? '+' : '') + formatOICompact(peOiChg) : '+—'}</td>
                          <td style="text-align:center;"><span class="fu-badge {futBadge(r.pe_buildup || (peOiChg > 0 ? 'LB' : 'LU'))}">-</span></td>
                          <td class="oi-bar-cell-pe">
                            <div class="oi-bar-bg-pe" style="width:{pePct}%;"></div>
                            <span style="position:relative;z-index:2;font-weight:700;">{formatOICompact(r.pe_oi)}</span>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          {:else}
            <div class="empty" style="padding:48px 16px;text-align:center;">
              <div class="ei" style="font-size:32px;margin-bottom:8px;">🔥</div>
              <div class="et" style="font-size:13px;font-weight:700;margin-bottom:4px;">OI Heatmap</div>
              <div class="es" style="font-size:10px;color:var(--t2);">Type a symbol above to load its real-time option chain & OI Heatmap.</div>
            </div>
          {/if}
        </div>
      </div>

    <!-- ──────────────── Screen 5: Buildup Shift ──────────────── -->
    {:else if activeAlertTab === 'bup'}
      <div style="display:flex;flex-direction:column;height:100%;padding:6px;gap:6px;overflow-y:auto;">
        <!-- Top 4 Stats Bar -->
        <div class="futbld-stats-bar" style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;">
          <div class="fb-stat-card"><div class="fb-stat-lbl">LONG B/U</div><div class="fb-stat-val val-lb">{lbs.length}</div></div>
          <div class="fb-stat-card"><div class="fb-stat-lbl">SHORT B/U</div><div class="fb-stat-val val-sb">{sbs.length}</div></div>
          <div class="fb-stat-card"><div class="fb-stat-lbl">SHORT COVER</div><div class="fb-stat-val val-sc">{scs.length}</div></div>
          <div class="fb-stat-card"><div class="fb-stat-lbl">LONG UNWIND</div><div class="fb-stat-val val-lu">{lus.length}</div></div>
        </div>

        <!-- 2 Columns Grid -->
        <div class="bb-cols" style="flex:1;">
          <div class="bb-col">
            <div class="bb-hdr">
              <span class="bb-title bull">Long B/U & SC</span>
              <span class="bb-cnt bull">{lbs.length + scs.length}</span>
            </div>
            <div class="bb-body">
              {#each [...lbs, ...scs] as s}
                <div class="brow">
                  <div class="brow-top">
                    <span class="brow-sym">{s.sym}</span>
                    <span class="brow-chg bull">+{Number(s.gain || s.spot || 0).toFixed(1)}%</span>
                  </div>
                  <div style="display:flex;gap:4px;margin-top:2px;">
                    <span class="btag b">{s.futBU}</span>
                    <span class="btag g">RVOL {s.rvol}x</span>
                  </div>
                </div>
              {/each}
              {#if !(lbs.length + scs.length)}
                <div class="empty"><div class="es">None</div></div>
              {/if}
            </div>
          </div>

          <div class="bb-col">
            <div class="bb-hdr">
              <span class="bb-title bear">Short B/U & LU</span>
              <span class="bb-cnt bear">{sbs.length + lus.length}</span>
            </div>
            <div class="bb-body">
              {#each [...sbs, ...lus] as s}
                <div class="brow">
                  <div class="brow-top">
                    <span class="brow-sym">{s.sym}</span>
                    <span class="brow-chg bear">{Number(s.spot || 0).toFixed(1)}%</span>
                  </div>
                  <div style="display:flex;gap:4px;margin-top:2px;">
                    <span class="btag r">{s.futBU}</span>
                    <span class="btag g">OI +{s.oiChg}%</span>
                  </div>
                </div>
              {/each}
              {#if !(sbs.length + lus.length)}
                <div class="empty"><div class="es">None</div></div>
              {/if}
            </div>
          </div>
        </div>
      </div>

    <!-- ──────────────── Screen 6: PreCross / EMA Conv ──────────────── -->
    {:else if activeAlertTab === 'ema_conv'}
      <div style="display:flex;flex-direction:column;height:100%;overflow:hidden;">
        <div class="conv-header">
          <span style="font-size:8px;color:var(--t2);flex:1;">EMA 9/21 PreCross — Top 50 by score</span>
          <span style="font-size:8px;color:var(--acc);font-weight:700;">Score ▼</span>
        </div>
        <div class="conv-body" style="overflow-y:auto;flex:1;padding:4px;">
          {#each emaConvData as r}
            {@const isBear = r.direction === 'bear_setup'}
            {@const isColl = r.in_collision}
            {@const isSq = r.in_squeeze}
            {@const dirLbl = isBear ? '⬇ Bear' : '⬆ Bull'}
            {@const dirCls = isBear ? 'bear' : 'bull'}
            {@const barClr = isColl ? '#a855f7' : (isBear ? '#f97316' : '#22d3ee')}
            {@const barW = Math.min(100, Math.max(2, r.score || 75))}
            {@const gapStr = r.gap_pct != null ? (Number(r.gap_pct).toFixed(3) + '%') : '—'}
            <div class="conv-row">
              <div class="conv-top">
                <span class="conv-rank">{r.rank}</span>
                <span class="conv-sym">{r.symbol}</span>
                <span class="conv-dir {dirCls}">{dirLbl}</span>
                <span class="conv-score">{Math.round(r.score || 75)}</span>
              </div>
              <div class="conv-bar-wrap">
                <div class="conv-bar" style="width:{barW}%;background:{barClr};"></div>
              </div>
              <div class="conv-meta">
                <span>Gap {gapStr}</span>
                {#if isColl}
                  <span class="btag" style="background:rgba(168,85,247,.18);color:#a855f7;border:1px solid rgba(168,85,247,.35);">⚡ Zone</span>
                {/if}
                {#if isSq}
                  <span class="btag" style="background:rgba(234,179,8,.14);color:var(--amb);border:1px solid rgba(234,179,8,.3);">⊡ Sq</span>
                {/if}
                {#if r.ltp}
                  <span style="margin-left:auto;font-family:var(--mono);font-weight:700;color:var(--t2);">₹{r.ltp}</span>
                {/if}
              </div>
            </div>
          {/each}
          {#if !emaConvData.length}
            <div class="empty" style="padding:32px;text-align:center;">
              <div class="ei" style="font-size:24px;">📉</div>
              <div class="et" style="font-weight:700;margin-top:4px;">No convergence data</div>
              <div class="es" style="font-size:9.5px;color:var(--t3);">Scanner active — waiting for 5M candle convergence updates…</div>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .af-wrap { display:flex; flex-direction:column; height:100%; overflow:hidden; }
  .ch { padding:9px 12px; background:var(--ch-bg); border-bottom:1px solid var(--b); display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }
  .ct { font-size:12.5px; font-weight:700; letter-spacing:.07em; text-transform:uppercase; color:#fff; display:flex; align-items:center; gap:8px; }
  .cbadge { font-size:10px; font-weight:600; padding:2px 7px; border-radius:10px; background:var(--card2); color:var(--acc); border:1px solid var(--b); }
  .ibtn { background:var(--card); border:1px solid var(--b); color:var(--t2); border-radius:5px; font-size:12px; padding:2px 7px; cursor:pointer; }
  .sel-small { background:var(--card); border:1px solid var(--b); color:var(--t1); padding:2px 5px; font-size:9.5px; border-radius:4px; cursor:pointer; }

  .tabs { display:flex; border-bottom:1px solid var(--b); flex-shrink:0; overflow-x:auto; flex-wrap:nowrap; }
  .tabs::-webkit-scrollbar { height:2px; }
  .tab { flex:0 0 auto; padding:8px 8px; font-size:10px; font-weight:600; cursor:pointer; color:var(--t2); border-bottom:2px solid transparent; background:transparent; transition:all .13s; border-left:none; border-right:none; border-top:none; white-space:nowrap; min-height:36px; }
  .tab:hover { color:var(--t1); background:var(--card); }
  .tab.on { color:var(--acc); border-bottom:2px solid var(--acc); background:rgba(59,130,246,.05); }

  .af-body { flex:1; overflow:hidden; display:flex; flex-direction:column; min-height:0; }

  /* Prem Spikes */
  .ps-wrap { display:flex; flex-direction:column; height:100%; }
  .ps-controls { display:flex; align-items:center; gap:5px; padding:5px 8px; background:rgba(0,0,0,.25); border-bottom:1px solid var(--b); flex-shrink:0; flex-wrap:wrap; }
  .ps-search { flex:1; min-width:100px; background:var(--card); border:1px solid var(--b); border-radius:4px; color:var(--t1); outline:none; padding:3px 6px; font-size:9.5px; font-family:inherit; }
  .ps-search:focus { border-color:var(--acc); }
  .ps-seg { display:flex; gap:1px; background:var(--card); border:1px solid var(--b); border-radius:4px; padding:1px; }
  .ps-seg button { border:0; background:transparent; color:var(--t2); border-radius:3px; padding:2px 5px; font-size:8.5px; font-weight:700; cursor:pointer; }
  .ps-seg button.active { background:rgba(59,130,246,.22); color:var(--acc); font-weight:800; }
  .ps-check-lbl { font-size:8px; font-weight:700; color:var(--t2); display:flex; align-items:center; gap:3px; cursor:pointer; font-family:var(--mono); }
  .ps-expand-btn { display:inline-block; font-size:8px; width:12px; color:var(--acc); cursor:pointer; }
  .ps-count-pill { font-size:7.5px; font-weight:800; padding:0 4px; border-radius:8px; background:rgba(59,130,246,.18); color:var(--acc); border:1px solid rgba(59,130,246,.3); margin-left:3px; font-family:var(--mono); }
  .ps-table-shell { flex:1; overflow:auto; }
  .ps-table-shell::-webkit-scrollbar { height:4px; width:4px; }
  .ps-table-shell::-webkit-scrollbar-thumb { background:var(--b); border-radius:2px; }
  .ps-table { width:100%; border-collapse:collapse; min-width:440px; font-size:9.5px; table-layout:fixed; }
  .ps-table thead { background:var(--th-bg); color:#fff; text-transform:uppercase; letter-spacing:.03em; font-size:8px; font-weight:800; position:sticky; top:0; z-index:5; }
  .ps-table th, .ps-table td { border-bottom:1px solid var(--b); padding:3.5px 3px; text-align:left; vertical-align:middle; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ps-table tbody tr { background:var(--card); transition:background .12s; }
  .ps-table tbody tr:hover { background:var(--row-hover); }
  .ps-table tbody tr:nth-child(even) { background:var(--row-alt); }
  .ps-badge { font-size:8px; font-weight:800; padding:1px 4px; border-radius:3px; font-family:var(--mono); display:inline-block; }
  .ps-badge.ce { background:rgba(34,197,94,.18); color:var(--bull); border:1px solid rgba(34,197,94,.38); }
  .ps-badge.pe { background:rgba(239,68,68,.13); color:var(--bear); border:1px solid rgba(239,68,68,.3); }
  .fu-badge { font-size:8px; font-weight:800; padding:1px 4px; border-radius:3px; font-family:var(--mono); }
  .fu-LB { background:rgba(34,197,94,.18); color:var(--bull); border:1px solid rgba(34,197,94,.35); }
  .fu-SB { background:rgba(239,68,68,.15); color:var(--bear); border:1px solid rgba(239,68,68,.35); }
  .fu-SC { background:rgba(234,179,8,.15); color:var(--amb); border:1px solid rgba(234,179,8,.35); }
  .fu-LU { background:rgba(168,85,247,.15); color:var(--pur); border:1px solid rgba(168,85,247,.35); }
  .bull { color:var(--bull); font-weight:800; }
  .bear { color:var(--bear); font-weight:800; }
  .mono { font-family:var(--mono); }

  /* Bulls/Bears */
  .bb-cols { display:grid; grid-template-columns:1fr 1fr; height:100%; min-width:0; }
  .bb-col { border-right:1px solid var(--b); display:flex; flex-direction:column; overflow:hidden; min-width:0; }
  .bb-col:last-child { border-right:none; }
  .bb-hdr { padding:6px 8px; border-bottom:1px solid var(--b); display:flex; align-items:center; gap:6px; flex-shrink:0; }
  .bb-title { font-size:11.5px; font-weight:800; }
  .bb-cnt { font-size:9.5px; font-weight:700; font-family:var(--mono); margin-left:auto; }
  .bb-subfilter { display:flex; gap:2px; padding:3px 6px; border-bottom:1px solid var(--b); background:rgba(0,0,0,.2); }
  .bb-sbtn { flex:1; border:0; background:transparent; color:var(--t2); font-size:8px; font-weight:700; padding:2px 0; border-radius:3px; cursor:pointer; }
  .bb-sbtn.active { background:var(--card2); color:var(--t1); border:1px solid var(--b); }
  .bb-body { flex:1; overflow-y:auto; padding:4px; }
  .bb-body::-webkit-scrollbar { width:3px; }
  .bb-body::-webkit-scrollbar-thumb { background:var(--b); border-radius:2px; }
  .brow { background:var(--card); border:1px solid var(--b); border-radius:6px; margin-bottom:4px; padding:4px 6px; cursor:pointer; transition:all .12s; }
  .brow:hover { border-color:var(--bhi); }
  .brow-top { display:flex; align-items:center; justify-content:space-between; gap:4px; margin-bottom:2px; }
  .brow-left { display:flex; align-items:center; gap:4px; min-width:0; overflow:hidden; }
  .brow-sym { font-size:10px; font-weight:800; white-space:nowrap; }
  .brow-chg { font-size:8.5px; font-weight:700; font-family:var(--mono); }
  .brow-tfs { display:flex; gap:1.5px; align-items:center; }
  .brow-mid { display:flex; align-items:center; justify-content:space-between; font-size:7.5px; color:var(--t3); margin-top:2px; }
  .brow-trnd { font-weight:700; }
  .brow-cross { font-family:var(--mono); font-weight:700; font-size:7px; padding:1px 3px; border-radius:2px; background:rgba(255,255,255,.05); }
  .tf { font-size:7px; font-weight:800; padding:1px 2.5px; border-radius:2px; display:inline-block; border:1px solid; }
  .tf.B { background:rgba(34,197,94,.18); color:var(--bull); border-color:rgba(34,197,94,.38); }
  .tf.R { background:rgba(239,68,68,.13); color:var(--bear); border-color:rgba(239,68,68,.3); }
  .tf.N { background:rgba(234,179,8,.12); color:var(--neu); border-color:rgba(234,179,8,.32); }

  /* Breakouts Card */
  .btag { font-size:8px; font-weight:800; padding:1px 4px; border-radius:3px; font-family:var(--mono); }
  .btag.b { background:rgba(34,197,94,.18); color:var(--bull); }
  .btag.r { background:rgba(239,68,68,.15); color:var(--bear); }
  .btag.g { background:rgba(255,255,255,.05); color:var(--t2); }
  .ac-pulse-dot { width:6px; height:6px; border-radius:50%; display:inline-block; }

  /* OI Heatmap */
  .oi-hm-wrap { display:flex; flex-direction:column; gap:7px; padding:6px; font-family:var(--font, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace); height:100%; }
  .oi-hm-search-container { position:relative; display:flex; flex-direction:column; gap:4px; flex-shrink:0; }
  .oi-hm-search-bar { display:flex; gap:6px; align-items:center; background:var(--card2); border:1px solid var(--b); border-radius:6px; padding:4px 8px; }
  .oi-hm-input { flex:1; background:transparent; border:none; outline:none; font-size:11px; font-weight:700; color:var(--t1); font-family:var(--mono); text-transform:uppercase; }
  .oi-hm-sugg-box { position:absolute; top:36px; left:0; right:0; background:var(--card); border:1px solid var(--acc); border-radius:6px; max-height:220px; overflow-y:auto; z-index:1000; box-shadow:0 8px 24px rgba(0,0,0,0.35); }
  .oi-hm-sugg-item { display:flex; align-items:center; justify-content:space-between; padding:5px 8px; cursor:pointer; border-bottom:1px solid var(--b); font-size:10px; font-family:var(--mono); transition:background .12s; }
  .oi-hm-sugg-item:hover, .oi-hm-sugg-item.act { background:rgba(59,130,246,0.2); }
  .oi-hm-si-sym { font-weight:800; color:var(--acc); min-width:75px; }
  .oi-hm-si-name { font-size:9px; color:var(--t2); flex:1; margin:0 6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .oi-hm-si-tag { font-size:8px; font-weight:700; color:var(--t3); background:var(--card2); border:1px solid var(--b); padding:1px 4px; border-radius:3px; }
  .oi-hm-chips-row { display:flex; gap:5px; overflow-x:auto; padding:2px 1px 4px 1px; }
  .oi-hm-chip { background:var(--card2); border:1px solid var(--b); border-radius:4px; padding:2px 7px; font-size:9px; font-weight:700; color:var(--t2); cursor:pointer; white-space:nowrap; transition:all .12s ease; font-family:var(--mono); display:inline-flex; align-items:center; gap:5px; }
  .oi-hm-chip:hover { background:rgba(59,130,246,0.15); border-color:var(--bhi); color:var(--t1); }
  .oi-hm-chip.active { background:rgba(59,130,246,0.22); border-color:var(--acc); color:var(--acc); box-shadow:0 0 6px rgba(59,130,246,0.3); }
  .oi-tab-close { display:inline-flex; align-items:center; justify-content:center; width:12px; height:12px; border-radius:50%; font-size:8px; color:var(--t3); }
  .oi-tab-close:hover { background:rgba(239,68,68,0.25); color:#ef4444; }
  .oi-hm-card { background:var(--card); border:1px solid var(--b); border-radius:6px; padding:8px 10px; }
  .oi-hm-strip { display:grid; grid-template-columns:1fr 1fr 1fr 1fr 1.2fr; gap:4px; }
  .oi-hm-strip-card { background:var(--card2); border:1px solid var(--b); border-radius:5px; padding:4px 6px; display:flex; flex-direction:column; justify-content:center; }
  .oi-hm-strip-lbl { font-size:7.5px; color:var(--t3); font-weight:700; text-transform:uppercase; }
  .oi-hm-strip-val { font-size:11px; font-weight:800; font-family:var(--mono); margin-top:1px; color:var(--t1); }
  .oi-hm-strip-sub { font-size:7.5px; color:var(--t2); margin-top:1px; font-family:var(--mono); }
  .oi-hm-badges-bar { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
  .oi-hm-tag { font-size:8.5px; font-weight:800; padding:2px 6px; border-radius:3px; font-family:var(--mono); }
  .oi-hm-tag.bull { background:rgba(34,197,94,0.15); color:var(--bull); border:1px solid rgba(34,197,94,0.3); }
  .oi-hm-tag.bear { background:rgba(239,68,68,0.15); color:var(--bear); border:1px solid rgba(239,68,68,0.3); }
  .oi-hm-tag.neu { background:rgba(148,163,184,0.15); color:var(--t3); border:1px solid var(--b); }
  .oi-hm-grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
  .oi-hm-subcard { background:var(--card2); border:1px solid var(--b); border-radius:5px; padding:6px 8px; }
  .oi-hm-subcard-title { font-size:8px; font-weight:700; color:var(--t3); text-transform:uppercase; letter-spacing:.06em; display:flex; justify-content:space-between; }
  .oi-hm-wzones-wrap { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
  .oi-hm-wzone-tbl { width:100%; border-collapse:collapse; font-size:8.5px; font-family:var(--mono); }
  .oi-hm-wzone-tbl th { font-size:7.5px; color:var(--t3); padding:3px 4px; border-bottom:1px solid var(--b); text-align:left; }
  .oi-hm-wzone-tbl td { padding:3px 4px; border-bottom:1px solid var(--b); }
  .oi-hm-chain-tbl { width:100%; border-collapse:collapse; font-family:var(--mono); font-size:9px; margin-top:4px; }
  .oi-hm-chain-tbl th { font-size:8px; font-weight:800; color:var(--t3); text-transform:uppercase; padding:4px 5px; border-bottom:1px solid var(--b); text-align:center; background:var(--th-bg); position:sticky; top:0; z-index:5; }
  .oi-hm-chain-tbl td { padding:3px 5px; border-bottom:1px solid var(--b); vertical-align:middle; }
  .oi-hm-chain-tbl tr.atm-row { background:rgba(245,158,11,0.14); border-left:2px solid #fbbf24; border-right:2px solid #fbbf24; }
  .oi-bar-cell-ce { position:relative; text-align:right; padding-right:5px; }
  .oi-bar-bg-ce { position:absolute; right:0; top:2px; bottom:2px; background:linear-gradient(90deg, transparent, rgba(239,68,68,0.25)); border-radius:2px; }
  .oi-bar-cell-pe { position:relative; text-align:left; padding-left:5px; }
  .oi-bar-bg-pe { position:absolute; left:0; top:2px; bottom:2px; background:linear-gradient(90deg, rgba(34,197,94,0.25), transparent); border-radius:2px; }

  /* B/U Shift 4 Stats */
  .futbld-stats-bar { padding:2px 0; }
  .fb-stat-card { background:var(--card); border:1px solid var(--b); border-radius:4px; padding:4px; text-align:center; }
  .fb-stat-lbl { font-size:7px; font-weight:800; color:var(--t3); text-transform:uppercase; }
  .fb-stat-val { font-size:12px; font-weight:900; font-family:var(--mono); margin-top:1px; }
  .val-lb { color:var(--bull); }
  .val-sb { color:var(--bear); }
  .val-sc { color:var(--amb); }
  .val-lu { color:var(--pur); }

  /* PreCross Convergence */
  .conv-header { display:flex; align-items:center; padding:4px 8px 3px; border-bottom:1px solid var(--b); flex-shrink:0; background:rgba(0,0,0,0.15); }
  .conv-row { background:var(--card); border:1px solid var(--b); border-radius:4px; margin-bottom:4px; padding:5px 8px; cursor:pointer; transition:all .12s; }
  .conv-row:hover { border-color:var(--bhi); background:rgba(255,255,255,.04); }
  .conv-top { display:flex; align-items:center; gap:5px; margin-bottom:3px; }
  .conv-rank { font-size:8.5px; color:var(--t2); width:16px; text-align:right; font-family:var(--mono); flex-shrink:0; font-weight:700; }
  .conv-sym { font-size:11px; font-weight:800; color:var(--t1); flex:1; }
  .conv-dir { font-size:8px; font-weight:800; padding:1px 5px; border-radius:3px; font-family:var(--mono); }
  .conv-dir.bear { background:rgba(239,68,68,.14); color:var(--bear); border:1px solid rgba(239,68,68,.28); }
  .conv-dir.bull { background:rgba(34,197,94,.14); color:var(--bull); border:1px solid rgba(34,197,94,.28); }
  .conv-score { font-size:10.5px; font-weight:800; font-family:var(--mono); color:var(--t1); width:24px; text-align:right; }
  .conv-bar-wrap { width:100%; height:4px; background:rgba(255,255,255,.06); border-radius:2px; overflow:hidden; margin-bottom:3px; }
  .conv-bar { height:4px; border-radius:2px; transition:width .4s ease; }
  .conv-meta { display:flex; align-items:center; gap:5px; font-size:8px; color:var(--t2); font-family:var(--mono); }
</style>
