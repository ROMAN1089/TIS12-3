"""
Temporal Worker initialization and startup.
Connects to Temporal server and starts processing workflows and activities.
"""
import asyncio
import logging
from logging.config import dictConfig

from temporalio.client import Client
from temporalio.worker import Worker

from .config import settings
from .workflow import MultiAgentWorkflow
from .activities import AgentActivities


# Configure logging
def setup_logging():
    """Configure structured logging for the application."""
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "temporalio": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }
    
    dictConfig(log_config)


async def run_worker():
    """
    Initialize and run the Temporal worker.
    
    The worker connects to Temporal server and starts polling for tasks
    from the configured task queue.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"[INFO] Connecting to Temporal at {settings.temporal_host}")
    logger.info(f"[INFO] Task queue: {settings.temporal_task_queue}")
    logger.info(f"[INFO] Namespace: {settings.temporal_namespace}")
    
    try:
        # Connect to Temporal server
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
        
        logger.info("[INFO] Successfully connected to Temporal server")
        
        # Initialize activities
        activities = AgentActivities()
        
        # Create and run worker
        worker = Worker(
            client,
            task_queue=settings.temporal_task_queue,
            workflows=[MultiAgentWorkflow],
            activities=[
                activities.call_decomposer,
                activities.call_executor,
                activities.call_validator,
            ],
        )
        
        logger.info("[INFO] Worker started. Waiting for tasks...")
        logger.info("[INFO] Press Ctrl+C to stop")
        
        # Run the worker
        await worker.run()
    
    except KeyboardInterrupt:
        logger.info("[INFO] Worker stopped by user")
    
    except Exception as e:
        logger.error(f"[ERROR] Worker failed to start: {str(e)}")
        raise


def main():
    """Entry point for the worker."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
