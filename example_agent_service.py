"""
Example: FastAPI Agent Service with Token Validation

This file demonstrates a complete implementation of an agent service
with token-based authentication.
"""
import os
from typing import Dict, Any, Annotated
from fastapi import FastAPI, Header, HTTPException, status, Depends
from pydantic import BaseModel, Field


# ============================================================================
# Token Validation Dependency
# ============================================================================

class TokenValidator:
    """Dependency class for validating X-Service-Token header."""
    
    def __init__(self):
        """Initialize with the expected token from environment."""
        self.expected_token = os.getenv("SERVICE_TOKEN")
        if not self.expected_token:
            raise ValueError("SERVICE_TOKEN environment variable must be set")
    
    async def __call__(
        self,
        x_service_token: Annotated[str | None, Header()] = None
    ) -> str:
        """
        Validate the X-Service-Token header.
        
        Args:
            x_service_token: Token from the X-Service-Token header
            
        Returns:
            The validated token
            
        Raises:
            HTTPException: If token is missing or invalid
        """
        if not x_service_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-Service-Token header is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if x_service_token != self.expected_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid service token",
            )
        
        return x_service_token


# Global token validator instance
token_validator = TokenValidator()


# ============================================================================
# Pydantic Models
# ============================================================================

class TaskInput(BaseModel):
    """Input model for agent tasks."""
    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Task description")
    data: Dict[str, Any] = Field(default_factory=dict, description="Task data")


class SubtaskOutput(BaseModel):
    """Output model for decomposed subtasks."""
    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    estimated_duration: int = 60


class DecomposeOutput(BaseModel):
    """Output model for decomposer agent."""
    subtasks: list[SubtaskOutput]
    total_subtasks: int
    status: str = "success"


class ExecutionOutput(BaseModel):
    """Output model for executor agent."""
    task_id: str
    result: Dict[str, Any]
    duration: int
    status: str = "success"


class ValidationOutput(BaseModel):
    """Output model for validator agent."""
    is_valid: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    status: str = "success"


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Multi-Agent Service",
    description="Agent service with token-based authentication",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)."""
    return {"status": "healthy", "service": "agent"}


@app.post("/decompose", response_model=DecomposeOutput)
async def decompose_task(
    task: TaskInput,
    token: str = Depends(token_validator)
):
    """
    Decompose a task into subtasks.
    Requires valid X-Service-Token header.
    
    Args:
        task: Input task to decompose
        token: Validated service token
        
    Returns:
        Decomposed subtasks
    """
    # Example decomposition logic
    subtasks = [
        SubtaskOutput(
            id=f"{task.task_id}-1",
            description="Validate input data",
            dependencies=[],
            estimated_duration=30
        ),
        SubtaskOutput(
            id=f"{task.task_id}-2",
            description="Process main task",
            dependencies=[f"{task.task_id}-1"],
            estimated_duration=120
        ),
        SubtaskOutput(
            id=f"{task.task_id}-3",
            description="Generate output",
            dependencies=[f"{task.task_id}-2"],
            estimated_duration=60
        ),
    ]
    
    return DecomposeOutput(
        subtasks=subtasks,
        total_subtasks=len(subtasks),
        status="success"
    )


@app.post("/execute", response_model=ExecutionOutput)
async def execute_task(
    task: TaskInput,
    token: str = Depends(token_validator)
):
    """
    Execute a subtask.
    Requires valid X-Service-Token header.
    
    Args:
        task: Subtask to execute
        token: Validated service token
        
    Returns:
        Execution result
    """
    # Example execution logic
    result = {
        "output": f"Executed task: {task.description}",
        "data_processed": task.data,
        "timestamp": "2024-01-01T12:00:00Z"
    }
    
    return ExecutionOutput(
        task_id=task.task_id,
        result=result,
        duration=95,
        status="success"
    )


@app.post("/validate", response_model=ValidationOutput)
async def validate_results(
    validation_data: TaskInput,
    token: str = Depends(token_validator)
):
    """
    Validate execution results.
    Requires valid X-Service-Token header.
    
    Args:
        validation_data: Data to validate
        token: Validated service token
        
    Returns:
        Validation result
    """
    # Example validation logic
    issues = []
    
    # Check if all required data is present
    if not validation_data.data:
        issues.append("No data provided for validation")
    
    is_valid = len(issues) == 0
    score = 1.0 if is_valid else 0.5
    
    return ValidationOutput(
        is_valid=is_valid,
        score=score,
        issues=issues,
        status="success"
    )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc)
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8001"))
    
    print("=" * 60)
    print(f"Starting Agent Service on port {port}")
    print("=" * 60)
    print("Endpoints:")
    print("  GET  /health     - Health check (no auth)")
    print("  POST /decompose  - Decompose task (requires auth)")
    print("  POST /execute    - Execute subtask (requires auth)")
    print("  POST /validate   - Validate results (requires auth)")
    print("=" * 60)
    print(f"\nRequired: SERVICE_TOKEN environment variable")
    print(f"Current: {'SET' if os.getenv('SERVICE_TOKEN') else 'NOT SET'}")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
