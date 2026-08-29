<script>
  import { settingsState, settingsActions } from '$lib/stores/settings';

  function handleTest() {
    settingsActions.testBackend($settingsState.backendUrl);
  }
</script>

<div class="card settings-group">
  <div class="card-header">
    <h3>🖥️ Backend Server</h3>
  </div>

  <div class="form-group">
    <label for="set-backend-url">BACKEND URL</label>
    <input
      id="set-backend-url"
      type="text"
      class="form-input"
      bind:value={$settingsState.backendUrl}
      placeholder="http://localhost:5000"
    />
  </div>

  <div class="form-group mt-12">
    <span class="label-text">STATUS</span>
    <div class="status-box mt-8">
      <span class="tag tag-{$settingsState.backendStatusType}">
        {$settingsState.backendStatusText}
      </span>
    </div>
  </div>

  <div class="mt-16">
    <button class="btn btn-secondary" on:click={handleTest}>
      🔍 Test Connection
    </button>
  </div>
</div>

<style>
  .settings-group {
    display: flex;
    flex-direction: column;
  }

  .status-box {
    display: flex;
    align-items: center;
    min-height: 28px;
  }
</style>
