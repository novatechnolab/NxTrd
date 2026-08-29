<script>
  export let liveBreakoutData = { triggered_alerts: [], collision_alerts: [], bb_squeezes: [], ema_coils: [] };
  export let breakouts = { bulls: [], bears: [], bb_squeezes: [], ema_coils: [] };
  export let sessionStats = {
    alertsToday: 1198,
    alertsSub: 'Prem: 1041 · Brk: 157 · A: 0',
    spurts: 49,
    spurtsSub: '≥15%: 10 stocks',
    longBull: 65,
    lbSub: 'SC: 19 · LU: 15',
    shortBear: 84,
    sbSub: 'Bear Conv.'
  };
  export let emaConvData = [];
  export let oiSpurts = [];
  export let stocks = [];

  $: alerts = liveBreakoutData?.triggered_alerts || [];
  $: collisions = liveBreakoutData?.collision_alerts || [];
  $: bbSqueezes = (liveBreakoutData?.bb_squeezes?.length ? liveBreakoutData.bb_squeezes : (breakouts?.bb_squeezes || []));
  $: emaCoils = (liveBreakoutData?.ema_coils?.length ? liveBreakoutData.ema_coils : (breakouts?.ema_coils || []));

  $: combinedAlerts = (() => {
    if (alerts.length || collisions.length) {
      const list = [
        ...alerts.map(a => ({ ...a, _kind: 'breakout' })),
        ...collisions.map(c => ({ ...c, _kind: 'collision' }))
      ];
      return list.sort((a, b) => (b.trigger_epoch || 0) - (a.trigger_epoch || 0));
    }
    // Fallback if empty
    return [
      ...(breakouts.bulls || []).map(b => ({ ...b, symbol: b.symbol || b.sym, direction: 'bullish', grade: b.crossBadge || '5M Cross', _kind: 'breakout' })),
      ...(breakouts.bears || []).map(b => ({ ...b, symbol: b.symbol || b.sym, direction: 'bearish', grade: b.crossBadge || '5M Cross', _kind: 'breakout' }))
    ];
  })();

  function fmtTime(ts) {
    if (!ts) return '';
    const raw = String(ts);
    return raw.length >= 5 ? raw.slice(-8).slice(0, 5) : raw;
  }
</script>

