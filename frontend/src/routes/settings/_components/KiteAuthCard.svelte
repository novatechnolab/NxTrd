<script>
  import { kiteState, kiteActions } from '$lib/stores/kite';

  function handleStartLogin() {
    if (!$kiteState.apiKey) {
      kiteState.update(s => ({
        ...s,
        statusMessage: 'Enter API Key first',
        statusType: 'bearish'
      }));
      return;
    }
    localStorage.setItem('ts_api_key', $kiteState.apiKey);
    if ($kiteState.apiSecret) localStorage.setItem('ts_api_secret', $kiteState.apiSecret);
    
    window.location.href = kiteActions.getLoginUrl($kiteState.apiKey);
  }

  function handleConnect() {
    kiteActions.connectDirectly();
  }
</script>

<div class="card settings-group">
  <div class="card-header">
    <h3>🔑 Kite Connect API</h3>
  </div>

  <div class="form-group">
    <label for="set-api-key">API KEY</label>
    <input
      id="set-api-key"
      type="password"
      class="form-input"
      bind:value={$kiteState.apiKey}
      placeholder="••••••••••••••"
      autocomplete="off"
    />
  </div>

  <div class="form-group">
    <label for="set-api-secret">API SECRET</label>
    <input
      id="set-api-secret"
      type="text"
      class="form-input {$kiteState.hasEnvSecret ? 'env-loaded' : ''}"
      bind:value={$kiteState.apiSecret}
      placeholder={$kiteState.hasEnvSecret ? "✓ Loaded from server .env" : "Your Kite API Secret"}
      readonly={$kiteState.hasEnvSecret}
      autocomplete="off"
    />
  </div>

  <div class="form-group">
    <label for="set-access-token">ACCESS TOKEN</label>
    <input
      id="set-access-token"
      type="password"
      class="form-input"
      bind:value={$kiteState.accessToken}
      placeholder="••••••••••••••••••••••••••••"
      autocomplete="off"
    />
  </div>

  <div class="flex gap-12 mt-16">
    <button
      class="btn btn-primary"
      on:click={handleStartLogin}
      disabled={$kiteState.isLoading}
    >
      <span class="btn-icon">🔗</span>
      Start Kite Login
    </button>

    <button
      class="btn btn-primary"
      on:click={handleConnect}
      disabled={$kiteState.isLoading}
    >
      <span class="btn-icon">⚡</span>
      Connect
    </button>
  </div>

  <div class="status-container mt-16">
    {#if $kiteState.isConnected}
      <span class="tag tag-bullish">
        CONNECTED ✓
      </span>
    {:else if $kiteState.statusMessage}
      <span class="tag tag-{$kiteState.statusType}">
        {$kiteState.statusMessage}
      </span>
    {:else}
      <span class="text-muted" style="font-size:0.8rem;">
        Click Start Login to automate session generation
      </span>
    {/if}
  </div>
</div>

<style>
  .settings-group {
    display: flex;
    flex-direction: column;
  }

  .font-mono {
    font-family: var(--font-mono);
    font-size: 0.82rem;
  }

  .env-loaded {
    background-color: #f8fafc;
    color: #475569;
    cursor: default;
    border-color: #e2e8f0;
  }

  .status-container {
    min-height: 24px;
    display: flex;
    align-items: center;
  }

  .btn-icon {
    font-size: 0.95rem;
    margin-right: 4px;
  }
</style>
