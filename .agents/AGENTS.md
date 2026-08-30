# NextGen Workspace Rules

- **Strict Approval Discipline:** The agent must never make any file modifications, edits, additions, or execute any write/modify operations unless the user has explicitly typed the word "Confirmed" (case-insensitive) in a message in this conversation. A plan or design review must be completed and approved first.

- **Token Efficiency & Concise Output:** The agent must strictly minimize output tokens. Avoid redundant summaries, detailed code walkthroughs, or repeating code snippets unless explicitly requested. Display only useful, relevant details and actionable summaries.

- **Changelog Discipline:** Every session that modifies, adds, or deletes code files MUST append a dated entry to `CHANGELOG.md` at the project root. The entry must include: date, session goal, files changed, and a concise summary of what was done.

- **Repository & Commit Discipline:** The agent must NEVER perform any `git commit` or `git push` automatically without explicit user request/permission. When authorized by the user to commit and push, always target exclusively the `nxtrd` remote / NxTrd repository (`https://github.com/novatechnolab/NxTrd.git`) for this workspace.

- **Agentic AI Architecture First:** All future features and changes must be designed from an **Agentic AI workflow perspective**, not an LLM-call perspective.
  - Before implementing any new capability, **audit existing agents** (`NextGen/backend/agents/`) first. If an existing agent can be extended or reused for the new function, extend it — do NOT create a new agent.
  - New agents should only be created when the function is genuinely distinct (different data domain, different lifecycle, or incompatible responsibility with all existing agents).
  - Agent design must treat the orchestrator as the coordination layer — route tasks through `orchestrator.py`, not through ad-hoc server.py logic.
  - Prefer **agent composition** (chain existing agents) over new code.

- **Device-Agnostic UI Design:** All future UI elements, dashboards, pages, and interactive components in NextGen must be designed and implemented to be **device-agnostic**, providing seamless usability across **mobile, tablet, laptop, and desktop** form factors:
  - Employ responsive layout techniques (adaptive CSS Grid/Flexbox with appropriate breakpoints, fluid sizing, and touch-scrolling enablement).
  - Ensure touch targets meet mobile ergonomics (>= 40px x 40px) and bind mobile touch events (`touchstart`, `touchmove`, `touchend`) for canvas/charts alongside mouse handlers.
  - Eliminate off-screen clipping on smaller viewports and ensure all data columns, cards, and feeds remain fully accessible on mobile devices.

- **Code Analysis Discipline — Mandatory Full Call-Chain Tracing:** Before answering ANY question about scope, volume, performance, timing, or behavior of a code path, the agent MUST trace the full call chain and verify trigger origins.

- **Immutable Legacy Workspace Discipline:** The current / legacy backup workspaces (`Agent backup/`, `TradeSignal -Backup*`, `app/`, etc.) are strictly **READ-ONLY reference code**. No modifications, additions, or deletions shall be made to any files outside `NextGen/`. All new developments, migrations, and UI implementations must target exclusively `NextGen/`.

- **Backend Modification Discipline — Mandatory Reasoning & Confirmation:** Any modification, edit, addition, or refactoring of existing backend code (`NextGen/backend/` routers, agents, services, repositories, or core pipeline) strictly requires:
  1. **Comprehensive Reasoning:** Provide explicit technical reasoning, root-cause analysis, and architectural justification detailing why existing NextGen backend code must be modified.
  2. **Non-Invasive Verification:** Verify and explain why the requirement cannot be fulfilled via frontend/presentation-layer adjustments or existing backend API endpoints.
  3. **Explicit Confirmation:** Require dedicated user confirmation specifically acknowledging the backend modification reasoning before executing any changes to existing NextGen backend files.

- **Zero Mock / Zero Synthetic Data Discipline (Universal — No Exceptions Across All Features):** Under no circumstances shall mock, synthetic, dummy, simulated fallback data, placeholder values, or mathematical sine waves be displayed anywhere in the application for ANY feature (including Master Board, Alert Feed, charts, PreCross, OI Heatmap, Futures Buildup, Max Pain, Screener, Analytics, Portfolio, etc.). If data is missing, incomplete, offline, or an API/backend error occurs, the UI MUST explicitly display a clear, prominent error message indicating the exact failure reason (e.g., `⚠️ No data available for {FEATURE/SYMBOL}. Check backend connection or Kite session.`) and clear the visualization. Fabricating fallback values or simulated curves to mask missing data is strictly prohibited across all features without exception.

- **Full-Bleed Page Layout Standard (All New Pages — No Exceptions):** Every new route/page added to NextGen MUST follow the full-bleed layout pattern established by OI Spurt Scanner and 360° Command Center. This is the mandatory standard going forward:
  1. **No top header bar:** The global Topbar (showing "Settings" or route title) must NOT appear. Register the route in `+layout.svelte` `isFullBleed` condition so `isFullBleed = true` for the new route.
  2. **Auto-hide global nav sidebar:** The global `<Sidebar>` must use `isAutoHide={isFullBleed}` and slide in only when the user hovers the left 16px edge trigger zone.
  3. **Zero padding on page wrapper:** `page-wrapper.full-bleed` already enforces `padding: 0; margin: 0`. Do not add any outer padding or margin inside the page component.
  4. **100% viewport usage:** The page must fill `100vw × 100vh` with `overflow: hidden` at the layout level. Internal panels may have their own scroll.
  5. **In-page left panels are always visible:** In-page sidebars/left panels (e.g., stock list, filter panel) are static layout elements (`flex-shrink: 0`, normal flow). They do NOT auto-hide. Only the **global Nxtrd nav sidebar** auto-hides on full-bleed routes.
  6. **Only the global nav sidebar auto-hides:** The `isFullBleed` flag in `+layout.svelte` controls `isAutoHide` on the global `<Sidebar>` component exclusively. In-page content panels are always rendered.
  7. **Implementation checklist for every new page:**
     - Add route to `isFullBleed` reactive in `frontend/src/routes/+layout.svelte`
     - Page root element: `display: flex; flex-direction: column; height: 100vh; overflow: hidden`
     - In-page left panel (if any): `width: Npx; flex-shrink: 0; overflow: hidden` — static, always visible
     - No `<svelte:head>` title bar padding; manage title only via `<svelte:head><title>…</title></svelte:head>`
