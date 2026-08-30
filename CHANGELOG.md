# TradeSignal NextGen — Change Log

## 2026-08-30 — Master Board Score Execution & Reactivity Fix

**Goal:** Eliminate unreachable dead code in `mapStocks` so `calcScore(row)` executes for every stock, and ensure Svelte reactive UI updates when live crossover stream updates are processed.

**Files Changed:**
- `NextGen/frontend/src/routes/360-command-center/+page.svelte` — Replaced early object return with `const row = { ... }` prior to `row.score = calcScore(row)`, and added `stocks = stocks;` at the end of `applyCrossoverData(crossRes)`.
- `NextGen/frontend/dist/` — Rebuilt and verified full static distribution bundle.

---

## 2026-08-30 — Dynamic Multi-Factor SCORE Calculation for 360° Master Board

**Goal:** Restore the 0–10 composite multi-factor score calculation (`calcScore`) in `360-command-center` so the Master Board displays active scores, color badges (A/B/C), and score-intensity row glows instead of showing zero.

**Files Changed:**
- `NextGen/frontend/src/routes/360-command-center/+page.svelte` — Implemented `calcScore(s)` incorporating timeframe confluence, OI intensity, RVOL, Fast Hurdle, Futures Buildup (`LB`/`SB`), and DXCount direction alignment, calculating `score` on each row during initial mapping and subsequent crossover stream updates.
- `NextGen/frontend/dist/` — Rebuilt and updated pre-compiled static distribution bundle.

---

## 2026-08-30 — Standalone New-Tab Navigation for 360° Command Center & OI Spurt Scanner

**Goal:** Allow 360° Command Center and OI Spurt Scanner to open in dedicated browser tabs directly when clicked from the left navigation bar, rendering pure standalone trading workspaces with no left menu bar or edge hover triggers.

**Files Changed:**
- `NextGen/frontend/src/lib/components/Sidebar.svelte` — Added `newTab: true` to `360-command-center` and `oi-spurt-scanner` route definitions, and updated `navigate(item)` to dispatch `window.open('/' + item.id, '_blank')`.
- `NextGen/frontend/src/routes/+layout.svelte` — Omitted `<Sidebar>` completely and eliminated `edge-trigger-zone` hover detector when `isFullBleed` is active (`/360-command-center` and `/oi-spurt-scanner`).
- `NextGen/frontend/dist/` — Rebuilt and updated pre-compiled static distribution bundle.

---

## 2026-08-30 — Dependent SQLite Tables Schema Initialization Fix

**Goal:** Ensure all dependent snapshot, alert history, and OI spurt tables (`fno_futures_buildup_snapshot`, `fno_gainers_snapshots`, `premium_spike_alerts`, `live_breakout_alerts`, `oi_spurt_log`) are created during `init_db()` and in `setup_termux.sh`.

**Files Changed:**
- `NextGen/backend/core/db.py` — Added DDL statements and time-series indexes for all snapshot and alert tracking tables.
- `NextGen/setup_termux.sh` — Added explicit Step 6 to run `init_db()` upon setup.
- `NextGen/backend/tests/test_week2_core.py` — Added assertions verifying all 12 core and snapshot tables are initialized.

---

## 2026-08-30 — Modern FastAPI Lifespan Handler Migration

**Goal:** Replace deprecated `@app.on_event("startup")` and `@app.on_event("shutdown")` in `server.py` with FastAPI's official `@asynccontextmanager` lifespan handler to eliminate startup deprecation warnings.

**Files Changed:**
- `NextGen/backend/server.py` — Implemented `@asynccontextmanager async def lifespan(app: FastAPI)` managing `init_db()` and `AgentOrchestrator` startup/shutdown cleanly.

---

## 2026-08-30 — Termux Global Symlink Resolution & Pre-Built UI Bundle Tracking

**Goal:** Resolve Termux global symlink execution path bug (`/data/data/com.termux/files/usr/bin/backend`), track pre-built `frontend/dist` in repository for zero-build mobile deployment, and unify default port to 5000.

