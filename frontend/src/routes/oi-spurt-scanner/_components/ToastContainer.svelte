<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let toasts = [];

  function fmt(n, d = 2) {
    if (n === null || n === undefined) return '–';
    return Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
</script>

<div class="toast-container">
  {#each toasts as t (t.id)}
    <div class="toast">
      <span class="toast-sym">{t.sym}</span>
      <span class="toast-body">
        {#each t.parts as p}
          {#if p.type === 'ltp'}
            LTP {fmt(p.old)} <b class={p.dir}>{p.arrow} {fmt(p.new)}</b>
          {:else if p.type === 'pcr'}
            PCR <b>{fmt(p.old, 2)}</b> → <b>{fmt(p.new, 2)}</b>
          {:else if p.type === 'max_pain'}
            MaxPain → <b class="kv-pivot">{fmt(p.new, 0)}</b>
          {/if}
          {#if p !== t.parts[t.parts.length - 1]}&nbsp;·&nbsp;{/if}
        {/each}
      </span>
      <span class="toast-x" on:click={() => dispatch('dismiss', t.id)} role="button" tabindex="0" on:keydown={e => e.key === 'Enter' && dispatch('dismiss', t.id)} aria-label="Dismiss notification">×</span>
      <div class="toast-bar"></div>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed; top: 58px; right: 12px;
    z-index: 9999; display: flex; flex-direction: column;
    gap: 6px; pointer-events: none; width: 310px;
  }
  .toast {
    background: var(--surface, #0f1320);
    border: 1px solid var(--border2, #243050);
    border-radius: 8px; padding: 8px 10px 14px;
    font-size: 10px; display: flex; align-items: flex-start;
    gap: 7px; flex-wrap: wrap; pointer-events: all;
    box-shadow: 0 6px 24px rgba(0,0,0,.6);
    position: relative; overflow: hidden;
    animation: toastIn .22s ease;
  }
  @keyframes toastIn { from { transform: translateX(30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

  .toast-sym { font-family: 'Syne', sans-serif; font-weight: 800; color: #00e5ff; font-size: 11px; white-space: nowrap; }
  .toast-body { color: #e2e8f0; flex: 1; line-height: 1.6; }
  .toast-x { cursor: pointer; color: #6b7a99; font-size: 15px; line-height: 1; margin-left: auto; flex-shrink: 0; transition: color .1s; }
  .toast-x:hover { color: #ff3d71; }
  .toast-bar {
    position: absolute; bottom: 0; left: 0; height: 3px;
    background: #00e5ff; width: 100%;
    animation: toastBarShrink 5s linear forwards;
  }
  @keyframes toastBarShrink { from { width: 100%; } to { width: 0; } }

  :global(.toast .pos) { color: #00e676; }
  :global(.toast .neg) { color: #ff3d71; }
  :global(.toast .kv-pivot) { color: #ffd740; }
</style>
