"""
Integration Test Example for New S3-based Agent Architecture

This file demonstrates how to test the orchestrator with the new AI agents.
It includes mock services that simulate the behavior of the real components.

Requirements for real integration testing:
1. MinIO/S3 running on localhost:9000
2. Ollama running on localhost:11434 with llama3 model
3. Temporal server running on localhost:7233
4. AI agent services running (decomposer, executor, validator)
"""

import asyncio
import json
from typing import Dict, Any


# ============================================================================
# Mock S3 Operations (for testing without MinIO)
# ============================================================================

class MockS3Client:
    """Mock S3 client for testing without real MinIO."""
    
    def __init__(self):
        self.storage = {}
    
    def upload(self, bucket: str, key: str, content: str):
        """Mock upload to S3."""
        self.storage[f"{bucket}/{key}"] = content
        print(f"[MOCK S3] Uploaded to {bucket}/{key} ({len(content)} bytes)")
    
    def download(self, bucket: str, key: str) -> str:
        """Mock download from S3."""
        full_key = f"{bucket}/{key}"
        if full_key not in self.storage:
            raise ValueError(f"Key not found: {full_key}")
        content = self.storage[full_key]
        print(f"[MOCK S3] Downloaded from {bucket}/{key} ({len(content)} bytes)")
        return content


# ============================================================================
# Mock Ollama Client (for testing without real Ollama)
# ============================================================================

class MockOllamaClient:
    """Mock Ollama client for testing without real LLM."""
    
    def chat(self, model: str, messages: list) -> Dict[str, Any]:
        """Mock chat completion."""
        system_prompt = messages[0]['content']
        user_prompt = messages[-1]['content']
        
        print(f"[MOCK OLLAMA] Generating response for model: {model}")
        
        # Generate mock responses based on role
        if "decomposer" in system_prompt.lower() or "architect" in system_prompt.lower():
            response_content = json.dumps({
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Setup database schema",
                        "description": "Create database tables and relationships",
                        "dependencies": []
                    },
                    {
                        "id": "task-2",
                        "title": "Implement API endpoints",
                        "description": "Create REST API endpoints",
                        "dependencies": ["task-1"]
                    },
                    {
                        "id": "task-3",
                        "title": "Add authentication",
                        "description": "Implement user authentication",
                        "dependencies": ["task-2"]
                    }
                ]
            })
        elif "code" in system_prompt.lower() or "python" in system_prompt.lower():
            response_content = '''```python
def hello_world():
    """Sample function."""
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
```'''
        else:
            response_content = "Mock validation: All checks passed. The workflow execution is valid."
        
        return {
            'message': {
                'content': response_content
            }
        }


# ============================================================================
# Test Workflow Execution
# ============================================================================

