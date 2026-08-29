<script>
  import { onMount } from 'svelte';
  import { kiteActions } from '$lib/stores/kite';
  import { settingsActions } from '$lib/stores/settings';
  import KiteAuthCard from './_components/KiteAuthCard.svelte';
  import ScoringParamsCard from './_components/ScoringParamsCard.svelte';
  import BackendStatusCard from './_components/BackendStatusCard.svelte';
  import DataCacheCard from './_components/DataCacheCard.svelte';

  onMount(async () => {
    // 1. Check for Kite redirect URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const requestToken = urlParams.get('request_token');

    if (requestToken) {
      console.log('[Kite] Detected request_token from Zerodha redirect:', requestToken);
      // Clean query params from address bar without reloading
      const cleanUrl = window.location.origin + window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);

      // Perform automatic session generation & connection
      await kiteActions.loginWithRequestToken(requestToken);
    } else {
      // 2. Initialize Kite session state
      await kiteActions.init();
    }

    // 3. Test backend connection
    await settingsActions.testBackend();
  });
</script>

<div class="settings-page">
  <div class="settings-grid grid-2">
    <!-- Card 1: Kite Connect API -->
    <KiteAuthCard />

    <!-- Card 2: Scoring Parameters -->
    <ScoringParamsCard />

    <!-- Card 3: Backend Server -->
    <BackendStatusCard />

    <!-- Card 4: Data Cache -->
    <DataCacheCard />
  </div>
</div>

<style>
  .settings-page {
    width: 100%;
  }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  @media (max-width: 1100px) {
    .settings-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
