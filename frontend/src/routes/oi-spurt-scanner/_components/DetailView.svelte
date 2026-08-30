<script>
  import { createEventDispatcher } from 'svelte';
  import OIHeatmap from './OIHeatmap.svelte';
  import TransitionConviction from './TransitionConviction.svelte';
  import AiAnalysisPanel from './AiAnalysisPanel.svelte';

  const dispatch = createEventDispatcher();

  export let sym = '';
  export let detail = null;
  export let spurtRow = {};
  export let aiCache = {};

  const INDEX_SET = new Set(['NIFTY','NIFTY50','BANKNIFTY','FINNIFTY','MIDCPNIFTY','SENSEX','BANKEX','NIFTYIT']);

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
  function pclr(v) { return v > 0 ? 'pos' : v < 0 ? 'neg' : 'neu'; }
  function sign(v) { return v >= 0 ? '+' : ''; }
  function buCls(b) {
    return b === 'Long Buildup' ? 'bu-lb' : b === 'Short Buildup' ? 'bu-sb' :
           b === 'Short Covering' ? 'bu-sc' : b === 'Long Unwinding' ? 'bu-lu' : 'bu-flat';
  }
  function buAbbr(b) {
    return b === 'Long Buildup' ? 'LB' : b === 'Short Buildup' ? 'SB' :
           b === 'Short Covering' ? 'SC' : b === 'Long Unwinding' ? 'LU' :
           b === 'Flat' ? 'Flat' : '–';
  }

  function getPCRLabel(pcr, isIndex) {
    if (pcr == null) return { tag: '–', cls: 'tag-yellow', color: 'var(--yellow)' };
    if (isIndex) {
      if (pcr >= 1.5) return { tag: 'Extreme Bullish', cls: 'tag-green', color: 'var(--green)' };
      if (pcr >= 1.2) return { tag: 'Bullish', cls: 'tag-green', color: 'var(--green)' };
      if (pcr >= 0.8) return { tag: 'Neutral', cls: 'tag-yellow', color: 'var(--yellow)' };
      if (pcr >= 0.5) return { tag: 'Bearish', cls: 'tag-red', color: 'var(--red)' };
      return { tag: 'Extreme Bearish', cls: 'tag-red', color: 'var(--red)' };
    } else {
      if (pcr >= 0.8) return { tag: 'Bullish', cls: 'tag-green', color: 'var(--green)' };
      if (pcr >= 0.5) return { tag: 'Neutral', cls: 'tag-yellow', color: 'var(--yellow)' };
      if (pcr >= 0.3) return { tag: 'Bearish', cls: 'tag-red', color: 'var(--red)' };
      return { tag: 'Extreme Bearish', cls: 'tag-red', color: 'var(--red)' };
    }
  }

  function isMarketOpen() {
    const now = new Date();
    const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
    const ist = new Date(utcMs + 5.5 * 3600000);
    const day = ist.getDay();
    if (day === 0 || day === 6) return false;
    const mins = ist.getHours() * 60 + ist.getMinutes();
    return mins >= 555 && mins <= 940;
  }

  $: d = detail || {};
  $: ltp = d.ltp || spurtRow.ltp || 0;
  $: priceChg = d.price_change_pct ?? spurtRow.price_change ?? 0;
  $: oiChgPct = spurtRow.oi_change_pct;
  $: currOI = spurtRow.curr_oi || 0;
  $: prevOI = spurtRow.prev_oi || 0;
  $: pcr = d.pcr;
  $: pv = d.pivots || {};
  $: strikes = d.strikes || {};
  $: top_ce = strikes.top_ce || [];
  $: top_pe = strikes.top_pe || [];
  $: isIndex = d.is_index || INDEX_SET.has(sym);
  $: pcrInfo = getPCRLabel(pcr, isIndex);
  $: dirCls = priceChg > 0 ? 'tag-green' : priceChg < 0 ? 'tag-red' : 'tag-yellow';
  $: isMktOpen = d.market_open !== undefined ? d.market_open : isMarketOpen();
  $: tsStr = d.data_as_of ? new Date(d.data_as_of).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '';
  $: now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  // Futures Layer 1
  $: f = d.futures_data || {};
  $: fLtp = f.ltp || spurtRow.ltp || ltp || 0;
  $: fPriceChg = f.price_change_pct ?? priceChg;
  $: fOi = f.oi || currOI;
  $: fOiPrev = f.oi_prev || f.oi || prevOI;
  $: fOiChgPct = f.oi_change_pct ?? oiChgPct ?? 0;
  $: fBuildup = f.buildup || '–';
  $: buildupBadgeClass =
    fBuildup === 'Long Buildup' ? 'badge-lb' :
    fBuildup === 'Short Buildup' ? 'badge-sb' :
    fBuildup === 'Short Covering' ? 'badge-sc' :
    fBuildup === 'Long Unwinding' ? 'badge-lu' : 'badge-flat';

  // ATM±5 engine
  $: atm5 = strikes.atm_window_5 || {};
  $: immRes = atm5.immediate_resistance || {};
  $: immSup = atm5.immediate_support || {};
  $: risk = atm5.risk_analysis || {};

  // Pivot source badge
  $: pivotSrcLabel = d.pivot_source === 'prev_day' ? 'Prev Day ✓' :
                     d.pivot_source === 'today_ohlc' ? 'Today OHLC' : '';
  $: pivotSrcClass = d.pivot_source === 'prev_day' ? 'badge-pvt-green' : 'badge-pvt-red';

  function strikeRowClass(r) {
    const pcr = r.strike_pcr != null ? r.strike_pcr : (r.ce_oi > 0 ? r.pe_oi / r.ce_oi : null);
    return pcr !== null ? (pcr > 1 ? 'pos' : 'neg') : 'neu';
  }
