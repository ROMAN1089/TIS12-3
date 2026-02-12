"""
Temporal Activities for calling external agents.
Implements network calls with timeouts, authentication headers, and proper error handling.
"""
import logging
from typing import Dict, Any
from datetime import timedelta

import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)


class AgentActivities:
    """Activities for interacting with external agent services."""
    
    @activity.defn(name="call_decomposer")
    async def call_decomposer(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Decomposer agent to break down a task.
        
        Args:
            task_data: Input data for the decomposer
            
        Returns:
            Response from the decomposer agent
            
        Raises:
            ApplicationError: For validation errors (400) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        workflow_id = activity.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Action: Calling Decomposer")
        
        return await self._call_agent(
            agent_name="decomposer",
            url=settings.decomposer_agent_url,
            endpoint="/decompose",
            data=task_data,
            workflow_id=workflow_id
        )
    
    @activity.defn(name="call_executor")
    async def call_executor(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Executor agent to execute a subtask.
        
        Args:
            execution_data: Input data for the executor
            
        Returns:
            Response from the executor agent
            
        Raises:
            ApplicationError: For validation errors (400) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        workflow_id = activity.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Action: Calling Executor")
        
        return await self._call_agent(
            agent_name="executor",
            url=settings.executor_agent_url,
            endpoint="/execute",
            data=execution_data,
            workflow_id=workflow_id
        )
    
    @activity.defn(name="call_validator")
    async def call_validator(self, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Validator agent to validate results.
        
        Args:
            validation_data: Input data for the validator
            
        Returns:
            Response from the validator agent
            
        Raises:
            ApplicationError: For validation errors (400) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        workflow_id = activity.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Action: Calling Validator")
        
        return await self._call_agent(
            agent_name="validator",
            url=settings.validator_agent_url,
            endpoint="/validate",
            data=validation_data,
            workflow_id=workflow_id
        )
    
    async def _call_agent(
        self,
        agent_name: str,
        url: str,
        endpoint: str,
        data: Dict[str, Any],
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Internal method to call an agent with proper authentication and error handling.
        
        Args:
            agent_name: Name of the agent (for token lookup)
            url: Base URL of the agent service
            endpoint: API endpoint path
            data: Request payload
            workflow_id: Current workflow ID for logging
            
        Returns:
            Response from the agent
            
        Raises:
            ApplicationError: For client errors (400-499) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        full_url = f"{url}{endpoint}"
        token = settings.get_agent_token(agent_name)
        
        headers = {
            "X-Service-Token": token,
            "Content-Type": "application/json",
            "X-Workflow-ID": workflow_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=settings.http_request_timeout) as client:
                logger.info(
                    f"[INFO] Workflow-ID: {workflow_id} | "
                    f"Sending request to {agent_name} at {full_url}"
                )
                
                response = await client.post(full_url, json=data, headers=headers)
                
                # Handle different status codes
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"[INFO] Workflow-ID: {workflow_id} | "
                        f"Successfully received response from {agent_name}"
                    )
                    return result
                
                elif 400 <= response.status_code < 500:
                    # Client error - don't retry (validation error, bad request, etc.)
                    error_msg = f"Client error from {agent_name}: {response.status_code} - {response.text}"
                    logger.error(
                        f"[ERROR] Workflow-ID: {workflow_id} | {error_msg}"
                    )
                    raise ApplicationError(
                        error_msg,
                        non_retryable=True,
                        type="ValidationError"
                    )
                
                else:
                    # Server error (5xx) or other - retry
                    error_msg = f"Server error from {agent_name}: {response.status_code} - {response.text}"
                    logger.warning(
                        f"[WARNING] Workflow-ID: {workflow_id} | {error_msg} | Will retry..."
                    )
                    raise Exception(error_msg)
        
        except httpx.TimeoutException as e:
            error_msg = f"Timeout calling {agent_name} at {full_url}: {str(e)}"
            logger.error(f"[ERROR] Workflow-ID: {workflow_id} | {error_msg} | Will retry...")
            raise Exception(error_msg)
        
        except httpx.RequestError as e:
            error_msg = f"Network error calling {agent_name} at {full_url}: {str(e)}"
            logger.error(f"[ERROR] Workflow-ID: {workflow_id} | {error_msg} | Will retry...")
            raise Exception(error_msg)
        
        except ApplicationError:
            # Re-raise ApplicationError as-is (non-retryable)
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error calling {agent_name}: {str(e)}"
            logger.error(f"[ERROR] Workflow-ID: {workflow_id} | {error_msg}")
            raise
