"""
TradeSignal NextGen — Agent Orchestrator
Supervises lifecycle of all agents: registration, startup, health monitoring, pause/resume, and auto-restart.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from agents.base_agent import BaseAgent, AgentState
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Central supervisor for all NextGen FSM agents.
    Runs agents as managed asyncio background tasks with auto-restart on unexpected crashes.
    """
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._agents: Dict[str, BaseAgent] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._restart_counts: Dict[str, int] = {}
        self._paused_agents: set = set()
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        return self._running

    def register(self, agent: BaseAgent):
        """Register an agent instance with the orchestrator."""
        self._agents[agent.name] = agent
        self._restart_counts[agent.name] = 0
        logger.info(f"[Orchestrator] Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get registered agent by name."""
        return self._agents.get(name)

    async def start(self):
        """Start all registered agents in background tasks."""
        if self._running:
            return
        self._running = True
        logger.info(f"[Orchestrator] Starting {len(self._agents)} agents...")
        for name, agent in self._agents.items():
            self._tasks[name] = asyncio.create_task(
                self._run_with_restart(agent),
                name=f"agent_{name}"
            )
        logger.info("[Orchestrator] All agents started.")

    async def stop(self):
        """Gracefully stop all agents and cancel tasks."""
        self._running = False
        logger.info("[Orchestrator] Stopping all agents...")
        for name, agent in self._agents.items():
            try:
                await agent.stop()
            except Exception as e:
                logger.warning(f"[Orchestrator] Error stopping agent {name}: {e}")

        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()

        self._tasks.clear()
        logger.info("[Orchestrator] All agents stopped.")

    def pause_agent(self, name: str) -> bool:
        """Pause scanning cycles for a specific agent."""
        if name in self._agents:
            self._paused_agents.add(name)
            logger.info(f"[Orchestrator] Agent '{name}' paused.")
            return True
        return False

    def resume_agent(self, name: str) -> bool:
        """Resume scanning cycles for a specific agent."""
        if name in self._paused_agents:
            self._paused_agents.remove(name)
            logger.info(f"[Orchestrator] Agent '{name}' resumed.")
            return True
        return False

    def is_agent_paused(self, name: str) -> bool:
        return name in self._paused_agents

    async def _run_with_restart(self, agent: BaseAgent):
        """Wrapper running an agent with exponential backoff on crashes."""
        delay = 2.0
        while self._running:
            try:
                logger.info(f"[Orchestrator] Running agent: {agent.name}")
                await agent.start()
                break  # If agent exited cleanly
            except asyncio.CancelledError:
                logger.info(f"[Orchestrator] Task cancelled for agent: {agent.name}")
                break
            except Exception as e:
                self._restart_counts[agent.name] = self._restart_counts.get(agent.name, 0) + 1
                agent.record_error(str(e))
                logger.error(
                    f"[Orchestrator] Agent '{agent.name}' crashed: {e}. "
                    f"Restarting in {delay}s (restart #{self._restart_counts[agent.name]})...",
                    exc_info=True
                )
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 30.0)

    def get_health_status(self) -> Dict[str, Any]:
        """Aggregate health status of all registered agents."""
        agent_statuses = {}
        healthy_count = 0
        for name, agent in self._agents.items():
            status = agent.get_status()
            status["restarts"] = self._restart_counts.get(name, 0)
            status["paused"] = name in self._paused_agents
            agent_statuses[name] = status
            if agent.state in (AgentState.IDLE, AgentState.MONITORING, AgentState.TRIGGERED, AgentState.COOLDOWN):
                healthy_count += 1

        return {
            "orchestrator_running": self._running,
            "total_agents": len(self._agents),
            "healthy_agents": healthy_count,
            "agents": agent_statuses
        }
