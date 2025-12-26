from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum
from datetime import datetime
from enum import Enum
from finetuneme.core.database import Base

class ProjectStatus(str, Enum):
    """Status of project processing"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Project(Base):
    """Project model for tracking dataset generation jobs"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    # File information
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Local filesystem path
    file_size = Column(Integer)  # Size in bytes

    # Processing configuration
    role = Column(String, nullable=False)  # "teacher", "strict_auditor", etc.
    custom_prompt = Column(Text, nullable=True)  # Custom system prompt if provided
    model_name = Column(String, default="llama3.1:8b")  # Model name

    # Provider configuration (new multi-provider system)
    provider_type = Column(String, default="ollama")  # "ollama", "groq", "openai", "anthropic"
    api_key = Column(String, nullable=True)  # API key for cloud providers

    # Legacy fields (kept for backward compatibility)
    use_ollama = Column(Integer, default=1)  # DEPRECATED: 1 = Ollama, 0 = OpenRouter

    # Output
    dataset_path = Column(String, nullable=True)  # Generated .jsonl path
    dataset_format = Column(String, default="sharegpt")  # "sharegpt" or "alpaca"

    # Status tracking
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.QUEUED, index=True)
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
