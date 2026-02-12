"""
Temporal Workflow definition.
Orchestrates the multi-agent system business logic.
"""
import logging
from typing import Dict, Any
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities
with workflow.unsafe.imports_passed_through():
    from .activities import AgentActivities

# Configure logging
logger = logging.getLogger(__name__)


@workflow.defn(name="MultiAgentOrchestrationWorkflow")
class MultiAgentWorkflow:
    """
    Main workflow that orchestrates multiple agents to complete a task.
    
    Flow:
    1. Decomposer: Breaks down the task into subtasks
    2. Executor: Executes each subtask
    3. Validator: Validates the results
    """
    
    @workflow.run
    async def run(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the multi-agent workflow.
        
        Args:
            task_input: Initial task data
            
        Returns:
            Final validated results
        """
        workflow_id = workflow.info().workflow_id
        logger.info(f"[INFO] Workflow-ID: {workflow_id} | Starting multi-agent orchestration")
        
        # Configure retry policy for activities
        # Retry on 500 errors, don't retry on 400 errors (handled in activities)
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
            maximum_attempts=3,
        )
        
        # Activity options with timeout and retry policy
        activity_options = {
            "start_to_close_timeout": timedelta(seconds=300),
            "retry_policy": retry_policy,
        }
        
        try:
            # Step 1: Call Decomposer to break down the task
            logger.info(f"[INFO] Workflow-ID: {workflow_id} | Step 1: Decomposing task")
            
            decomposed_tasks = await workflow.execute_activity(
                AgentActivities.call_decomposer,
                task_input,
                **activity_options
            )
            
            logger.info(
                f"[INFO] Workflow-ID: {workflow_id} | "
                f"Decomposed into {len(decomposed_tasks.get('subtasks', []))} subtasks"
            )
            
            # Step 2: Execute each subtask
            execution_results = []
            subtasks = decomposed_tasks.get("subtasks", [])
            
            for idx, subtask in enumerate(subtasks, 1):
                logger.info(
                    f"[INFO] Workflow-ID: {workflow_id} | "
                    f"Step 2.{idx}: Executing subtask {idx}/{len(subtasks)}"
                )
                
                execution_result = await workflow.execute_activity(
                    AgentActivities.call_executor,
                    subtask,
                    **activity_options
                )
                
                execution_results.append(execution_result)
                
                logger.info(
                    f"[INFO] Workflow-ID: {workflow_id} | "
                    f"Completed subtask {idx}/{len(subtasks)}"
                )
            
            # Step 3: Validate all results
            logger.info(f"[INFO] Workflow-ID: {workflow_id} | Step 3: Validating results")
            
            validation_input = {
                "original_task": task_input,
                "decomposed_tasks": decomposed_tasks,
                "execution_results": execution_results,
            }
            
            validation_result = await workflow.execute_activity(
                AgentActivities.call_validator,
                validation_input,
                **activity_options
            )
            
            logger.info(
                f"[INFO] Workflow-ID: {workflow_id} | "
                f"Validation status: {validation_result.get('status', 'unknown')}"
            )
            
            # Return final result
            final_result = {
                "workflow_id": workflow_id,
                "status": "completed",
                "decomposition": decomposed_tasks,
                "executions": execution_results,
                "validation": validation_result,
            }
            
            logger.info(f"[INFO] Workflow-ID: {workflow_id} | Workflow completed successfully")
            
            return final_result
        
        except Exception as e:
            logger.error(
                f"[ERROR] Workflow-ID: {workflow_id} | "
                f"Workflow failed with error: {str(e)}"
            )
            raise
