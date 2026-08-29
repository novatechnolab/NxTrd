<script>
  import { onMount } from 'svelte';
  import { settingsState, settingsActions } from '$lib/stores/settings';

  onMount(() => {
    settingsActions.refreshCacheStats();
  });

  function handleRefresh() {
    settingsActions.refreshCacheStats();
  }

  function handleClear() {
    settingsActions.clearCache();
  }
</script>

<div class="card settings-group">
  <div class="card-header">
    <h3>💾 Data Cache</h3>
  </div>

  <p class="cache-desc">
    Historical OHLCV data is cached locally in SQLite for faster access. Only new/recent candles are fetched from Kite API on subsequent scans.
  </p>

  <div class="grid-4 mb-16">
    <div class="stat-card">
      <span class="stat-label">CANDLES CACHED</span>
      <span class="stat-value">{$settingsState.cache.candles}</span>
    </div>

    <div class="stat-card">
      <span class="stat-label">INSTRUMENTS</span>
      <span class="stat-value">{$settingsState.cache.instruments}</span>
    </div>

    <div class="stat-card">
      <span class="stat-label">UNIQUE STOCKS</span>
      <span class="stat-value">{$settingsState.cache.tokens}</span>
    </div>

    <div class="stat-card">
      <span class="stat-label">DB SIZE</span>
      <span class="stat-value">{$settingsState.cache.dbSize}</span>
    </div>
  </div>

  <div class="flex gap-8">
    <button class="btn btn-secondary" on:click={handleRefresh}>
      🔄 Refresh Stats
    </button>
    <button class="btn btn-danger-outline" on:click={handleClear}>
      🗑️ Clear Cache
    </button>
  </div>

  {#if $settingsState.cache.statusMsg}
    <div class="mt-12">
      <span class="tag tag-{$settingsState.cache.statusType}">
        {$settingsState.cache.statusMsg}
      </span>
    </div>
  {/if}
</div>

<style>
  .settings-group {
    display: flex;
    flex-direction: column;
  }

  .cache-desc {
    font-size: 0.78rem;
    line-height: 1.45;
    color: var(--text-secondary);
    margin-bottom: 14px;
  }

  .stat-card {
    background-color: var(--input-bg);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .stat-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--text-muted);
  }

  .stat-value {
    font-size: 1.05rem;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--text-primary);
  }
</style>
