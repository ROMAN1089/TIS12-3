# Quick Start Guide

## Prerequisites

1. Python 3.10+
2. Temporal server running
3. Agent services deployed

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd TIS12-3

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Edit `.env` file:

```bash
# Required
SERVICE_TOKEN=your-secret-token-here

# Optional (defaults shown)
TEMPORAL_HOST=localhost:7233
DECOMPOSER_AGENT_URL=http://decomposer:8001
EXECUTOR_AGENT_URL=http://executor:8002
VALIDATOR_AGENT_URL=http://validator:8003
```

## Running the Orchestrator

### 1. Start Temporal Server

```bash
# Using Docker
docker run -d -p 7233:7233 temporalio/auto-setup:latest

# OR using Temporal CLI
temporal server start-dev
```

### 2. Start the Worker

```bash
python -m orchestrator.worker
```

Expected output:
```
[INFO] Connecting to Temporal at localhost:7233
[INFO] Task queue: multi-agent-orchestrator
[INFO] Worker started. Waiting for tasks...
```

### 3. Start an Agent Service (Example)

```bash
SERVICE_TOKEN=your-secret-token-here python example_agent_service.py
```

### 4. Execute a Workflow

```bash
python example_start_workflow.py
```

## Testing

### Validate Structure

```bash
SERVICE_TOKEN=test-token python validate_structure.py
```

### Test Agent Authentication

```bash
# Without token (should fail)
curl -X POST http://localhost:8001/decompose \
  -H "Content-Type: application/json" \
  -d '{"task_id": "test", "description": "test task", "data": {}}'

# With token (should succeed)
curl -X POST http://localhost:8001/decompose \
  -H "Content-Type: application/json" \
  -H "X-Service-Token: your-secret-token-here" \
  -d '{"task_id": "test", "description": "test task", "data": {}}'
```

## Troubleshooting

### Worker won't start
- Check Temporal server is running: `temporal server check-health`
- Verify `TEMPORAL_HOST` in `.env`
- Check logs for connection errors

### Authentication failures
- Verify `SERVICE_TOKEN` is set correctly
- Check agent logs for token mismatches
- Ensure token is passed in `X-Service-Token` header

### Workflow failures
- Check Temporal UI: http://localhost:8233
- Review worker logs for errors
- Verify agent services are accessible

## Next Steps

1. **Deploy Agents**: Implement your actual agent logic in separate services
2. **Configure NetBird**: Set up VPN and update agent URLs
3. **Add Monitoring**: Integrate with your logging/monitoring system
4. **Scale Workers**: Run multiple worker instances for HA
5. **Add Tests**: Create unit and integration tests

## Common Commands

```bash
# Check Temporal workflows
temporal workflow list

# Describe a workflow
temporal workflow describe --workflow-id=<workflow-id>

# Get workflow result
temporal workflow show --workflow-id=<workflow-id>

# Stop a workflow
temporal workflow cancel --workflow-id=<workflow-id>
```

## Support

For issues or questions:
1. Check the README.md for detailed documentation
2. Review Temporal documentation: https://docs.temporal.io
3. Check agent service logs
4. Review workflow execution in Temporal UI
