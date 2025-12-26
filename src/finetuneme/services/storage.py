"""
Local filesystem storage service.
Replaces S3/R2 with simple local file operations.
"""
import shutil
from pathlib import Path
from fastapi import UploadFile
from datetime import datetime
import uuid
from finetuneme.core.config import settings

async def save_uploaded_file(file: UploadFile, filename: str) -> str:
    """
    Save uploaded file to local filesystem.
    Returns the file path.
    """
    # Generate unique file path
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    file_extension = filename.split('.')[-1]
    file_name = f"{timestamp}_{unique_id}.{file_extension}"

    file_path = settings.UPLOAD_DIR / file_name
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(file_path)

def delete_file(file_path: str) -> bool:
    """Delete file from local filesystem"""
    try:
        Path(file_path).unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"Error deleting file {file_path}: {str(e)}")
        return False

def get_file_path(filename: str) -> Path:
    """Get full path for a file in the upload directory"""
    return settings.UPLOAD_DIR / filename

def save_dataset(content: str, filename: str) -> str:
    """
    Save generated dataset to local filesystem.
    Returns the file path.
    """
    file_path = settings.DATASET_DIR / filename
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return str(file_path)

def get_dataset_path(filename: str) -> Path:
    """Get full path for a dataset file"""
    return settings.DATASET_DIR / filename