async def test_workflow_execution():
    """
    Test the complete workflow with mocked services.
    
    This demonstrates the flow:
    1. Call decomposer -> generates task breakdown -> stores in S3
    2. Download decomposed tasks from S3
    3. For each task, call executor -> generates code -> stores in S3
    4. Download execution results from S3
    5. Call validator with context in S3 -> generates validation report
    6. Download validation results
    """
    print("=" * 80)
    print("INTEGRATION TEST: S3-based Agent Workflow")
    print("=" * 80)
    
    # Initialize mock services
    mock_s3 = MockS3Client()
    mock_ollama = MockOllamaClient()
    
    # Test data
    task_input = {
        "task_id": "test-workflow-001",
        "description": "Build a user authentication system",
        "data": {
            "requirements": ["JWT tokens", "Password hashing", "Role-based access"]
        }
    }
    
    print(f"\n📋 Input Task: {task_input['description']}")
    print("=" * 80)
    
    # ========================================================================
    # Step 1: Decomposer Agent
    # ========================================================================
    print("\n1️⃣  DECOMPOSER AGENT")
    print("-" * 80)
    
    # Simulate agent generating decomposition
    decomposer_prompt = f"Task: {task_input['description']}\nData: {json.dumps(task_input['data'])}"
    print(f"Input to agent: {decomposer_prompt[:100]}...")
    
    decomposer_response = mock_ollama.chat(
        "llama3",
        [
            {"role": "system", "content": "You are a decomposer agent..."},
            {"role": "user", "content": decomposer_prompt}
        ]
    )
    
    # Simulate storing in S3
    decomposer_s3_key = "decomposer/20240101_abc123.json"
    mock_s3.upload("agent-artifacts", decomposer_s3_key, decomposer_response['message']['content'])
    
    # Simulate orchestrator downloading
    decomposed_content = mock_s3.download("agent-artifacts", decomposer_s3_key)
    decomposed_tasks = json.loads(decomposed_content)
    
    print(f"✅ Generated {len(decomposed_tasks['tasks'])} subtasks")
    for task in decomposed_tasks['tasks']:
        print(f"   - {task['id']}: {task['title']}")
    
    # ========================================================================
    # Step 2: Executor Agents
    # ========================================================================
    print("\n2️⃣  EXECUTOR AGENTS")
    print("-" * 80)
    
    execution_results = []
    
    for idx, subtask in enumerate(decomposed_tasks['tasks'], 1):
        print(f"\nExecuting subtask {idx}/{len(decomposed_tasks['tasks'])}: {subtask['title']}")
        
        # Simulate agent generating code
        executor_prompt = f"Subtask Information:\n{json.dumps(subtask, indent=2)}"
        
        executor_response = mock_ollama.chat(
            "llama3",
            [
                {"role": "system", "content": "You are a Python coder..."},
                {"role": "user", "content": executor_prompt}
            ]
        )
        
        # Simulate storing in S3
        executor_s3_key = f"coder/20240101_{idx}_def456.py"
        mock_s3.upload("agent-artifacts", executor_s3_key, executor_response['message']['content'])
        
        # Simulate orchestrator downloading
        code_content = mock_s3.download("agent-artifacts", executor_s3_key)
        
        execution_results.append({
            "task_id": subtask['id'],
            "artifact_s3_key": executor_s3_key,
            "status": "success"
        })
        
        print(f"   ✅ Code generated and stored at {executor_s3_key}")
    
    # ========================================================================
    # Step 3: Validator Agent
    # ========================================================================
    print("\n3️⃣  VALIDATOR AGENT")
    print("-" * 80)
    
    # Simulate orchestrator uploading context to S3
    validation_context = {
        "original_task": task_input,
        "decomposed_tasks": decomposed_tasks,
        "execution_results": execution_results
    }
    
    context_s3_key = "context/20240101_validation_ghi789.json"
    mock_s3.upload("agent-artifacts", context_s3_key, json.dumps(validation_context, indent=2))
    print(f"📤 Uploaded validation context to {context_s3_key}")
    
    # Simulate validator downloading context
    context_content = mock_s3.download("agent-artifacts", context_s3_key)
    print(f"📥 Validator received context ({len(context_content)} bytes)")
    
    # Simulate validator generating validation report
    validator_response = mock_ollama.chat(
        "llama3",
        [
            {"role": "system", "content": "You are a validator..."},
            {"role": "user", "content": "Validate the workflow execution"}
        ]
    )
    
    # Simulate storing validation report in S3
    validator_s3_key = "generic/20240101_validation_jkl012.txt"
    mock_s3.upload("agent-artifacts", validator_s3_key, validator_response['message']['content'])
    
    # Simulate orchestrator downloading validation report
    validation_report = mock_s3.download("agent-artifacts", validator_s3_key)
    
    print(f"✅ Validation report generated")
    print(f"   Report: {validation_report[:100]}...")
    
    # ========================================================================
    # Final Result
    # ========================================================================
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    final_result = {
        "workflow_id": task_input['task_id'],
        "status": "completed",
        "decomposition_artifact": decomposer_s3_key,
        "execution_artifacts": [r['artifact_s3_key'] for r in execution_results],
        "validation_artifact": validator_s3_key,
        "total_artifacts_in_s3": len(mock_s3.storage)
    }
    
    print(f"\n📊 Summary:")
    print(f"   - Decomposition: {decomposer_s3_key}")
    print(f"   - Executions: {len(execution_results)} artifacts")
    print(f"   - Validation: {validator_s3_key}")
    print(f"   - Total S3 artifacts: {final_result['total_artifacts_in_s3']}")
    
    return final_result


# ============================================================================
# Real Integration Test (requires services running)
# ============================================================================

async def test_real_integration():
    """
    Real integration test with actual services.
    
    Prerequisites:
    - MinIO running on localhost:9000
    - Ollama running on localhost:11434
    - Temporal server on localhost:7233
    - Agent services running (ports 8001, 8002, 8003)
    """
    print("\n" + "=" * 80)
    print("REAL INTEGRATION TEST")
    print("=" * 80)
    print("\nThis test requires:")
    print("1. MinIO/S3 on localhost:9000")
    print("2. Ollama on localhost:11434 with llama3 model")
    print("3. Temporal server on localhost:7233")
    print("4. Agent services on ports 8001, 8002, 8003")
    print("\nSkipping real test (use example_start_workflow.py for real testing)")
    print("=" * 80)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                 S3-based Agent Architecture Test                           ║
║                                                                            ║
║  This test demonstrates the Claim Check pattern with mocked services      ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Run mock test
    result = asyncio.run(test_workflow_execution())
    
    print("\n" + "=" * 80)
    print("✅ Mock integration test completed successfully!")
    print("=" * 80)
    
    # Show real integration test info
    asyncio.run(test_real_integration())
