"""
Temporal Activities for calling external agents.
Implements network calls with timeouts, authentication headers, and proper error handling.
Updated to work with the new agent API using /generate endpoint and S3 artifact storage.
"""
import logging
from typing import Dict, Any
from datetime import timedelta

import httpx
import boto3
from botocore.exceptions import ClientError
from temporalio import activity
from temporalio.exceptions import ApplicationError

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# --- S3 CLIENT SETUP ---
s3_client = boto3.client(
    's3',
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.s3_region
)


def download_artifact_from_s3(s3_key: str) -> str:
    """Download artifact content from S3."""
    try:
        obj = s3_client.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        content = obj['Body'].read().decode('utf-8')
        logger.info(f"Downloaded artifact from S3: {s3_key}")
        return content
    except ClientError as e:
        logger.error(f"Failed to download artifact {s3_key}: {e}")
        raise Exception(f"S3 download error: {str(e)}")


def upload_context_to_s3(content: str, context_name: str) -> str:
    """Upload context data to S3 and return the S3 key."""
    import uuid
    from datetime import datetime
    
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d")
    s3_key = f"context/{timestamp}_{unique_id}_{context_name}.json"
    
    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket,
            Key=s3_key,
            Body=content.encode('utf-8'),
            ContentType='application/json'
        )
        logger.info(f"Uploaded context to S3: {s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"Failed to upload context to S3: {e}")
        raise Exception(f"S3 upload error: {str(e)}")


class AgentActivities:
    """Activities for interacting with external agent services."""
    
    @activity.defn(name="call_decomposer")
    async def call_decomposer(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Decomposer agent to break down a task.
        
        Args:
            task_data: Input data for the decomposer
            
        Returns:
            Response from the decomposer agent with artifact reference
            
        Raises:
            ApplicationError: For validation errors (400) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        workflow_id = activity.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Action: Calling Decomposer")
        
        # Prepare request for new agent API
        import json
        input_data = f"Task: {task_data.get('description', '')}\nData: {json.dumps(task_data.get('data', {}))}"
        
        agent_request = {
            "input_data": input_data
        }
        
        response = await self._call_agent(
            agent_name="decomposer",
            url=settings.decomposer_agent_url,
            data=agent_request,
            workflow_id=workflow_id
        )
        
        # Download the artifact from S3
        artifact = response.get("artifact", {})
        s3_key = artifact.get("s3_key")
        
        if s3_key:
            content = download_artifact_from_s3(s3_key)
            # Parse JSON content for decomposer
            import json
            try:
                decomposed_data = json.loads(content)
                return {
                    "subtasks": decomposed_data.get("tasks", []),
                    "total_subtasks": len(decomposed_data.get("tasks", [])),
                    "status": "success",
                    "artifact_s3_key": s3_key
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from artifact: {content[:100]}")
                raise ApplicationError(
                    "Invalid JSON in decomposer response",
                    non_retryable=True,
                    type="ParseError"
                )
        else:
            raise ApplicationError(
                "No artifact returned from decomposer",
                non_retryable=True,
                type="MissingArtifact"
            )
    
    @activity.defn(name="call_executor")
    async def call_executor(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Executor agent to execute a subtask.
        
        Args:
            execution_data: Input data for the executor
            
        Returns:
            Response from the executor agent with artifact reference
            
        Raises:
            ApplicationError: For validation errors (400) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        workflow_id = activity.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Action: Calling Executor")
        
        # Prepare request for new agent API
        import json
        subtask_info = {
            "task_id": execution_data.get('task_id', ''),
            "description": execution_data.get('description', ''),
            "data": execution_data.get('data', {})
        }
        input_data = f"Subtask Information:\n{json.dumps(subtask_info, indent=2)}"
        
        agent_request = {
            "input_data": input_data
        }
        
        response = await self._call_agent(
            agent_name="executor",
            url=settings.executor_agent_url,
            data=agent_request,
            workflow_id=workflow_id
        )
        
        # Download the artifact from S3
        artifact = response.get("artifact", {})
        s3_key = artifact.get("s3_key")
        
        if s3_key:
            content = download_artifact_from_s3(s3_key)
            return {
                "task_id": execution_data.get("task_id", ""),
                "result": {"output": content},
                "duration": 0,
                "status": "success",
                "artifact_s3_key": s3_key
            }
        else:
            raise ApplicationError(
                "No artifact returned from executor",
                non_retryable=True,
                type="MissingArtifact"
            )
    
    @activity.defn(name="call_validator")
    async def call_validator(self, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Validator agent to validate results.
        
        Args:
            validation_data: Input data for the validator
            
        Returns:
            Response from the validator agent with artifact reference
            
        Raises:
            ApplicationError: For validation errors (400) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        workflow_id = activity.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Action: Calling Validator")
        
        # Prepare context data for validation
        import json
        context_data = json.dumps({
            "original_task": validation_data.get("data", {}).get("original_task", {}),
            "decomposed_tasks": validation_data.get("data", {}).get("decomposed_tasks", {}),
            "execution_results": validation_data.get("data", {}).get("execution_results", [])
        }, indent=2)
        
        # Upload context to S3
        context_s3_key = upload_context_to_s3(context_data, "validation_context")
        
        # Prepare request for new agent API
        input_data = "Validate the following workflow execution results"
        
        agent_request = {
            "input_data": input_data,
            "context_keys": {"validation_data": context_s3_key}
        }
        
        response = await self._call_agent(
            agent_name="validator",
            url=settings.validator_agent_url,
            data=agent_request,
            workflow_id=workflow_id
        )
        
        # Download the artifact from S3
        artifact = response.get("artifact", {})
        s3_key = artifact.get("s3_key")
        
        if s3_key:
            content = download_artifact_from_s3(s3_key)
            # Try to parse as JSON for validation results
            try:
                validation_result = json.loads(content)
                return {
                    "is_valid": validation_result.get("is_valid", True),
                    "score": validation_result.get("score", 1.0),
                    "issues": validation_result.get("issues", []),
                    "status": "success",
                    "artifact_s3_key": s3_key
                }
            except json.JSONDecodeError:
                # If not JSON, treat as text validation report
                return {
                    "is_valid": True,
                    "score": 1.0,
                    "issues": [],
                    "status": "success",
                    "validation_report": content,
                    "artifact_s3_key": s3_key
                }
        else:
            raise ApplicationError(
                "No artifact returned from validator",
                non_retryable=True,
                type="MissingArtifact"
            )
    
    async def _call_agent(
        self,
        agent_name: str,
        url: str,
        data: Dict[str, Any],
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Internal method to call an agent with proper authentication and error handling.
        Updated to use /generate endpoint.
        
        Args:
            agent_name: Name of the agent (for token lookup)
            url: Base URL of the agent service
            data: Request payload (AgentRequest format)
            workflow_id: Current workflow ID for logging
            
        Returns:
            Response from the agent (AgentResponse format)
            
        Raises:
            ApplicationError: For client errors (400-499) - non-retryable
            Exception: For server errors (500+) - retryable
        """
        full_url = f"{url}/generate"
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
