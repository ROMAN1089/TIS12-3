"""
Multi-Agent Orchestrator Package.
Production-ready orchestration of multiple agents using Temporal.io.
"""
from .config import settings, Settings

__version__ = "0.1.0"

__all__ = [
    "settings",
    "Settings",
]

# Lazy imports for Temporal-dependent modules
def _import_workflow():
    from .workflow import MultiAgentWorkflow
    return MultiAgentWorkflow

def _import_activities():
    from .activities import AgentActivities
    return AgentActivities

def _import_worker():
    from .worker import run_worker
    return run_worker