</script>

{#if !detail}
  <div class="loading-state">
    <div class="spinner"></div> Loading {sym}…
  </div>
{:else}
  <div class="det-wrap">
    <!-- Market closed banner -->
    {#if !isMktOpen}
      <div class="mkt-closed-banner">
        🌙 Market closed — showing EOD snapshot {tsStr ? `(${tsStr} IST)` : ''} &nbsp;|&nbsp; Live updates resume 9:15 AM IST
      </div>
    {/if}

    <!-- (a) Header -->
    <div class="det-header">
      <div class="det-sym-group">
        <span class="det-sym">{sym}</span>
        <div class="det-live"><div class="dot"></div> LIVE · {now}</div>
      </div>

      <!-- Stat strip: LTP | OI Change | Max Pain | Overall PCR | Pivot Levels -->
      <div class="stat-strip">
        <!-- LTP -->
        <div class="stat-box">
          <div class="stat-label">LTP</div>
          <div class="stat-val {pclr(priceChg)}">{fmt(ltp)}</div>
          <div class="stat-sub">{sign(priceChg)}{fmt(priceChg)}% today</div>
        </div>
        <!-- OI Change -->
        <div class="stat-box">
          <div class="stat-label">OI Change %</div>
          <div class="stat-val pos">{oiChgPct != null ? '+' + fmt(oiChgPct) + '%' : '–'}</div>
          <div class="stat-sub">{fmtOI(prevOI)} → {fmtOI(currOI)}</div>
        </div>
        <!-- Max Pain -->
        <div class="stat-box">
          <div class="stat-label">Max Pain</div>
          <div class="stat-val kv-pivot">{d.max_pain ? fmt(d.max_pain, 0) : '–'}</div>
          <div class="stat-sub">{d.max_pain && ltp ? (d.max_pain > ltp ? '▲ Above LTP' : '▼ Below LTP') : '–'}</div>
        </div>
        <!-- Overall PCR -->
        <div class="stat-box">
          <div class="stat-label">Overall PCR</div>
          <div class="stat-val" style="color:{pcrInfo.color}">{pcr != null ? fmt(pcr, 3) : '–'}</div>
          <div class="stat-sub">{pcrInfo.tag}</div>
        </div>
        <!-- Pivot Levels -->
        <div class="stat-box stat-box-pivot">
          <div class="stat-label">
            Pivot Levels
            {#if pivotSrcLabel}<span class="pvt-src {pivotSrcClass}">{pivotSrcLabel}</span>{/if}
          </div>
          {#if pv.P}
            <div class="pivot-grid">
              <span class="pk">R3:</span> <span class="pv kv-res">{fmt(pv.R3, 0)}</span>
              <span class="pk">S1:</span> <span class="pv kv-sup">{fmt(pv.S1, 0)}</span>
              <span class="pk">R2:</span> <span class="pv kv-res">{fmt(pv.R2, 0)}</span>
              <span class="pk">S2:</span> <span class="pv kv-sup">{fmt(pv.S2, 0)}</span>
              <span class="pk">R1:</span> <span class="pv kv-res">{fmt(pv.R1, 0)}</span>
              <span class="pk">S3:</span> <span class="pv kv-sup">{fmt(pv.S3, 0)}</span>
              <span class="pvt-center" style="grid-column:span 2">PVT: <span class="kv-pivot" style="font-weight:700">{fmt(pv.P, 0)}</span></span>
            </div>
          {:else}
            <div class="pivot-na">Kite Not Connected</div>
          {/if}
        </div>
      </div>

      <button class="det-close" on:click={() => dispatch('close')}>✕ Close</button>
    </div>

    <!-- Tags -->
    <div class="tags">
      <span class="tag {dirCls}">{priceChg > 0 ? '▲ Bullish' : priceChg < 0 ? '▼ Bearish' : '↔ Neutral'}</span>
      {#if pcr != null}<span class="tag {pcrInfo.cls}">PCR: {fmt(pcr, 2)} · {pcrInfo.tag}</span>{/if}
      {#if d.expiry}<span class="tag tag-blue">Expiry: {d.expiry}</span>{/if}
    </div>

    <!-- Errors -->
    {#if d.errors?.length}
      <div class="err-msg">⚠ {d.errors.filter(e => !e.includes('Kite not')).join(' | ')}</div>
    {/if}

    <!-- Main 2-column grid -->
    <div class="det-grid">
      <!-- COL 1 -->
      <div class="col1">
        <!-- F&O 3-Layer Analytics -->
        <div class="sec-head">📊 F&amp;O 3-Layer Analytics</div>

        <div class="layer-row1-grid">
          <!-- Layer 1 -->
          <div class="layer-card l1">
            <div class="layer-title">LAYER 1 — DIRECTIONAL COMMITMENT <span>FUTURES OI</span></div>
            <div class="l1-top">
              <div>
                <div class="l-ltp">₹{fmt(fLtp)}</div>
                <div class="l-sub {pclr(fPriceChg)}">{sign(fPriceChg)}{fmt(fPriceChg)}% today</div>
              </div>
              <span class="badge-buildup {buildupBadgeClass}">{fBuildup}</span>
            </div>
            <div class="kv" style="border-top:1px solid rgba(128,128,128,.15);padding-top:6px">
              <span class="kv-k">Futures OI (Curr/Prev)</span>
              <span class="kv-v">{fmtOI(fOi)} / {fmtOI(fOiPrev)}</span>
            </div>
            <div class="kv">
              <span class="kv-k">Futures OI Change %</span>
              <span class="kv-v {pclr(fOiChgPct)}">{sign(fOiChgPct)}{fmt(fOiChgPct)}%</span>
            </div>
          </div>

          <!-- Layer 2 -->
          <div class="layer-card l2">
            <div class="layer-title">LAYER 2 — SENTIMENT BIAS <span>OPTIONS PCR</span></div>
            <div class="l1-top">
              <div>
                <div class="l-ltp" style="color:{pcrInfo.color}">{pcr != null ? fmt(pcr, 3) : '–'}</div>
                <div class="l-sub" style="color:var(--muted)">{pcrInfo.tag} Sentiment</div>
              </div>
              <div class="pcr-bar-wrap">
                <div class="pcr-bar" style="width:{Math.min(100, Math.log1p(pcr || 0) / Math.log1p(2.5) * 100).toFixed(1)}%;background:{pcrInfo.color}"></div>
              </div>
            </div>
            <div class="kv" style="border-top:1px solid rgba(128,128,128,.15);padding-top:6px">
              <span class="kv-k">PCR Ratio (Total PE / CE)</span>
              <span class="kv-v" style="color:{pcrInfo.color};font-weight:600">{pcr != null ? fmt(pcr, 2) : '–'}</span>
            </div>
          </div>
        </div>

        <!-- Layer 3 -->
        <div class="layer-card l3">
          <div class="layer-title" style="display:flex;justify-content:space-between">
            <span>LAYER 3 — KEY TRADING BARRIERS &amp; ATM ± 5 ENGINE</span>
            <span style="font-size:8px;color:var(--muted2)">INTRADAY FLOW ANALYSIS</span>
          </div>
          {#if risk.alert_title}
            <div class="risk-pill" style="border-color:{risk.flag_cls === 'tag-red' ? 'var(--red)' : risk.flag_cls === 'tag-green' ? 'var(--green)' : 'var(--accent)'}; color:{risk.flag_cls === 'tag-red' ? 'var(--red)' : risk.flag_cls === 'tag-green' ? 'var(--green)' : 'var(--accent)'}">
              <span>{risk.alert_title}: {risk.short_desc || ''}</span>
              <span class="tag {risk.flag_cls || 'tag-blue'}" style="font-size:8px">ATM ± 5 ENGINE</span>
            </div>
          {/if}
          <div class="layer3-subgrid">
            <div class="l3-col l3-res">
              <div class="l3-col-title">IMM RESISTANCE (ATM+5)</div>
              <div class="l3-strike" style="color:var(--red)">{immRes.strike ? fmt(immRes.strike, 0) : '–'}</div>
              <div class="l3-strength" style="color:{immRes.color || 'var(--text)'}">Strength: {immRes.strength_score != null ? immRes.strength_score : '–'}/100 <span>({immRes.strength_rating || '–'})</span></div>
              <div class="l3-flow">Flow: {immRes.buildup || '–'}</div>
            </div>
            <div class="l3-col l3-sup">
              <div class="l3-col-title">IMM SUPPORT (ATM-5)</div>
              <div class="l3-strike" style="color:var(--green)">{immSup.strike ? fmt(immSup.strike, 0) : '–'}</div>
              <div class="l3-strength" style="color:{immSup.color || 'var(--text)'}">Strength: {immSup.strength_score != null ? immSup.strength_score : '–'}/100 <span>({immSup.strength_rating || '–'})</span></div>
              <div class="l3-flow">Flow: {immSup.buildup || '–'}</div>
            </div>
            <div class="l3-col">
              <div class="l3-col-title">GLOBAL WALLS &amp; MAX PAIN</div>
              <div class="kv" style="padding:1px 0"><span class="kv-k" style="font-size:8.5px">CE Wall (Res)</span><span class="kv-v kv-res" style="font-size:9px;font-weight:600">{strikes.ce_wall ? fmt(strikes.ce_wall, 0) : '–'}</span></div>
              <div class="kv" style="padding:1px 0"><span class="kv-k" style="font-size:8.5px">PE Wall (Sup)</span><span class="kv-v kv-sup" style="font-size:9px;font-weight:600">{strikes.pe_wall ? fmt(strikes.pe_wall, 0) : '–'}</span></div>
              <div class="kv" style="padding:1px 0;border-top:1px solid rgba(128,128,128,.15);margin-top:2px"><span class="kv-k" style="font-size:8.5px">Max Pain</span><span class="kv-v kv-pivot" style="font-size:9px;font-weight:600">{d.max_pain ? fmt(d.max_pain, 0) : '–'}</span></div>
            </div>
          </div>
        </div>

        <!-- Strike PCR Buildup Trap -->
        <div class="sec-head" style="margin-top:4px">(e) Strike PCR, Buildup, Trap</div>
        <div class="strike-tables-grid">
          <div class="card">
            <div class="card-title" style="color:var(--red)">📞 CE Writing — Resistance Zones</div>
            {#if top_ce.length}
              <table class="mt">
                <thead><tr><th>Strike</th><th>OI</th><th>OI Chg</th><th>PCR</th><th>Buildup</th><th>Trap</th></tr></thead>
                <tbody>
                  {#each top_ce as r}
                    {@const sPCR = r.strike_pcr != null ? r.strike_pcr : null}
                    {@const pcrColor = sPCR !== null ? (sPCR > 1 ? 'var(--green)' : 'var(--red)') : 'var(--muted)'}
                    <tr>
                      <td><b>{fmt(r.strike, 0)}</b></td>
                      <td>{fmtOI(r.oi)}<span class="oi-bar" style="background:var(--red);width:{Math.round((r.oi / Math.max(...top_ce.map(x=>x.oi),1)) * 34)}px"></span></td>
                      <td class={r.oi_chg >= 0 ? 'pos' : 'neg'}>{r.oi_chg >= 0 ? '+' : ''}{fmtOI(r.oi_chg)}</td>
                      <td style="color:{pcrColor}">{sPCR !== null ? fmt(sPCR, 2) : '–'}</td>
                      <td><span class={buCls(r.buildup)}>{r.buildup}</span></td>
                      <td>{#if r.trap}<span class="trap">⚠ {r.trap}</span>{/if}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="no-data">No data — connect Kite for option chain</div>
            {/if}
          </div>
          <div class="card">
            <div class="card-title" style="color:var(--green)">📉 PE Writing — Support Zones</div>
            {#if top_pe.length}
              <table class="mt">
                <thead><tr><th>Strike</th><th>OI</th><th>OI Chg</th><th>PCR</th><th>Buildup</th><th>Trap</th></tr></thead>
                <tbody>
                  {#each top_pe as r}
                    {@const sPCR = r.strike_pcr != null ? r.strike_pcr : null}
                    {@const pcrColor = sPCR !== null ? (sPCR > 1 ? 'var(--green)' : 'var(--red)') : 'var(--muted)'}
                    <tr>
                      <td><b>{fmt(r.strike, 0)}</b></td>
                      <td>{fmtOI(r.oi)}<span class="oi-bar" style="background:var(--green);width:{Math.round((r.oi / Math.max(...top_pe.map(x=>x.oi),1)) * 34)}px"></span></td>
                      <td class={r.oi_chg >= 0 ? 'pos' : 'neg'}>{r.oi_chg >= 0 ? '+' : ''}{fmtOI(r.oi_chg)}</td>
                      <td style="color:{pcrColor}">{sPCR !== null ? fmt(sPCR, 2) : '–'}</td>
                      <td><span class={buCls(r.buildup)}>{r.buildup}</span></td>
                      <td>{#if r.trap}<span class="trap">⚠ {r.trap}</span>{/if}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="no-data">No data — connect Kite for option chain</div>
            {/if}
          </div>
        </div>

        <!-- Live Retail Action & H-Action -->
        <div class="sec-head" style="margin-top:4px">⚡ Live Retail Action &amp; H-Action Signal</div>
        <div class="strike-tables-grid">
          <div class="card">
            {#if d.gap_detected}
              <div class="gap-banner">⚡ Gap day detected — price/IV trends suppressed. Signal based on OI momentum only.</div>
            {/if}
            <div class="kv"><span class="kv-k">Action</span><span class="kv-v" style="color:{(d.retail_action||'').includes('BUY') ? 'var(--green)' : 'var(--yellow)'};font-weight:600">{d.retail_action || 'WAIT (No clear setup)'}</span></div>
            {#if d.signal_source}<div class="kv"><span class="kv-k" style="font-size:9px;opacity:.7">↳ Signal from</span><span class="kv-v" style="font-size:9px;color:var(--muted2)">{d.signal_source.side} {fmt(d.signal_source.strike,0)} &nbsp;·&nbsp; OI: {fmtOI(d.signal_source.oi)}</span></div>{/if}
            <div class="kv"><span class="kv-k">H-Action</span><span class="kv-v" style="color:var(--green);font-weight:600">{d.h_action || '—'}</span></div>
            {#if d.h_action_source}<div class="kv"><span class="kv-k" style="font-size:9px;opacity:.7">↳ H-Signal from</span><span class="kv-v" style="font-size:9px;color:var(--muted2)">{d.h_action_source.side} {fmt(d.h_action_source.strike,0)} &nbsp;·&nbsp; OI: {fmtOI(d.h_action_source.oi)}</span></div>{/if}
            <div style="margin-top:6px;font-size:9px;color:var(--muted);text-align:right">Probabilistic signals — not guaranteed outcomes</div>
          </div>
          <div class="card">
            <div class="card-title" style="color:var(--accent)">🔁 F&amp;O Synergy Profile</div>
            <div class="kv"><span class="kv-k">Synergy Status</span><span class="kv-v" style="font-weight:600;color:{(d.synergy_profile||'').includes('🟢') ? 'var(--green)' : (d.synergy_profile||'').includes('🔴') ? 'var(--red)' : 'var(--yellow)'}">{d.synergy_profile || 'Mixed Flow (No Setup)'}</span></div>
            <div class="kv"><span class="kv-k">Action Plan</span><span class="kv-v" style="font-weight:600;color:{(d.synergy_action||'').includes('BUY') ? 'var(--green)' : (d.synergy_action||'').includes('SELL') ? 'var(--accent)' : 'var(--yellow)'}">{d.synergy_action || 'WAIT'}</span></div>
            <div style="margin-top:6px;font-size:9px;color:var(--muted);text-align:right">Aligned to 7-Profile Institutional Matrix</div>
          </div>
        </div>
      </div>

      <!-- COL 2 -->
      <div class="col2">
        <OIHeatmap {sym} chain={d.chain_data} {ltp} maxPain={d.max_pain} straddle={d.straddle} atm={d.atm} expiry={d.expiry} {pcr} prevChain={null} dualSide={d.dual_side_analysis} />
        <TransitionConviction tc={d.transition_conviction} />
        <AiAnalysisPanel {sym} cache={aiCache[sym]} on:cacheUpdate={e => dispatch('aiCache', e.detail)} />
      </div>
    </div>
  </div>
{/if}

<style>
  .loading-state {
    display: flex; align-items: center; gap: 8px;
    padding: 30px; color: var(--muted); font-size: 12px;
  }
  .spinner {
    width: 14px; height: 14px; border: 2px solid var(--border);
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin .7s linear infinite; display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .det-wrap { padding: 14px; }

  .mkt-closed-banner {
    background: rgba(217,119,6,.1); border: 1px solid rgba(217,119,6,.3);
    border-radius: 6px; padding: 5px 10px; font-size: 9px;
    color: var(--yellow); margin-bottom: 8px;
  }

  /* Header */
  .det-header {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; margin-bottom: 12px; padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .det-sym-group { display: flex; flex-direction: column; gap: 2px; min-width: 100px; }
  .det-sym { font-family: 'Syne', sans-serif; font-size: 20px; font-weight: 800; color: var(--accent); line-height: 1.1; }
  .det-live { display: flex; align-items: center; gap: 4px; font-size: 9px; color: var(--green); }
  .dot { width: 5px; height: 5px; border-radius: 50%; background: var(--green); animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(0,230,118,.4)} 50%{opacity:.7;box-shadow:0 0 0 4px rgba(0,230,118,0)} }

  .det-close {
    margin-left: auto; background: transparent;
    border: 1px solid var(--border); color: var(--muted2);
    border-radius: 4px; padding: 3px 10px;
    font-family: inherit; font-size: 10px; cursor: pointer; transition: all .2s;
  }
  .det-close:hover { border-color: var(--red); color: var(--red); }

  /* Stat strip */
  .stat-strip { display: flex; gap: 6px; flex: 1; flex-wrap: wrap; margin-left: 16px; }
  .stat-box {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 6px; padding: 5px 8px; position: relative;
    flex: 1; max-width: 170px; min-width: 100px;
  }
  .stat-box-pivot { min-width: 160px; max-width: 200px; }
  .stat-label { font-size: 8px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted2); margin-bottom: 2px; display: flex; align-items: center; justify-content: space-between; }
  .stat-val { font-family: 'Syne', sans-serif; font-size: 14px; font-weight: 700; }
  .stat-sub { font-size: 8px; color: var(--muted2); margin-top: 1px; }

  .pvt-src { font-size: 7px; padding: 1px 4px; border-radius: 3px; border: 1px solid; margin-left: 4px; }
  .badge-pvt-green { background: rgba(22,163,74,.1); color: var(--green); border-color: rgba(22,163,74,.2); }
  .badge-pvt-red { background: rgba(220,38,38,.1); color: var(--red); border-color: rgba(220,38,38,.2); }

  .pivot-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 1px 14px; font-size: 9px; line-height: 1.05; }
  .pk { color: var(--muted2); }
  .pv { font-weight: 600; text-align: right; }
  .pvt-center { border-top: 1px solid rgba(255,255,255,.08); padding-top: 1px; text-align: center; font-size: 9px; }
  .pivot-na { color: var(--muted2); font-style: italic; font-size: 8px; text-align: center; padding: 6px 0; }

  /* Tags */
  .tags { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px; }
  .tag { display: inline-flex; align-items: center; padding: 3px 8px; border-radius: 10px; font-size: 9px; font-weight: 600; white-space: nowrap; border: 1px solid; }
  .tag-green { background: rgba(22,163,74,.1); color: var(--green); border-color: rgba(22,163,74,.2); }
  .tag-red { background: rgba(220,38,38,.1); color: var(--red); border-color: rgba(220,38,38,.2); }
  .tag-yellow { background: rgba(217,119,6,.1); color: var(--yellow); border-color: rgba(217,119,6,.2); }
  .tag-blue { background: rgba(2,132,199,.1); color: var(--accent); border-color: rgba(2,132,199,.2); }

  .err-msg { padding: 8px 12px; background: rgba(220,38,38,.08); border: 1px solid rgba(220,38,38,.2); border-radius: 6px; color: var(--red); font-size: 10px; margin-bottom: 10px; }

  /* Main grid */
  .det-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 10px; align-items: start; margin-top: 10px; }
  .col1 { display: flex; flex-direction: column; gap: 7px; }
  .col2 { display: flex; flex-direction: column; gap: 7px; }

  .sec-head {
    font-family: 'Syne', sans-serif; font-size: 8px; font-weight: 700;
    letter-spacing: 2px; color: var(--muted2); text-transform: uppercase;
    margin: 8px 0 5px; display: flex; align-items: center; gap: 8px;
  }
  .sec-head::after { content: ''; flex: 1; height: 1px; background: var(--border); }

  /* Layer cards */
  .layer-row1-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .layer-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 7px; padding: 8px 12px; position: relative; color: var(--text);
  }
  .layer-card::before {
    content: ''; position: absolute; top: 0; left: 0; height: 100%; width: 3px;
    border-top-left-radius: 7px; border-bottom-left-radius: 7px;
  }
  .layer-card.l1::before { background: var(--accent); }
  .layer-card.l2::before { background: var(--yellow); }
  .layer-card.l3::before { background: var(--red); }

  .layer-title { font-size: 10px; text-transform: uppercase; color: var(--muted2); font-weight: 700; letter-spacing: .8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
  .layer-title span { font-size: 8px; padding: 1px 5px; border-radius: 3px; background: rgba(255,255,255,.06); }
  .l1-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .l-ltp { font-size: 14px; font-weight: 700; color: var(--text); }
  .l-sub { font-size: 9px; }

  .pcr-bar-wrap { width: 80px; background: rgba(128,128,128,.15); height: 4px; border-radius: 2px; position: relative; }
  .pcr-bar { height: 100%; border-radius: 2px; }

  /* Buildup badges */
  .badge-buildup { display: inline-block; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: .5px; }
  .badge-lb { background: rgba(0,230,118,.15); color: var(--green); border: 1px solid rgba(0,230,118,.3); }
  .badge-sb { background: rgba(255,61,113,.15); color: var(--red); border: 1px solid rgba(255,61,113,.3); }
  .badge-sc { background: rgba(0,229,255,.15); color: var(--accent); border: 1px solid rgba(0,229,255,.3); }
  .badge-lu { background: rgba(255,145,0,.15); color: var(--orange); border: 1px solid rgba(255,145,0,.3); }
  .badge-flat { background: rgba(255,255,255,.08); color: var(--muted); border: 1px solid rgba(255,255,255,.15); }

  /* Layer 3 subgrid */
  .layer3-subgrid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 4px; }
  .l3-col { background: rgba(255,255,255,.025); padding: 6px 8px; border-radius: 5px; }
  .l3-res { border-left: 3px solid var(--red); }
  .l3-sup { border-left: 3px solid var(--green); }
  .l3-col-title { font-size: 8.5px; color: var(--muted2); font-weight: 600; }
  .l3-strike { font-size: 14px; font-weight: 700; margin: 2px 0; }
  .l3-strength { font-size: 9px; font-weight: 600; }
  .l3-strength span { font-size: 7.5px; }
  .l3-flow { font-size: 8px; color: var(--muted); margin-top: 1px; }

  .risk-pill {
    background: rgba(255,255,255,.035); border: 1px solid; border-radius: 4px;
    padding: 4px 8px; margin: 4px 0 6px; font-size: 9.5px; font-weight: 700;
    display: flex; justify-content: space-between; align-items: center;
  }

  /* KV rows */
  .kv { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 10px; border-bottom: 1px solid rgba(30,42,66,.5); }
  .kv:last-child { border-bottom: none; }
  .kv-k { color: var(--muted2); }
  .kv-v { font-weight: 500; }
  .kv-pivot { color: var(--yellow); }
  .kv-res { color: var(--red); }
  .kv-sup { color: var(--green); }

  /* Strike tables */
  .strike-tables-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 7px; padding: 8px 12px; }
  .card-title { font-size: 8px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted2); margin-bottom: 6px; }
  .no-data { color: var(--muted); font-size: 9px; padding: 6px; }

  .mt { width: 100%; font-size: 10px; border-collapse: collapse; }
  .mt th { font-size: 8px; letter-spacing: .8px; text-transform: uppercase; color: var(--muted2); padding: 3px 5px; text-align: left; border-bottom: 1px solid var(--border); }
  .mt td { padding: 5px 5px; border-bottom: 1px solid rgba(30,42,66,.4); }
  .mt tr:last-child td { border-bottom: none; }
  .mt tr:hover td { background: var(--surface2); }

  .oi-bar { width: 36px; height: 3px; border-radius: 2px; display: inline-block; vertical-align: middle; margin-left: 4px; }
  .trap { font-size: 7px; padding: 1px 3px; border-radius: 2px; background: rgba(255,145,0,.15); color: var(--orange); margin-left: 3px; }

  .gap-banner { background: rgba(217,119,6,.12); border: 1px solid rgba(217,119,6,.35); border-radius: 5px; padding: 5px 8px; font-size: 9px; color: var(--yellow); margin-bottom: 8px; }

  :global(.pos) { color: var(--green); }
  :global(.neg) { color: var(--red); }
  :global(.neu) { color: var(--muted2); }
  :global(.bu-lb) { color: var(--green); }
  :global(.bu-sb) { color: var(--red); }
  :global(.bu-sc) { color: var(--accent); }
  :global(.bu-lu) { color: var(--muted2); }
  :global(.bu-flat) { color: var(--muted); opacity: .6; }

  @media (max-width: 1024px) {
    .det-grid { grid-template-columns: 1fr; }
    .layer-row1-grid { grid-template-columns: 1fr; }
    .layer3-subgrid { grid-template-columns: 1fr; }
    .strike-tables-grid { grid-template-columns: 1fr; }
    .stat-strip { margin-left: 0; margin-top: 8px; }
    .det-header { flex-direction: column; align-items: flex-start; }
  }
</style>
