<script>
  export let activeMobileCol = 0;
  export let hasNewBoard = false;

  const BTNS = [
    { idx:0, icon:'📊', label:'Board' },
    { idx:1, icon:'⚡', label:'Alerts' },
    { idx:2, icon:'🚀', label:'Panel' },
  ];
</script>

<div class="mobile-nav">
  {#each BTNS as btn}
    <button class="mcn-btn {activeMobileCol===btn.idx?'active':''}" on:click={()=>activeMobileCol=btn.idx} id="mcn-{btn.idx}">
      <span>{btn.icon}</span>
      <span>{btn.label}{btn.idx===0&&hasNewBoard?' 🔴':''}</span>
    </button>
  {/each}
</div>

<style>
  .mobile-nav {
    display:flex; position:fixed; bottom:0; left:0; right:0; z-index:9000;
    background:var(--card2); border-top:1px solid var(--b);
    padding:4px 8px 6px; gap:4px;
    padding-bottom:max(6px, env(safe-area-inset-bottom));
  }
  .mcn-btn {
    flex:1; background:transparent; border:1px solid var(--b); color:var(--t2);
    font-size:10px; font-weight:700; padding:6px 4px; border-radius:6px;
    cursor:pointer; transition:all .15s; min-height:40px; font-family:inherit;
    display:flex; flex-direction:column; align-items:center; gap:2px;
  }
  .mcn-btn.active { background:var(--acc); color:#040916; border-color:var(--acc); }
</style>
