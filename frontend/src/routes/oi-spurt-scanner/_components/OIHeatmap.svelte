<script>
  export let sym = '';
  export let chain = [];
  export let ltp = 0;
  export let maxPain = null;
  export let straddle = null;
  export let atm = null;
  export let expiry = null;
  export let pcr = null;
  export let prevChain = null;
  export let dualSide = null;

  function fmt(n, d = 2) {
    if (n === null || n === undefined) return '–';
    return Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function fmtOI(n) {
    if (!n) return '–';
    if (n >= 1e7) return (n / 1e7).toFixed(2) + ' Cr';
    if (n >= 1e5) return (n / 1e5).toFixed(2) + ' L';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(n);
  }
  function buCls(b) {
    return b === 'Long Buildup' ? 'bu-lb' : b === 'Short Buildup' ? 'bu-sb' :
           b === 'Short Covering' ? 'bu-sc' : b === 'Long Unwinding' ? 'bu-lu' : 'bu-flat';
  }
  function buAbbr(b) {
    return b === 'Long Buildup' ? 'LB' : b === 'Short Buildup' ? 'SB' :
           b === 'Short Covering' ? 'SC' : b === 'Long Unwinding' ? 'LU' :
           b === 'Flat' ? 'Flat' : '–';
  }

  $: sortedChain = chain ? [...chain].sort((a, b) => b.strike - a.strike) : [];
  $: maxPEOI = sortedChain.length ? Math.max(...sortedChain.map(r => r.pe_oi), 1) : 1;
  $: maxCEOI = sortedChain.length ? Math.max(...sortedChain.map(r => r.ce_oi), 1) : 1;

  // Build prevMap for tick-by-tick arrows
  $: prevMap = (() => {
    const m = {};
    if (prevChain) prevChain.forEach(r => { m[r.strike] = { ce_oi: r.ce_oi || 0, pe_oi: r.pe_oi || 0 }; });
    return m;
  })();

  function getCeArrow(r) {
    const p = prevMap[r.strike];
    if (!p) return '';
    const diff = r.ce_oi - p.ce_oi;
    if (diff > 0) return `<span style="color:var(--green);font-weight:bold;font-size:9.5px;margin-left:3px">▲(+${fmtOI(diff)})</span>`;
    if (diff < 0) return `<span style="color:var(--red);font-weight:bold;font-size:9.5px;margin-left:3px">▼(-${fmtOI(Math.abs(diff))})</span>`;
    return '';
  }
  function getPeArrow(r) {
    const p = prevMap[r.strike];
    if (!p) return '';
    const diff = r.pe_oi - p.pe_oi;
    if (diff > 0) return `<span style="color:var(--green);font-weight:bold;font-size:9.5px;margin-left:3px">▲(+${fmtOI(diff)})</span>`;
    if (diff < 0) return `<span style="color:var(--red);font-weight:bold;font-size:9.5px;margin-left:3px">▼(-${fmtOI(Math.abs(diff))})</span>`;
    return '';
  }

  $: dsState = dualSide?.state || 'Not live';
  $: dsSignal = dualSide?.signal || 'Not live';
  $: dsBias = dualSide?.bias || 'Not live';
  $: stateColor = dsState === 'TRENDING' ? 'var(--green)' : dsState === 'VOL_COILING' ? 'var(--accent)' : dsState === 'RANGE_PINNING' ? 'var(--yellow)' : 'var(--muted)';
  $: biasBg = dsBias === 'NEUTRAL_THETA_FAVORABLE' ? 'var(--green)' : dsBias === 'NEUTRAL_BREAKOUT_WATCH' ? 'var(--yellow)' : 'rgba(255,255,255,.1)';
  $: biasText = (dsBias === 'NEUTRAL_THETA_FAVORABLE' || dsBias === 'NEUTRAL_BREAKOUT_WATCH') ? '#000' : '#fff';
</script>

<div class="sec-head">OI Chain Heatmap</div>

{#if !chain || chain.length === 0}
  <div class="heatmap-wrap offline">
    <div class="offline-label">⚠️ OFFLINE</div>
    <div class="dual-side-stub">
      <div class="ds-row">
        <span class="ds-title">🔄 DUAL-SIDE STATE ANALYSIS</span>
        <span class="ds-badge">BIAS: Not live</span>
      </div>
      <div class="ds-body">
        <div><strong>State:</strong> <span>Not live</span></div>
        <div><strong>Signal:</strong> <span>Not live</span></div>
        <div><strong>Bias:</strong> <span>Not live</span></div>
      </div>
    </div>
  </div>
{:else}
  <div class="heatmap-wrap">
    <!-- Header -->
    <div class="heatmap-header">
      <span class="hm-title">📊 OI CHAIN &nbsp;·&nbsp; {expiry || '–'}</span>
      <div class="hm-meta">
        <span>Max Pain: <b class="kv-pivot">{maxPain ? fmt(maxPain, 0) : '–'}</b></span>
        <span>Spot: <b>{fmt(ltp)}</b></span>
        <span>Straddle: <b>₹{straddle ? fmt(straddle, 1) : '–'}</b></span>
        <span>PCR: <b style="color:{pcr >= 1 ? 'var(--green)' : 'var(--red)'}">{pcr ? fmt(pcr, 2) : '–'}</b></span>
      </div>
    </div>
    <!-- Legend -->
    <div class="hm-legend">
      <span><span class="leg-dot" style="background:var(--green)"></span>Call OI</span>
      <span><span class="leg-dot" style="background:var(--red)"></span>Put OI</span>
      <span><span class="leg-dot" style="background:var(--yellow)"></span>Max Pain</span>
      <span><span class="leg-dot" style="background:var(--accent)"></span>ATM</span>
    </div>
    <!-- Table -->
    <div class="hm-scroll">
      <table class="hm-table">
        <thead><tr>
          <th>CE OI</th><th>CE Buildup</th><th>ΔCEI</th><th>CE LTP</th>
          <th class="strike-th">STRIKE</th>
          <th>PE LTP</th><th>ΔPE OI</th><th>PE Buildup</th><th>PE OI</th>
          <th>PCR</th><th class="action-th">Action</th>
        </tr></thead>
        <tbody>
          {#each sortedChain as r (r.strike)}
            {@const isATM = r.strike === atm}
            {@const isMP = r.strike === maxPain}
            {@const pePct = r.pe_oi / maxPEOI}
            {@const cePct = r.ce_oi / maxCEOI}
            {@const sPCR = r.strike_pcr != null ? r.strike_pcr : (r.ce_oi > 0 ? r.pe_oi / r.ce_oi : null)}
            {@const pcrStr = sPCR !== null ? fmt(sPCR, 2) : '–'}
            {@const pcrColor = sPCR !== null ? (sPCR >= 1 ? 'var(--green)' : 'var(--red)') : 'var(--muted)'}
            {@const ceEodPct = r.ce_oi_eod_chg_pct || 0}
            {@const peEodPct = r.pe_oi_eod_chg_pct || 0}
            {@const ceAct = r.ce_action || ''}
            {@const peAct = r.pe_action || ''}
            {@const actPri = a => a.includes('BUY') ? 2 : (a.includes('WAIT') || a.includes('PREPARE')) ? 1 : 0}
            {@const topAct = actPri(ceAct) >= actPri(peAct) ? (ceAct || peAct) : (peAct || ceAct)}
            {@const actText = (ceAct && peAct && ceAct !== peAct) ? (actPri(ceAct) >= actPri(peAct) ? `${ceAct} / ${peAct}` : `${peAct} / ${ceAct}`) : (ceAct || peAct || '')}
            {@const actColor = topAct.includes('BUY') ? 'var(--green)' : topAct.includes('WAIT') ? 'var(--yellow)' : 'var(--muted)'}
            <tr class:atm-row={isATM} class:mp-row={isMP}>
              <td class="ce-cell" style="background:rgba(0,230,118,{(cePct * .35).toFixed(2)})">
                {fmtOI(r.ce_oi)}
                {#if ceEodPct !== 0}<span class="{ceEodPct > 0 ? 'pos' : 'neg'}" style="font-size:8.5px;font-weight:600;margin-left:3px">({ceEodPct > 0 ? '+' : ''}{ceEodPct.toFixed(1)}%)</span>{/if}
              </td>
              <td><span class="{buCls(r.ce_buildup)}" style="font-size:9px;font-weight:600">{buAbbr(r.ce_buildup)}</span></td>
              <td class="{r.ce_oi_chg >= 0 ? 'pos' : 'neg'}">{r.ce_oi_chg >= 0 ? '+' : ''}{fmtOI(r.ce_oi_chg)}</td>
              <td>₹{fmt(r.ce_ltp, 1)}</td>
              <td class="strike-td">
                {#if isMP}<span class="mp-badge">MAX PAIN</span>{/if}
                {#if isATM}<span class="atm-badge">ATM</span>{/if}
                {fmt(r.strike, 0)}
              </td>
              <td>₹{fmt(r.pe_ltp, 1)}</td>
              <td class="{r.pe_oi_chg >= 0 ? 'pos' : 'neg'}">{r.pe_oi_chg >= 0 ? '+' : ''}{fmtOI(r.pe_oi_chg)}
                {#if peEodPct !== 0}<span class="{peEodPct > 0 ? 'pos' : 'neg'}" style="font-size:8.5px;font-weight:600;margin-left:3px">({peEodPct > 0 ? '+' : ''}{peEodPct.toFixed(1)}%)</span>{/if}
              </td>
              <td><span class="{buCls(r.pe_buildup)}" style="font-size:9px;font-weight:600">{buAbbr(r.pe_buildup)}</span></td>
              <td class="pe-cell" style="background:rgba(255,61,113,{(pePct * .35).toFixed(2)})">
                {fmtOI(r.pe_oi)}
                {#if peEodPct !== 0}<span class="{peEodPct > 0 ? 'pos' : 'neg'}" style="font-size:8.5px;font-weight:600;margin-left:3px">({peEodPct > 0 ? '+' : ''}{peEodPct.toFixed(1)}%)</span>{/if}
              </td>
              <td style="color:{pcrColor};font-weight:600">{pcrStr}</td>
              <td class="action-td" style="color:{actColor};font-weight:600;font-size:9px;white-space:nowrap">{actText || '–'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Dual-side state panel -->
    <div class="dual-side-alert">
      <div class="ds-row">
        <span class="ds-title" style="color:{stateColor}">🔄 STATE: {dsState}</span>
        <span class="ds-badge" style="background:{biasBg};color:{biasText}">BIAS: {dsBias}</span>
      </div>
      <div class="ds-body">
        <div><strong>State:</strong> <span style="color:#fff;font-weight:500">{dsState}</span></div>
        <div><strong>Signal:</strong> <span style="color:#fff;font-weight:500">{dsSignal}</span></div>
        <div><strong>Bias:</strong> <span style="color:#fff;font-weight:500">{dsBias}</span></div>
      </div>
    </div>
  </div>
{/if}

<style>
  .sec-head {
    font-family: 'Syne', sans-serif; font-size: 8px; font-weight: 700;
    letter-spacing: 2px; color: var(--muted2); text-transform: uppercase;
    margin: 8px 0 5px; display: flex; align-items: center; gap: 8px;
  }
  .sec-head::after { content: ''; flex: 1; height: 1px; background: var(--border); }

  .heatmap-wrap {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden; margin-bottom: 8px;
  }
  .heatmap-wrap.offline { padding: 16px; text-align: center; }
  .offline-label { color: var(--muted); font-size: 11px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 12px; }

  .heatmap-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 6px;
  }
  .hm-title { font-family: 'Syne', sans-serif; font-size: 10px; font-weight: 700; color: var(--accent); letter-spacing: 1px; }
  .hm-meta { display: flex; align-items: center; gap: 12px; font-size: 10px; }
  .hm-meta span { color: var(--muted2); }
  .hm-meta b { color: var(--text); }
  .kv-pivot { color: var(--yellow); }

  .hm-legend { display: flex; gap: 10px; font-size: 9px; padding: 4px 12px; border-bottom: 1px solid var(--border); }
  .leg-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 3px; vertical-align: middle; }

  .hm-scroll { overflow-x: auto; }
  .hm-table {
    width: 100%; min-width: 900px; border-collapse: collapse;
    font-size: 9.5px; table-layout: auto;
  }
  .hm-table th {
    font-size: 7.5px; letter-spacing: .5px; text-transform: uppercase;
    color: var(--muted2); padding: 4px 4px;
    background: var(--surface2); border-bottom: 1px solid var(--border);
    text-align: right; white-space: nowrap;
  }
  .hm-table th.strike-th { text-align: center; color: var(--accent); }
  .hm-table th.action-th { text-align: left; }
  .hm-table td {
    padding: 3px 5px; border-bottom: 1px solid rgba(30,42,66,.35);
    text-align: right; font-variant-numeric: tabular-nums;
    transition: background .15s; white-space: nowrap;
  }
  .hm-table td.strike-td {
    text-align: center; font-family: 'Syne', sans-serif;
    font-weight: 700; font-size: 10px; color: var(--text); min-width: 70px;
  }
  .hm-table td.action-td { text-align: left; }
  .hm-table td.ce-cell { text-align: right; }
  .hm-table td.pe-cell { text-align: right; }
  .hm-table tr:hover td { background: rgba(0,229,255,.04); }
  .hm-table tr.atm-row td { background: rgba(2,132,199,.06); }
  .hm-table tr.atm-row td.strike-td { color: var(--accent); }
  .hm-table tr.mp-row td { background: rgba(217,119,6,.06); }
  .hm-table tr.mp-row td.strike-td { color: var(--yellow); }

  .mp-badge { display: block; font-size: 7px; font-weight: 700; color: var(--yellow); letter-spacing: .5px; line-height: 1; }
  .atm-badge { display: block; font-size: 7px; font-weight: 700; color: var(--accent); letter-spacing: .5px; line-height: 1; }

  /* Dual-side */
  .dual-side-alert {
    margin-top: 12px; padding: 10px 14px; border-radius: 6px;
    background: rgba(255,255,255,.02); border: 1px dashed rgba(255,255,255,.1);
    display: flex; flex-direction: column; gap: 6px; margin: 12px;
  }
  .dual-side-stub { padding: 10px 14px; border-radius: 6px; background: rgba(255,255,255,.02); border: 1px dashed rgba(255,255,255,.1); display: flex; flex-direction: column; gap: 6px; text-align: left; }
  .ds-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,.05); padding-bottom: 5px; }
  .ds-title { font-size: 10px; font-weight: 700; color: var(--muted); }
  .ds-badge { font-weight: 700; font-size: 8.5px; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
  .ds-body { font-size: 9.5px; color: var(--muted); line-height: 1.6; }

  :global(.pos) { color: var(--green) !important; }
  :global(.neg) { color: var(--red) !important; }
  :global(.bu-lb) { color: var(--green); }
  :global(.bu-sb) { color: var(--red); }
  :global(.bu-sc) { color: var(--accent); }
  :global(.bu-lu) { color: var(--muted2); }
  :global(.bu-flat) { color: var(--muted); opacity: .6; }
</style>
