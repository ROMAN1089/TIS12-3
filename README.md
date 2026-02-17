# Multi-Agent Orchestrator with S3 Artifact Storage

Production-ready orchestrator for a multi-agent system using Temporal.io, with S3/MinIO artifact storage, Ollama AI generation, and proper security, resilience, and logging.

## Architecture

- **Orchestrator**: Temporal.io workflow that coordinates multiple AI agents
- **Agents**: FastAPI microservices with Ollama integration for AI generation
- **Artifact Storage**: S3/MinIO for storing generated artifacts (Claim Check pattern)
- **Security**: Token-based authentication using `X-Service-Token` header
- **Resilience**: Retry policies with smart error handling (retry on 5xx, fail on 4xx)
- **AI Generation**: Ollama-powered agents with self-healing capabilities

## Project Structure

```
orchestrator/
├── __init__.py         # Package initialization
├── config.py           # Pydantic settings (reads from .env)
├── activities.py       # Network calls with auth, retry, and S3 operations
├── workflow.py         # Business logic orchestration
└── worker.py           # Temporal worker startup

ai_agent_service.py     # New AI agent service with S3 and Ollama
agent_middleware.py     # Example FastAPI middleware for agents (legacy)
example_agent_service.py # Legacy example agent
requirements.txt        # Python dependencies
.env.example           # Orchestrator environment configuration
.env.agent.example     # Agent service environment configuration
```

## Key Features

### 1. S3/MinIO Artifact Storage (New)
- **Claim Check Pattern**: Agents store large artifacts (code, JSON, etc.) in S3
- **Presigned URLs**: Temporary access URLs for artifact retrieval
- **Context Passing**: Upload context data to S3 for agent processing
- **Scalability**: Handles large generated artifacts efficiently

### 2. AI Agent Architecture (New)
- **Ollama Integration**: AI-powered generation using local LLM models
- **Self-Healing**: Automatic linting and fixing for code generation
- **Role-Based Prompts**: Different system prompts for decomposer/db_architect/coder roles
- **Unified Endpoint**: Single `/generate` endpoint with role configuration

### 3. Configuration Management (`config.py`)
- Uses `pydantic-settings` to read all configuration from `.env`
- Centralized settings for URLs, tokens, timeouts, retry policies, and S3
- Type-safe configuration with validation

### 4. Security (`activities.py` & AI agents)
- All HTTP requests include `X-Service-Token` header for authentication
- Agent services validate tokens using FastAPI dependency injection
- Support for per-agent tokens or shared service token

### 5. Resilience (`activities.py`)
- Temporal retry policies with exponential backoff
- Smart error handling:
  - **5xx errors**: Retried automatically (transient failures)
  - **4xx errors**: Non-retryable (validation/client errors) - raises `ApplicationError`
- Configurable timeouts for network requests and activities

### 6. Logging
- Structured logging with workflow IDs
- Format: `[LEVEL] Timestamp | Logger | Workflow-ID: 123 | Action: Description`
- Configurable log levels via environment variables

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

#### Orchestrator Configuration
Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required configuration:
- `SERVICE_TOKEN`: Your secret authentication token
- `S3_ENDPOINT`: MinIO/S3 endpoint URL
- `S3_ACCESS_KEY` and `S3_SECRET_KEY`: S3 credentials
- Agent URLs (if different from defaults)
- Temporal server address (if not localhost)

#### Agent Configuration
Copy `.env.agent.example` to `.env.agent` and configure:

```bash
cp .env.agent.example .env.agent
# Edit .env.agent with your agent configuration
```

Required configuration:
- `AGENT_ROLE`: decomposer | db_architect | coder | generic
- `AGENT_SECRET_TOKEN`: Must match orchestrator's SERVICE_TOKEN
- `OLLAMA_HOST`: Ollama server URL
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`: S3 credentials

### 3. Start MinIO (S3-compatible storage)

```bash
# Using Docker
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Access MinIO Console: http://localhost:9001
# Access MinIO API: http://localhost:9000
```

### 4. Start Ollama (AI Generation)

```bash
# Install Ollama (see https://ollama.ai)
ollama serve

# Pull a model
ollama pull llama3
```

### 5. Start Temporal Server

If you don't have Temporal running:

```bash
# Using Docker
docker run -d -p 7233:7233 temporalio/auto-setup:latest

# Or using Temporal CLI
temporal server start-dev
```

### 6. Run the Worker

```bash
python -m orchestrator.worker
```

### 7. Run AI Agent Services

Start each agent with its specific role:

```bash
# Decomposer agent (port 8001)
AGENT_ROLE=decomposer PORT=8001 python ai_agent_service.py

# Executor agent (port 8002)  
AGENT_ROLE=coder PORT=8002 python ai_agent_service.py

# Validator agent (port 8003)
AGENT_ROLE=generic PORT=8003 python ai_agent_service.py
```

Or use environment files:
```bash
# Create agent-specific .env files
cp .env.agent.example .env.decomposer
cp .env.agent.example .env.executor
cp .env.agent.example .env.validator

# Edit each file with the appropriate AGENT_ROLE and PORT
# Then run:
python ai_agent_service.py  # Reads from .env
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

### New AI Agent Architecture

The new `ai_agent_service.py` implements:
- **Ollama Integration**: AI-powered generation using local LLM models
- **S3 Artifact Storage**: Large artifacts stored in S3/MinIO (Claim Check pattern)
- **Self-Healing Code**: Automatic linting and fixing for Python code
- **Unified Endpoint**: Single `/generate` endpoint with role configuration

Example request to AI agent:
```python
import requests

response = requests.post(
    "http://localhost:8001/generate",
    headers={"X-Service-Token": "your-token"},
    json={
        "input_data": "Create a user authentication system",
        "context_keys": None,  # Optional: {"spec": "s3-key-to-context"}
        "system_prompt_override": None  # Optional: custom prompt
    }
)

# Response contains S3 reference, not the actual content
result = response.json()
print(f"Artifact stored at: {result['artifact']['s3_key']}")
print(f"Download URL: {result['artifact']['s3_url']}")
```

### Legacy Agent Example

See `agent_middleware.py` and `example_agent_service.py` for legacy examples of:
- FastAPI agent service with role-specific endpoints
- Token validation dependency
- Direct response (no S3)

## Workflow Flow

1. **Decomposer Agent**: Breaks down the main task into subtasks (generates JSON)
2. **Executor Agents**: Execute each subtask (generates code or results)
3. **Validator Agent**: Validates all results and returns final assessment

### New Flow with S3 Artifacts

1. Orchestrator calls agent's `/generate` endpoint
2. Agent generates content using Ollama
3. Agent uploads artifact to S3
4. Agent returns S3 reference to orchestrator
5. Orchestrator downloads artifact from S3 for processing
6. For validation, orchestrator uploads context to S3
7. Validator downloads context, generates validation report
8. Orchestrator retrieves final results

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
