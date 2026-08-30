<script>
  import '../app.css';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Topbar from '$lib/components/Topbar.svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';

  let isMobileSidebarOpen = false;
  let isSidebarHovered = false;
  let hoverTimeout = null;

  const routeTitles = {
    '/settings': 'Settings',
    '/': 'Settings',
    '/live-movers': 'Live Movers',
    '/index-movers': 'Index Movers',
    '/news': 'News',
    '/strategy-builder': 'Strategy Builder',
    '/backtester': 'Backtester',
    '/journal': 'Trading Journal',
    '/paper-trade': 'Paper Trade',
    '/recommendations': 'Recommendations',
    '/reco-tracker': 'Recommendation Tracker',
    '/historical': 'Historical Analysis',
    '/notion-notes': 'Notion Notes',
    '/alerts': 'Live Alerts',
    '/fno-sessions': 'FNO Sessions',
    '/fno-trade-alerts': 'FNO Trade Alerts'
  };

  $: activePath = $page.url.pathname.replace(/\/$/, '') || '/';
  $: is360 = activePath === '/360-command-center' || activePath.startsWith('/360-command-center');
  $: isOI  = activePath === '/oi-spurt-scanner'  || activePath.startsWith('/oi-spurt-scanner');
  $: isFullBleed = is360 || isOI;
  $: activeTitle = routeTitles[activePath] || 'Settings';

  function handleNavigate(id) {
    isMobileSidebarOpen = false;
    isSidebarHovered = false;
    goto(`/${id}`);
  }

  function handleEdgeEnter() {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
      hoverTimeout = null;
    }
    isSidebarHovered = true;
  }

  function handleSidebarEnter() {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
      hoverTimeout = null;
    }
    isSidebarHovered = true;
  }

  function handleSidebarLeave() {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    hoverTimeout = setTimeout(() => {
      isSidebarHovered = false;
    }, 280);
  }
</script>

<div class="app-container" class:is-360={is360}>
  <!-- Sidebar Navigation (Omitted on standalone full-bleed pages) -->
  {#if !isFullBleed}
    <Sidebar
      activeRoute={activePath.replace('/', '') || 'settings'}
      isOpen={isMobileSidebarOpen}
      isAutoHide={false}
      isHoverOpen={false}
      onNavigate={handleNavigate}
      onMouseEnter={handleSidebarEnter}
      onMouseLeave={handleSidebarLeave}
    />
  {/if}

  <!-- Main View Area -->
  <main class="main-content" class:full-bleed={isFullBleed}>
    {#if !isFullBleed}
      <Topbar
        title={activeTitle}
        onMenuToggle={() => (isMobileSidebarOpen = !isMobileSidebarOpen)}
      />
    {/if}

    <div class="page-wrapper {isFullBleed ? 'full-bleed' : ''}">
      <slot />
    </div>
  </main>
</div>

<style>
  .app-container {
    display: flex;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    position: relative;
  }

  .edge-trigger-zone {
    position: fixed;
    top: 0;
    left: 0;
    width: 16px;
    height: 100%;
    z-index: 65;
    background: transparent;
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    overflow: hidden;
  }

  .main-content.full-bleed {
    width: 100%;
    height: 100%;
  }

  .page-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 24px;
    box-sizing: border-box;
  }

  .page-wrapper.full-bleed {
    padding: 0;
    margin: 0;
    max-width: 100%;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }
</style>
