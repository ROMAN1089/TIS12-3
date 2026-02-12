"""
Configuration module using Pydantic Settings.
Reads all URLs, ports, and tokens from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Temporal configuration
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "multi-agent-orchestrator"
    
    # Agent URLs
    decomposer_agent_url: str = "http://decomposer:8001"
    executor_agent_url: str = "http://executor:8002"
    validator_agent_url: str = "http://validator:8003"
    
    # Security tokens
    service_token: str
    decomposer_token: Optional[str] = None
    executor_token: Optional[str] = None
    validator_token: Optional[str] = None
    
    # Timeouts (in seconds)
    activity_start_to_close_timeout: int = 300
    http_request_timeout: int = 60
    
    # Retry configuration
    max_retry_attempts: int = 3
    initial_retry_interval: int = 1
    max_retry_interval: int = 10
    backoff_coefficient: float = 2.0
    
    # Logging
    log_level: str = "INFO"
    
    def get_agent_token(self, agent_name: str) -> str:
        """Get token for specific agent, fallback to service_token."""
        agent_tokens = {
            "decomposer": self.decomposer_token,
            "executor": self.executor_token,
            "validator": self.validator_token,
        }
        return agent_tokens.get(agent_name) or self.service_token


# Global settings instance
settings = Settings()
