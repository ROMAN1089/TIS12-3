# Multi-Agent Orchestrator

Production-ready orchestrator for a multi-agent system using Temporal.io, with proper security, resilience, and logging.

## Architecture

- **Orchestrator**: Temporal.io workflow that coordinates 3 agents
- **Agents**: FastAPI microservices accessible through NetBird VPN
- **Security**: Token-based authentication using `X-Service-Token` header
- **Resilience**: Retry policies with smart error handling (retry on 5xx, fail on 4xx)

## Project Structure

```
orchestrator/
├── __init__.py         # Package initialization
├── config.py           # Pydantic settings (reads from .env)
├── activities.py       # Network calls with auth & retry logic
├── workflow.py         # Business logic orchestration
└── worker.py           # Temporal worker startup

agent_middleware.py     # Example FastAPI middleware for agents
requirements.txt        # Python dependencies
.env.example           # Environment configuration template
```

## Key Features

### 1. Configuration Management (`config.py`)
- Uses `pydantic-settings` to read all configuration from `.env`
- Centralized settings for URLs, tokens, timeouts, and retry policies
- Type-safe configuration with validation

### 2. Security (`activities.py` & `agent_middleware.py`)
- All HTTP requests include `X-Service-Token` header for authentication
- Agent services validate tokens using FastAPI dependency injection
- Support for per-agent tokens or shared service token

### 3. Resilience (`activities.py`)
- Temporal retry policies with exponential backoff
- Smart error handling:
  - **5xx errors**: Retried automatically (transient failures)
  - **4xx errors**: Non-retryable (validation/client errors) - raises `ApplicationError`
- Configurable timeouts for network requests and activities

### 4. Logging
- Structured logging with workflow IDs
- Format: `[LEVEL] Timestamp | Logger | Workflow-ID: 123 | Action: Description`
- Configurable log levels via environment variables

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required configuration:
- `SERVICE_TOKEN`: Your secret authentication token
- Agent URLs (if different from defaults)
- Temporal server address (if not localhost)

### 3. Start Temporal Server

If you don't have Temporal running:

```bash
# Using Docker
docker run -d -p 7233:7233 temporalio/auto-setup:latest

# Or using Temporal CLI
temporal server start-dev
```

### 4. Run the Worker

```bash
python -m orchestrator.worker
```

## Usage

### Starting a Workflow

```python
from temporalio.client import Client
import asyncio

async def main():
    client = await Client.connect("localhost:7233")
    
    result = await client.execute_workflow(
        "MultiAgentOrchestrationWorkflow",
        {"task": "Process user request", "data": {"user_id": 123}},
        id="workflow-001",
        task_queue="multi-agent-orchestrator",
    )
    
    print(f"Workflow result: {result}")

asyncio.run(main())
```

### Agent Implementation Example

See `agent_middleware.py` for a complete example of:
- FastAPI agent service
- Token validation dependency
- Endpoint implementations

Example agent service:

```python
from fastapi import FastAPI, Depends
from agent_middleware import token_validator

app = FastAPI()

@app.post("/decompose")
async def decompose(task: dict, token: str = Depends(token_validator)):
    # Your decomposition logic here
    return {"subtasks": [...]}
```

## Workflow Flow

1. **Decomposer**: Breaks down the main task into subtasks
2. **Executor**: Executes each subtask (parallel execution possible)
3. **Validator**: Validates all results and returns final output

## Error Handling

### Retryable Errors (5xx)
- Network timeouts
- Service unavailable (503)
- Internal server errors (500)

These trigger automatic retries with exponential backoff.

### Non-Retryable Errors (4xx)
- Bad request (400) - validation errors
- Unauthorized (401) - authentication failed
- Forbidden (403) - authorization failed

These fail immediately without retries to avoid wasting resources.

## Monitoring

- All actions are logged with workflow IDs for traceability
- Temporal UI provides workflow execution visibility
- Logs include timing and status information

## Production Considerations

1. **Security**:
   - Store tokens securely (use secrets manager in production)
   - Rotate tokens regularly
   - Use HTTPS in production environments

2. **Scaling**:
   - Run multiple workers for high availability
   - Configure appropriate timeouts based on agent response times
   - Monitor Temporal metrics

3. **Monitoring**:
   - Integrate with logging aggregation (ELK, Splunk, etc.)
   - Set up alerts for workflow failures
   - Monitor retry rates and timeouts

4. **Network**:
   - Ensure NetBird VPN connectivity
   - Configure appropriate network timeouts
   - Consider circuit breakers for unstable services

## Development

### Adding New Agents

1. Add agent URL and token to `.env`
2. Add configuration in `config.py`
3. Create activity method in `activities.py`
4. Update workflow in `workflow.py`
5. Register activity in `worker.py`

### Testing

```bash
# Unit tests
pytest tests/

# Integration tests (requires Temporal server)
pytest tests/integration/
```

## License

MIT
