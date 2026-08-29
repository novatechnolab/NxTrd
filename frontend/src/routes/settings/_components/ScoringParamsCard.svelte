<script>
  import { settingsState, settingsActions } from '$lib/stores/settings';

  let saveSuccess = false;

  function handleSave() {
    settingsActions.saveSettings({
      scoreThreshold: $settingsState.scoreThreshold,
      maxIvp: $settingsState.maxIvp,
      minRr: $settingsState.minRr,
      minOi: $settingsState.minOi,
      posSize: $settingsState.posSize
    });
    saveSuccess = true;
    setTimeout(() => {
      saveSuccess = false;
    }, 2500);
  }
</script>

<div class="card settings-group">
  <div class="card-header">
    <h3>⚙️ Scoring Parameters</h3>
  </div>

  <div class="form-group">
    <label for="set-score-threshold">MINIMUM SCORE THRESHOLD</label>
    <input
      id="set-score-threshold"
      type="number"
      class="form-input"
      bind:value={$settingsState.scoreThreshold}
      min="0"
      max="100"
    />
  </div>

  <div class="form-group">
    <label for="set-max-ivp">MAX IV PERCENTILE (BUY)</label>
    <input
      id="set-max-ivp"
      type="number"
      class="form-input"
      bind:value={$settingsState.maxIvp}
      min="0"
      max="100"
    />
  </div>

  <div class="form-group">
    <label for="set-min-rr">MIN RISK-REWARD RATIO</label>
    <input
      id="set-min-rr"
      type="number"
      step="0.5"
      class="form-input"
      bind:value={$settingsState.minRr}
      min="1"
    />
  </div>

  <div class="form-group">
    <label for="set-min-oi">MIN OI FILTER (CONTRACTS)</label>
    <input
      id="set-min-oi"
      type="number"
      step="500"
      class="form-input"
      bind:value={$settingsState.minOi}
      min="0"
    />
  </div>

  <div class="form-group">
    <label for="set-pos-size">POSITION SIZE % OF CAPITAL</label>
    <input
      id="set-pos-size"
      type="number"
      class="form-input"
      bind:value={$settingsState.posSize}
      min="1"
      max="100"
    />
  </div>

  <div class="flex items-center gap-12 mt-16">
    <button class="btn btn-secondary" on:click={handleSave}>
      💾 Save Settings
    </button>

    {#if saveSuccess}
      <span class="tag tag-bullish">Saved ✓</span>
    {/if}
  </div>
</div>

<style>
  .settings-group {
    display: flex;
    flex-direction: column;
  }
</style>