**Files Changed / Added:**
- `NextGen/nxtrd` — Implemented recursive symlink resolution to find true repository folder regardless of symlink execution path.
- `NextGen/start_termux.sh` — Implemented recursive symlink resolution for background session runner.
- `NextGen/.gitignore` — Whitelisted `!frontend/dist/` to include pre-built UI bundle.
- `NextGen/frontend/dist/` — Built and committed full static SvelteKit distribution bundle.
- `NextGen/backend/server.py` — Unified default fallback port to `PORT=5000`.

---

## 2026-08-29 — Uvicorn & WebSocket Dependencies Permanent Fix for Termux & Cross-Platform

**Goal:** Ensure `uvicorn[standard]` and `websockets` are explicitly defined in `requirements.txt`, installed in `setup_termux.sh`, and automatically recovered on first launch in `nxtrd`.

**Files Changed:**
- `NextGen/backend/requirements.txt` — Added `uvicorn[standard]>=0.30.0` and `websockets>=12.0`.
- `NextGen/setup_termux.sh` — Added explicit installation of `uvicorn[standard]` and `websockets`.
- `NextGen/nxtrd` — Added automatic fallback check to self-install `uvicorn` and `websockets` if missing before server launch.

---

## 2026-08-29 — Git Configuration & Governance for `NxTrd` Repository

**Goal:** Configure git tracking in `NextGen/` to target exclusively the `NxTrd` remote repository (`https://github.com/novatechnolab/NxTrd.git`) and update workspace governance rules.

**Files Changed / Added:**
- `NextGen/.agents/AGENTS.md` — Updated **Repository & Commit Discipline** rule to target `NxTrd` (`https://github.com/novatechnolab/NxTrd.git`).
- `NextGen/.gitignore` — Created repository `.gitignore` for Python, Svelte/Node, environment secrets, and runtime data.
- Git configuration — Initialized git in `NextGen/` with remotes `origin` and `nxtrd` set to `https://github.com/novatechnolab/NxTrd.git`.

---

**Goal:** Provide automated setup for Android Termux and universal one-command execution via `nxtrd` with automatic virtual environment activation, wake-lock acquisition, device IP resolution, and background `tmux` runner support.

**Files Created:**
- `NextGen/nxtrd` — Universal executable server launcher with IP detection and wake-lock management (`chmod +x`).
- `NextGen/setup_termux.sh` — Automated one-time Termux installer configuring TUR repo, precompiled ARM64 numpy/pandas, `.venv`, and linking global `$PREFIX/bin/nxtrd`.
- `NextGen/start_termux.sh` — Background persistent `tmux` session runner with automatic restart resilience.

---

## 2026-08-29 — Rebranding to Nxtrd Across NextGen

**Goal:** Rebrand the application to **Nxtrd** across all user-facing frontend components, headers, browser titles, metadata, package configuration, and backend API service definitions.

**Files Changed:**
- `NextGen/frontend/src/lib/components/Sidebar.svelte` — Updated navigation brand header title to `Nxtrd`.
- `NextGen/frontend/src/routes/360-command-center/_components/TopBar360.svelte` — Updated brand logo badge to `NX` and brand title to `Nxtrd`.
- `NextGen/frontend/src/routes/360-command-center/+page.svelte` — Updated page `<title>` to `360° Command Center — Nxtrd`.
- `NextGen/frontend/src/app.html` & `NextGen/frontend/index.html` — Updated root document title to `Nxtrd — NSE F&O Intelligence`.
- `NextGen/frontend/package.json` — Updated package name to `nxtrd-frontend`.
- `NextGen/backend/server.py` — Updated FastAPI application title to `Nxtrd API`.
- `NextGen/backend/routers/ws.py` — Updated WebSocket connection acknowledgement message to `Connected to Nxtrd Live Stream`.

---

## 2026-08-29 — Market Hours Schedule Updated to 09:15–15:40 IST

**Goal:** Extend live market hours window to 09:15–15:40 IST across backend agent loops and frontend session detectors to maintain real-time high-frequency streaming and prevent premature EOD mode transitions through the post-market closing auction.

**Files Changed:**
- `NextGen/backend/core/utils.py` — Updated `is_market_hours()` upper limit to `time(15, 40)`.
- `NextGen/backend/routers/market.py` — Updated `GET /api/market-status` session boundary to `15 * 60 + 40` (15:40 IST).
- `NextGen/frontend/src/routes/360-command-center/+page.svelte` — Updated `isMarketOpen()` to `mins <= 940` (15:40 IST).

