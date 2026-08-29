<script>
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Topbar from '$lib/components/Topbar.svelte';
  import SettingsPage from '$routes/settings/SettingsPage.svelte';

  let activeRoute = $state('settings');
  let isMobileSidebarOpen = $state(false);

  const routeTitles = {
    'settings': 'Settings',
    'live-movers': 'Live Movers',
    'index-movers': 'Index Movers',
    'news': 'News',
    'strategy-builder': 'Strategy Builder',
    'backtester': 'Backtester',
    'journal': 'Trading Journal',
    'paper-trade': 'Paper Trade',
    'recommendations': 'Recommendations',
    'reco-tracker': 'Recommendation Tracker',
    'historical': 'Historical Analysis',
    'notion-notes': 'Notion Notes',
    'alerts': 'Live Alerts',
    'fno-sessions': 'FNO Sessions',
    'fno-trade-alerts': 'FNO Trade Alerts'
  };

  function handleNavigate(route) {
    activeRoute = route;
    isMobileSidebarOpen = false;
  }
</script>

<div class="app-container">
  <!-- Sidebar Navigation -->
  <Sidebar
    {activeRoute}
    isOpen={isMobileSidebarOpen}
    onNavigate={handleNavigate}
  />

  <!-- Main View Area -->
  <main class="main-content">
    <Topbar
      title={routeTitles[activeRoute] || 'Dashboard'}
      onMenuToggle={() => (isMobileSidebarOpen = !isMobileSidebarOpen)}
    />

    <div class="page-wrapper">
      {#if activeRoute === 'settings'}
        <SettingsPage />
      {:else}
        <!-- Placeholder for upcoming screens in Phase 2 -->
        <div class="card" style="padding: 40px; text-align: center;">
          <h2 style="margin-bottom: 12px;">{routeTitles[activeRoute] || activeRoute}</h2>
          <p class="text-secondary" style="font-size: 0.9rem;">
            This screen is scheduled for migration in Phase 2. Current active screen is <strong>Settings</strong>.
          </p>
        </div>
      {/if}
    </div>
  </main>
</div>

<style>
  .app-container {
    display: flex;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
  }
</style>
