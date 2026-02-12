"""
Example: Starting a Multi-Agent Workflow

This script demonstrates how to start and execute a workflow
using the orchestrator.
"""
import asyncio
from temporalio.client import Client


async def start_workflow():
    """Start a multi-agent orchestration workflow."""
    
    # Connect to Temporal server
    print("Connecting to Temporal server...")
    client = await Client.connect("localhost:7233")
    
    # Define the input task
    task_input = {
        "task_id": "task-001",
        "description": "Process customer order",
        "data": {
            "customer_id": 12345,
            "order_id": 67890,
            "items": [
                {"product_id": "A123", "quantity": 2},
                {"product_id": "B456", "quantity": 1},
            ],
            "priority": "high"
        }
    }
    
    # Start the workflow
    print(f"Starting workflow with task: {task_input['description']}")
    
    workflow_id = f"order-workflow-{task_input['data']['order_id']}"
    
    result = await client.execute_workflow(
        "MultiAgentOrchestrationWorkflow",
        task_input,
        id=workflow_id,
        task_queue="multi-agent-orchestrator",
    )
    
    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETED")
    print("=" * 60)
    print(f"Workflow ID: {result['workflow_id']}")
    print(f"Status: {result['status']}")
    print(f"\nDecomposition result:")
    print(f"  - Subtasks: {len(result['decomposition'].get('subtasks', []))}")
    print(f"\nExecution results:")
    print(f"  - Completed: {len(result['executions'])}")
    print(f"\nValidation:")
    print(f"  - Status: {result['validation'].get('status', 'unknown')}")
    print("=" * 60)
    
    return result


async def get_workflow_status(workflow_id: str):
    """Get the status of a running workflow."""
    
    client = await Client.connect("localhost:7233")
    
    handle = client.get_workflow_handle(workflow_id)
    
    # Get workflow description
    description = await handle.describe()
    
    print(f"\nWorkflow: {workflow_id}")
    print(f"Status: {description.status}")
    print(f"Start time: {description.start_time}")
    
    return description


def main():
    """Main entry point."""
    print("=" * 60)
    print("Multi-Agent Orchestrator - Example Usage")
    print("=" * 60)
    print("\nThis example requires:")
    print("1. Temporal server running (temporal server start-dev)")
    print("2. Orchestrator worker running (python -m orchestrator.worker)")
    print("3. Agent services running and configured")
    print("\nStarting workflow...")
    print("=" * 60 + "\n")
    
    try:
        result = asyncio.run(start_workflow())
        print("\n✅ Workflow completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
