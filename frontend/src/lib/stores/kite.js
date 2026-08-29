import { writable } from 'svelte/store';
import { apiFetch } from '../api/client';

export const kiteState = writable({
  apiKey: localStorage.getItem('ts_api_key') || '',
  apiSecret: localStorage.getItem('ts_api_secret') || '',
  accessToken: localStorage.getItem('ts_access_token') || '',
  requestToken: '',
  isConnected: false,
  statusMessage: '',
  statusType: 'neutral', // 'bullish', 'bearish', 'neutral'
  hasEnvSecret: false,
  isLoading: false
});

export const kiteActions = {
  getLoginUrl(apiKey) {
    const key = apiKey || localStorage.getItem('ts_api_key') || '';
    return `https://kite.zerodha.com/connect/login?v=3&api_key=${encodeURIComponent(key)}`;
  },

  async init() {
    try {
      const config = await apiFetch('/api/config');
      
      const loadedKey = config.api_key || localStorage.getItem('ts_api_key') || '';
      if (loadedKey) {
        localStorage.setItem('ts_api_key', loadedKey);
      }

      kiteState.update(s => ({
        ...s,
        apiKey: loadedKey,
        hasEnvSecret: config.has_env_secret,
        accessToken: config.has_access_token ? (localStorage.getItem('ts_access_token') || '••••••••••••••••••••••••••••') : s.accessToken
      }));

      // Check active session status
      const authStatus = await apiFetch('/kite/auth/status');
      if (authStatus.status === 'ok') {
        kiteState.update(s => ({
          ...s,
          isConnected: true,
          statusMessage: 'CONNECTED ✓',
          statusType: 'bullish'
        }));
      } else {
        kiteState.update(s => ({
          ...s,
          isConnected: false,
          statusMessage: '',
          statusType: 'neutral'
        }));
      }
    } catch (e) {
      console.warn('[Kite] Session init fallback:', e);
    }
  },

  async loginWithRequestToken(requestToken) {
    if (!requestToken) return false;
    kiteState.update(s => ({ ...s, isLoading: true, statusMessage: 'Exchanging token with Kite...', statusType: 'neutral' }));
    
    let current;
    kiteState.subscribe(val => current = val)();

    try {
      const res = await apiFetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({
          api_key: current.apiKey,
          api_secret: current.apiSecret,
          request_token: requestToken
        })
      });

      if (res.access_token) {
        localStorage.setItem('ts_access_token', res.access_token);
        if (current.apiKey) localStorage.setItem('ts_api_key', current.apiKey);
        if (current.apiSecret) localStorage.setItem('ts_api_secret', current.apiSecret);

        kiteState.update(s => ({
          ...s,
          accessToken: res.access_token,
          requestToken: requestToken,
          isConnected: true,
          isLoading: false,
          statusMessage: 'CONNECTED ✓',
          statusType: 'bullish'
        }));
        return true;
      }
    } catch (e) {
      kiteState.update(s => ({
        ...s,
        isLoading: false,
        statusMessage: `Login Failed: ${e.message}`,
        statusType: 'bearish'
      }));
      return false;
    }
  },

  async connectDirectly() {
    let current;
    kiteState.subscribe(val => current = val)();

    if (!current.apiKey || (!current.accessToken && !current.hasEnvSecret)) {
      kiteState.update(s => ({
        ...s,
        statusMessage: 'Enter API Key and Access Token',
        statusType: 'bearish'
      }));
      return;
    }

    kiteState.update(s => ({ ...s, isLoading: true, statusMessage: 'Connecting...', statusType: 'neutral' }));

    try {
      await apiFetch('/kite/auth', {
        method: 'POST',
        body: JSON.stringify({
          api_key: current.apiKey,
          access_token: current.accessToken || 'active'
        })
      });

      localStorage.setItem('ts_api_key', current.apiKey);
      if (current.accessToken) localStorage.setItem('ts_access_token', current.accessToken);
      if (current.apiSecret) localStorage.setItem('ts_api_secret', current.apiSecret);

      kiteState.update(s => ({
        ...s,
        isConnected: true,
        isLoading: false,
        statusMessage: 'CONNECTED ✓',
        statusType: 'bullish'
      }));
    } catch (e) {
      kiteState.update(s => ({
        ...s,
        isConnected: false,
        isLoading: false,
        statusMessage: `Failed: ${e.message}`,
        statusType: 'bearish'
      }));
    }
  }
};
