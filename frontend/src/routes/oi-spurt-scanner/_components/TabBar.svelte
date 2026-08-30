<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let watchList = [];
  export let activeTab = null;
</script>

{#if watchList.length > 0}
<div class="tab-bar">
  {#each watchList as sym (sym)}
    <div
      class="tab"
      class:tab-active={sym === activeTab}
      on:click={() => dispatch('switch', sym)}
      on:keydown={e => e.key === 'Enter' && dispatch('switch', sym)}
      role="tab"
      tabindex="0"
    >
      {sym}
      <span
        class="tab-x"
        on:mousedown|stopPropagation={() => dispatch('close', sym)}
        on:keydown|stopPropagation={e => e.key === 'Enter' && dispatch('close', sym)}
        role="button"
        tabindex="0"
        aria-label="Close {sym} tab"
      >×</span>
    </div>
  {/each}
  <span class="tab-hint">Click a symbol to open a tab →</span>
</div>
{/if}

<style>
  .tab-bar {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 14px 0;
    background: var(--surface);
    border-bottom: 2px solid var(--border);
    flex-wrap: wrap;
    min-height: 38px;
  }
  .tab {
    display: flex; align-items: center; gap: 5px;
    padding: 4px 10px;
    border-radius: 6px 6px 0 0;
    font-family: 'Syne', sans-serif;
    font-size: 10px; font-weight: 700;
    cursor: pointer;
    border: 1px solid var(--border);
    border-bottom: none;
    background: var(--surface2);
    color: var(--muted2);
    transition: all .15s;
    white-space: nowrap;
    user-select: none;
    position: relative;
    bottom: -2px;
  }
  .tab:hover { border-color: var(--accent); color: var(--accent); background: var(--surface); }
  .tab.tab-active {
    background: var(--bg);
    color: var(--accent);
    border-color: var(--accent);
    border-bottom-color: var(--bg);
  }
  .tab-x {
    font-size: 14px; line-height: 1;
    color: var(--muted2); cursor: pointer;
    padding: 0 1px; margin-left: 2px;
    border-radius: 3px; transition: color .1s;
  }
  .tab-x:hover { color: var(--red); }
  .tab-hint {
    font-size: 9px; color: var(--muted);
    margin-left: auto; padding-bottom: 4px; white-space: nowrap;
  }
</style>
