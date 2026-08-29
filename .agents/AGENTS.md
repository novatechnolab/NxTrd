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
