/**
 * TradeSignal NextGen — API Client
 * Centralized fetch helper for FastAPI backend endpoints.
 */

let customBackendUrl = '';

export function setBackendUrl(url) {
  customBackendUrl = (url || '').replace(/\/+$/, '');
}

export function getBackendUrl() {
  return customBackendUrl || window.location.origin;
}

export async function apiFetch(endpoint, options = {}) {
  const base = getBackendUrl();
  const url = endpoint.startsWith('http') ? endpoint : `${base}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers
    });
    
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || `Request failed with status ${res.status}`);
    }
    return data;
  } catch (err) {
    console.error(`[API] Error on ${endpoint}:`, err);
    throw err;
  }
}
