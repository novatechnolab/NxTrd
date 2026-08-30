<script>
  import { kiteState } from '../stores/kite';

  export let activeRoute = 'settings';
  export let isOpen = false;
  export let isAutoHide = false;
  export let isHoverOpen = false;
  export let onNavigate = (id) => {};
  export let onMouseEnter = () => {};
  export let onMouseLeave = () => {};

  const navSections = [
    {
      title: 'MAIN',
      items: [
        { id: 'dashboard',             label: 'Dashboard',             icon: '🏠' },
        { id: 'historical-analysis',   label: 'Historical Analysis',   icon: '📉' },
        { id: 'fno-resanalyzer',       label: 'F&O ResAnalyzer',       icon: '📊', hasChevron: true },
        { id: 'nifty-candle-analyzer', label: 'Nifty Candle Analyzer', icon: '🕯️', hasChevron: true },
        { id: 'multi-chart-tracking',  label: 'Multi-Chart Tracking',  icon: '⬛' },
        { id: 'equity-screener',       label: 'Equity Screener',       icon: '🔍' },
        { id: 'stock-analysis',        label: 'Stock Analysis',        icon: '📐' },
        { id: 'smc-dashboard',         label: 'SMC Dashboard',         icon: '🎯' },
        { id: 'apex-intraday',         label: 'APEX Intraday',         icon: '⚡' },
        { id: 'fno-trap-dashboard',    label: 'FNO Trap Dashboard',    icon: '🚨', hasChevron: true },
        { id: '360-command-center',    label: '360° Command Center',   icon: '🤖', newTab: true },
        { id: 'premium-gainers-board', label: 'Premium Gainers Board', icon: '🏆' },
        { id: 'premium-spike-alerts',  label: 'Premium Spike Alerts',  icon: '🔴', hasChevron: true },
        { id: 'oi-spurt-scanner',      label: 'OI Spurt Scanner',      icon: '🔥', hasChevron: true, newTab: true },
        { id: 'fno-synergy-scanner',   label: 'F&O Synergy Scanner',   icon: '⚡', hasChevron: true },
        { id: 'market-profiler',       label: 'Market Profiler',       icon: '📊' },
        { id: 'watchlist',             label: 'Watchlist',             icon: '⭐' },
        { id: 'portfolio',             label: 'Portfolio',             icon: '💼' },
        { id: 'live-movers',           label: 'Live Movers',           icon: '🔥' },
        { id: 'index-movers',          label: 'Index Movers',          icon: '📊' },
        { id: 'news',                  label: 'News',                  icon: '📰' }
      ]
    },

    {
      title: 'PRO TOOLS',
      items: [
        { id: 'strategy-builder', label: 'Strategy Builder', icon: '🛠️' },
        { id: 'backtester', label: 'Backtester', icon: '📈' },
        { id: 'journal', label: 'Journal', icon: '📓' },
        { id: 'paper-trade', label: 'Paper Trade', icon: '📝' }
      ]
    },
    {
      title: 'ANALYSIS',
      items: [
        { id: 'recommendations', label: 'Recommendations', icon: '🎯', badge: '3' },
        { id: 'reco-tracker', label: 'Reco Tracker', icon: '📊' },
        { id: 'historical', label: 'Historical', icon: '📉' },
        { id: 'notion-notes', label: 'Notion Notes', icon: '📑' },
        { id: 'alerts', label: 'Alerts', icon: '🔔', badge: '85' }
      ]
    },
    {
      title: 'TRADING',
      items: [
        { id: 'fno-sessions', label: 'FNO Sessions', icon: '⏰' },
        { id: 'fno-trade-alerts', label: 'FNO Trade Alerts', icon: '🚨' }
      ]
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'settings', label: 'Settings', icon: '⚙️' }
      ]
    }
  ];

  function navigate(item) {
    if (item.newTab) {
      window.open(`/${item.id}`, '_blank');
    } else {
      onNavigate(item.id);
    }
  }
</script>

