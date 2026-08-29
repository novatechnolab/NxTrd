import { writable } from 'svelte/store';
import { apiFetch, setBackendUrl } from '../api/client';

export const settingsState = writable({
  scoreThreshold: Number(localStorage.getItem('ts_score_threshold')) || 70,
  maxIvp: Number(localStorage.getItem('ts_max_ivp')) || 50,
  minRr: Number(localStorage.getItem('ts_min_rr')) || 2,
  minOi: Number(localStorage.getItem('ts_min_oi')) || 5000,
  posSize: Number(localStorage.getItem('ts_pos_size')) || 20,
  
  backendUrl: localStorage.getItem('ts_backend_url') || 'http://localhost:5000',
  backendOnline: false,
  backendStatusText: 'Not Tested',
  backendStatusType: 'neutral',
  
  cache: {
    candles: '—',
    instruments: '—',
    tokens: '—',
    dbSize: '—',
    statusMsg: '',
    statusType: 'neutral'
  }
});

export const settingsActions = {
  saveSettings(values) {
    settingsState.update(s => {
      const updated = { ...s, ...values };
      localStorage.setItem('ts_score_threshold', updated.scoreThreshold);
      localStorage.setItem('ts_max_ivp', updated.maxIvp);
      localStorage.setItem('ts_min_rr', updated.minRr);
      localStorage.setItem('ts_min_oi', updated.minOi);
      localStorage.setItem('ts_pos_size', updated.posSize);
      if (updated.backendUrl) {
        localStorage.setItem('ts_backend_url', updated.backendUrl);
        setBackendUrl(updated.backendUrl);
      }
      return updated;
    });
  },

  async testBackend(url) {
    const target = url || localStorage.getItem('ts_backend_url') || window.location.origin;
    settingsState.update(s => ({ ...s, backendStatusText: 'Testing...', backendStatusType: 'neutral' }));
    
    try {
      const res = await apiFetch('/api/health');
      if (res.status === 'healthy' || res.status === 'ok') {
        settingsState.update(s => ({
          ...s,
          backendOnline: true,
          backendStatusText: 'BACKEND ONLINE ✓',
          backendStatusType: 'bullish'
        }));
        await this.refreshCacheStats();
      } else {
        throw new Error('Unhealthy status');
      }
    } catch (e) {
      settingsState.update(s => ({
        ...s,
        backendOnline: false,
        backendStatusText: 'BACKEND OFFLINE',
        backendStatusType: 'bearish'
      }));
    }
  },

  async refreshCacheStats() {
    try {
      const stats = await apiFetch('/api/cache/stats');
      settingsState.update(s => ({
        ...s,
        cache: {
          candles: (stats.ohlcv_candles || 0).toLocaleString(),
          instruments: (stats.instruments || 0).toLocaleString(),
          tokens: (stats.unique_tokens || 0).toLocaleString(),
          dbSize: `${stats.db_size_mb || 0} MB`,
          statusMsg: 'Stats refreshed ✓',
          statusType: 'bullish'
        }
      }));
    } catch (e) {
      settingsState.update(s => ({
        ...s,
        cache: {
          ...s.cache,
          statusMsg: 'Failed to fetch cache stats',
          statusType: 'bearish'
        }
      }));
    }
  },

  async clearCache() {
    if (!confirm('Clear all cached OHLCV data? Next scan will re-fetch from Kite API.')) return;
    try {
      await apiFetch('/api/cache/clear', { method: 'POST' });
      settingsState.update(s => ({
        ...s,
        cache: {
          candles: '0',
          instruments: s.cache.instruments,
          tokens: '0',
          dbSize: '0.0 MB',
          statusMsg: 'Cache cleared ✓',
          statusType: 'bullish'
        }
      }));
    } catch (e) {
      settingsState.update(s => ({
        ...s,
        cache: {
          ...s.cache,
          statusMsg: `Clear failed: ${e.message}`,
          statusType: 'bearish'
        }
      }));
    }
  }
};
