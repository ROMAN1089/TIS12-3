"""
Multi-Agent Orchestrator Package.
Production-ready orchestration of multiple agents using Temporal.io.
"""
from .config import settings, Settings
from .workflow import MultiAgentWorkflow
from .activities import AgentActivities
from .worker import run_worker

__version__ = "0.1.0"

__all__ = [
    "settings",
    "Settings",
    "MultiAgentWorkflow",
    "AgentActivities",
    "run_worker",
]
