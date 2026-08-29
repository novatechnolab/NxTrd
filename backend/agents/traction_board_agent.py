"""
TradeSignal NextGen — Traction Board Agent (Redirect Notice)
=============================================================
No standalone implementation needed.

Traction board logic is fully owned by BoardAgent:
  agents/board_agent.py:
    - compute_traction_quadrant()  →  classifies each row into
      confirm-up / confirm-down / div-bull / div-bear
    - get_traction_board()         →  returns enriched board with
      traction_quadrant per symbol

Reference origin: server.py:4844 api_traction_board() (Flask monolith)
Migration status: ✅ Fully ported to BoardAgent in Week 8.

This file is intentionally a no-op stub kept for scaffolding completeness.
If a future requirement genuinely separates traction from the board agent,
implement TractionBoardAgent here as a BaseAgent subclass.
"""
from agents.base_agent import BaseAgent


class TractionBoardAgent(BaseAgent):
    """
    Intentional no-op stub.
    All traction computation lives in BoardAgent.get_traction_board().
    See migration note above.
    """
    name = "traction_board_agent"

    async def run(self):
        """No-op: traction logic delegated to BoardAgent."""
        import asyncio
        while self._running:
            await asyncio.sleep(60.0)
