"""
Multi-Agent Orchestrator Package.
Production-ready orchestration of multiple agents using Temporal.io.
"""

__version__ = "0.1.0"

__all__ = [
    "get_settings",
    "get_settings_class",
]


def get_settings():
    """Lazily load settings to avoid workflow sandbox side effects."""
    from .config import settings
    return settings


def get_settings_class():
    """Lazily load Settings class to avoid workflow sandbox side effects."""
    from .config import Settings as _Settings
    return _Settings

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
