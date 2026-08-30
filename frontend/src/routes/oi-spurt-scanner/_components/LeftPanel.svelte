<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let spurtData = [];
  export let minPct = 5;
  export let activeTab = null;
  export let oiTimestampMap = {};
  export let lpTimestamp = '–';

  function fmt(n, d = 2) {
    if (n === null || n === undefined) return '–';
    return Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function pclr(v) { return v > 0 ? 'pos' : v < 0 ? 'neg' : 'neu'; }

  $: maxOI = spurtData.length ? Math.max(...spurtData.map(d => d.oi_change_pct), 1) : 1;

  let sliderVal = minPct;

  function onSliderInput(e) {
    sliderVal = Number(e.target.value);
  }
  function onSliderChange(e) {
    dispatch('sliderChange', Number(e.target.value));
  }
</script>

<aside class="left-panel">
  <!-- Header -->
  <div class="lp-header">
    <div class="lp-title">
      🔥 OI Spurt
      <span class="lp-badge">{spurtData.length || '–'}</span>
    </div>
    <div class="lp-filter">
      Min OI%&nbsp;
      <input
        type="range" min="1" max="20" step="1"
        bind:value={sliderVal}
        on:input={onSliderInput}
        on:change={onSliderChange}
      />
      <span class="lp-filter-val">{sliderVal}%</span>
    </div>
    <div class="lp-timer">Auto-refresh 60s &nbsp;|&nbsp; <span>{lpTimestamp}</span></div>
  </div>

  <!-- Stock list -->
  <div class="stock-list">
    {#if spurtData.length === 0}
      <div class="lp-empty">
        <div class="spinner"></div>
        <span>Loading…</span>
      </div>
    {:else}
      {#each spurtData as d, i (d.symbol)}
        {@const isActive = activeTab === d.symbol}
        {@const oiSign = d.oi_change_pct >= 0 ? '+' : ''}
        {@const barW = Math.round((d.oi_change_pct / maxOI) * 100)}
        <div
          class="sl-item"
          class:active={isActive}
          on:click={() => dispatch('select', d.symbol)}
          on:keydown={e => e.key === 'Enter' && dispatch('select', d.symbol)}
          role="button"
          tabindex="0"
        >
          <div class="sl-left">
            <div class="sl-sym">
              {d.symbol}
              <span class="sl-series">{d.series || 'FUT'}</span>
            </div>
            <div class="sl-ltp">LTP: <span class={pclr(d.price_change)}>{fmt(d.ltp)}</span></div>
            <div class="sl-ts">⏱ {d._ts || oiTimestampMap[d.symbol]?.time || '–'}</div>
          </div>
          <div class="sl-right">
            <div class="sl-oichg">{oiSign}{fmt(d.oi_change_pct)}%</div>
            <div class="sl-oilabel">OI Change</div>
          </div>
          <div class="sl-bar" style="width:{barW}%"></div>
        </div>
      {/each}
    {/if}
  </div>
</aside>

<style>
  .left-panel {
    width: 290px;
    flex-shrink: 0;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .lp-header {
    padding: 8px 10px 6px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .lp-title {
    font-family: 'Syne', sans-serif;
    font-size: 9px; font-weight: 700;
    letter-spacing: 2px; color: var(--muted2);
    text-transform: uppercase;
    display: flex; align-items: center; gap: 6px;
  }
  .lp-badge {
    background: var(--accent); color: #000;
    border-radius: 4px; padding: 1px 5px;
    font-size: 9px; font-weight: 700;
  }
  .lp-filter {
    margin-top: 6px; display: flex; align-items: center;
    gap: 5px; font-size: 9px; color: var(--muted2);
  }
  .lp-filter input[type=range] {
    flex: 1; accent-color: var(--accent); height: 3px; cursor: pointer;
  }
  .lp-filter-val { color: var(--accent); font-weight: 700; min-width: 28px; }
  .lp-timer { font-size: 9px; color: var(--muted); margin-top: 4px; }

  .stock-list { flex: 1; overflow-y: auto; }
  .stock-list::-webkit-scrollbar { width: 3px; }
  .stock-list::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  .sl-item {
    display: flex; align-items: center;
    padding: 8px 10px; border-bottom: 1px solid var(--border);
    cursor: pointer; transition: background .12s;
    position: relative; gap: 6px;
  }
  .sl-item:hover { background: var(--surface2); }
  .sl-item.active {
    background: rgba(0,229,255,.07);
    border-left: 2px solid var(--accent);
    padding-left: 8px;
  }
  .sl-left { flex: 1; min-width: 0; }
  .sl-sym {
    font-family: 'Syne', sans-serif; font-weight: 700;
    font-size: 12px; color: var(--text);
  }
  .sl-series {
    font-size: 8px; padding: 1px 3px; border-radius: 3px;
    background: var(--surface3); color: var(--muted2);
    margin-left: 3px; vertical-align: middle;
  }
  .sl-ltp { font-size: 9px; color: var(--muted2); margin-top: 1px; }
  .sl-ts { font-size: 7px; color: rgba(255,255,255,.6); margin-top: 1px; }

  .sl-right { text-align: right; flex-shrink: 0; }
  .sl-oichg {
    font-family: 'Syne', sans-serif; font-weight: 800;
    font-size: 13px; color: var(--green);
  }
  .sl-oilabel { font-size: 8px; color: var(--muted); margin-top: 1px; }

  .sl-bar {
    position: absolute; bottom: 0; left: 0; height: 2px;
    background: linear-gradient(90deg, var(--green), transparent);
    max-width: 100%;
  }

  .lp-empty {
    display: flex; align-items: center; justify-content: center;
    padding: 30px; gap: 8px; color: var(--muted); font-size: 11px;
  }
  .spinner {
    width: 14px; height: 14px; border: 2px solid var(--border);
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin .7s linear infinite; display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  :global(.pos) { color: var(--green); }
  :global(.neg) { color: var(--red); }
  :global(.neu) { color: var(--muted2); }

  @media (max-width: 768px) {
    .left-panel { width: 100%; height: 220px; border-right: none; border-bottom: 1px solid var(--border); }
    .stock-list { display: flex; flex-direction: row; overflow-x: auto; overflow-y: hidden; }
    .sl-item { min-width: 140px; flex-direction: column; align-items: flex-start; padding: 6px 8px; }
    .sl-bar { width: 100% !important; top: auto; }
  }
</style>
