"""
FastAPI middleware and dependencies for agent services.
This file demonstrates how to implement token-based authentication for agent services.
"""
from typing import Annotated
from fastapi import Header, HTTPException, status, Depends
import os


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


# Example FastAPI agent implementation
"""
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI(title="Agent Service")

class TaskInput(BaseModel):
    task_id: str
    data: dict

class TaskOutput(BaseModel):
    result: dict
    status: str

@app.post("/decompose", response_model=TaskOutput)
async def decompose_task(
    task: TaskInput,
    token: str = Depends(token_validator)
):
    '''
    Decompose a task into subtasks.
    Requires valid X-Service-Token header.
    '''
    # Process the task
    result = {
        "subtasks": [
            {"id": "1", "description": "Subtask 1"},
            {"id": "2", "description": "Subtask 2"},
        ]
    }
    
    return TaskOutput(result=result, status="success")


@app.post("/execute", response_model=TaskOutput)
async def execute_task(
    task: TaskInput,
    token: str = Depends(token_validator)
):
    '''
    Execute a subtask.
    Requires valid X-Service-Token header.
    '''
    # Execute the task
    result = {"output": "Task executed successfully"}
    
    return TaskOutput(result=result, status="success")


@app.post("/validate", response_model=TaskOutput)
async def validate_results(
    validation_data: TaskInput,
    token: str = Depends(token_validator)
):
    '''
    Validate execution results.
    Requires valid X-Service-Token header.
    '''
    # Validate results
    result = {"validation": "passed", "score": 0.95}
    
    return TaskOutput(result=result, status="success")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
"""