---

## 2026-08-29 — Full-Bleed 360 Command Center & Edge-Hover Auto-Hide Sidebar

**Goal:** Provide maximum full-screen viewport space for 360 Command Center by eliminating the redundant global top header on the route, removing page-level padding, and configuring the left navigation sidebar to auto-hide by default with smooth slide-out reveal when hovering near the left edge (< 16px).

**Files Changed:**
- `NextGen/frontend/src/lib/components/Sidebar.svelte` — Added `isAutoHide` and `isHoverOpen` props, binding hover detection and applying overlay transformation styles (`transform: translateX(-100%)` → `translateX(0)`).
- `NextGen/frontend/src/routes/+layout.svelte` — Conditionally suppressed global `<Topbar>` on `/360-command-center`, applied full-bleed zero-padding wrapper, and installed the invisible left-edge trigger zone.

---

## 2026-08-29 — Column 3: Live Breakouts, Squeeze & EMA Coil Watchlists & Session Stats Integration

**Goal:** Restore Column 3 in 360 Command Center to render genuine live breakout and EMA collision alerts (116 alerts), Squeeze Watchlist (0), EMA Coil Watchlist (51 coils with real spot prices & gap delta), and live 4-card Session Stats matching the reference implementation and visual design.

**Files Changed:**
- `NextGen/backend/agents/ema_agent.py` — In `get_live_breakouts()`, enriched `ema_coils` with live spot price (`last_ltp`) looked up from the latest futures buildup snapshot map, and updated query limit to capture up to 200 session alerts.
- `NextGen/frontend/src/routes/360-command-center/+page.svelte` — Captured full `liveBreakoutData` payload (`triggered_alerts`, `collision_alerts`, `bb_squeezes`, `ema_coils`), computed reactive dynamic `sessionStats` (Alerts Today, OI Spurts, Long B/U, Short B/U), and passed props to `<RightPanel>`.
- `NextGen/frontend/src/routes/360-command-center/_components/RightPanel.svelte` — Completely rebuilt Column 3 with:
  1. Section 1 (Live Breakouts): Merged `triggered_alerts` + `collision_alerts` with directional arrows (`▲`/`▼`), badges (`Grade A`, `5M Cross`, `EMA COLLISION`), exact timestamps, LTP (`₹2608.7`), and volume multipliers (`×747.3`).
  2. Section 2 (Squeeze Watchlist): Amber/gold squeeze badge, LTP, duration, and empty state ("No active squeezes").
  3. Section 3 (EMA Coil Watchlist): Cyan coil icon `⟳`, symbol, `Coil` badge, LTP, delta gap pill (`- Δ0.050%`), and trigger time (`15:25`) for all 51 coils.
  4. Section 4 (Confluence Rules & Session Stats): Confluence rule scores and 4-card live Session Stats grid matching the reference UI.

---

## 2026-08-29 — Zero-Mock Policy Enforcement & Real Historical Candlestick Chart Integration

**Goal:** Completely eliminate synthetic/dummy candle generator from the Master Board inline chart in Futures Buildup, enforce universal Zero-Mock policy with explicit error banners, connect backend SQLite DB to 56k instruments and 147k cached OHLCVs, and register `GET /api/historical`.

**Files Changed:**
- `NextGen/.agents/AGENTS.md` — Enshrined universal **Zero Mock / Zero Synthetic Data Discipline** prohibiting mock or synthetic fallbacks across all features without exception.
- `NextGen/backend/core/db.py` — Updated `DB_PATH` default resolution to load `tradesignal_cache.db` (56,765 instruments + 147,185 OHLCV records).
- `NextGen/backend/routers/core.py` — Registered `GET /api/historical` route delegating queries to `KiteDataAgent.get_historical()` with smart caching.
- `NextGen/backend/agents/kite_data_agent.py` — Extended default intraday query window to 10 days for robust off-hours and weekend cache retrieval.
- `NextGen/backend/repositories/ohlcv.py` — Added latest session fallback for out-of-market intraday queries.
- `NextGen/frontend/src/routes/360-command-center/_components/MasterBoard.svelte` — Purged all synthetic candle generators; integrated real OHLCV data parsing, EMA 9/21, VWAP, and added explicit error state banner when historical data is missing.

---

