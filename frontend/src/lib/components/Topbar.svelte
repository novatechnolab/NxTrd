<script>
  export let title = 'Settings';
  export let onMenuToggle = () => {};

  let wsMode = 'dedicated';
  let isFullscreen = false;

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      isFullscreen = true;
    } else {
      document.exitFullscreen().catch(() => {});
      isFullscreen = false;
    }
  }
</script>

<header class="topbar">
  <div class="topbar-left">
    <!-- Mobile Hamburger Toggle -->
    <button class="mobile-toggle" on:click={onMenuToggle} aria-label="Toggle Menu">
      <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none">
        <path d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <h1 class="page-title">{title}</h1>

    <!-- Live Market Tickers -->
    <div class="market-chips">
      <div class="chip">
        <span class="chip-name">NIFTY</span>
        <span class="chip-price">24,175.65</span>
        <span class="chip-change pos">+0.35%</span>
      </div>

      <div class="chip">
        <span class="chip-name">BANKNIFTY</span>
        <span class="chip-price">57,496.3</span>
        <span class="chip-change neg">-0.02%</span>
      </div>

      <div class="chip">
        <span class="chip-name">INDIA VIX</span>
        <span class="chip-price">10.68</span>
        <span class="vix-badge">LOW</span>
      </div>
    </div>
  </div>

  <div class="topbar-right">
    <!-- WS Dropdown -->
    <div class="ws-select-wrap">
      <select bind:value={wsMode} class="ws-select">
        <option value="dedicated">WS: Dedicated (Real-time)</option>
        <option value="polling">Polling (Fallback)</option>
      </select>
    </div>

    <!-- Fullscreen Action -->
    <button class="action-btn" on:click={toggleFullscreen} title="Toggle Fullscreen" aria-label="Fullscreen">
      <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
        <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
      </svg>
    </button>

    <!-- Notification Bell with Counter -->
    <div class="notification-wrap">
      <button class="action-btn" title="Alerts" aria-label="Notifications">
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      </button>
      <span class="bell-badge">85</span>
    </div>
  </div>
</header>

<style>
  .topbar {
    height: var(--topbar-height);
    background-color: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border-card);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    z-index: 30;
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 0;
  }

  .mobile-toggle {
    display: none;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--text-primary);
    padding: 4px;
  }

  .page-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
  }

  .market-chips {
    display: flex;
    align-items: center;
    gap: 16px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .chip {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    font-family: var(--font-mono);
    white-space: nowrap;
  }

  .chip-name {
    font-weight: 600;
    color: var(--text-muted);
  }

  .chip-price {
    font-weight: 700;
    color: var(--text-primary);
  }

  .chip-change.pos {
    color: #16a34a;
    font-weight: 600;
    background-color: #dcfce7;
    padding: 1px 4px;
    border-radius: 3px;
  }

  .chip-change.neg {
    color: #dc2626;
    font-weight: 600;
    background-color: #fee2e2;
    padding: 1px 4px;
    border-radius: 3px;
  }

  .vix-badge {
    background-color: #dcfce7;
    color: #15803d;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 4px;
  }

  .topbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .ws-select {
    height: 32px;
    padding: 0 10px;
    font-size: 0.76rem;
    font-weight: 500;
    border-radius: 6px;
    border: 1px solid var(--border-card);
    background-color: #ffffff;
    color: var(--text-primary);
    outline: none;
    cursor: pointer;
  }

  .action-btn {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    background-color: #ffffff;
    border: 1px solid var(--border-card);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .action-btn:hover {
    background-color: #f8fafc;
    color: var(--text-primary);
  }

  .notification-wrap {
    position: relative;
  }

  .bell-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    background-color: #dc2626;
    color: #ffffff;
    font-size: 0.6rem;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 10px;
    pointer-events: none;
  }

  @media (max-width: 1024px) {
    .mobile-toggle {
      display: flex;
    }
  }

  @media (max-width: 768px) {
    .market-chips {
      display: none;
    }
  }
</style>
