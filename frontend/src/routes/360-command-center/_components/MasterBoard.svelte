<script>
  export let stocks = [];
  export let oiSpurts = [];
  export let boardLoading = false;
  export let boardLoadingMsg = '';
  export let isEodMode = false;
  export let activeFilter = 'all';

  // Board state
  let sortCol = 'score';
  let sortDir = -1;
  let oidockOpen = true;
  let oidockSearch = '';

  // Futures Buildup sub-filter
  let subBuildupFilter = 'all';

  // Expanded option contracts state for PremGain
  let expandedStocks = new Set();
  function toggleStockContracts(sym) {
    if (expandedStocks.has(sym)) expandedStocks.delete(sym);
    else expandedStocks.add(sym);
    expandedStocks = new Set(expandedStocks);
  }

  // Inline Candlestick Chart state for Futures Buildup
  let activeChartStock = null;
  let chartTf = 5;
  let chartViewZoom = {};
  let chartCache = {};

  function calcEMA(data, period) {
    const k = 2 / (period + 1);
    const ema = [];
    let prev = data[0] || 0;
    for (let i = 0; i < data.length; i++) {
      const val = data[i];
      if (i === 0) { ema.push(val); prev = val; }
      else { const cur = val * k + prev * (1 - k); ema.push(cur); prev = cur; }
    }
    return ema;
  }

  function calcVWAP(candles) {
    let cumVol = 0, cumVolPrice = 0;
    const vwap = [];
    for (const c of candles) {
      const typical = (c.high + c.low + c.close) / 3;
      const vol = c.volume || 1;
      cumVol += vol;
      cumVolPrice += typical * vol;
      vwap.push(cumVol > 0 ? cumVolPrice / cumVol : typical);
    }
    return vwap;
  }

  function toggleStockChart(s) {
    const sym = s.sym;
    if (activeChartStock === sym) {
      activeChartStock = null;
    } else {
      activeChartStock = sym;
      const pdhVal = s.pdh, pdlVal = s.pdl;
      let pivVal = null, bcVal = null, tcVal = null;
      if (pdhVal != null && pdlVal != null) {
        const pdc = (s.spotLtp && s.spot) ? (s.spotLtp / (1 + s.spot / 100)) : (s.spotLtp || (pdhVal + pdlVal) / 2);
        pivVal = (pdhVal + pdlVal + pdc) / 3;
        bcVal = (pdhVal + pdlVal) / 2;
        tcVal = 2 * pivVal - bcVal;
        if (tcVal < bcVal) { const tmp = tcVal; tcVal = bcVal; bcVal = tmp; }
      }
      const levels = { pdh: pdhVal, pdl: pdlVal, tc: tcVal, piv: pivVal, bc: bcVal };
      setTimeout(() => loadInlineChart(sym, levels), 40);
    }
  }

  async function loadInlineChart(sym, levels = {}) {
    const canvas = document.getElementById(`ichart-canvas-${sym}`);
    const loadingEl = document.getElementById(`ichart-loading-${sym}`);
    const errorEl = document.getElementById(`ichart-error-${sym}`);
    if (!canvas) return;

    if (errorEl) errorEl.style.display = 'none';
    if (loadingEl) {
      loadingEl.style.display = 'block';
      loadingEl.textContent = '⏳ Loading intraday candle data…';
    }

    const intervalStr = chartTf === 15 ? '15minute' : '5minute';
    const now = new Date();
    const toDate = now.toISOString().split('T')[0];
    const fromDate = new Date(now.getTime() - 10 * 24 * 3600000).toISOString().split('T')[0];

    let candles = [];
    try {
      const res = await fetch(`/api/historical?symbol=${encodeURIComponent(sym)}&interval=${intervalStr}&from=${fromDate}&to=${toDate}`);
      if (res.ok) {
        const json = await res.json();
        candles = (json.candles || []).map(c => ({
          timestamp: new Date(c.date || c.timestamp).getTime(),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
          volume: Number(c.volume || 0)
        })).filter(c => !isNaN(c.timestamp) && !isNaN(c.close));
      }
    } catch (e) {
      console.warn('[Inline Chart] Fetch error for', sym, e);
    }

    if (loadingEl) loadingEl.style.display = 'none';

    // Zero-Mock Policy: Never synthesize or fabricate mock candles
    if (!candles.length) {
      if (errorEl) {
        errorEl.style.display = 'block';
        errorEl.innerHTML = `⚠️ No historical candle data available for <strong>${sym}</strong>. Check backend connection or active Kite session.`;
      }
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    const fullCloses = candles.map(c => c.close);
    const ema9 = calcEMA(fullCloses, 9);
    const ema21 = calcEMA(fullCloses, 21);
    const vwap = calcVWAP(candles);

    chartCache[sym] = { candles, ema9, ema21, vwap, levels, tf: chartTf };
    drawCandles(sym, canvas, null);
    attachMouse(sym, canvas);
  }

  function drawCandles(sym, canvas, hoverPos = null) {
    const data = chartCache[sym];
    if (!canvas || !data || !data.candles || !data.candles.length) return;
    const { candles, ema9, ema21, vwap, levels } = data;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || 800;
    const height = 380;

    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    const pl = 14, pr = 78, pt = 42, pb = 26;
    const cw = width - pl - pr, ch = height - pt - pb;

    const total = candles.length;
    const visibleCount = Math.min(total, chartViewZoom[sym] || 75);
    const startIdx = Math.max(0, total - visibleCount);
    const visibleCandles = candles.slice(startIdx);
    const n = visibleCandles.length;

    let minP = Infinity, maxP = -Infinity;
    visibleCandles.forEach(c => {
      if (c.low < minP) minP = c.low;
      if (c.high > maxP) maxP = c.high;
    });
    for (let i = startIdx; i < total; i++) {
      if (ema9[i] && ema9[i] < minP) minP = ema9[i];
      if (ema9[i] && ema9[i] > maxP) maxP = ema9[i];
      if (ema21[i] && ema21[i] < minP) minP = ema21[i];
      if (ema21[i] && ema21[i] > maxP) maxP = ema21[i];
      if (vwap[i] && vwap[i] < minP) minP = vwap[i];
      if (vwap[i] && vwap[i] > maxP) maxP = vwap[i];
    }
    [levels.pdh, levels.pdl, levels.tc, levels.piv, levels.bc].forEach(lvl => {
      if (lvl != null && Number.isFinite(lvl)) {
        if (lvl < minP) minP = lvl;
        if (lvl > maxP) maxP = lvl;
      }
    });
    const pRange = Math.max(1, maxP - minP);
    minP -= pRange * 0.03;
    maxP += pRange * 0.03;
    const effRange = maxP - minP;

    const getY = p => pt + ch * (1 - (p - minP) / effRange);
    const getX = i => pl + (i + 0.5) * (cw / n);
    const candleW = Math.max(2.5, Math.min(24, (cw / n) * 0.7));

    // Info header
    let infoIdx = total - 1;
    if (hoverPos && hoverPos.x >= pl && hoverPos.x <= width - pr && hoverPos.y >= pt && hoverPos.y <= pt + ch) {
      const lIdx = Math.floor(((hoverPos.x - pl) / cw) * n);
      infoIdx = startIdx + Math.max(0, Math.min(n - 1, lIdx));
    }
    const ic = candles[infoIdx] || candles[total - 1];
    const icChg = ic.close - ic.open;
    const icChgPct = (icChg / Math.max(0.01, ic.open)) * 100;
    const icColor = icChg >= 0 ? '#16a34a' : '#dc2626';

    ctx.font = 'bold 10px Inter,sans-serif';
    ctx.fillStyle = '#1e293b';
    let curX = pl;
    const hTxt = `${sym} · ${data.tf || 5}m   `;
    ctx.fillText(hTxt, curX, 13);
    curX += ctx.measureText(hTxt).width;

    const ohlc = [
      { l: 'O:', v: ic.open.toFixed(2), c: '#64748b' },
      { l: 'H:', v: ic.high.toFixed(2), c: '#16a34a' },
      { l: 'L:', v: ic.low.toFixed(2), c: '#dc2626' },
      { l: 'C:', v: ic.close.toFixed(2), c: icColor },
    ];
    for (const o of ohlc) {
      ctx.font = '9px Inter,sans-serif'; ctx.fillStyle = '#94a3b8';
      ctx.fillText(o.l, curX, 13); curX += ctx.measureText(o.l).width + 1;
      ctx.font = 'bold 10px Inter,sans-serif'; ctx.fillStyle = o.c;
      ctx.fillText(o.v + '  ', curX, 13); curX += ctx.measureText(o.v + '  ').width;
    }
    ctx.font = 'bold 10px Inter,sans-serif'; ctx.fillStyle = icColor;
    const chgTxt = `${icChg >= 0 ? '+' : ''}${icChg.toFixed(2)} (${icChgPct >= 0 ? '+' : ''}${icChgPct.toFixed(2)}%)`;
    ctx.fillText(chgTxt, curX, 13); curX += ctx.measureText(chgTxt).width + 8;
    ctx.font = '9px Inter,sans-serif'; ctx.fillStyle = '#94a3b8';
    ctx.fillText('Vol:', curX, 13); curX += ctx.measureText('Vol:').width + 2;
    ctx.font = 'bold 9.5px Inter,sans-serif'; ctx.fillStyle = '#475569';
    ctx.fillText(String(ic.volume || 0), curX, 13);

    // Indicator line 2
    let curX2 = pl;
    const indList = [
      { l: 'EMA9', v: ema9[infoIdx]?.toFixed(2) || '—', c: '#2563eb' },
      { l: 'EMA21', v: ema21[infoIdx]?.toFixed(2) || '—', c: '#dc2626' },
      { l: 'VWAP', v: vwap[infoIdx]?.toFixed(2) || '—', c: '#16a34a' },
    ];
    for (const ind of indList) {
      ctx.font = '9px Inter,sans-serif'; ctx.fillStyle = '#94a3b8';
      ctx.fillText(ind.l + ': ', curX2, 28); curX2 += ctx.measureText(ind.l + ': ').width;
      ctx.font = 'bold 9px Inter,sans-serif'; ctx.fillStyle = ind.c;
      ctx.fillText(ind.v + '    ', curX2, 28); curX2 += ctx.measureText(ind.v + '    ').width;
    }

    // Grid ticks
    ctx.lineWidth = 1; ctx.font = '10px monospace'; ctx.fillStyle = '#475569';
    for (let i = 0; i <= 6; i++) {
      const p = minP + (effRange / 6) * i;
      const y = getY(p);
      ctx.strokeStyle = 'rgba(0,0,0,0.07)'; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(pl, y); ctx.lineTo(width - pr, y); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = '#475569';
      ctx.fillText('₹' + (p >= 100 ? p.toFixed(1) : p.toFixed(2)), width - pr + 8, y + 3.5);
    }

    // Time ticks
    const step = Math.max(1, Math.floor(n / 6));
    for (let i = 0; i < n; i += step) {
      const gIdx = startIdx + i;
      const x = getX(i);
      const d = new Date(candles[gIdx].timestamp);
      const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
      ctx.strokeStyle = 'rgba(0,0,0,0.05)'; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(x, pt); ctx.lineTo(x, pt + ch); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = '#475569';
      ctx.fillText(timeStr, x - 14, height - 8);
    }

    // Volume histogram
    const maxV = Math.max(...visibleCandles.map(c => c.volume || 1), 1);
    visibleCandles.forEach((c, i) => {
      const x = getX(i);
      const vH = ((c.volume || 0) / maxV) * (ch * 0.22);
      ctx.fillStyle = c.close >= c.open ? 'rgba(22,163,74,0.22)' : 'rgba(220,38,38,0.22)';
      ctx.fillRect(x - candleW / 2, pt + ch - vH, candleW, vH);
    });

    // CPR Levels
    const drawLvl = (val, label, color) => {
      if (val == null || !Number.isFinite(val)) return;
      const y = getY(val);
      if (y < pt - 5 || y > pt + ch + 5) return;
      ctx.strokeStyle = color; ctx.setLineDash([5, 4]); ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(pl, y); ctx.lineTo(width - pr, y); ctx.stroke();
      ctx.setLineDash([]);
      const txt = `${label} ₹${val >= 100 ? val.toFixed(1) : val.toFixed(2)}`;
      ctx.font = 'bold 9px monospace';
      const tw = ctx.measureText(txt).width;
      ctx.fillStyle = '#ffffff'; ctx.fillRect(width - pr + 4, y - 8, tw + 8, 16);
      ctx.strokeStyle = color; ctx.strokeRect(width - pr + 4, y - 8, tw + 8, 16);
      ctx.fillStyle = color; ctx.fillText(txt, width - pr + 8, y + 3.5);
    };
    drawLvl(levels.pdh, 'PDH', '#16a34a');
    drawLvl(levels.pdl, 'PDL', '#dc2626');
    drawLvl(levels.tc, 'TC', '#9333ea');
    drawLvl(levels.piv, 'PIV', '#0284c7');
    drawLvl(levels.bc, 'BC', '#4f46e5');

    // Indicators
    const drawLine = (series, color) => {
      if (!series || !series.length) return;
      ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.setLineDash([]); ctx.beginPath();
      let started = false;
      for (let i = 0; i < n; i++) {
        const gIdx = startIdx + i;
        const v = series[gIdx]; if (v == null || !Number.isFinite(v)) continue;
        const x = getX(i), y = getY(v);
        if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
      }
      ctx.stroke();
    };
    drawLine(ema9, '#2563eb');
    drawLine(ema21, '#dc2626');
    drawLine(vwap, '#16a34a');

    // Candlesticks
    visibleCandles.forEach((c, i) => {
      const x = getX(i), yO = getY(c.open), yC = getY(c.close), yH = getY(c.high), yL = getY(c.low);
      const isUp = c.close >= c.open;
      const col = isUp ? '#16a34a' : '#dc2626';
      ctx.strokeStyle = col; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, yH); ctx.lineTo(x, yL); ctx.stroke();
      const topY = Math.min(yO, yC), bodyH = Math.max(1.5, Math.abs(yC - yO));
      ctx.fillStyle = col; ctx.fillRect(x - candleW / 2, topY, candleW, bodyH);
    });

    // Crosshair
    if (hoverPos && hoverPos.x >= pl && hoverPos.x <= width - pr && hoverPos.y >= pt && hoverPos.y <= pt + ch) {
      const lIdx = Math.floor(((hoverPos.x - pl) / cw) * n);
      const clIdx = Math.max(0, Math.min(n - 1, lIdx));
      const hx = getX(clIdx), hy = hoverPos.y;
      ctx.strokeStyle = 'rgba(0,0,0,0.28)'; ctx.lineWidth = 0.8; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(hx, pt); ctx.lineTo(hx, pt + ch); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pl, hy); ctx.lineTo(width - pr, hy); ctx.stroke();
      ctx.setLineDash([]);
      const hoverPrice = minP + (1 - (hy - pt) / ch) * effRange;
      const pLbl = '₹' + hoverPrice.toFixed(2);
      ctx.fillStyle = '#0f172a'; ctx.fillRect(width - pr + 4, hy - 8, 68, 16);
      ctx.fillStyle = '#ffffff'; ctx.font = 'bold 9px monospace'; ctx.fillText(pLbl, width - pr + 8, hy + 3.5);
    }
    ctx.restore();
  }

  function attachMouse(sym, canvas) {
    if (!canvas) return;
    canvas.onmousemove = (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      drawCandles(sym, canvas, { x, y });
    };
    canvas.onmouseleave = () => {
      drawCandles(sym, canvas, null);
    };
  }

  function switchChartTf(sym, tf) {
    chartTf = tf;
    const s = stocks.find(st=>st.sym===sym);
    if (s) toggleStockChart(s);
  }
  function zoomChart(sym, delta) {
    const cur = chartViewZoom[sym] || 75;
    chartViewZoom[sym] = Math.max(15, Math.min(150, cur + delta * 15));
    const canvas = document.getElementById(`ichart-canvas-${sym}`);
    if (canvas) drawCandles(sym, canvas);
  }
  function resetChartZoom(sym) {
    chartViewZoom[sym] = 75;
    const canvas = document.getElementById(`ichart-canvas-${sym}`);
    if (canvas) drawCandles(sym, canvas);
  }

  // Max Pain state
  let maxpainData = [];
  let maxpainCounts = { strong_up: 0, strong_down: 0, high_achieve: 0, total: 0 };
  let maxpainMedianPcr = 0;
  let maxpainFetchedAt = '';
  let maxpainLoading = false;
  let subPainFilter = 'ALL';

  // Watchlist state (localStorage)
  let wlSymbols = JSON.parse(typeof localStorage !== 'undefined' ? (localStorage.getItem('ts_watchlist') || '[]') : '[]');
  let wlSearch = '';
  let wlSortCol = 'score';
  let wlSortDir = -1;
  let wlSuggestions = [];

  // NSE Heatmap state
  let selectedSector = null;
  let sectorBuildupFilter = 'all';
  let secSortCol = 'spot';
  let secSortDir = -1;

  const NSE_SECTOR_LIST = [
    { name:'NIFTY AUTO', key:'AUTO' }, { name:'NIFTY BANK', key:'BANK' },
    { name:'NIFTY FIN SERVICE', key:'FINSERV' }, { name:'NIFTY FINSRV25/50', key:'FIN2550' },
    { name:'NIFTY FMCG', key:'FMCG' }, { name:'NIFTY IT', key:'IT' },
    { name:'NIFTY MEDIA', key:'MEDIA' }, { name:'NIFTY METAL', key:'METAL' },
    { name:'NIFTY PHARMA', key:'PHARMA' }, { name:'NIFTY PSU BANK', key:'PSUBANK' },
    { name:'NIFTY REALTY', key:'REALTY' }, { name:'NIFTY PVT BANK', key:'PVTBANK' },
    { name:'NIFTY HEALTHCARE', key:'HEALTHCARE' }, { name:'NIFTY CONSR DURBL', key:'CONSRDURBL' },
    { name:'NIFTY OIL AND GAS', key:'OILGAS' }, { name:'NIFTY MIDSML HLTH', key:'MIDSMHEALTH' },
    { name:'NIFTY CHEMICALS', key:'CHEMICALS' }, { name:'NIFTY500 HEALTHCARE', key:'N500HEALTH' },
    { name:'NIFTY FINSEREXBNK', key:'FINEXBANK' }, { name:'NIFTY MS FIN SERV', key:'MSFINSERV' },
    { name:'NIFTY MS IT TELCOM', key:'MSITTEL' }, { name:'NIFTY CEMENT', key:'CEMENT' },
    { name:'NIFTY REITS REALTY', key:'REITSREALTY' },
  ];

  const NSE_STOCK_SECTOR_MAP = {
    // AUTO
    'BAJAJ-AUTO':'NIFTY AUTO','MARUTI':'NIFTY AUTO','M&M':'NIFTY AUTO','TATAMOTORS':'NIFTY AUTO',
    'EICHERMOT':'NIFTY AUTO','HEROMOTOCO':'NIFTY AUTO','TVSMOTOR':'NIFTY AUTO','BHARATFORG':'NIFTY AUTO',
    'ASHOKLEY':'NIFTY AUTO','BALKRISIND':'NIFTY AUTO','MRF':'NIFTY AUTO','APOLLOTYRE':'NIFTY AUTO',
    'EXIDEIND':'NIFTY AUTO','MOTHERSON':'NIFTY AUTO','BOSCHLTD':'NIFTY AUTO','TIINDIA':'NIFTY AUTO',
    'ESCORTS':'NIFTY AUTO',

    // BANK & PVT BANK
    'HDFCBANK':'NIFTY BANK','ICICIBANK':'NIFTY BANK','KOTAKBANK':'NIFTY BANK','AXISBANK':'NIFTY BANK',
    'INDUSINDBK':'NIFTY BANK','FEDERALBNK':'NIFTY BANK','IDFCFIRSTB':'NIFTY BANK','BANDHANBNK':'NIFTY BANK',
    'AUBANK':'NIFTY BANK','RBLBANK':'NIFTY BANK',

    // PSU BANK
    'SBIN':'NIFTY PSU BANK','BANKBARODA':'NIFTY PSU BANK','PNB':'NIFTY PSU BANK','CANBK':'NIFTY PSU BANK',
    'UNIONBANK':'NIFTY PSU BANK','INDIANB':'NIFTY PSU BANK',

    // FIN SERVICE / MS FIN SERV / FINSRV25/50
    'BAJFINANCE':'NIFTY FIN SERVICE','BAJAJFINSV':'NIFTY FIN SERVICE','CHOLAFIN':'NIFTY FIN SERVICE',
    'SHRIRAMFIN':'NIFTY FIN SERVICE','MUTHOOTFIN':'NIFTY FIN SERVICE','M&MFIN':'NIFTY FIN SERVICE',
    'MANAPPURAM':'NIFTY FIN SERVICE','POONAWALLA':'NIFTY FIN SERVICE','LICHSGFIN':'NIFTY FIN SERVICE',
    'LICIHSGFIN':'NIFTY FIN SERVICE','PNBHOUSING':'NIFTY FIN SERVICE','HDFCLIFE':'NIFTY FIN SERVICE',
    'SBILIFE':'NIFTY FIN SERVICE','ICICIPRULI':'NIFTY FIN SERVICE','LICI':'NIFTY FIN SERVICE',
    'HDFCAMC':'NIFTY FIN SERVICE','NAM-INDIA':'NIFTY FIN SERVICE','UTIAMC':'NIFTY FIN SERVICE',
    'CAMS':'NIFTY FIN SERVICE','KFINTECH':'NIFTY FIN SERVICE','BSE':'NIFTY FIN SERVICE',
    'MCX':'NIFTY FIN SERVICE','CDSL':'NIFTY FIN SERVICE','IEX':'NIFTY FIN SERVICE',
    'JIOFIN':'NIFTY FIN SERVICE','PFC':'NIFTY FIN SERVICE','RECLTD':'NIFTY FIN SERVICE',
    'ABCAPITAL':'NIFTY FIN SERVICE','L&TFH':'NIFTY FIN SERVICE','PAYTM':'NIFTY FIN SERVICE',
    'POLICYBZR':'NIFTY FIN SERVICE',

    // FMCG
    'ITC':'NIFTY FMCG','HINDUNILVR':'NIFTY FMCG','NESTLEIND':'NIFTY FMCG','BRITANNIA':'NIFTY FMCG',
    'TATACONSUM':'NIFTY FMCG','DABUR':'NIFTY FMCG','GODREJCP':'NIFTY FMCG','MARICO':'NIFTY FMCG',
    'COLPAL':'NIFTY FMCG','UBL':'NIFTY FMCG','UNITDSPR':'NIFTY FMCG','RADICO':'NIFTY FMCG',
    'JUBLFOOD':'NIFTY FMCG','DEVYANI':'NIFTY FMCG','PAGEIND':'NIFTY FMCG',

    // IT & MS IT TELCOM
    'TCS':'NIFTY IT','INFY':'NIFTY IT','HCLTECH':'NIFTY IT','WIPRO':'NIFTY IT','TECHM':'NIFTY IT',
    'LTIM':'NIFTY IT','PERSISTENT':'NIFTY IT','COFORGE':'NIFTY IT','MPHASIS':'NIFTY IT',
    'LTTS':'NIFTY IT','TATAELXSI':'NIFTY IT','OFSS':'NIFTY IT','KPITTECH':'NIFTY IT','CYIENT':'NIFTY IT',
    'NAUKRI':'NIFTY IT',

    // METAL
    'TATASTEEL':'NIFTY METAL','JSWSTEEL':'NIFTY METAL','HINDALCO':'NIFTY METAL','VEDL':'NIFTY METAL',
    'JINDALSTEL':'NIFTY METAL','SAIL':'NIFTY METAL','NMDC':'NIFTY METAL','NATIONALUM':'NIFTY METAL',
    'HINDCOPPER':'NIFTY METAL','HINDZINC':'NIFTY METAL','APLAPOLLO':'NIFTY METAL',

    // PHARMA & HEALTHCARE & MIDSML HLTH
    'SUNPHARMA':'NIFTY PHARMA','DRREDDY':'NIFTY PHARMA','CIPLA':'NIFTY PHARMA','DIVISLAB':'NIFTY PHARMA',
    'AUROPHARMA':'NIFTY PHARMA','LUPIN':'NIFTY PHARMA','ZYDUSLIFE':'NIFTY PHARMA','ALKEM':'NIFTY PHARMA',
    'TORNTPHARM':'NIFTY PHARMA','IPCALAB':'NIFTY PHARMA','BIOCON':'NIFTY PHARMA','GLENMARK':'NIFTY PHARMA',
    'LAURUSLABS':'NIFTY PHARMA','GRANULES':'NIFTY PHARMA','APOLLOHOSP':'NIFTY HEALTHCARE',
    'MAXHEALTH':'NIFTY HEALTHCARE','FORTIS':'NIFTY HEALTHCARE','METROPOLIS':'NIFTY HEALTHCARE',
    'LALPATHLAB':'NIFTY HEALTHCARE','SYNGENE':'NIFTY HEALTHCARE','GLAND':'NIFTY HEALTHCARE',

    // REALTY & REITS REALTY
    'DLF':'NIFTY REALTY','GODREJPROP':'NIFTY REALTY','OBEROIRLTY':'NIFTY REALTY','PHOENIXLTD':'NIFTY REALTY',
    'PRESTIGE':'NIFTY REALTY','BRIGADE':'NIFTY REALTY','SOBHA':'NIFTY REALTY','LODHA':'NIFTY REALTY',
    'SUNTECK':'NIFTY REALTY',

    // OIL AND GAS
    'RELIANCE':'NIFTY OIL AND GAS','ONGC':'NIFTY OIL AND GAS','IOC':'NIFTY OIL AND GAS',
    'BPCL':'NIFTY OIL AND GAS','HINDPETRO':'NIFTY OIL AND GAS','GAIL':'NIFTY OIL AND GAS',
    'OIL':'NIFTY OIL AND GAS','PETRONET':'NIFTY OIL AND GAS','GUJGASLTD':'NIFTY OIL AND GAS',
    'IGL':'NIFTY OIL AND GAS','MGL':'NIFTY OIL AND GAS','GSPL':'NIFTY OIL AND GAS',

    // CONSR DURBL
    'TITAN':'NIFTY CONSR DURBL','HAVELLS':'NIFTY CONSR DURBL','VOLTAS':'NIFTY CONSR DURBL',
    'DIXON':'NIFTY CONSR DURBL','CROMPTON':'NIFTY CONSR DURBL','BLUESTARCO':'NIFTY CONSR DURBL',
    'WHIRLPOOL':'NIFTY CONSR DURBL','KAYNES':'NIFTY CONSR DURBL','AMBER':'NIFTY CONSR DURBL',
    'BATAINDIA':'NIFTY CONSR DURBL','RELAXO':'NIFTY CONSR DURBL','KALYANKJIL':'NIFTY CONSR DURBL',
    'VGUARD':'NIFTY CONSR DURBL',

    // CHEMICALS
    'PIDILITIND':'NIFTY CHEMICALS','SRF':'NIFTY CHEMICALS','PIIND':'NIFTY CHEMICALS',
    'AARTIIND':'NIFTY CHEMICALS','DEEPAKNTR':'NIFTY CHEMICALS','TATACHEM':'NIFTY CHEMICALS',
    'NAVINFLUOR':'NIFTY CHEMICALS','ATUL':'NIFTY CHEMICALS','COROMANDEL':'NIFTY CHEMICALS',
    'UPL':'NIFTY CHEMICALS','LINDE':'NIFTY CHEMICALS','AAVAS':'NIFTY CHEMICALS',

    // CEMENT
    'ULTRACEMCO':'NIFTY CEMENT','GRASIM':'NIFTY CEMENT','AMBUJACEM':'NIFTY CEMENT',
    'ACC':'NIFTY CEMENT','DALBHARAT':'NIFTY CEMENT','RAMCOCEM':'NIFTY CEMENT',
    'SHREECEM':'NIFTY CEMENT','JKCEMENT':'NIFTY CEMENT','HEIDELBERG':'NIFTY CEMENT',
    'DALMIACEM':'NIFTY CEMENT',

    // MEDIA
    'PVRINOX':'NIFTY MEDIA','ZEEL':'NIFTY MEDIA','SUNTV':'NIFTY MEDIA',
    'BHARTIARTL':'NIFTY MEDIA','IDEA':'NIFTY MEDIA',
  };

  const FILTERS = [
    { key:'all',       label:'🔥 PremGain' },
    { key:'futbld',    label:'📈 Futures Buildup' },
    { key:'heatmap',   label:'🗺️ NSE Heatmap' },
    { key:'bull',      label:'🟢 Bullish ≥4' },
    { key:'bear',      label:'🔴 Bearish ≥4' },
    { key:'oi',        label:'⚡ OI≥5%' },
    { key:'prem',      label:'🔥 Gain≥100%' },
    { key:'aligned',   label:'✅ TF Aligned' },
    { key:'maxpain',   label:'🎯 Max Pain Dev' },
    { key:'watchlist', label:'📋 Watch List' },
  ];

  // ── Helpers ────────────────────────────────────────────────────────────────
  function rowDir(s) {
    const b = (s.conf||[]).filter(c=>c==='b').length;
    const r = (s.conf||[]).filter(c=>c==='r').length;
    return b > r ? 'BR' : r > b ? 'BE' : 'NE';
  }
  function rowGlow(s) {
    const sc = s.score; const d = rowDir(s);
    if (sc>=8 && d==='BR') return 'glow-hi';
    if (sc>=8 && d==='BE') return 'glow-bear-hi';
    if (sc>=5) return 'glow-med';
    return '';
  }
  function gradeClass(sc) { return sc>=8?'sc-hi':sc>=5?'sc-me':'sc-lo'; }
  function capClass(cap) { return cap==='L'?'cap-l':cap==='M'?'cap-m':'cap-s'; }
  function futClass(bu) {
    if (bu==='LB') return 'fb-lb'; if (bu==='SB') return 'fb-sb';
    if (bu==='SC') return 'fb-sc'; if (bu==='LU') return 'fb-lu';
    return 'fb-no';
  }
  function tfClass(v) { return v==='b'?'B':v==='r'?'R':'N'; }

  // ── Filtered + sorted board rows ───────────────────────────────────────────
  function getFiltered(stockList = stocks, filter = activeFilter, subB = subBuildupFilter, sc = sortCol, sd = sortDir) {
    let rows = [...(stockList || [])];
    if (filter === 'all') {
      // PremGain displays all loaded board stocks
    }
    else if (filter === 'futbld') {
      if (subB==='LB') rows = rows.filter(s=>s.futBU==='LB');
      else if (subB==='SB') rows = rows.filter(s=>s.futBU==='SB');
      else if (subB==='SC') rows = rows.filter(s=>s.futBU==='SC');
      else if (subB==='LU') rows = rows.filter(s=>s.futBU==='LU');
      else if (subB==='FLAT') rows = rows.filter(s=>!s.futBU||s.futBU==='—'||s.futBU==='FLAT');
    }
    else if (filter==='bull')    rows = rows.filter(s=>(s.conf||[]).filter(c=>c==='b').length>=4);
    else if (filter==='bear')    rows = rows.filter(s=>(s.conf||[]).filter(c=>c==='r').length>=4);
    else if (filter==='oi')      rows = rows.filter(s=>Math.abs(s.oiChg||0)>=5);
    else if (filter==='prem')    rows = rows.filter(s=>(s.gain||0)>=100);
    else if (filter==='aligned') rows = rows.filter(s=>{ const a=(s.conf||[]).slice(0,3); return a.length>0 && a.every(c=>c===a[0]&&c!=='n'); });
    const sortFn = { score:s=>s.score, gain:s=>s.gain, rvol:s=>s.rvol, oiChg:s=>s.oiChg, spot:s=>s.spot, futChg:s=>s.futChg, lin:s=>s.lin }[sc] || (()=>0);
    return rows.sort((a,b) => sd*(sortFn(b)-sortFn(a)));
  }

  function sortBoard(col) {
    if (sortCol===col) sortDir=-sortDir; else { sortCol=col; sortDir=-1; }
  }

  // ── Max Pain ───────────────────────────────────────────────────────────────
  async function loadMaxPain(force=false) {
    if (maxpainLoading) return;
    maxpainLoading = true;
    try {
      const r = await fetch(`/api/max-pain/deviation${force?'?force=1':''}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      maxpainData = d.stocks || d.data || [];
      maxpainCounts = {
        strong_up: maxpainData.filter(s=>s.direction==='UP'&&(s.conviction==='STRONG'||s.conviction==='MODERATE')&&s.buildup_align==='ALIGNED').length,
        strong_down: maxpainData.filter(s=>s.direction==='DOWN'&&(s.conviction==='STRONG'||s.conviction==='MODERATE')&&s.buildup_align==='ALIGNED').length,
        high_achieve: maxpainData.filter(s=>s.achievability==='HIGH').length,
        total: maxpainData.length,
      };
      maxpainMedianPcr = d.median_pcr || 0;
      maxpainFetchedAt = new Date().toLocaleTimeString('en-IN',{hour12:false,hour:'2-digit',minute:'2-digit'});
    } catch(e) { console.warn('[MP]', e); }
    finally { maxpainLoading = false; }
  }

  function setPainSubFilter(code) {
    subPainFilter = subPainFilter===code?'ALL':code;
  }

  function getMaxPainFiltered() {
    let d = [...maxpainData];
    if (subPainFilter==='STRONG_UP')   d=d.filter(s=>s.direction==='UP'&&(s.conviction==='STRONG'||s.conviction==='MODERATE')&&s.buildup_align==='ALIGNED');
    else if (subPainFilter==='STRONG_DOWN') d=d.filter(s=>s.direction==='DOWN'&&(s.conviction==='STRONG'||s.conviction==='MODERATE')&&s.buildup_align==='ALIGNED');
    else if (subPainFilter==='HIGH_ACHIEVE') d=d.filter(s=>s.achievability==='HIGH');
    return d;
  }

  // load Max Pain when tab selected
  $: if (activeFilter==='maxpain' && !maxpainData.length && !maxpainLoading) loadMaxPain();

  // ── NSE Heatmap ────────────────────────────────────────────────────────────
  function buildSectorStats(stockList) {
    const map = {};
    NSE_SECTOR_LIST.forEach(sec => {
      map[sec.name] = { name:sec.name, key:sec.key, stocks:[], spotReturns:[], futReturns:[], lbs:0, sbs:0, scs:0, lus:0, flats:0 };
    });
    (stockList||[]).forEach(s => {
      const sym = s.sym?.toUpperCase();
      const sn = NSE_STOCK_SECTOR_MAP[sym];
      if (sn && map[sn]) {
        map[sn].stocks.push(s);
        if (Number.isFinite(s.spot)) map[sn].spotReturns.push(s.spot);
        if (Number.isFinite(s.futChg)) map[sn].futReturns.push(s.futChg);
        else if (Number.isFinite(s.spot)) map[sn].futReturns.push(s.spot);
        const bu = s.futBU || s.fut;
        if (bu==='LB' || bu==='Long Buildup') map[sn].lbs++;
        else if (bu==='SB' || bu==='Short Buildup') map[sn].sbs++;
        else if (bu==='SC' || bu==='Short Covering') map[sn].scs++;
        else if (bu==='LU' || bu==='Long Unwinding') map[sn].lus++;
        else map[sn].flats++;
      }
    });
    NSE_SECTOR_LIST.forEach(sec => {
      const st = map[sec.name];
      st.avgSpot = st.spotReturns.length ? st.spotReturns.reduce((a,b)=>a+b,0)/st.spotReturns.length : 0;
      st.avgFut  = st.futReturns.length  ? st.futReturns.reduce((a,b)=>a+b,0)/st.futReturns.length  : 0;
      st.count   = st.stocks.length;
    });
    return map;
  }

  function hmCardCls(avg) {
    if (avg >= 3) return 'hm-p3'; if (avg >= 1) return 'hm-p1'; if (avg > 0) return 'hm-p0p';
    if (avg <= -3) return 'hm-m3'; if (avg <= -1) return 'hm-m1'; if (avg < 0) return 'hm-m0p';
    return 'hm-0';
  }

  $: sectorStats = buildSectorStats(stocks);
  $: secDetailStocks = selectedSector && sectorStats[selectedSector] ? (() => {
    let rows = [...sectorStats[selectedSector].stocks];
    if (sectorBuildupFilter==='LB') rows=rows.filter(s=>s.futBU==='LB');
    else if (sectorBuildupFilter==='SB') rows=rows.filter(s=>s.futBU==='SB');
    else if (sectorBuildupFilter==='SC') rows=rows.filter(s=>s.futBU==='SC');
    else if (sectorBuildupFilter==='LU') rows=rows.filter(s=>s.futBU==='LU');
    else if (sectorBuildupFilter==='FLAT') rows=rows.filter(s=>!s.futBU||s.futBU==='—');
    const fn = { spot:s=>s.spot, oiChg:s=>s.oiChg, rvol:s=>s.rvol, score:s=>s.score, lin:s=>s.lin }[secSortCol] || (s=>s.spot);
    return rows.sort((a,b) => secSortDir*(fn(b)-fn(a)));
  })() : [];

  // ── Watchlist ──────────────────────────────────────────────────────────────
  function wlAdd(sym) {
    if (!sym || wlSymbols.includes(sym)) return;
    wlSymbols = [...wlSymbols, sym];
    if (typeof localStorage !== 'undefined') localStorage.setItem('ts_watchlist', JSON.stringify(wlSymbols));
    wlSearch = ''; wlSuggestions = [];
  }
  function wlRemove(sym) {
    wlSymbols = wlSymbols.filter(s=>s!==sym);
    if (typeof localStorage !== 'undefined') localStorage.setItem('ts_watchlist', JSON.stringify(wlSymbols));
  }
  function wlSearchInput(e) {
    const q = e.target.value.trim().toUpperCase();
    wlSearch = q;
    wlSuggestions = q.length > 0
      ? (stocks||[]).map(s=>s.sym).filter(sym=>sym&&sym.toUpperCase().includes(q)&&!wlSymbols.includes(sym)).slice(0,8)
      : [];
  }
  function wlKeydown(e) {
    if (e.key==='Enter') {
      const v = e.target.value.trim().toUpperCase();
      if (v) { wlAdd(v); e.target.value=''; }
    }
  }
  function sortWl(col) {
    if (wlSortCol===col) wlSortDir=-wlSortDir; else { wlSortCol=col; wlSortDir=-1; }
  }
  $: wlRows = (() => {
    const syms = wlSymbols;
    const rows = syms.map(sym => stocks.find(s=>s.sym===sym)).filter(Boolean);
    const notFound = syms.filter(sym=>!stocks.find(s=>s.sym===sym));
    const fn = { spot:s=>s.spot, oiChg:s=>s.oiChg, rvol:s=>s.rvol, score:s=>s.score, gap:s=>s.gap, fhS:s=>s.fhS }[wlSortCol]||(s=>s.score);
    return { live: rows.sort((a,b)=>wlSortDir*(fn(b)-fn(a))), notFound };
  })();

  // ── Derived board rows ─────────────────────────────────────────────────────
  $: rows = (activeFilter!=='heatmap' && activeFilter!=='maxpain' && activeFilter!=='watchlist') ? getFiltered(stocks, activeFilter, subBuildupFilter, sortCol, sortDir) : [];

  // Futures Buildup stats
  $: futStat = { lbs:stocks.filter(s=>s.futBU==='LB').length, sbs:stocks.filter(s=>s.futBU==='SB').length, scs:stocks.filter(s=>s.futBU==='SC').length, lus:stocks.filter(s=>s.futBU==='LU').length, flats:stocks.filter(s=>!s.futBU||s.futBU==='—').length };

  $: filteredOISpurts = oidockSearch ? oiSpurts.filter(d=>d.symbol?.toUpperCase().includes(oidockSearch.toUpperCase())) : oiSpurts;
</script>

<div class="board-wrap">
  <!-- Column header -->
  <div class="ch">
    <div class="ct">🎯 Unified Master Board <span class="cbadge">{activeFilter==='maxpain'?getMaxPainFiltered().length:activeFilter==='watchlist'?wlSymbols.length:rows.length}</span></div>
    <div style="display:flex;gap:5px;align-items:center;">
      {#if activeFilter!=='heatmap' && activeFilter!=='watchlist' && activeFilter!=='maxpain'}
        <button class="fbtn {oidockOpen?'on':''}" on:click={()=>oidockOpen=!oidockOpen} style="padding:2px 8px;font-size:10px;display:flex;align-items:center;gap:3px;">⚡ OI</button>
      {/if}
      <button class="ibtn" on:click={()=>rows=getFiltered()}>↺</button>
    </div>
  </div>

  <!-- Filter bar -->
  <div class="fb">
    {#each FILTERS as f}
      <button class="fbtn {activeFilter===f.key?'on':''}" on:click={()=>activeFilter=f.key}>{f.label}</button>
    {/each}
  </div>

  <!-- Futures Buildup sub-filter bar (5 Stats Cards matching Screenshot) -->
  {#if activeFilter==='futbld'}
    <div class="futbld-stats-bar">
      <div class="fb-stat-card {subBuildupFilter==='LB'?'active':''}" on:click={()=>subBuildupFilter = subBuildupFilter==='LB'?'all':'LB'}>
        <div class="fb-stat-lbl">LONG BUILDUP</div>
        <div class="fb-stat-val val-lb">{futStat.lbs}</div>
      </div>
      <div class="fb-stat-card {subBuildupFilter==='SB'?'active':''}" on:click={()=>subBuildupFilter = subBuildupFilter==='SB'?'all':'SB'}>
        <div class="fb-stat-lbl">SHORT BUILDUP</div>
        <div class="fb-stat-val val-sb">{futStat.sbs}</div>
      </div>
      <div class="fb-stat-card {subBuildupFilter==='SC'?'active':''}" on:click={()=>subBuildupFilter = subBuildupFilter==='SC'?'all':'SC'}>
        <div class="fb-stat-lbl">SHORT COVER</div>
        <div class="fb-stat-val val-sc">{futStat.scs}</div>
      </div>
      <div class="fb-stat-card {subBuildupFilter==='LU'?'active':''}" on:click={()=>subBuildupFilter = subBuildupFilter==='LU'?'all':'LU'}>
        <div class="fb-stat-lbl">LONG UNWIND</div>
        <div class="fb-stat-val val-lu">{futStat.lus}</div>
      </div>
      <div class="fb-stat-card {subBuildupFilter==='FLAT'?'active':''}" on:click={()=>subBuildupFilter = subBuildupFilter==='FLAT'?'all':'FLAT'}>
        <div class="fb-stat-lbl">FLAT BUILDUP</div>
        <div class="fb-stat-val val-flat">{futStat.flats}</div>
      </div>
    </div>
  {/if}

  <!-- Max Pain sub-filter bar -->
  {#if activeFilter==='maxpain'}
    <div class="mp-stats-bar">
      <div class="mp-card {subPainFilter==='STRONG_UP'?'active':''}" on:click={()=>setPainSubFilter('STRONG_UP')} on:keypress>
        <div class="mp-lbl">🟢 STRONG UPWARD</div>
        <div class="mp-val val-bull">{maxpainCounts.strong_up}</div>
        <div class="mp-sub">Small Gap + Aligned Buildup</div>
      </div>
      <div class="mp-card {subPainFilter==='STRONG_DOWN'?'active':''}" on:click={()=>setPainSubFilter('STRONG_DOWN')} on:keypress>
        <div class="mp-lbl">🔴 STRONG DOWNWARD</div>
        <div class="mp-val val-bear">{maxpainCounts.strong_down}</div>
        <div class="mp-sub">Small Gap + Aligned Buildup</div>
      </div>
      <div class="mp-card {subPainFilter==='HIGH_ACHIEVE'?'active':''}" on:click={()=>setPainSubFilter('HIGH_ACHIEVE')} on:keypress>
        <div class="mp-lbl">🎯 HIGH ACHIEVE (≤1%)</div>
        <div class="mp-val val-achieve">{maxpainCounts.high_achieve}</div>
        <div class="mp-sub">Optimal Expiry Pull Magnet</div>
      </div>
      <div class="mp-card {subPainFilter==='ALL'?'active':''}" on:click={()=>setPainSubFilter('ALL')} on:keypress>
        <div class="mp-lbl">📊 ALL DEVIATIONS</div>
        <div class="mp-val val-total">{maxpainCounts.total || maxpainData.length}</div>
        <div class="mp-sub">Median PCR: {maxpainMedianPcr.toFixed(2)}</div>
      </div>
      <div class="mp-card mp-refresh" on:click={()=>loadMaxPain(true)} on:keypress>
        <div class="mp-lbl">↻ 30M REFRESH</div>
        <div class="mp-ts">{maxpainFetchedAt||'Live'}</div>
        <div class="mp-sub" style="color:var(--acc);">{maxpainLoading?'Loading…':'Click to Refresh'}</div>
      </div>
    </div>
  {/if}

  <!-- Confluence legend -->
  {#if activeFilter!=='heatmap' && activeFilter!=='maxpain' && activeFilter!=='watchlist'}
    <div class="conf-leg">
      <span><span class="dot b"></span> Bull</span>
      <span><span class="dot r"></span> Bear</span>
      <span><span class="dot n"></span> Neutral</span>
      <span style="margin-left:8px;color:var(--t2);">15m · 1h · Day · OI · Vol · Fut · DXCNT · Drift</span>
      <span style="margin-left:auto;color:var(--grn);font-weight:600;">Row glow = score intensity</span>
    </div>
  {/if}

  <!-- Main split: OI dock + content -->
  <div class="board-split">
    <!-- OI Spurt dock -->
    {#if oidockOpen && activeFilter!=='heatmap' && activeFilter!=='watchlist' && activeFilter!=='maxpain'}
      <div class="oi-dock">
        <div class="oi-dock-hdr">
          <div class="oi-dock-title">⚡ OI Spurt <span class="cbadge" style="font-size:8px;padding:1px 4px;">{oiSpurts.length}</span></div>
          <input class="oi-dock-input" type="text" placeholder="🔍 Search OI..." bind:value={oidockSearch} />
        </div>
        <div class="oi-dock-list">
          {#each filteredOISpurts as item, i}
            {@const bull = (item.oi_change_pct||0) > 0}
            <div class="oi-dock-item {i<5?'top-spurt':''}">
              <div class="oi-rank">{i+1}</div>
              <div class="oi-sym">{item.symbol}</div>
              <div class="pct-badge {bull?'bull':'bear'}">{bull?'+':''}{(item.oi_change_pct||0).toFixed(1)}%</div>
            </div>
          {/each}
          {#if !filteredOISpurts.length}
            <div style="padding:16px;text-align:center;font-size:9px;color:var(--t3);">No OI data</div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Board content area -->
    <div class="board-content">
      {#if boardLoading}
        <div class="board-loading">
          <div style="font-size:28px;margin-bottom:8px;">⏳</div>
          <div style="font-size:12px;font-weight:700;color:var(--t1);">{boardLoadingMsg}</div>
          <div style="font-size:10px;color:var(--t2);margin-top:4px;">Auto-refreshing in 30s.</div>
        </div>

      {:else if activeFilter==='heatmap'}
        <!-- NSE Heatmap -->
        <div class="hm-wrap">
          <div class="heatmap-topbar">
            <div class="heatmap-title">
              <span>🗺️ NSE Sectoral Indices Heatmap</span>
              <span style="font-size:9px;color:var(--t2);font-weight:600;">(23 Official NSE Sectors · {stocks.length} F&O Stocks)</span>
            </div>
            <div class="heatmap-legend">
              <span style="font-size:8px;color:var(--t2);margin-right:4px;">Returns Scale:</span>
              <span class="hm-leg-chip hm-leg-p5">+5%</span>
              <span class="hm-leg-chip hm-leg-p3">+3%</span>
              <span class="hm-leg-chip hm-leg-p1">+1%</span>
              <span class="hm-leg-chip hm-leg-0">0%</span>
              <span class="hm-leg-chip hm-leg-m1">-1%</span>
              <span class="hm-leg-chip hm-leg-m3">-3%</span>
              <span class="hm-leg-chip hm-leg-m5">-5%</span>
            </div>
          </div>

          <!-- Sector Drilldown -->
          {#if selectedSector && sectorStats[selectedSector]}
            {@const sec = sectorStats[selectedSector]}
            {@const sign = sec.avgSpot>0?'+':''}
            {@const chgCls = sec.avgSpot>0?'pos':sec.avgSpot<0?'neg':'neu'}
            <div class="sec-detail-container">
              <div class="sec-detail-hdr">
                <div class="sec-detail-left">
                  <button class="sec-back-btn" on:click={()=>{selectedSector=null;sectorBuildupFilter='all';}}>← All Sectors</button>
                  <div class="sec-detail-title">{sec.name}</div>
                  <span class="sec-card-chg {chgCls}" style="font-size:12px;padding:2px 8px;">Spot: {sign}{sec.avgSpot.toFixed(2)}%</span>
                </div>
                <div class="sec-detail-metrics">
                  <div class="sec-metric-chip">Constituents: <span>{sec.count} Stocks</span></div>
                  <div class="sec-metric-chip">Avg Fut: <span>{sec.avgFut>0?'+':''}{sec.avgFut.toFixed(2)}%</span></div>
                  <div class="sec-metric-chip">
                    <span style="color:#22c55e;">LB:{sec.lbs}</span> ·
                    <span style="color:#eab308;">SC:{sec.scs}</span> ·
                    <span style="color:#ef4444;">SB:{sec.sbs}</span> ·
                    <span style="color:#c084fc;">LU:{sec.lus}</span>
                  </div>
                </div>
              </div>
              <!-- Buildup filter pills -->
              <div style="display:flex;gap:6px;margin:6px 10px 8px;align-items:center;flex-wrap:wrap;">
                <span style="font-size:9px;font-weight:700;color:var(--t2);text-transform:uppercase;">Filter:</span>
                {#each [{k:'all',l:`All (${sec.count})`},{k:'LB',l:`🟢 LB (${sec.lbs})`},{k:'SC',l:`🟡 SC (${sec.scs})`},{k:'SB',l:`🔴 SB (${sec.sbs})`},{k:'LU',l:`🟠 LU (${sec.lus})`},{k:'FLAT',l:`⚪ FLAT (${sec.flats})`}] as f}
                  <button class="fbtn {sectorBuildupFilter===f.k?'on':''}" on:click={()=>sectorBuildupFilter=f.k} style="font-size:10px;padding:2px 7px;">{f.l}</button>
                {/each}
              </div>
              <!-- Sector 13-col stock matrix -->
              <div class="tbl-shell" style="flex:1;">
                <table class="tbl">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th class="sortable" on:click={()=>{ secSortCol='sym'; secSortDir=-secSortDir; }}>SYMBOL</th>
                      <th>CAP</th>
                      <th class="sortable" on:click={()=>{ secSortCol='spot'; secSortDir=-1; }}>SPOT%</th>
                      <th class="sortable" on:click={()=>{ secSortCol='oiChg'; secSortDir=-1; }}>OI% CHG</th>
                      <th>BUILDUP</th>
                      <th class="sortable" on:click={()=>{ secSortCol='rvol'; secSortDir=-1; }}>RVOL</th>
                      <th class="sortable" on:click={()=>{ secSortCol='lin'; secSortDir=-1; }}>LIN%</th>
                      <th>CONFLUENCE</th>
                      <th class="sortable" on:click={()=>{ secSortCol='score'; secSortDir=-1; }}>SCORE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each secDetailStocks as s, idx}
                      {@const sCls = s.spot>0?'bull':s.spot<0?'bear':''}
                      {@const oiCls = s.oiChg>0?'bull':s.oiChg<0?'bear':'oi-zero'}
                      <tr class="{rowDir(s)} {rowGlow(s)}">
                        <td class="rank">{idx+1}</td>
                        <td class="sym">{s.sym}</td>
                        <td><span class="{capClass(s.cap)}">{s.cap}</span></td>
                        <td class="mono"><span class="spot-badge {sCls}">{s.spot>0?'+':''}{s.spot}%</span></td>
                        <td class="mono {oiCls}">{s.oiChg>0?'+':''}{s.oiChg}%</td>
                        <td><span class="{futClass(s.futBU)}">{s.futBU||'—'}</span></td>
                        <td class="mono {s.rvol>=3?'bull':s.rvol<1?'bear':''}">{s.rvol}x</td>
                        <td class="mono">{s.lin>0?'+':''}{s.lin}%</td>
                        <td style="white-space:nowrap;">
                          {#each (s.conf||[]).slice(0,3) as c, ti}
                            <span class="tf {tfClass(c)}" style="font-size:7.5px;margin-right:1px;">{['15m','1H','D'][ti]}</span>
                          {/each}
                        </td>
                        <td><span class="{gradeClass(s.score)}">{s.score}</span></td>
                      </tr>
                    {/each}
                    {#if !secDetailStocks.length}
                      <tr><td colspan="10" style="text-align:center;padding:24px;color:var(--t2);font-size:10px;">No stocks match the active filter.</td></tr>
                    {/if}
                  </tbody>
                </table>
              </div>
            </div>
          {/if}

          <!-- All Sectors Grid -->
          <div class="sec-grid" style="{selectedSector?'margin-top:10px;':''}">
            {#each NSE_SECTOR_LIST as sec}
              {@const st = sectorStats[sec.name]}
              {@const isPos = st.count>0 && st.avgSpot>0.0001}
              {@const isNeg = st.count>0 && st.avgSpot<-0.0001}
              {@const chgCls = isPos?'pos':isNeg?'neg':'neu'}
              {@const sign = isPos?'+':''}
              <div class="sec-card {hmCardCls(st.avgSpot)} {isPos?'is-green':isNeg?'is-red':'is-zero'} {selectedSector===sec.name?'selected':''}"
                   on:click={()=>{ selectedSector=sec.name; sectorBuildupFilter='all'; }}
                   on:keypress>
                <div class="sec-card-hdr">
                  <span class="sec-card-name" title={sec.name}>{sec.name}</span>
                  <span class="sec-card-chg {chgCls}">{sign}{st.avgSpot.toFixed(2)}%</span>
                </div>
                <div class="sec-card-stats">
                  <span>{st.count} Stocks</span>
                  <span>Fut: {st.avgFut>0?'+':''}{st.avgFut.toFixed(2)}%</span>
                </div>
                <div class="sec-card-pills">
                  {#if st.lbs>0}<span class="sec-pill lb">LB:{st.lbs}</span>{/if}
                  {#if st.scs>0}<span class="sec-pill sc">SC:{st.scs}</span>{/if}
                  {#if st.sbs>0}<span class="sec-pill sb">SB:{st.sbs}</span>{/if}
                  {#if st.lus>0}<span class="sec-pill lu">LU:{st.lus}</span>{/if}
                </div>
              </div>
            {/each}
          </div>
        </div>

      {:else if activeFilter==='maxpain'}
        <!-- Max Pain Deviation Table -->
        <div class="tbl-shell">
          {#if maxpainLoading && !maxpainData.length}
            <div class="board-loading">
              <div style="font-size:28px;margin-bottom:8px;">🎯</div>
              <div style="font-size:12px;font-weight:700;color:var(--t1);">Loading Max Pain Deviation…</div>
            </div>
          {:else}
            <table class="tbl">
              <thead>
                <tr>
                  <th>#</th><th>SYMBOL</th>
                  <th class="sortable" on:click={()=>sortBoard('spot')}>SPOT LTP</th>
                  <th>ATM</th>
                  <th>MAX PAIN</th>
                  <th class="sortable" on:click={()=>sortBoard('spread_pct')}>SPREAD%</th>
                  <th>CONVICTION</th>
                  <th>FUT B/U</th>
                  <th>PCR</th>
                  <th class="sortable" on:click={()=>sortBoard('oiChg')}>OI%</th>
                  <th>THESIS / READ</th>
                </tr>
              </thead>
              <tbody>
                {#each getMaxPainFiltered() as s, i}
                  {@const upDir = s.direction==='UP'}
                  {@const convCls = s.conviction==='STRONG'?'sc-hi':s.conviction==='MODERATE'?'sc-me':'sc-lo'}
                  <tr>
                    <td class="rank">{i+1}</td>
                    <td class="sym">{s.symbol}</td>
                    <td class="mono" style="font-weight:800;">₹{(s.spot_ltp||0).toFixed(2)}</td>
                    <td class="mono" style="color:var(--acc);">₹{s.atm_strike||'—'}</td>
                    <td class="mono" style="color:var(--amb);">₹{s.max_pain||'—'}</td>
                    <td class="mono {upDir?'bull':'bear'}">{(s.spread_pct||0) > 0?'+':''}{(s.spread_pct||0).toFixed(2)}%</td>
                    <td><span class="{convCls}">{s.conviction||'—'}</span></td>
                    <td><span class="{futClass(s.fut_buildup)}">{s.fut_buildup||'—'}</span></td>
                    <td class="mono {(s.pcr||0)>=1?'bull':'bear'}">{(s.pcr||0).toFixed(2)}</td>
                    <td class="mono {(s.oi_spurt_pct||0)>0?'bull':'bear'}">{(s.oi_spurt_pct||0)>0?'+':''}{(s.oi_spurt_pct||0).toFixed(1)}%</td>
                    <td style="font-size:9px;color:var(--t2);max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{s.read||s.thesis||s.note||'—'}</td>
                  </tr>
                {/each}
                {#if !getMaxPainFiltered().length}
                  <tr><td colspan="11" style="text-align:center;padding:48px;color:var(--t3);font-size:10px;">
                    <div style="font-size:24px;margin-bottom:8px;">🎯</div>
                    {maxpainLoading?'Loading Max Pain data…':'No stocks match the active sub-filter'}
                  </td></tr>
                {/if}
              </tbody>
            </table>
          {/if}
        </div>

      {:else if activeFilter==='watchlist'}
        <!-- Watch List -->
        <div class="wl-panel">
          <div class="wl-header">
            <div class="wl-title">📋 Watch List <span style="color:var(--t3);font-weight:400;font-size:10px;">({wlSymbols.length} symbols)</span></div>
            <div class="wl-search-wrap">
              <input class="wl-search" type="text" placeholder="🔍 Search & add symbol…"
                on:input={wlSearchInput} on:keydown={wlKeydown} />
              {#if wlSuggestions.length}
                <div class="wl-suggestions">
                  {#each wlSuggestions as sym}
                    <div class="wl-sug-item" on:click={()=>wlAdd(sym)} on:keypress>{sym}</div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
          <div class="tbl-shell">
            <table class="tbl">
              <thead>
                <tr>
                  <th>#</th>
                  <th class="sortable" on:click={()=>sortWl('sym')}>SYMBOL</th>
                  <th class="sortable" on:click={()=>sortWl('spot')}>SPOT%</th>
                  <th>FUT B/U</th>
                  <th class="sortable" on:click={()=>sortWl('oiChg')}>OI%</th>
                  <th class="sortable" on:click={()=>sortWl('gap')}>GAP%</th>
                  <th class="sortable" on:click={()=>sortWl('rvol')}>RVOL</th>
                  <th class="sortable" on:click={()=>sortWl('fhS')}>FH VOL</th>
                  <th>TF</th>
                  <th class="sortable" on:click={()=>sortWl('score')}>SCORE</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {#each wlRows.live as s, i}
                  {@const sCls = s.spot>0?'bull':s.spot<0?'bear':''}
                  {@const oiCls = s.oiChg>0?'bull':s.oiChg<0?'bear':'oi-zero'}
                  {@const rvolCls = s.rvol>=3?'bull':s.rvol<1?'bear':''}
                  {@const gapCls = s.gap>0?'bull':s.gap<0?'bear':''}
                  <tr>
                    <td class="rank">{i+1}</td>
                    <td class="sym">{s.sym}</td>
                    <td class="mono"><span class="spot-badge {sCls}">{s.spot>0?'+':''}{s.spot}%</span></td>
                    <td><span class="{futClass(s.futBU)}">{s.futBU||'—'}</span></td>
                    <td class="mono {oiCls}">{s.oiChg>0?'+':''}{s.oiChg}%</td>
                    <td class="mono {gapCls}">{s.gap>0?'+':''}{s.gap}%</td>
                    <td class="mono {rvolCls}">{s.rvol>=3?'▲':'▽'} {s.rvol}x</td>
                    <td class="mono" style="font-size:9px;"><span class="bull">{s.fhS}x</span><br/><span style="color:var(--t3);">{s.fhC}x</span></td>
                    <td style="white-space:nowrap;">
                      {#each (s.conf||[]).slice(0,3) as c, ti}
                        <span class="tf {tfClass(c)}" style="font-size:7.5px;margin-right:1px;">{['15m','1H','D'][ti]}</span>
                      {/each}
                    </td>
                    <td><span class="{gradeClass(s.score)}">{s.score}</span></td>
                    <td><button class="wl-rm" on:click={()=>wlRemove(s.sym)} title="Remove">✕</button></td>
                  </tr>
                {/each}
                {#each wlRows.notFound as sym}
                  <tr style="opacity:.5;">
                    <td class="rank">—</td>
                    <td class="sym" colspan="9">{sym} <span style="font-size:8px;color:var(--bear);">(not in board)</span></td>
                    <td><button class="wl-rm" on:click={()=>wlRemove(sym)} title="Remove">✕</button></td>
                  </tr>
                {/each}
                {#if !wlSymbols.length}
                  <tr><td colspan="11" style="text-align:center;padding:48px 16px;color:var(--t2);">
                    <div style="font-size:24px;margin-bottom:8px;">📋</div>
                    <div style="font-size:12px;font-weight:700;color:var(--t1);margin-bottom:4px;">Your watchlist is empty</div>
                    <div style="font-size:10px;">Search for a symbol above and click to add it.</div>
                  </td></tr>
                {/if}
              </tbody>
            </table>
          </div>
        </div>

      {:else}
        <!-- Standard board table (PremGain / Futures Buildup / filters) -->
        <div class="tbl-shell">
          <table class="tbl">
            <thead>
              {#if activeFilter==='futbld'}
                <tr>
                  <th>#</th><th>SYMBOL</th>
                  <th class="sortable" on:click={()=>sortBoard('spot')}>SPOT%</th>
                  <th class="sortable" on:click={()=>sortBoard('futChg')}>FUT%</th>
                  <th>FUT B/U</th>
                  <th class="sortable" on:click={()=>sortBoard('oiChg')}>OI%</th>
                  <th>TF</th><th>CAP</th>
                  <th>DXCNT</th>
                  <th>GAP%</th>
                  <th>INST</th>
                  <th class="sortable" on:click={()=>sortBoard('rvol')}>RVOL</th>
                  <th>FH VOL</th><th>E9H</th><th>SPOT PRICE</th>
                  <th class="sortable" on:click={()=>sortBoard('score')}>SCORE</th>
                </tr>
              {:else}
                <tr>
                  <th>#</th><th>SYMBOL</th>
                  <th class="sortable" on:click={()=>sortBoard('spot')}>SPOT%</th>
                  <th class="sortable" on:click={()=>sortBoard('fut')}>FUT B/U</th>
                  <th class="sortable" on:click={()=>sortBoard('futChg')}>FUT%</th>
                  <th class="sortable" on:click={()=>sortBoard('oiChg')}>OI%</th>
                  <th>TF</th>
                  <th>CAP</th>
                  <th class="sortable" on:click={()=>sortBoard('lin')}>LIN%</th>
                  <th>DXCNT</th>
                  <th class="sortable" on:click={()=>sortBoard('gain')}>GAIN%</th>
                  <th>GAP%</th>
                  <th class="sortable" on:click={()=>sortBoard('rvol')}>RVOL</th>
                  <th>FH VOL</th>
                  <th>E9H</th>
                  <th class="sortable" on:click={()=>sortBoard('score')}>SCORE</th>
                </tr>
              {/if}
            </thead>
            <tbody>
              {#if !rows.length}
                <tr><td colspan="17" style="text-align:center;padding:48px 16px;color:var(--t2);">
                  <div style="font-size:24px;margin-bottom:8px;">🔍</div>
                  <div style="font-size:12px;font-weight:700;color:var(--t1);margin-bottom:4px;">No stocks match filter</div>
                </td></tr>
              {:else}
                {#each rows as s}
                  {@const dir = rowDir(s)}
                  {@const glow = rowGlow(s)}
                  {@const sCls = s.spot>0?'bull':s.spot<0?'bear':''}
                  {@const oiCls = s.oiChg>0?'bull':s.oiChg<0?'bear':'oi-zero'}
                  {@const dCls = (s.dxcnt||0)>0?'bull':(s.dxcnt||0)<0?'bear':''}
                  {@const isExp = expandedStocks.has(s.sym)}
                  {#if activeFilter==='futbld'}
                    {@const isChartOpen = activeChartStock === s.sym}
                    <tr class="{dir} {glow} {isChartOpen ? 'selected' : ''}" style="cursor:pointer;" on:click={() => toggleStockChart(s)}>
                      <td class="rank">{s.rank}</td>
                      <td class="sym">
                        <span style="display:inline-block;font-size:8px;margin-right:4px;color:var(--t2);transform:{isChartOpen ? 'rotate(90deg)' : 'none'};transition:transform .15s;">▶</span>
                        {s.sym}
                      </td>
                      <td class="mono"><span class="spot-badge {sCls}">{s.spot>0?'+':''}{s.spot}%</span></td>
                      <td class="mono {s.futChg>0?'bull':s.futChg<0?'bear':''}">{s.futChg>0?'+':''}{s.futChg}%</td>
                      <td><span class="{futClass(s.futBU)}">{s.futBU||'—'}</span></td>
                      <td class="mono {oiCls}">{s.oiChg>0?'+':''}{s.oiChg}%</td>
                      <td style="white-space:nowrap;">{#each (s.conf||[]).slice(0,3) as c, ti}<span class="tf {tfClass(c)}" style="font-size:7.5px;margin-right:1px;">{['15m','1H','D'][ti]}</span>{/each}</td>
                      <td><span class="{capClass(s.cap)}">{s.cap}</span></td>
                      <td class="mono {dCls}">{(s.dxcnt||0)>0?'+':''}{s.dxcnt||0}D</td>
                      <td class="mono {s.gap>0?'bull':s.gap<0?'bear':''}">{s.gap>0?'+':''}{s.gap}%</td>
                      <td class="mono" style="font-size:9px;color:{s.instHi?'var(--cyn)':'inherit'};">{s.inst || '—'}</td>
                      <td class="mono"><span class="{s.rvol>=3?'bull':s.rvol<1?'bear':''}">{s.rvol>=3?'▲':'▽'} {s.rvol}x</span></td>
                      <td class="mono" style="font-size:9px;"><span class="bull">{s.fhS}x</span><br/><span style="color:var(--t3);">{s.fhC}x</span></td>
                      <td class="mono {s.e9hCls}" style="font-size:9px;">{s.e9hText}</td>
                      <td class="mono" style="font-weight:800;">₹{(s.spotLtp||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</td>
                      <td><span class="{gradeClass(s.score)}">{s.score}</span></td>
                    </tr>
                    {#if isChartOpen}
                      <tr class="chart-subrow">
                        <td colspan="16" style="padding:0;">
                          <div class="inline-chart-box" id="ichart-container-{s.sym}">
                            <div class="inline-chart-topbar">
                              <div class="ichart-info">
                                <span style="font-size:12px;font-weight:800;color:#fff;">📊 {s.sym}</span>
                                <span class="ichart-badge">{s.futBU||'FLAT'} · ₹{(s.spotLtp||0).toFixed(2)} ({s.spot>0?'+':''}{s.spot}%)</span>
                                <div class="ichart-levels">
                                  {#if s.pdh}<span class="lvl-badge pdh">PDH: ₹{s.pdh.toFixed(1)}</span>{/if}
                                  {#if s.pdl}<span class="lvl-badge pdl">PDL: ₹{s.pdl.toFixed(1)}</span>{/if}
                                  {#if s.tc}<span class="lvl-badge tc">TC: ₹{s.tc.toFixed(1)}</span>{/if}
                                  {#if s.piv}<span class="lvl-badge piv">PIV: ₹{s.piv.toFixed(1)}</span>{/if}
                                  {#if s.bc}<span class="lvl-badge bc">BC: ₹{s.bc.toFixed(1)}</span>{/if}
                                </div>
                              </div>
                              <div class="ichart-actions">
                                <div class="tf-btn-group">
                                  <button class="ichart-tf-btn {chartTf===5?'active':''}" on:click|stopPropagation={()=>switchChartTf(s.sym, 5)}>5m</button>
                                  <button class="ichart-tf-btn {chartTf===15?'active':''}" on:click|stopPropagation={()=>switchChartTf(s.sym, 15)}>15m</button>
                                </div>
                                <div style="display:flex;gap:2px;">
                                  <button class="ichart-tf-btn" title="Zoom in" on:click|stopPropagation={()=>zoomChart(s.sym, -1)}>🔍+</button>
                                  <button class="ichart-tf-btn" title="Zoom out" on:click|stopPropagation={()=>zoomChart(s.sym, 1)}>🔍-</button>
                                  <button class="ichart-tf-btn" title="Reset zoom" on:click|stopPropagation={()=>resetChartZoom(s.sym)}>↺</button>
                                </div>
                                <a href="/apex-dashboard?symbol={s.sym}" target="_blank" class="chart-popout-btn" on:click|stopPropagation>↗ Full APEX Dashboard</a>
                                <button class="ichart-tf-btn" style="color:var(--bear);font-size:11px;" on:click|stopPropagation={()=>toggleStockChart(s)}>✕</button>
                              </div>
                            </div>
                            <div class="ichart-canvas-container">
                              <div id="ichart-loading-{s.sym}" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:11px;color:#64748b;">⏳ Loading intraday chart…</div>
                              <div id="ichart-error-{s.sym}" class="ichart-error-msg" style="display:none;"></div>
                              <canvas id="ichart-canvas-{s.sym}" class="ichart-canvas"></canvas>
                            </div>
                          </div>
                        </td>
                      </tr>
                    {/if}
                  {:else}
                    <tr class="{dir} {glow} {isExp ? 'selected' : ''}" style="cursor:pointer;" on:click={() => toggleStockContracts(s.sym)}>
                      <td class="rank">{s.rank}</td>
                      <td class="sym">
                        {#if s.hasOptionGain}
                          <span style="display:inline-block;font-size:8px;margin-right:4px;color:var(--t2);transform:{isExp ? 'rotate(90deg)' : 'none'};transition:transform .15s;">▶</span>
                        {/if}
                        {s.sym}
                      </td>
                      <td class="mono"><span class="spot-badge {sCls}">{s.spot>0?'+':''}{s.spot}%</span></td>
                      <td><span class="{futClass(s.futBU)}">{s.futBU||'—'}</span></td>
                      <td class="mono {s.futChg>0?'bull':s.futChg<0?'bear':''}">{s.futChg>0?'+':''}{s.futChg}%</td>
                      <td class="mono {oiCls}">{s.oiChg>0?'+':''}{s.oiChg}%</td>
                      <td style="white-space:nowrap;">{#each (s.conf||[]).slice(0,3) as c, ti}<span class="tf {tfClass(c)}" style="font-size:7.5px;margin-right:1px;">{['15m','1H','D'][ti]}</span>{/each}</td>
                      <td><span class="{capClass(s.cap)}">{s.cap}</span></td>
                      <td class="mono neu">{s.lin}%</td>
                      <td class="mono {dCls}">{(s.dxcnt||0)>0?'+':''}{s.dxcnt||0}D</td>
                      <td><span class="gbadge {(s.gain||0)>=100?'bull':''}">{s.gain}%</span></td>
                      <td class="mono {s.gap>0?'bull':s.gap<0?'bear':''}">{s.gap>0?'+':''}{s.gap}%</td>
                      <td class="mono"><span class="{s.rvol>=3?'bull':s.rvol<1?'bear':''}">{s.rvol>=3?'▲':'▽'} {s.rvol}x</span></td>
                      <td class="mono" style="font-size:9px;"><span class="bull">{s.fhS}x</span><br/><span style="color:var(--t3);">{s.fhC}x</span></td>
                      <td class="mono {s.e9hCls}" style="font-size:9px;">{s.e9hText}</td>
                      <td><span class="{gradeClass(s.score)}">{s.score}</span></td>
                    </tr>
                    {#if isExp}
                      <tr class="contracts-subrow">
                        <td colspan="16" style="padding:0;">
                          <div class="contracts-container">
                            {#each s.contracts || [] as c}
                              {@const gainVal = Number(c.gain_pct || 0)}
                              {@const isStale = !!c.ltp_stale}
                              {@const gClass = isStale ? 'gain-stale' : (gainVal >= 100 ? 'gain-fire' : (gainVal >= 50 ? 'gain-rocket' : 'gain-up'))}
                              {@const emoji = isStale ? '⏳' : (gainVal >= 100 ? '🔥' : (gainVal >= 50 ? '🚀' : '📈'))}
                              {@const isOpening = !!c.is_opening}
                              {@const tag = isOpening ? '⭐' : '🏃'}
                              {@const tagCls = isOpening ? 'gold' : 'run'}
                              {@const optType = c.opt_type || 'CE'}
                              {@const openPrem = (c.open_prem != null ? Number(c.open_prem) : 0).toFixed(1)}
                              {@const curLtp = (c.ltp != null ? Number(c.ltp) : 0).toFixed(1)}
                              {@const gPct = gainVal.toFixed(1)}
                              <div class="option-card" title="Click to view 20% incremental milestone timeline">
                                <div class="opt-left">
                                  <span class="layer-tag {tagCls}" title="{isOpening ? 'Opening strike (locked at 09:15)' : 'Running strike (accumulated)'}">{tag}</span>
                                  <div class="opt-meta">
                                    <div class="strike-wrap">
                                      <span class="strike-price">₹{(+c.strike).toLocaleString('en-IN')}</span>
                                      <span class="opt-badge {optType}">{optType}</span>
                                    </div>
                                    <div class="premium-flow">
                                      <span class="flow-open" title="Strike open price">₹{openPrem}</span>
                                      <span class="flow-arrow">→</span>
                                      <span class="flow-ltp" title="Current LTP">₹{curLtp}</span>
                                    </div>
                                  </div>
                                </div>
                                <div class="opt-right">
                                  <span class="gain-badge {gClass}">{emoji} +{gPct}%</span>
                                </div>
                              </div>
                            {/each}
                            {#if !(s.contracts && s.contracts.length)}
                              <div style="padding:10px 16px;color:var(--t2);font-size:10px;text-align:center;">⏳ Loading premium contracts… refresh in a moment.</div>
                            {/if}
                          </div>
                        </td>
                      </tr>
                    {/if}
                  {/if}
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .board-wrap { display:flex; flex-direction:column; height:100%; overflow:hidden; }
  .ch { padding:9px 12px; background:var(--ch-bg); border-bottom:1px solid var(--b); display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }
  .ct { font-size:12.5px; font-weight:700; letter-spacing:.07em; text-transform:uppercase; color:#fff; display:flex; align-items:center; gap:8px; }
  .cbadge { font-size:10px; font-weight:600; padding:2px 7px; border-radius:10px; background:var(--card2); color:var(--acc); border:1px solid var(--b); }
  .fb { padding:6px; display:flex; gap:5px; flex-wrap:wrap; border-bottom:1px solid var(--b); flex-shrink:0; background:var(--card); }
  .sub-bar { padding:4px 8px; display:flex; gap:5px; flex-wrap:wrap; border-bottom:1px solid var(--b); flex-shrink:0; align-items:center; background:rgba(0,0,0,.2); }
  .fbtn { padding:4px 10px; border-radius:5px; border:1px solid var(--b); font-size:11px; font-weight:600; background:var(--card); color:var(--t2); cursor:pointer; transition:all .13s; white-space:nowrap; }
  .fbtn:hover,.fbtn.on { background:var(--accg); border-color:var(--acc); color:var(--t1); }
  .ibtn { background:var(--card); border:1px solid var(--b); color:var(--t2); border-radius:5px; font-size:12px; padding:2px 7px; cursor:pointer; }

  /* Confluence legend */
  .conf-leg { padding:4px 10px; font-size:8.5px; color:var(--t3); border-bottom:1px solid var(--b); display:flex; align-items:center; gap:8px; flex-shrink:0; flex-wrap:wrap; }
  .dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:2px; }
  .dot.b { background:var(--bull); box-shadow:0 0 3px var(--bull); }
  .dot.r { background:var(--bear); box-shadow:0 0 3px var(--bear); }
  .dot.n { background:var(--neu);  box-shadow:0 0 3px var(--neu); }

  /* Max Pain stats bar */
  .mp-stats-bar { display:flex; gap:6px; padding:6px 10px; border-bottom:1px solid var(--b); flex-shrink:0; overflow-x:auto; }
  .mp-stats-bar::-webkit-scrollbar { height:2px; }
  .mp-card { flex:1; min-width:100px; background:var(--card); border:1px solid var(--b); border-radius:7px; padding:7px 10px; cursor:pointer; transition:all .14s; }
  .mp-card:hover,.mp-card.active { border-color:var(--acc); background:var(--accg); }
  .mp-card.mp-refresh { min-width:90px; }
  .mp-lbl { font-size:8.5px; font-weight:800; color:var(--t2); text-transform:uppercase; letter-spacing:.04em; margin-bottom:3px; }
  .mp-val { font-size:22px; font-weight:800; font-family:var(--mono); line-height:1.1; }
  .val-bull { color:var(--bull); }
  .val-bear { color:var(--bear); }
  .val-achieve { color:var(--amb); }
  .val-total { color:var(--acc); }
  .mp-sub { font-size:7.5px; color:var(--t3); margin-top:2px; }
  .mp-ts { font-size:11px; font-weight:700; font-family:var(--mono); color:var(--t1); margin-top:3px; }
  .mp-refresh:hover .mp-ts { color:var(--acc); }

  /* Split */
  .board-split { display:flex; flex:1; overflow:hidden; min-height:0; }
  .board-content { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }
  .board-loading { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px; text-align:center; }

  /* OI Dock */
  .oi-dock { width:175px; flex-shrink:0; background:var(--card); border-right:1px solid var(--b); display:flex; flex-direction:column; overflow:hidden; }
  .oi-dock-hdr { padding:6px 8px; background:var(--th-bg); border-bottom:1px solid var(--b); flex-shrink:0; }
  .oi-dock-title { font-size:10px; font-weight:700; color:#fbbf24; text-transform:uppercase; letter-spacing:.06em; display:flex; align-items:center; gap:5px; margin-bottom:4px; }
  .oi-dock-input { width:100%; background:var(--card2); border:1px solid var(--b); border-radius:4px; color:var(--t1); outline:none; padding:3px 6px; font-size:9px; }
  .oi-dock-list { flex:1; overflow-y:auto; }
  .oi-dock-list::-webkit-scrollbar { width:3px; }
  .oi-dock-list::-webkit-scrollbar-thumb { background:var(--b); border-radius:2px; }
  .oi-dock-item { display:flex; align-items:center; gap:5px; padding:4px 8px; border-bottom:1px solid rgba(24,48,93,.3); font-size:9px; cursor:pointer; transition:background .12s; }
  .oi-dock-item:hover { background:rgba(255,255,255,.04); }
  .oi-dock-item.top-spurt { background:rgba(251,191,36,.05); }
  .oi-rank { font-size:9px; color:var(--t3); font-family:var(--mono); width:14px; text-align:center; }
  .oi-sym { font-size:10px; font-weight:700; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .pct-badge { font-size:8.5px; font-weight:800; padding:1px 4px; border-radius:3px; font-family:var(--mono); }
  .pct-badge.bull { background:rgba(34,197,94,.15); color:var(--bull); border:1px solid rgba(34,197,94,.3); }
  .pct-badge.bear { background:rgba(239,68,68,.13); color:var(--bear); border:1px solid rgba(239,68,68,.25); }

  /* Table shell */
  .tbl-shell { flex:1; overflow:auto; }
  .tbl-shell::-webkit-scrollbar { width:4px; height:4px; }
  .tbl-shell::-webkit-scrollbar-thumb { background:var(--b); border-radius:2px; }

  /* Table */
  .tbl { width:100%; border-collapse:collapse; font-size:11px; }
  .tbl thead th { padding:5px 4px; font-size:9.5px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:#fff; border-bottom:1px solid var(--b); white-space:nowrap; background:var(--th-bg); position:sticky; top:0; z-index:10; text-align:left; }
  .tbl thead th.sortable { cursor:pointer; user-select:none; }
  .tbl thead th.sortable:hover { color:var(--acc); }
  .tbl tbody tr { border-bottom:1px solid var(--b); transition:background .15s; cursor:pointer; }
  .tbl tbody tr:hover { background:var(--row-hover); }
  .tbl tbody tr:nth-child(even) { background:var(--row-alt); }
  .tbl td { padding:4px 5px; white-space:nowrap; vertical-align:middle; }
  .tbl tbody tr.BR td:first-child { border-left:3px solid var(--bull); }
  .tbl tbody tr.BE td:first-child { border-left:3px solid var(--bear); }
  .tbl tbody tr.NE td:first-child { border-left:3px solid var(--neu); }
  .tbl tbody tr.glow-hi { background:rgba(34,197,94,.07); }
  .tbl tbody tr.glow-hi:hover { background:rgba(34,197,94,.12); }
  .tbl tbody tr.glow-bear-hi { background:rgba(239,68,68,.06); }
  .tbl tbody tr.glow-bear-hi:hover { background:rgba(239,68,68,.11); }
  .tbl tbody tr.glow-med { background:rgba(234,179,8,.04); }
  .rank { font-size:10px; color:var(--t2); font-family:var(--mono); font-weight:800; }
  .sym  { font-weight:800; font-size:12px; }
  .mono { font-family:var(--mono); font-weight:700; }
  .bull { color:var(--bull); font-weight:800; }
  .bear { color:var(--bear); font-weight:800; }
  .neu  { color:var(--neu);  font-weight:800; }
  .oi-zero { color:#fff; }
  .cap-l { background:rgba(59,130,246,.18); color:var(--acc); font-size:10px; font-weight:800; padding:1px 5px; border-radius:3px; border:1px solid rgba(59,130,246,.35); }
  .cap-m { background:rgba(234,179,8,.15); color:var(--amb); font-size:10px; font-weight:800; padding:1px 5px; border-radius:3px; border:1px solid rgba(234,179,8,.35); }
  .cap-s { background:rgba(168,85,247,.15); color:var(--pur); font-size:10px; font-weight:800; padding:1px 5px; border-radius:3px; border:1px solid rgba(168,85,247,.3); }
  .spot-badge { font-size:10px; font-weight:800; padding:2px 6px; border-radius:5px; font-family:var(--mono); display:inline-block; }
  .spot-badge.bull { background:rgba(34,197,94,.18); color:#22c55e; border:1px solid rgba(34,197,94,.42); }
  .spot-badge.bear { background:rgba(239,68,68,.18); color:#ef4444; border:1px solid rgba(239,68,68,.42); }
  .tf { font-size:10px; font-weight:800; padding:2px 5px; border-radius:3px; display:inline-block; border:1px solid; }
  .tf.B { background:rgba(34,197,94,.18); color:var(--bull); border-color:rgba(34,197,94,.38); }
  .tf.R { background:rgba(239,68,68,.13); color:var(--bear); border-color:rgba(239,68,68,.3); }
  .tf.N { background:rgba(234,179,8,.12); color:var(--neu); border-color:rgba(234,179,8,.32); }
  .sc-hi { font-size:9px; font-weight:800; padding:1px 6px; border-radius:4px; font-family:var(--mono); background:rgba(34,197,94,.2); color:var(--bull); border:1px solid rgba(34,197,94,.38); }
  .sc-me { font-size:9px; font-weight:800; padding:1px 6px; border-radius:4px; font-family:var(--mono); background:rgba(234,179,8,.18); color:var(--amb); border:1px solid rgba(234,179,8,.35); }
  .sc-lo { font-size:9px; font-weight:800; padding:1px 6px; border-radius:4px; font-family:var(--mono); background:rgba(239,68,68,.13); color:var(--bear); border:1px solid rgba(239,68,68,.25); }
  .fb-lb { background:rgba(34,197,94,.15); color:var(--bull); font-size:10px; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(34,197,94,.32); }
  .fb-sb { background:rgba(239,68,68,.13); color:var(--bear); font-size:10px; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(239,68,68,.28); }
  .fb-sc { background:rgba(234,179,8,.13); color:var(--amb); font-size:10px; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(234,179,8,.32); }
  .fb-lu { background:rgba(168,85,247,.13); color:var(--pur); font-size:10px; font-weight:800; padding:1px 6px; border-radius:4px; border:1px solid rgba(168,85,247,.3); }
  .fb-no { color:var(--t3); font-size:11px; }

  /* ── NSE Heatmap ─────────────────────────────────────────────────── */
  .hm-wrap { display:flex; flex-direction:column; height:100%; overflow:hidden; }
  .heatmap-topbar { display:flex; align-items:center; justify-content:space-between; padding:6px 10px; border-bottom:1px solid var(--b); flex-shrink:0; flex-wrap:wrap; gap:6px; }
  .heatmap-title { display:flex; align-items:center; gap:8px; font-size:11px; font-weight:700; }
  .heatmap-legend { display:flex; align-items:center; gap:3px; }
  .hm-leg-chip { font-size:7.5px; font-weight:800; padding:2px 5px; border-radius:3px; font-family:var(--mono); }
  .hm-leg-p5 { background:#14532d; color:#4ade80; }
  .hm-leg-p3 { background:#166534; color:#86efac; }
  .hm-leg-p1 { background:#15803d; color:#bbf7d0; }
  .hm-leg-0  { background:var(--card2); color:var(--t2); }
  .hm-leg-m1 { background:#7f1d1d; color:#fca5a5; }
  .hm-leg-m3 { background:#991b1b; color:#f87171; }
  .hm-leg-m5 { background:#b91c1c; color:#fecaca; }
  .sec-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:4px; padding:8px 10px; overflow-y:auto; flex:1; align-content:start; }
  .sec-grid::-webkit-scrollbar { width:4px; }
  .sec-grid::-webkit-scrollbar-thumb { background:var(--b); border-radius:2px; }
  .sec-card { border:1px solid var(--b); border-radius:7px; padding:7px 8px; cursor:pointer; transition:all .15s; }
  .sec-card:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(0,0,0,.3); }
  .sec-card.selected { border:2px solid var(--acc); }
  .sec-card.is-green { background:rgba(21,128,61,.25); border-color:rgba(34,197,94,.25); }
  .sec-card.is-green:hover { background:rgba(21,128,61,.38); }
  .sec-card.is-red { background:rgba(153,27,27,.22); border-color:rgba(239,68,68,.22); }
  .sec-card.is-red:hover { background:rgba(153,27,27,.35); }
  .sec-card.is-zero { background:var(--card2); }
  .sec-card-hdr { display:flex; justify-content:space-between; align-items:center; gap:4px; margin-bottom:3px; }
  .sec-card-name { font-size:8.5px; font-weight:800; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#fff; }
  .sec-card-chg { font-size:10px; font-weight:800; font-family:var(--mono); flex-shrink:0; }
  .sec-card-chg.pos { color:var(--bull); } .sec-card-chg.neg { color:var(--bear); } .sec-card-chg.neu { color:var(--t2); }
  .sec-card-stats { font-size:7px; color:var(--t3); display:flex; justify-content:space-between; margin-bottom:3px; }
  .sec-card-pills { display:flex; gap:2px; flex-wrap:wrap; }
  .sec-pill { font-size:6.5px; font-weight:800; padding:0 3px; border-radius:3px; }
  .sec-pill.lb { background:rgba(34,197,94,.2); color:var(--bull); }
  .sec-pill.sc { background:rgba(234,179,8,.2); color:var(--amb); }
  .sec-pill.sb { background:rgba(239,68,68,.18); color:var(--bear); }
  .sec-pill.lu { background:rgba(168,85,247,.18); color:var(--pur); }

  /* Drilldown */
  .sec-detail-container { padding:8px 10px 0; flex-shrink:0; border-bottom:1px solid var(--b); display:flex; flex-direction:column; }
  .sec-detail-hdr { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px; margin-bottom:6px; }
  .sec-detail-left { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .sec-back-btn { background:var(--card2); border:1px solid var(--b); color:var(--t2); border-radius:5px; padding:2px 8px; font-size:10px; cursor:pointer; }
  .sec-back-btn:hover { color:var(--acc); border-color:var(--acc); }
  .sec-detail-title { font-size:13px; font-weight:800; color:#fff; }
  .sec-detail-metrics { display:flex; gap:8px; flex-wrap:wrap; }
  .sec-metric-chip { font-size:8.5px; font-weight:600; color:var(--t2); background:var(--card2); border:1px solid var(--b); border-radius:10px; padding:2px 8px; }

  /* Watchlist */
  .wl-panel { display:flex; flex-direction:column; height:100%; overflow:hidden; }
  .wl-header { display:flex; align-items:center; justify-content:space-between; padding:8px 12px; border-bottom:1px solid var(--b); flex-shrink:0; gap:10px; flex-wrap:wrap; }
  .wl-title { font-size:12px; font-weight:800; color:#fff; flex-shrink:0; }
  .wl-search-wrap { position:relative; flex:1; max-width:320px; }
  .wl-search { width:100%; background:var(--card); border:1px solid var(--b); border-radius:5px; color:var(--t1); outline:none; padding:4px 10px; font-size:10px; font-family:inherit; }
  .wl-search:focus { border-color:var(--acc); }
  .wl-suggestions { position:absolute; top:100%; left:0; right:0; background:var(--card2); border:1px solid var(--b); border-radius:5px; z-index:50; box-shadow:0 4px 12px rgba(0,0,0,.4); }
  .wl-sug-item { padding:5px 10px; font-size:10px; font-weight:700; cursor:pointer; }
  .wl-sug-item:hover { background:var(--accg); color:var(--t1); }
  .wl-rm { background:transparent; border:1px solid rgba(239,68,68,.35); color:var(--bear); border-radius:4px; padding:1px 5px; font-size:9px; cursor:pointer; }
  .wl-rm:hover { background:rgba(239,68,68,.15); }

  /* Contracts Sub-row Expansion (Vertical List matching Screenshot 2) */
  .contracts-subrow {
    background: rgba(0, 0, 0, 0.45) !important;
    border-bottom: 1px solid rgba(55, 110, 210, .25);
  }
  .contracts-container {
    padding: 3px 0;
  }
  .option-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    transition: background .15s;
  }
  .option-card:last-child {
    border-bottom: none;
  }
  .option-card:hover {
    background: rgba(255, 255, 255, 0.03);
  }
  .opt-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .layer-tag {
    font-size: 12px;
    display: inline-block;
    width: 16px;
    text-align: center;
  }
  .layer-tag.gold {
    color: #e3b341;
  }
  .layer-tag.run {
    color: #58a6ff;
  }
  .opt-meta {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .strike-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .strike-price {
    font-size: 12px;
    font-weight: 800;
    font-family: var(--mono);
    color: var(--t1);
  }
  .opt-badge {
    font-size: 8px;
    font-weight: 800;
    padding: 2px 5px;
    border-radius: 3px;
    line-height: 1;
    font-family: var(--mono);
  }
  .opt-badge.CE {
    background: rgba(34, 197, 94, .18);
    color: var(--bull);
    border: 1px solid rgba(34, 197, 94, .3);
  }
  .opt-badge.PE {
    background: rgba(239, 68, 68, .18);
    color: var(--bear);
    border: 1px solid rgba(239, 68, 68, .3);
  }
  .premium-flow {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--t2);
    font-family: var(--mono);
  }
  .flow-open {
    color: var(--t2);
  }
  .flow-arrow {
    font-size: 10px;
    opacity: .5;
    margin: 0 2px;
    color: var(--t3);
  }
  .flow-ltp {
    color: var(--t1);
    font-weight: 700;
  }
  .opt-right {
    text-align: right;
  }
  .gain-badge {
    font-size: 11px;
    font-weight: 800;
    font-family: var(--mono);
    padding: 2px 6px;
    border-radius: 4px;
  }
  .gain-badge.gain-fire {
    color: #ff8c40;
    background: rgba(239, 120, 40, .18);
    border: 1px solid rgba(239, 120, 40, .35);
    text-shadow: 0 0 6px rgba(255, 140, 64, .4);
  }
  .gain-badge.gain-rocket {
    color: var(--bull);
    background: rgba(34, 197, 94, .15);
    border: 1px solid rgba(34, 197, 94, .28);
  }
  .gain-badge.gain-up {
    color: var(--acc);
    background: rgba(59, 130, 246, .12);
    border: 1px solid rgba(59, 130, 246, .25);
  }
  .gain-badge.gain-stale {
    color: var(--t3);
    background: rgba(120, 120, 120, .1);
    border: 1px solid rgba(120, 120, 120, .2);
    font-style: italic;
  }

  /* Futures Buildup 5 Stats Cards */
  .futbld-stats-bar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 6px;
    margin: 6px 0 8px;
  }
  .fb-stat-card {
    background: var(--card2);
    border: 1px solid var(--b);
    border-radius: 6px;
    padding: 8px 12px;
    cursor: pointer;
    transition: all .15s;
    text-align: center;
  }
  .fb-stat-card:hover {
    border-color: var(--acc);
    background: rgba(255,255,255,0.03);
  }
  .fb-stat-card.active {
    border-color: var(--acc);
    background: var(--accg);
  }
  .fb-stat-lbl {
    font-size: 8.5px;
    font-weight: 800;
    color: var(--t2);
    letter-spacing: .05em;
    margin-bottom: 2px;
  }
  .fb-stat-val {
    font-size: 16px;
    font-weight: 900;
    font-family: var(--mono);
  }
  .val-lb { color: var(--bull); }
  .val-sb { color: var(--bear); }
  .val-sc { color: var(--amb); }
  .val-lu { color: var(--pur); }
  .val-flat { color: #ffffff; }

  /* Inline Candlestick Chart Subrow */
  .chart-subrow {
    background: #020617 !important;
    border-bottom: 2px solid var(--acc);
  }
  .inline-chart-box {
    padding: 6px 12px 10px;
    background: var(--card);
  }
  .inline-chart-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: #091224;
    border: 1px solid var(--b);
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    flex-wrap: wrap;
    gap: 8px;
  }
  .ichart-info {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  .ichart-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    background: var(--accg);
    color: var(--t1);
    font-family: var(--mono);
  }
  .ichart-levels {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-wrap: wrap;
  }
  .lvl-badge {
    font-size: 9px;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 3px;
    font-family: var(--mono);
  }
  .lvl-badge.pdh {
    background: rgba(34, 197, 94, .12);
    color: var(--bull);
    border: 1px solid rgba(34, 197, 94, .35);
  }
  .lvl-badge.pdl {
    background: rgba(239, 68, 68, .12);
    color: var(--bear);
    border: 1px solid rgba(239, 68, 68, .35);
  }
  .lvl-badge.tc {
    background: rgba(168, 85, 247, .12);
    color: var(--pur);
    border: 1px solid rgba(168, 85, 247, .35);
  }
  .lvl-badge.piv {
    background: rgba(6, 182, 212, .12);
    color: var(--cyn);
    border: 1px solid rgba(6, 182, 212, .35);
  }
  .lvl-badge.bc {
    background: rgba(129, 140, 248, .12);
    color: #818cf8;
    border: 1px solid rgba(129, 140, 248, .35);
  }
  .ichart-actions {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }
  .tf-btn-group {
    display: flex;
    border: 1px solid var(--b);
    border-radius: 4px;
    overflow: hidden;
  }
  .ichart-tf-btn {
    font-size: 9.5px;
    font-weight: 800;
    padding: 4px 8px;
    background: var(--card2);
    color: #cbd5e1;
    border: none;
    cursor: pointer;
    transition: all .15s;
    user-select: none;
    min-height: 26px;
  }
  .ichart-tf-btn:hover {
    background: var(--bhi);
    color: #ffffff;
  }
  .ichart-tf-btn.active {
    background: var(--acc);
    color: #ffffff;
  }
  .chart-popout-btn {
    font-size: 9px;
    font-weight: 700;
    padding: 4px 8px;
    background: var(--accg);
    color: var(--acc);
    border: 1px solid var(--b);
    border-radius: 4px;
    text-decoration: none;
    transition: all .15s;
    display: inline-flex;
    align-items: center;
    min-height: 26px;
  }
  .chart-popout-btn:hover {
    background: var(--acc);
    color: #ffffff;
  }
  .ichart-canvas-container {
    position: relative;
    width: 100%;
    height: 380px;
    background: #ffffff;
    border: 1px solid var(--b);
    border-top: none;
    border-radius: 0 0 6px 6px;
    overflow: hidden;
    touch-action: none;
  }
  .ichart-canvas {
    width: 100%;
    height: 100%;
    display: block;
  }
  .ichart-error-msg {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    padding: 14px 22px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    text-align: center;
    max-width: 80%;
    line-height: 1.5;
    z-index: 5;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }
</style>
