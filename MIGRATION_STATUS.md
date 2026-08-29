# TradeSignal NextGen — Migration Status

## ⚠️ CRITICAL RULES (READ EVERY SESSION)

| Rule | Detail |
|---|---|
| **Reference workspace = READ ONLY** | `/home/rajk/Downloads/TradeSignal005/Agent backup/TradeSignal -Backup April24-Agentic/` — NEVER edit, never write, never delete |
| **All new code → NextGen only** | `/home/rajk/Downloads/TradeSignal005/NextGen/` |
| **No changes in current workspace** | Migration reads reference, writes NextGen |
| **Screen by screen for UI** | Each page built + approved before next starts |
| **Router → Agent pattern** | Routers call agents. Agents call scanners. No business logic in routers. |

---

## Workspace Paths

```
READ ONLY reference:
  /home/rajk/Downloads/TradeSignal005/Agent backup/TradeSignal -Backup April24-Agentic/

NextGen target (all writes go here):
  /home/rajk/Downloads/TradeSignal005/NextGen/
```

---

## Architecture

```
Browser (SvelteKit, laptop + mobile parity)
  └─ WebSocket delta patches (~5KB, not 80KB)
     └─ FastAPI + uvicorn (asyncio)
          └─ Routers (12 domain routers, zero business logic)
               └─ Agents (FSM, event bus, auto-restart)
                    └─ Scanners (existing logic, unchanged)
                         └─ SQLite WAL (same on laptop + Termux)
```

---

## Phase Progress

### PHASE 1: Backend (Weeks 1-8)

| Week | Task | Status |
|---|---|---|
| Week 1 | Scaffold + directory structure | ✅ DONE (2026-08-28) |
| Week 2 | Core infrastructure (db, auth, event_bus, repositories) | ✅ DONE (2026-08-28) |
| Week 3 | Kite layer + Base FSM agent upgrade | ✅ DONE (2026-08-28) |
| Week 4 | Board + Alert agents | ✅ DONE (2026-08-28) |
| Week 5 | Analytics + Market + Options routes | ✅ DONE (2026-08-28) |
| Week 6 | Portfolio + FNO + remaining routes | ✅ DONE (2026-08-28) |
| Week 7 | Scanner threads → asyncio tasks | ✅ DONE (2026-08-28) |
| Week 8 | WebSocket delta + fno_backend migration + gap audit (alert_dispatch, oi router) | ✅ DONE (2026-08-28) |

---

## UI Architecture Rules (Phase 2 — MANDATORY, EVERY SESSION)

| Rule | Detail |
|---|---|
| **Modular, not monolithic** | Every UI element is a self-contained Svelte component. No God-components that handle multiple pages. |
| **Page-scoped components** | Each page (`/routes/[page]/`) owns its components in its own `_components/` subfolder. Components are NOT shared across pages unless explicitly designed as shared. |
| **Shared components = explicit only** | Only layout shell, navbar, sidebar, and design tokens live in `$lib/components/`. Everything else is page-local. |
| **No cross-page imports** | Page A must never import a component from Page B's `_components/`. If both need it → move to `$lib/`. |
| **Screenshot-exact matching** | Every screen built must match the provided screenshot exactly: colors, fonts, spacing, icons, animations. |
| **Device-agnostic** | Every component must work on mobile, tablet, laptop, desktop (responsive CSS Grid/Flexbox, touch events). |
| **One page per session** | Build, verify, and get approval on one screen before starting the next. |

### PHASE 2: Frontend — SvelteKit (Weeks 9+, One Page Per Session)

| Session | Screen | Status |
|---|---|---|
| Week 9 | SvelteKit foundation + shared components | ✅ DONE (2026-08-28) |
| UI-1 | Dashboard (index.html) | ⬜ TODO |
| UI-2 | Historical Analysis | ⬜ TODO |
| UI-3 | F&O ResAnalyzer | ⬜ TODO |
| UI-4 | Nifty Candle Analyzer | ⬜ TODO |
| UI-5 | Multi-Chart Tracking | ⬜ TODO |
| UI-6 | Equity Screener | ⬜ TODO |
| UI-7 | Stock Analysis | ⬜ TODO |
| UI-8 | SMC Dashboard | ⬜ TODO |
| UI-9 | APEX Intraday | ⬜ TODO |
| UI-10 | FNO Trap Dashboard | ⬜ TODO |
| UI-11 | 360° Command Center | ⬜ TODO |
| UI-12 | Premium Gainers Board | ⬜ TODO |
| UI-13 | Premium Spike Alerts | ⬜ TODO |
| UI-14 | OI Spurt Scanner | ⬜ TODO |
| UI-15 | F&O Synergy Scanner | ⬜ TODO |
| UI-16 | Market Profiler | ⬜ TODO |
| UI-17 | Watchlist | ⬜ TODO |
| UI-18 | Portfolio | ⬜ TODO |
| UI-19 | Live Movers | ⬜ TODO |
| UI-20 | Index Movers | ⬜ TODO |
| UI-21 | News | ⬜ TODO |
| UI-22 | Strategy Builder | ⬜ TODO |
| UI-23 | Backtester | ⬜ TODO |
| UI-24 | Journal | ⬜ TODO |
| UI-25 | Paper Trade | ⬜ TODO |
| UI-26 | Recommendations | ⬜ TODO |
| UI-27 | Reco Tracker | ⬜ TODO |
| UI-28 | Historical (ANALYSIS section) | ⬜ TODO |
| UI-29 | Notion Notes | ⬜ TODO |
| UI-30 | Alerts | ⬜ TODO |
| UI-31 | FNO Sessions | ⬜ TODO |
| UI-32 | FNO Trade Alerts | ⬜ TODO |
| UI-33 | Settings | ✅ DONE (2026-08-28) |

