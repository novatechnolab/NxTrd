<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let sym = '';
  export let cache = null; // { html: '', open: false, loaded: '0' }

  let loading = false;
  let isOpen = cache?.open || false;
  let bodyHtml = cache?.html || '';
  let loaded = cache?.loaded || '0';

  async function runAnalysis() {
    // Toggle collapse if already loaded
    if (isOpen && loaded === '1') {
      isOpen = false;
      updateCache();
      return;
    }
    // Re-expand if loaded but closed
    if (!isOpen && loaded === '1') {
      isOpen = true;
      updateCache();
      return;
    }

    isOpen = true;
    loading = true;
    bodyHtml = '<div class="ai-spinner">✨ Analyzing heatmap with Gemini AI…</div>';
    loaded = '0';
    updateCache();

    try {
      const res = await fetch(`/api/oi/symbol/${encodeURIComponent(sym)}/ai-analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const json = await res.json();
      if (!json.ok) {
        bodyHtml = `<div class="ai-error">⚠ ${json.error || 'Unknown error'}</div>`;
        loaded = '0';
      } else {
        const md = (json.analysis || '')
          .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          .replace(/^## (.+)$/gm, '<h2>$1</h2>')
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/^- (.+)$/gm, '<li>$1</li>')
          .replace(/(<li>[\s\S]*?<\/li>)+/g, m => `<ul>${m}</ul>`)
          .trim();
        bodyHtml = `<div>${md}</div>`;
        loaded = '1';
      }
    } catch (err) {
      bodyHtml = `<div class="ai-error">⚠ Request failed: ${err.message}</div>`;
      loaded = '0';
    } finally {
      loading = false;
      updateCache();
    }
  }

  function updateCache() {
    dispatch('cacheUpdate', { html: bodyHtml, open: isOpen, loaded });
  }
</script>

<div class="ai-panel">
  <button
    class="ai-btn"
    class:open={isOpen}
    class:loading
    on:click={runAnalysis}
    disabled={loading}
  >
    <span class="ai-btn-left">
      <span>✨</span>
      <span class="ai-label">AI Heatmap Analysis</span>
    </span>
    <span class="ai-chevron">▾</span>
  </button>
  {#if isOpen}
    <div class="ai-body">
      {@html bodyHtml}
    </div>
  {/if}
</div>

<style>
  .ai-panel {
    background: var(--surface);
    border: 1px solid rgba(139,92,246,.35);
    border-radius: 8px;
    overflow: hidden;
  }
  .ai-btn {
    width: 100%; padding: 9px 14px;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    font-family: 'Syne', sans-serif; font-size: 10px; font-weight: 700;
    letter-spacing: .8px; color: #fff; text-transform: uppercase;
    transition: background .2s, opacity .2s;
  }
  .ai-btn:hover { background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%); }
  .ai-btn:disabled { opacity: .6; cursor: not-allowed; }
  .ai-btn-left { display: flex; align-items: center; gap: 6px; }
  .ai-chevron { font-size: 10px; transition: transform .25s; }
  .ai-btn.open .ai-chevron { transform: rotate(180deg); }

  @keyframes ai-pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
  .ai-btn.loading .ai-label::after { content: '…'; animation: ai-pulse 1s infinite; }

  .ai-body {
    padding: 12px 14px; font-size: 10.5px; line-height: 1.65;
    color: var(--text); border-top: 1px solid rgba(139,92,246,.2);
  }
  :global(.ai-body h2) {
    font-family: 'Syne', sans-serif; font-size: 10px; font-weight: 700;
    letter-spacing: .5px; color: var(--accent); margin: 10px 0 4px; text-transform: uppercase;
  }
  :global(.ai-body p) { margin: 3px 0 6px; color: var(--muted2); }
  :global(.ai-body ul) { margin: 3px 0 6px; padding-left: 16px; color: var(--muted2); }
  :global(.ai-body li) { margin-bottom: 2px; }
  :global(.ai-body strong) { color: var(--text); font-weight: 600; }
  :global(.ai-error) { color: var(--red); font-size: 10px; }
  :global(.ai-spinner) { color: var(--muted); font-size: 10px; text-align: center; padding: 8px 0; animation: ai-pulse 1s infinite; }
  @keyframes ai-pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
</style>
