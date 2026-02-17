# Migration Guide: From Legacy to S3-based Agent Architecture

## Overview

This guide explains the changes made to adapt the orchestrator to work with the new AI agent architecture that uses S3/MinIO for artifact storage and Ollama for AI generation.

## Key Architectural Changes

### Before (Legacy Architecture)
- **Endpoints**: Role-specific endpoints (`/decompose`, `/execute`, `/validate`)
- **Response**: Direct content in HTTP response body
- **Data Transfer**: Full artifacts in request/response
- **Agent Logic**: Manual implementation by developers

### After (New S3-based Architecture)
- **Endpoint**: Unified `/generate` endpoint for all agents
- **Response**: S3 references (keys and presigned URLs)
- **Data Transfer**: Claim Check pattern (artifacts stored in S3)
- **Agent Logic**: AI-powered generation using Ollama with self-healing

## What Changed

### 1. Dependencies (`requirements.txt`)
**Added:**
- `boto3>=1.34.0,<2.0.0` - S3/MinIO client
- `ollama>=0.1.0,<1.0.0` - Ollama AI client

### 2. Configuration (`orchestrator/config.py`)
**Added settings:**
```python
# S3/MinIO configuration for artifact storage
s3_endpoint: str = "http://localhost:9000"
s3_access_key: str = "minioadmin"
s3_secret_key: str = "minioadmin"
s3_bucket: str = "agent-artifacts"
s3_region: str = "us-east-1"
```

### 3. Activities (`orchestrator/activities.py`)
**Major changes:**
- Changed from calling role-specific endpoints to `/generate`
- Added S3 client initialization
- Added `download_artifact_from_s3()` function
- Added `upload_context_to_s3()` function
- Modified all agent call methods to:
  - Format data as JSON for better readability
  - Remove redundant `None` values from requests
  - Download artifacts from S3 after agent response
  - Upload context to S3 before validation

**Example transformation:**
```python
# Before
response = await client.post(f"{url}/decompose", json=task_data)
return response.json()

# After
response = await client.post(f"{url}/generate", json={
    "input_data": f"Task: {task_data['description']}\n..."
})
artifact_s3_key = response.json()['artifact']['s3_key']
content = download_artifact_from_s3(artifact_s3_key)
return parse_and_transform(content)
```

### 4. New Agent Service (`ai_agent_service.py`)
**Complete new implementation:**
- FastAPI service with single `/generate` endpoint
- Ollama integration for AI generation
- Role-based system prompts (configurable via `AGENT_ROLE` env var)
- Self-healing Python code with AST linting
- Automatic markdown cleanup
- S3 artifact storage with presigned URLs

### 5. Environment Configuration
**New files:**
- `.env.example` - Orchestrator configuration (includes S3 settings)
- `.env.agent.example` - Agent configuration template

## Migration Steps

### For Orchestrator Deployment

1. **Update environment variables:**
   ```bash
   # Add to .env
   S3_ENDPOINT=http://localhost:9000
   S3_ACCESS_KEY=minioadmin
   S3_SECRET_KEY=minioadmin
   S3_BUCKET=agent-artifacts
   S3_REGION=us-east-1
   ```

2. **Deploy MinIO/S3:**
   ```bash
   docker run -d \
     -p 9000:9000 -p 9001:9001 \
     --name minio \
     -e MINIO_ROOT_USER=minioadmin \
     -e MINIO_ROOT_PASSWORD=minioadmin \
     minio/minio server /data --console-address ":9001"
   ```

3. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **No code changes required** - orchestrator automatically works with new agents

### For Agent Deployment

1. **Deploy Ollama:**
   ```bash
   # Install Ollama
   curl https://ollama.ai/install.sh | sh
   
   # Start Ollama
   ollama serve
   
   # Pull required model
   ollama pull llama3
   ```

2. **Deploy new agent service:**
   ```bash
   # For decomposer
   AGENT_ROLE=decomposer \
   PORT=8001 \
   AGENT_SECRET_TOKEN=your-token \
   S3_ENDPOINT=http://localhost:9000 \
   S3_ACCESS_KEY=minioadmin \
   S3_SECRET_KEY=minioadmin \
   OLLAMA_HOST=http://localhost:11434 \
   python ai_agent_service.py
   
   # Repeat for executor (AGENT_ROLE=coder, PORT=8002)
   # and validator (AGENT_ROLE=generic, PORT=8003)
   ```

## Backward Compatibility

### Legacy Agents Still Supported
The orchestrator can work with both:
- **Legacy agents** (`example_agent_service.py`) - role-specific endpoints
- **New AI agents** (`ai_agent_service.py`) - S3-based with Ollama

Simply point the orchestrator to the appropriate agent URLs in the `.env` file.

## Benefits of New Architecture

### 1. Scalability
- Large artifacts don't bloat HTTP responses
- S3 handles storage and distribution
- Agents can be stateless

### 2. Performance
- Parallel artifact generation and storage
- Presigned URLs for direct client access
- Reduced network overhead

### 3. Auditability
- All artifacts persisted in S3
- Easy to review historical outputs
- Supports versioning and lifecycle policies

### 4. AI-Powered
- Automatic code generation
- Self-healing with linting
- Consistent quality through system prompts

### 5. Cost Efficiency
- S3 cheaper than database storage
- Lifecycle policies for automatic cleanup
- Pay only for storage used

## Testing

### Mock Test
Run the integration test example:
```bash
python test_integration_example.py
```

### Real Integration Test
Prerequisites:
1. MinIO on localhost:9000
2. Ollama on localhost:11434 with llama3
3. Temporal server on localhost:7233
4. Agent services on ports 8001, 8002, 8003

Then use:
```bash
python example_start_workflow.py
```

## Troubleshooting

### S3 Connection Issues
```bash
# Check MinIO is running
curl http://localhost:9000/minio/health/live

# Check bucket exists
aws --endpoint-url http://localhost:9000 s3 ls s3://agent-artifacts
```

### Ollama Issues
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check model is available
ollama list
```

### Agent Issues
```bash
# Test agent health
curl http://localhost:8001/health

# Test generation (with auth)
curl -X POST http://localhost:8001/generate \
  -H "X-Service-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{"input_data": "test task"}'
```

## Performance Considerations

### S3 Presigned URL Expiry
- Default: 1 hour
- Adjust in `ai_agent_service.py` if needed
- Consider longer expiry for long-running workflows

### S3 Bucket Organization
- Artifacts organized by: `{role}/{date}_{uuid}.{ext}`
- Implement lifecycle policies to delete old artifacts
- Consider bucket versioning for critical artifacts

### Ollama Model Selection
- `llama3` - Good balance of speed and quality
- Larger models: Better quality, slower generation
- Smaller models: Faster, may need more retries

## Next Steps

1. **Production Deployment**:
   - Use production S3 (AWS S3, MinIO cluster)
   - Deploy Ollama on dedicated GPU instances
   - Configure Temporal cluster
   - Set up monitoring and alerts

2. **Optimization**:
   - Implement artifact caching
   - Tune Ollama model parameters
   - Configure S3 lifecycle policies
   - Add metrics and tracing

3. **Enhancement**:
   - Add support for multiple LLM models
   - Implement streaming generation
   - Add artifact versioning
   - Create web UI for artifact browsing

## Support

For issues or questions:
1. Check the README.md for detailed documentation
2. Review IMPLEMENTATION_SUMMARY.md for architecture details
3. Run `python validate_structure.py` to verify setup
4. Check agent/orchestrator logs for errors
