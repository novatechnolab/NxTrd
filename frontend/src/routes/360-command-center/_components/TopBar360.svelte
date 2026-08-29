<script>
  export let clockStr = '--:--:--';
  export let statusText = 'INITIALIZING...';
  export let connectionStatus = 'initializing';
  export let marketQuotes = {};
  export let boardCount = 0;
  export let contractCount = 0;
  export let gainerCount = 0;
  export let theme = 'dark';
  export let onToggleTheme = () => {};

  function getIndexVal(key) {
    const q = marketQuotes[key];
    if (!q) return { v: '--', chg: null };
    const chg = q.change_percent ?? q.pct ?? null;
    return { v: q.last_price ? q.last_price.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--', chg };
  }
  function clsChg(chg) { return chg == null ? '' : chg > 0 ? 'b' : chg < 0 ? 'r' : 'a'; }
  function fmtChg(chg) { if (chg == null) return ''; return (chg > 0 ? '+' : '') + chg.toFixed(2) + '%'; }

  $: nifty = getIndexVal('NIFTY 50');
  $: bnf   = getIndexVal('NIFTY BANK');
  $: vix   = getIndexVal('INDIA VIX');
  $: usdinr = getIndexVal('USD/INR');
</script>

<div class="tb">
  <div class="logo">NX</div>
  <div>
    <div class="brand">Nxtrd</div>
    <div class="brand-s">360° Command v2</div>
  </div>

  <div class="pill {connectionStatus === 'live' ? 'live' : connectionStatus === 'eod' ? 'eod' : 'stale'}">
    <span class="sdot {connectionStatus === 'live' ? 'p' : ''}"></span>
    <span>{statusText}</span>
  </div>

  <div class="mkt">
    <div class="mi">
      <div class="lbl">NIFTY</div>
      <div class="v {clsChg(nifty.chg)}">{nifty.v} <span style="font-size:9px">{fmtChg(nifty.chg)}</span></div>
    </div>
    <div class="mi">
      <div class="lbl">BANKNIFTY</div>
      <div class="v {clsChg(bnf.chg)}">{bnf.v} <span style="font-size:9px">{fmtChg(bnf.chg)}</span></div>
    </div>
    <div class="mi">
      <div class="lbl">VIX</div>
      <div class="v {clsChg(vix.chg)}">{vix.v}</div>
    </div>
    <div class="mi">
      <div class="lbl">USD/INR</div>
      <div class="v {clsChg(usdinr.chg)}">{usdinr.v}</div>
    </div>
  </div>

  <div class="pill live" style="margin-left:4px;">
    <span class="sdot p"></span>
    <span>{boardCount} Stocks · {contractCount} Contracts · {gainerCount} Gainers</span>
  </div>

  <button class="fbtn" on:click={onToggleTheme} style="margin-left:4px;display:flex;align-items:center;gap:4px;font-size:10px;padding:3px 9px;border-radius:14px;cursor:pointer;">
    <span>{theme === 'dark' ? '☀️' : '🌙'}</span>
    <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
  </button>

  <div class="clk">{clockStr}</div>
</div>

<style>
  .tb {
    display:flex; align-items:center; padding:8px 16px;
    background:var(--tb-bg); border-bottom:1px solid var(--b);
    backdrop-filter:blur(12px); position:sticky; top:0; z-index:200;
    gap:14px; height:48px; flex-shrink:0;
    transition:background .2s, border-color .2s;
  }
  .logo {
    width:28px; height:28px; border-radius:7px;
    background:linear-gradient(135deg,#3b82f6,#8b5cf6);
    display:flex; align-items:center; justify-content:center;
    font-size:13px; font-weight:800; color:#fff; flex-shrink:0;
  }
  .brand { font-size:13px; font-weight:700; color:var(--t1); }
  .brand-s { font-size:9px; color:var(--t2); letter-spacing:.07em; text-transform:uppercase; }
  .pill {
    display:flex; align-items:center; gap:5px; padding:4px 10px;
    border-radius:16px; font-size:10px; font-weight:600; border:1px solid;
    white-space:nowrap;
  }
  .pill.live { background:rgba(34,197,94,.08); border-color:rgba(34,197,94,.28); color:var(--bull); }
  .pill.eod  { background:rgba(234,179,8,.08);  border-color:rgba(234,179,8,.28);  color:var(--amb); }
  .pill.stale{ background:rgba(239,68,68,.08);  border-color:rgba(239,68,68,.28);  color:var(--bear);}
  .sdot { width:6px; height:6px; border-radius:50%; background:currentColor; }
  .sdot.p { animation:sdpulse 1.8s ease-in-out infinite; }
  @keyframes sdpulse { 0%,100%{opacity:1} 50%{opacity:.25} }
  .mkt { display:flex; gap:18px; }
  .mi .lbl { font-size:9px; color:var(--t2); text-transform:uppercase; letter-spacing:.05em; }
  .mi .v { font-size:12px; font-weight:700; font-family:var(--mono); }
  .mi .v.b { color:var(--bull); }
  .mi .v.r { color:var(--bear); }
  .mi .v.a { color:var(--amb); }
  .clk { font-family:var(--mono); font-size:12px; font-weight:600; color:var(--acc); white-space:nowrap; margin-left:auto; }
  .fbtn { background:var(--card); border:1px solid var(--b); color:var(--t2); border-radius:5px; font-size:11px; font-weight:600; cursor:pointer; transition:all .14s; }
  .fbtn:hover { background:var(--accg); border-color:var(--acc); color:var(--t1); }
</style>