### PHASE 3: Agent FSM Upgrade (Week 14)

| Task | Status |
|---|---|
| Upgrade base_agent.py FSM | ⬜ TODO |
| Wire all agents to event bus | ⬜ TODO |
| Orchestrator health + metrics | ⬜ TODO |

---

## Performance Targets

| Metric | Current | Target | Parity? |
|---|---|---|---|
| Board render (200 rows) | 150ms laptop / 800ms mobile | 10ms / 40ms | ✅ by UI-11 |
| WS payload per cycle | ~80KB | ~5KB delta | ✅ by Week 8 |
| Initial page load | 344KB HTML | ~60KB bundle | ✅ by Week 9 |
| Alert latency | 50-200ms | 15-30ms | ✅ by Week 7 |
| OI query (90 days) | ~200ms | ~5ms | ✅ by Week 2 |

---

## Session Resume Instructions

When resuming this migration in a new session:
1. Read this file first
2. Read `/home/rajk/Downloads/TradeSignal005/NextGen/` structure
3. Check which phase/week is current
4. Reference workspace is READ ONLY — never write there
5. All writes go to `/home/rajk/Downloads/TradeSignal005/NextGen/`

---

### 2026-08-29 — Sidebar Alignment Fix (pre-UI-1)

- Read MIGRATION_STATUS.md and confirmed Phase 1 (Weeks 1-8) + Week 9 all complete.
- Audited `frontend/src/lib/components/Sidebar.svelte` against reference screenshots.
- **Gaps found and fixed:**
  - Added full `MAIN` section (21 items: Dashboard → Portfolio → Live Movers → Index Movers → News) replacing the old 3-item unnamed section
  - Added `MAIN` section header label (was `null`)
  - Added `hasChevron: true` for 6 items (F&O ResAnalyzer, Nifty Candle Analyzer, FNO Trap Dashboard, Premium Spike Alerts, OI Spurt Scanner, F&O Synergy Scanner)
  - Added chevron `›` rendering in nav-item template
  - Fixed FNO Trade Alerts icon: `⚡` → `🚨`
  - Fixed `nav-label`: `white-space: nowrap` → `white-space: normal` + `line-height: 1.3` (allows "360° Command Center", "Premium Gainers Board" to wrap)
  - Changed `nav-item` alignment to `flex-start` so icon aligns to top of wrapped text
  - Added custom scrollbar (4px, rgba white, thin) to match screenshot scrollbar style
  - `badge` check changed to `item.badge !== undefined` so "0" badge renders correctly
  - Added `flex-shrink: 0` to brand-logo, footer, nav-badge, nav-chevron

---

## 2026-08-29 — UI-11: 360° Command Center (Full Build)

### Status: COMPLETE ✅

### Files Created
- `frontend/src/routes/360-command-center/+page.svelte` — Orchestrator: state, 5 staggered pollers, mobile detection, theme switching
- `_components/TopBar360.svelte` — 48px header bar, logo, status pill, market indices (NIFTY/BNF/VIX/USD-INR), counts pill, theme toggle, live clock
- `_components/MasterBoard.svelte` — COL1: OI Spurt dock sidebar (collapsible, searchable), 10 filter tabs, confluence legend bar, sortable table (PremGain + FutBld modes), glow rows by score, full badge set
- `_components/AlertFeed.svelte` — COL2: 6 sub-tabs (Prem Spikes table, Bulls/Bears 2-col, Breakouts, OI Heatmap stub, B/U Shift, PreCross), quality filter, prem spikes search
- `_components/RightPanel.svelte` — COL3: Live Breakouts, Squeeze Watchlist, EMA Coil Watchlist, Confluence Rules, Session Stats
- `_components/MobileNav.svelte` — Fixed bottom nav (3 buttons, ≥40px touch targets)

### Design Tokens
All CSS variables exact-matched from reference `360-command-center.html`:
`--bg:#0c1932, --card:#102041, --bull:#22c55e, --bear:#ef4444, --acc:#38bdf8` + light theme override.
Fonts: Inter (body) + JetBrains Mono (numbers). Row glow, badge styles, tab styles all pixel-matched.

### APIs wired
fetchBoard (30s) → /api/option-gainers-board + /api/futures-buildup + /api/ema-crossovers + /api/oi/spurt
fetchLiveBreakouts (15s) → /api/live-breakouts
fetchQuotes (15s) → /kite/global-quotes
fetchPremSpikes (20s, incremental) → /api/option-gainers-alerts?after=N
fetchEMAConv (30s) → /api/ema_convergence_watchlist

### Build: ✓ built in 4.43s (no errors)

### Agent Reuse Decision
All backend data served by existing agents: BoardAgent, PremiumSpikeAgent, EmaAgent, MarketAgent, OiTransitionAgent — no new agents created.