<!-- Backdrop on mobile -->
{#if isOpen}
  <div 
    class="sidebar-backdrop" 
    on:click={() => onNavigate(activeRoute, false)}
    role="button" 
    tabindex="0"
    on:keydown={(e) => e.key === 'Escape' && onNavigate(activeRoute, false)}
  ></div>
{/if}

<aside 
  class="sidebar {isOpen ? 'is-open' : ''} {isAutoHide ? 'auto-hide' : ''} {isHoverOpen ? 'hover-open' : ''}"
  on:mouseenter={onMouseEnter}
  on:mouseleave={onMouseLeave}
>
  <!-- Brand Header -->
  <div class="brand">
    <div class="brand-logo">
      <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M3 12h4l3 8 4-16 3 8h4"/>
      </svg>
    </div>
    <div class="brand-text">
      <div class="brand-title">Nxtrd</div>
      <div class="brand-subtitle">NSE F&O INTELLIGENCE</div>
    </div>
  </div>

  <!-- Navigation Items -->
  <nav class="nav-list">
    {#each navSections as section}
      {#if section.title}
        <div class="nav-header">{section.title}</div>
      {/if}
      {#each section.items as item}
        <button
          class="nav-item {activeRoute === item.id ? 'active' : ''}"
          on:click={() => navigate(item)}
        >
          <span class="nav-icon">{item.icon}</span>
          <span class="nav-label">{item.label}</span>
          {#if item.badge !== undefined}
            <span class="nav-badge">{item.badge}</span>
          {/if}
          {#if item.hasChevron}
            <span class="nav-chevron">›</span>
          {/if}
        </button>
      {/each}
    {/each}
  </nav>

  <!-- Bottom Connection Pill -->
  <div class="sidebar-footer">
    <div class="connection-status">
      <span class="status-dot {$kiteState.isConnected ? 'connected' : ''}"></span>
      <span class="status-text">{$kiteState.isConnected ? 'Connected' : 'Disconnected'}</span>
    </div>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    height: 100%;
    background-color: var(--bg-sidebar);
    color: var(--sidebar-text);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    user-select: none;
    z-index: 50;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .sidebar.auto-hide {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 70;
    transform: translateX(-100%);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
  }

  .sidebar.auto-hide.hover-open,
  .sidebar.auto-hide.is-open {
    transform: translateX(0);
  }

  .brand {
    padding: 16px 18px 14px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .brand-logo {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #1e60db, #3b82f6);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
  }

  .brand-icon {
    width: 18px;
    height: 18px;
  }

  .brand-title {
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: #ffffff;
  }

  .brand-subtitle {
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: #60a5fa;
    margin-top: 1px;
  }

  .nav-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 1px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,255,255,0.15) transparent;
  }

  .nav-list::-webkit-scrollbar {
    width: 4px;
  }

  .nav-list::-webkit-scrollbar-track {
    background: transparent;
  }

  .nav-list::-webkit-scrollbar-thumb {
    background-color: rgba(255,255,255,0.15);
    border-radius: 4px;
  }

  .nav-header {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--sidebar-header);
    padding: 14px 10px 4px 10px;
    text-transform: uppercase;
  }

  .nav-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 7px 10px;
    border-radius: 7px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--sidebar-text);
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    width: 100%;
    text-decoration: none;
    box-sizing: border-box;
    transition: all 0.15s ease;
  }

  .nav-item:hover {
    background-color: var(--bg-sidebar-hover);
    color: var(--sidebar-text-bright);
  }

  .nav-item.active {
    background-color: var(--bg-sidebar-active);
    color: #60a5fa;
    font-weight: 600;
    box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.25);
  }

  .nav-icon {
    font-size: 0.9rem;
    width: 18px;
    min-width: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 1px;
    flex-shrink: 0;
  }

  .nav-label {
    flex: 1;
    white-space: normal;
    word-break: break-word;
    line-height: 1.3;
  }

  .nav-chevron {
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.4);
    flex-shrink: 0;
    align-self: center;
    line-height: 1;
  }

  .nav-badge {
    padding: 1px 6px;
    border-radius: 10px;
    background-color: #0284c7;
    color: #ffffff;
    font-size: 0.65rem;
    font-weight: 700;
    flex-shrink: 0;
    align-self: center;
  }

  .sidebar-footer {
    padding: 14px 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    flex-shrink: 0;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    color: #94a3b8;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #64748b;
    transition: background-color 0.2s ease;
  }

  .status-dot.connected {
    background-color: #22c55e;
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
  }

  /* Responsive Drawer styles */
  @media (max-width: 1024px) {
    .sidebar {
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      transform: translateX(-100%);
      box-shadow: 4px 0 20px rgba(0, 0, 0, 0.4);
    }

    .sidebar.is-open {
      transform: translateX(0);
    }

    .sidebar-backdrop {
      position: fixed;
      inset: 0;
      background-color: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(2px);
      z-index: 40;
    }
  }
</style>