<div class="rp">
  <!-- Section 1: Live Breakouts -->
  <div class="rp-section" style="flex:1 1 0;min-height:0;display:flex;flex-direction:column;overflow:hidden;">
    <div class="rp-sh">
      <span style="display:flex;align-items:center;gap:4px;">🚀 <span>LIVE BREAKOUTS</span></span>
      <span class="cbadge">{combinedAlerts.length}</span>
    </div>
    <div class="rp-body">
      {#each combinedAlerts as item}
        {@const isBull = item.direction === 'bullish' || item.direction === 'BULL' || item.direction === 'BULLISH' || item.bull}
        {@const arrow = isBull ? '▲' : '▼'}
        {@const ltpStr = item.ltp ? '₹' + Number(item.ltp).toFixed(1) : ''}
        {@const volStr = item.vol_multiplier ? `×${item.vol_multiplier}` : ''}
        {@const timeStr = fmtTime(item.time || item.timestamp || item.coil_time)}

        {#if item._kind === 'collision'}
          {@const colColor = isBull ? '#388bfd' : '#e09400'}
          {@const colBg = isBull ? 'rgba(56,139,253,0.12)' : 'rgba(224,148,0,0.12)'}
          <div class="brk-item" style="border-left:2px solid {colColor};background:{colBg};margin-bottom:2px;border-radius:4px;padding:5px 8px;">
            <div style="display:flex;align-items:center;gap:4px;">
              <span style="color:{colColor};font-size:10px;font-weight:900;width:10px;flex-shrink:0;">{arrow}</span>
              <span class="brk-sym" style="color:{colColor};font-weight:800;">{item.symbol}</span>
              <span class="btag" style="font-size:7px;padding:1px 4px;background:{colBg};color:{colColor};border:1px solid {colColor}40;">EMA COLLISION</span>
              <span style="margin-left:auto;font-size:8px;color:var(--t2);font-family:var(--mono);">{timeStr}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;margin-top:1px;padding-left:14px;">
              <span style="font-size:10px;font-weight:700;font-family:var(--mono);color:var(--t1);">{ltpStr}</span>
              {#if volStr}<span style="font-size:8px;color:var(--t2);font-weight:600;">{volStr}</span>{/if}
            </div>
          </div>
        {:else}
          {@const cls = isBull ? 'bull' : 'bear'}
          {@const tagCls = isBull ? 'b' : 'r'}
          {@const grade = item.grade || '5M Cross'}
          <div class="brk-item">
            <div style="display:flex;align-items:center;gap:4px;">
              <span class="{cls}" style="font-size:10px;font-weight:900;width:10px;flex-shrink:0;">{arrow}</span>
              <span class="brk-sym {cls}">{item.symbol}</span>
              <span class="btag {tagCls}" style="font-size:7px;padding:1px 4px;">{grade}</span>
              <span style="margin-left:auto;font-size:8px;color:var(--t2);font-family:var(--mono);">{timeStr}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;margin-top:1px;padding-left:14px;">
              <span style="font-size:10px;font-weight:700;font-family:var(--mono);color:var(--t1);">{ltpStr}</span>
              {#if volStr}<span style="font-size:8px;color:var(--t2);font-weight:600;">{volStr}</span>{/if}
            </div>
          </div>
        {/if}
      {/each}

      {#if !combinedAlerts.length}
        <div class="empty" style="padding:16px 8px;">
          <div class="ei">⚡</div>
          <div class="et">No active breakouts</div>
          <div class="es">Scanning EMA crossovers</div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Section 2: Squeeze Watchlist -->
  <div class="rp-section" style="flex:1 1 0;min-height:0;display:flex;flex-direction:column;overflow:hidden;">
    <div class="rp-sh">
      <span style="display:flex;align-items:center;gap:4px;">🏹 <span>SQUEEZE WATCHLIST</span></span>
      <span class="cbadge">{bbSqueezes.length}</span>
    </div>
    <div class="rp-body">
      {#each [...bbSqueezes].sort((a,b)=>(b.squeeze_duration_mins||0)-(a.squeeze_duration_mins||0)) as sq}
        {@const durLabel = (sq.squeeze_duration_mins >= 2) ? `${sq.squeeze_duration_mins}m` : '<1m'}
        {@const ltpStr = sq.last_ltp ? `₹${Number(sq.last_ltp).toFixed(1)}` : '—'}
        <div class="brk-item" style="padding:4px 8px;border-bottom:1px solid var(--b);">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:4px;">
              <span style="color:#ffd700;font-size:9px;">◌</span>
              <span style="font-size:10px;font-weight:700;color:#ffd700;">{sq.symbol}</span>
              <span style="font-size:7px;padding:0.5px 3px;border-radius:2px;background:rgba(255,215,0,0.12);color:#ffd700;font-weight:600;">Squeeze</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-size:9px;font-weight:700;font-family:var(--mono);color:var(--t1);">{ltpStr}</span>
              <span style="font-size:8px;font-weight:700;background:rgba(210,153,34,0.18);border-radius:2px;padding:0.5px 3px;color:#e3b341;font-family:var(--mono);">⏳ {durLabel}</span>
            </div>
          </div>
        </div>
      {/each}
      {#if !bbSqueezes.length}
        <div style="padding:10px 8px;font-size:9px;color:var(--t2);text-align:center;">No active squeezes</div>
      {/if}
    </div>
  </div>

  <!-- Section 3: EMA Coil Watchlist -->
  <div class="rp-section" style="flex:1 1 0;min-height:0;display:flex;flex-direction:column;overflow:hidden;">
    <div class="rp-sh">
      <span style="display:flex;align-items:center;gap:4px;">🌀 <span>EMA COIL WATCHLIST</span></span>
      <span class="cbadge">{emaCoils.length}</span>
    </div>
    <div class="rp-body">
      {#each emaCoils as coil}
        {@const gapLabel = coil.ema_gap_pct ? `${Number(coil.ema_gap_pct).toFixed(3)}%` : '0.050%'}
        {@const coilTime = fmtTime(coil.coil_time || '15:25')}
        {@const ltpStr = coil.last_ltp && coil.last_ltp > 0 ? `₹${Number(coil.last_ltp).toFixed(1)}` : ''}
        <div class="brk-item" style="padding:4px 8px;border-bottom:1px solid var(--b);border-left:2px solid #388bfd;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:4px;">
            <div style="display:flex;align-items:center;gap:3px;min-width:0;">
              <span style="color:#388bfd;font-size:9px;flex-shrink:0;">⟳</span>
              <span style="font-size:10px;font-weight:700;color:#388bfd;white-space:nowrap;">{coil.symbol}</span>
              <span style="font-size:7px;padding:0.5px 3px;border-radius:2px;background:rgba(56,139,253,0.15);color:#388bfd;font-weight:600;white-space:nowrap;flex-shrink:0;">Coil</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
              {#if ltpStr}<span style="font-size:9px;font-weight:700;font-family:var(--mono);color:var(--t1);">{ltpStr}</span>{/if}
              <span style="font-size:7.5px;font-weight:700;background:rgba(56,139,253,0.15);border-radius:2px;padding:0.5px 2px;color:#388bfd;font-family:var(--mono);">- Δ{gapLabel}</span>
              <span style="font-size:8px;color:var(--t2);font-family:var(--mono);">{coilTime}</span>
            </div>
          </div>
        </div>
      {/each}
      {#if !emaCoils.length}
        <div style="padding:10px 8px;font-size:9px;color:var(--t2);text-align:center;">No EMA coil stocks</div>
      {/if}
    </div>
  </div>

  <!-- Bottom: fixed rules + stats (matches reference exactly) -->
  <div style="flex-shrink:0;border-top:1px solid var(--b);background:var(--ch-bg);">
    <!-- Confluence Rules -->
    <div class="rp-section" style="padding:5px 8px;border-bottom:1px solid var(--b);">
      <div style="font-size:8px;font-weight:700;color:var(--t1);margin-bottom:3px;text-transform:uppercase;letter-spacing:.06em;display:flex;justify-content:space-between;">
        <span>CONFLUENCE RULES</span>
        <span style="font-size:7.5px;color:var(--t3);">A:8-10 · B:5-7 · C:0-4</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 8px;font-size:7.5px;color:var(--t2);">
        <div style="display:flex;justify-content:space-between;"><span>TF Align</span><b class="bull">+3</b></div>
        <div style="display:flex;justify-content:space-between;"><span>OI Spurt</span><b class="pur">+2</b></div>
        <div style="display:flex;justify-content:space-between;"><span>RVOL/FH</span><b class="cyn">+1</b></div>
        <div style="display:flex;justify-content:space-between;"><span>Fut/DX/Drift</span><b class="amb">+1</b></div>
      </div>
    </div>

    <!-- Session Stats: 4 cards matching reference exactly -->
    <div style="padding:5px 8px;">
      <div style="font-size:8px;font-weight:700;color:var(--t1);margin-bottom:4px;text-transform:uppercase;letter-spacing:.06em;">SESSION STATS</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
        <div class="stat-card" style="text-align:center;">
          <div class="stat-lbl">ALERTS TODAY</div>
          <div class="stat-val" style="color:var(--bull);">{sessionStats.alertsToday}</div>
          <div style="font-size:7px;color:var(--t3);">{sessionStats.alertsSub || 'Prem: 1041 · Brk: 157 · A: 0'}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="stat-lbl">OI SPURTS</div>
          <div class="stat-val" style="color:var(--pur);">{sessionStats.spurts}</div>
          <div style="font-size:7px;color:var(--t3);">{sessionStats.spurtsSub || '≥15%: 10 stocks'}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="stat-lbl">LONG B/U</div>
          <div class="stat-val" style="color:var(--bull);">{sessionStats.longBull}</div>
          <div style="font-size:7px;color:var(--t3);">{sessionStats.lbSub || 'SC: 19 · LU: 15'}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="stat-lbl">SHORT B/U</div>
          <div class="stat-val" style="color:var(--bear);">{sessionStats.shortBear}</div>
          <div style="font-size:7px;color:var(--t3);">{sessionStats.sbSub || 'Bear Conv.'}</div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .rp { display:flex; flex-direction:column; height:100%; overflow:hidden; }
  .rp-section { border-bottom:1px solid var(--b); }
  .rp-sh { padding:6px 10px; font-size:10px; font-weight:800; letter-spacing:.06em; text-transform:uppercase; display:flex; align-items:center; justify-content:space-between; color:#fff; flex-shrink:0; background:rgba(255,255,255,.015); border-bottom:1px solid rgba(255,255,255,.04); }
  .cbadge { font-size:9.5px; font-weight:700; padding:1.5px 6px; border-radius:10px; background:rgba(56,189,248,.14); color:#38bdf8; border:1px solid rgba(56,189,248,.25); font-family:var(--mono); }
  .rp-body { flex:1; overflow-y:auto; min-height:0; -webkit-overflow-scrolling:touch; }
  .rp-body::-webkit-scrollbar { width:3px; }
  .rp-body::-webkit-scrollbar-thumb { background:var(--b); border-radius:2px; }
  .brk-item { padding:4.5px 8px; border-bottom:1px solid var(--b); cursor:pointer; transition:background .12s; }
  .brk-item:hover { background:rgba(255,255,255,.04); }
  .brk-item:last-child { border-bottom:none; }
  .brk-sym { font-size:10px; font-weight:800; }
  .btag { font-size:7px; font-weight:700; border-radius:3px; padding:1px 4px; text-transform:uppercase; font-family:var(--mono); }
  .btag.b { background:rgba(34,197,94,.16); color:#22c55e; border:1px solid rgba(34,197,94,.3); }
  .btag.r { background:rgba(239,68,68,.16); color:#ef4444; border:1px solid rgba(239,68,68,.3); }
  /* Empty state */
  .empty { text-align:center; padding:16px 8px; }
  .ei { font-size:22px; margin-bottom:4px; }
  .et { font-size:10px; font-weight:700; color:var(--t2); }
  .es { font-size:8.5px; color:var(--t3); margin-top:2px; }
  /* Stats */
  .stat-card { background:var(--card); border:1px solid var(--b); border-radius:6px; padding:4px 3px; }
  .stat-lbl { font-size:7px; color:var(--t2); font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
  .stat-val { font-size:13px; font-weight:800; font-family:var(--mono); line-height:1.15; margin:1px 0; }
  /* Confluence colors */
  .bull { color:var(--bull); }
  .bear { color:var(--bear); }
  .pur  { color:var(--pur); }
  .cyn  { color:var(--cyn); }
  .amb  { color:var(--amb); }
</style>
