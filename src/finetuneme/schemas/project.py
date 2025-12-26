from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from finetuneme.models.project import ProjectStatus

class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    role: str  # Preset role or "custom"
    custom_prompt: Optional[str] = None
    guest_email: Optional[EmailStr] = None  # For guest users
    dataset_format: str = "sharegpt"  # "sharegpt" or "alpaca"

class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: int
    user_id: Optional[int]
    original_filename: str
    status: ProjectStatus
    progress: int
    role: str
    dataset_format: str
    dataset_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    """Schema for updating project status (internal use)"""
    status: Optional[ProjectStatus] = None
    progress: Optional[int] = None
    dataset_path: Optional[str] = None
    error_message: Optional[str] = None
