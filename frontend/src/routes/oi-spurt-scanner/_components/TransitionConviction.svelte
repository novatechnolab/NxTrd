<script>
  export let tc = null;

  function fmt(n, d = 2) {
    if (n === null || n === undefined) return '–';
    return Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  $: compositeVal = tc?.composite_score ?? 0;
  $: biasText = tc?.bias || 'Neutral';
  $: netDrift = tc?.net_drift || 'Neutral';
  $: pct = Math.min(100, Math.max(0, ((compositeVal + 15) / 30) * 100));
  $: biasColor = compositeVal > 0 ? 'var(--green)' : compositeVal < 0 ? 'var(--red)' : 'var(--muted2)';
  $: driftColor = netDrift.startsWith('Bullish') ? 'var(--green)' : netDrift.startsWith('Bearish') ? 'var(--red)' : netDrift.startsWith('Range') ? 'var(--yellow)' : 'var(--accent)';
  $: atmDetails = tc?.strike_details?.filter(s => s.zone === 'ATM±3') || [];
  $: registryDetails = tc?.strike_details?.filter(s => s.zone === 'ATM±4-7') || [];

  function mapStateToClass(s) {
    if (s === 'LB') return 'badge-lb';
    if (s === 'LU') return 'badge-lu';
    if (s === 'SB') return 'badge-sb';
    if (s === 'SC') return 'badge-sc';
    return 'badge-flat';
  }
  function ceClass(s) { return s === 'LB' || s === 'SC' ? 'pos' : s === 'LU' || s === 'SB' ? 'neg' : 'neu'; }
</script>

{#if tc && tc.strike_details?.length > 0}
  <div class="sec-head">🔄 State Transition Conviction</div>
  <div class="layer-card" style="margin-bottom:7px">
    <div class="layer-title">
      🔄 STATE TRANSITION CONVICTION METER
      <span style="font-size:7.5px;background:rgba(2,132,199,.1);color:var(--accent);border:1px solid rgba(2,132,199,.2);border-radius:3px;padding:1px 4px">ATM±3 Zone</span>
    </div>

    <div class="conv-grid">
      <!-- Left: Gauge -->
      <div>
        <div class="gauge-header">
          <div>
            <div class="composite-score" style="color:{biasColor}">Composite Score: {compositeVal >= 0 ? '+' : ''}{fmt(compositeVal)}</div>
            <div class="gauge-sub">Active Bias: <b style="color:{biasColor}">{biasText}</b></div>
            <div class="gauge-sub">Net Drift: <b style="color:{driftColor}">{netDrift}</b></div>
          </div>
          <div style="text-align:right">
            <div style="font-size:8px;color:var(--muted2)">IV Window check</div>
            <span class="tag {tc.is_event_window ? 'tag-yellow' : 'tag-green'}" style="font-size:7px;padding:1px 4px">
              {tc.is_event_window ? '⚠️ Event Dampened' : '✓ Normal'}
            </span>
          </div>
        </div>

        <!-- Gauge slider -->
        <div class="gauge-wrap">
          <div class="gauge-track"></div>
          <div class="gauge-thumb" style="left:calc({pct}% - 3px)"></div>
        </div>
        <div class="gauge-labels">
          <span>Bearish (-15.0)</span>
          <span>Neutral (0.0)</span>
          <span>Bullish (+15.0)</span>
        </div>

        <!-- Alerts -->
        {#if tc.alerts?.length > 0}
          {#each tc.alerts as a}
            <div class="alert-row">🚨 <b>{a.type.toUpperCase()}:</b> {a.message}</div>
          {/each}
        {:else}
          <div class="no-alerts">No active alerts in this cycle (or under cooldown suppression)</div>
        {/if}
      </div>

      <!-- Right: Wall Strength Registry -->
      <div class="registry">
        <div class="reg-title">🛡️ Wall Strength Registry (ATM±4–7)</div>
        <div class="reg-body">
          {#if registryDetails.length > 0}
            {#each registryDetails as r}
              <div class="reg-row">
                <span><b>Strike {fmt(r.strike, 0)}:</b></span>
                <span>
                  CE:<span class={ceClass(r.ce.to_state)}>{r.ce.to_state}</span> |
                  PE:<span class={ceClass(r.pe.to_state)}>{r.pe.to_state}</span>
                </span>
              </div>
            {/each}
          {:else}
            <div style="color:var(--muted2);font-style:italic;font-size:7.5px">No logged strikes</div>
          {/if}
        </div>
      </div>
    </div>

    <!-- ATM±3 Strikes Table -->
    <table class="mt" style="width:100%;margin-top:4px">
      <thead>
        <tr>
          <th>Strike</th>
          <th>CE Transition (Score)</th>
          <th>PE Transition (Score)</th>
          <th>Composite</th>
          <th>Strength</th>
        </tr>
      </thead>
      <tbody>
        {#each atmDetails as row}
          {@const isATM = row.strike === tc.atm_strike}
          {@const ceScore = row.ce.score}
          {@const peScore = row.pe.score}
          <tr style="{isATM ? 'background:rgba(2,132,199,.06);font-weight:600' : ''}">
            <td>
              <b>{fmt(row.strike, 0)}</b>
              {#if isATM}<span class="atm-pill">ATM</span>{/if}
            </td>
            <td>
              <span class="badge-buildup {mapStateToClass(row.ce.to_state)}" style="font-size:8px;padding:1px 4px">{row.ce.from_state || '–'} → {row.ce.to_state}</span>
              <span style="font-size:8px;color:{ceScore >= 0 ? 'var(--green)' : 'var(--red)'};margin-left:3px">({ceScore >= 0 ? '+' : ''}{ceScore})</span>
            </td>
            <td>
              <span class="badge-buildup {mapStateToClass(row.pe.to_state)}" style="font-size:8px;padding:1px 4px">{row.pe.from_state || '–'} → {row.pe.to_state}</span>
              <span style="font-size:8px;color:{peScore >= 0 ? 'var(--green)' : 'var(--red)'};margin-left:3px">({peScore >= 0 ? '+' : ''}{peScore})</span>
            </td>
            <td style="color:{row.composite >= 0 ? 'var(--green)' : 'var(--red)'};font-weight:700">
              {row.composite >= 0 ? '+' : ''}{fmt(row.composite)}
            </td>
            <td>
              <span class="tag {row.strength === 'High' ? 'tag-red' : row.strength === 'Medium' ? 'tag-yellow' : 'tag-blue'}" style="font-size:7.5px;padding:1px 4px">{row.strength}</span>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .sec-head {
    font-family: 'Syne', sans-serif; font-size: 8px; font-weight: 700;
    letter-spacing: 2px; color: var(--muted2); text-transform: uppercase;
    margin: 8px 0 5px; display: flex; align-items: center; gap: 8px;
  }
  .sec-head::after { content: ''; flex: 1; height: 1px; background: var(--border); }

  .layer-card { background: var(--surface); border: 1px solid var(--border); border-radius: 7px; padding: 10px 12px; }
  .layer-title { font-size: 10px; text-transform: uppercase; color: var(--muted2); font-weight: 700; letter-spacing: .8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }

  .conv-grid { display: grid; grid-template-columns: 1.25fr 0.75fr; gap: 8px; margin-bottom: 5px; }

  .gauge-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .composite-score { font-size: 13px; font-weight: 700; }
  .gauge-sub { font-size: 9px; color: var(--muted2); margin-top: 2px; }

  .gauge-wrap { margin-bottom: 6px; position: relative; height: 12px; }
  .gauge-track {
    height: 5px; position: absolute; top: 3.5px; left: 0; right: 0;
    background: linear-gradient(90deg, var(--red) 0%, #cbd5e1 50%, var(--green) 100%);
    border-radius: 3px;
  }
  .gauge-thumb {
    position: absolute; top: 0; width: 6px; height: 12px;
    background: var(--text); border: 1px solid #fff; border-radius: 2px;
    box-shadow: 0 1px 3px rgba(0,0,0,.25);
  }
  .gauge-labels { display: flex; justify-content: space-between; font-size: 7.5px; color: var(--muted2); margin-bottom: 8px; }

  .alert-row { background: rgba(220,38,38,.1); border: 1px solid rgba(220,38,38,.35); border-radius: 4px; padding: 5px 8px; margin-bottom: 5px; font-size: 9px; color: var(--red); display: flex; align-items: center; gap: 5px; }
  .no-alerts { background: rgba(128,128,128,.06); border: 1px solid rgba(128,128,128,.15); border-radius: 4px; padding: 5px 8px; margin-bottom: 5px; font-size: 8.5px; color: var(--muted2); text-align: center; }

  .registry { background: rgba(128,128,128,.03); border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; }
  .reg-title { font-size: 8px; font-weight: 700; color: var(--muted2); text-transform: uppercase; margin-bottom: 4px; border-bottom: 1px solid rgba(128,128,128,.1); padding-bottom: 2px; }
  .reg-body { max-height: 85px; overflow-y: auto; font-size: 8px; color: var(--text); }
  .reg-row { display: flex; justify-content: space-between; margin-bottom: 3px; padding-bottom: 3px; border-bottom: 1px dashed rgba(128,128,128,.08); }

  .mt { width: 100%; font-size: 10px; border-collapse: collapse; }
  .mt th { font-size: 8px; letter-spacing: .8px; text-transform: uppercase; color: var(--muted2); padding: 3px 5px; text-align: left; border-bottom: 1px solid var(--border); }
  .mt td { padding: 5px 5px; border-bottom: 1px solid rgba(30,42,66,.4); }
  .mt tr:last-child td { border-bottom: none; }
  .mt tr:hover td { background: var(--surface2); }

  .atm-pill { font-size: 7px; background: var(--accent); color: #fff; padding: 1px 3px; border-radius: 2px; margin-left: 3px; }

  .tag { display: inline-flex; align-items: center; padding: 3px 8px; border-radius: 10px; font-size: 9px; font-weight: 600; white-space: nowrap; border: 1px solid; }
  .tag-green { background: rgba(22,163,74,.1); color: var(--green); border-color: rgba(22,163,74,.2); }
  .tag-red { background: rgba(220,38,38,.1); color: var(--red); border-color: rgba(220,38,38,.2); }
  .tag-yellow { background: rgba(217,119,6,.1); color: var(--yellow); border-color: rgba(217,119,6,.2); }
  .tag-blue { background: rgba(2,132,199,.1); color: var(--accent); border-color: rgba(2,132,199,.2); }

  .badge-buildup { display: inline-block; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: .5px; }
  .badge-lb { background: rgba(0,230,118,.15); color: var(--green); border: 1px solid rgba(0,230,118,.3); }
  .badge-sb { background: rgba(255,61,113,.15); color: var(--red); border: 1px solid rgba(255,61,113,.3); }
  .badge-sc { background: rgba(0,229,255,.15); color: var(--accent); border: 1px solid rgba(0,229,255,.3); }
  .badge-lu { background: rgba(255,145,0,.15); color: var(--orange); border: 1px solid rgba(255,145,0,.3); }
  .badge-flat { background: rgba(255,255,255,.08); color: var(--muted); border: 1px solid rgba(255,255,255,.15); }

  :global(.pos) { color: var(--green) !important; }
  :global(.neg) { color: var(--red) !important; }
  :global(.neu) { color: var(--muted2) !important; }
</style>