## 2026-08-29 — Breakouts Tab Data Accuracy, Labels & Real Triggered Alerts Integration

**Goal:** Fix Screen 3 (Breakouts) in 360 Command Center Alert Feed to render genuine breakout alerts (`triggered_alerts`), accurate price move percentages (`move_pct`), volume surge multipliers (`vol_multiplier`), real timestamps (`time`), and proper grade tags (`5M Cross`, `Grade A`) matching the reference implementation.

**Files Changed:**
- `NextGen/backend/agents/ema_agent.py` — Implemented `get_live_breakouts()` returning actual triggered breakout alerts from SQLite table with real spot movement percentage and volume multipliers.
- `NextGen/backend/routers/analytics.py` — Wired `GET /live-breakouts` to call `EmaAgent.get_live_breakouts()` directly.
- `NextGen/frontend/src/routes/360-command-center/+page.svelte` — Extracted `triggered_alerts` from `/api/live-breakouts` and passed `breakoutAlerts` to `<AlertFeed>`.
- `NextGen/frontend/src/routes/360-command-center/_components/AlertFeed.svelte` — Bound `breakoutGroups` to `breakoutAlerts`, formatting price moves (`Mv +X.XX%`), volume ratios (`Vol X.Xx`), exact event timestamps, and grade tags.

---

## 2026-08-30 — UI-14: OI Spurt Scanner

**Session goal:** Build the OI Spurt Scanner page in NextGen, above the 360° Command Center in the sidebar.

**Files created:**
- `frontend/src/routes/oi-spurt-scanner/+page.svelte` — main orchestrator
- `_components/LeftPanel.svelte` — stock list, OI% slider, 60s auto-refresh
- `_components/TabBar.svelte` — multi-tab navigation
- `_components/EmptyState.svelte` — empty state placeholder
- `_components/DetailView.svelte` — full 6-section detail panel (stat strip, 3-layer analytics, strike tables, retail action, synergy, heatmap, conviction)
- `_components/OIHeatmap.svelte` — 11-col chain heatmap table, ATM/MaxPain highlights, dual-side state panel
- `_components/TransitionConviction.svelte` — composite score gauge, ATM±3 table, wall strength registry
- `_components/AiAnalysisPanel.svelte` — collapsible AI analysis, purple gradient button, Gemini POST endpoint
- `_components/ToastContainer.svelte` — fixed toast notifications with 5s auto-dismiss

**Summary:** Full pixel-matched port of `oi-spurt-scanner.html` reference (2897 lines). Dark left panel + light right panel theme, JetBrains Mono + Syne fonts, all 4 API endpoints wired (spurt list, symbol detail, AI analyze, equity search). Build: ✓ 3.24s zero errors. Agent reuse: OiTransitionAgent (no new backend code).

---

## 2026-08-30 — Full-Bleed Layout Standard + OI Spurt UI Fixes

**Session goal:** Enforce full-bleed layout for OI Spurt Scanner; codify as mandatory rule for all future pages.

**Files changed:**
- `frontend/src/routes/+layout.svelte` — Extended `isFullBleed` condition to include `/oi-spurt-scanner`; Topbar hidden, sidebar auto-hides, zero padding on all full-bleed routes
- `frontend/src/routes/oi-spurt-scanner/_components/LeftPanel.svelte` — Converted to `position: fixed` overlay with `translateX(-100%)` default; 10px invisible edge-trigger strip; slides in on hover, out on mouse leave (250ms debounce)
- `frontend/src/routes/oi-spurt-scanner/+page.svelte` — Right panel `width: 100%` (LeftPanel now out of layout flow); search error message instead of hardcoded fallback
- `backend/routers/instruments.py` — Added `/equity-list` route (same shape as legacy server.py L3410)
- `backend/routers/oi.py` — Added `POST /oi/symbol/{symbol}/ai-analyze` route
- `backend/agents/oi_transition_agent.py` — Added `ai_analyze()` method (Gemini API, ports legacy oi_spurt_routes.py L1901)
- `.agents/AGENTS.md` — **Full-Bleed Page Layout Standard rule** added: mandatory for all future NextGen pages

**Summary:** All 4 OI Spurt Scanner API endpoints now wired and verified. Full-bleed + auto-hide left panel pattern set as universal standard for all new pages.
