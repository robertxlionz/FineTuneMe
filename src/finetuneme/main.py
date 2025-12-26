"""
FineTuneMe Local - Main FastAPI Application
Simplified local version without cloud dependencies.
"""
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import uuid

from finetuneme.core.config import settings
from finetuneme.core.database import get_db, init_db
from finetuneme.models.project import Project, ProjectStatus
from finetuneme.services import storage, ingestion, generation, formatter
from finetuneme.services.providers import list_all_providers
from finetuneme.services.loaders import get_loader_for_file
from finetuneme.services.hardware import detect_hardware_status, check_pytorch_cuda_availability

# Initialize FastAPI app
app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    print(f" -> Database initialized at: {settings.DATABASE_URL}")
    print(f" -> Upload directory: {settings.UPLOAD_DIR}")
    print(f" -> Dataset directory: {settings.DATASET_DIR}")

@app.get("/")
def root():
    providers = list_all_providers()
    return {
        "message": "FineTuneMe Local API - Universal Data Ingestion",
        "version": settings.VERSION,
        "providers": providers,
        "supported_file_types": [
            ".pdf", ".docx", ".xlsx", ".xls", ".csv",
            ".html", ".htm", ".xml", ".txt", ".md",
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs"
        ]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "ollama": generation.check_ollama_available()
    }

@app.get("/system/health")
def system_health():
    """
    System health check including hardware compatibility status (V2.0).
    Returns hardware tier, GPU info, PyTorch status, and provider availability.
    """
    # Get hardware status
    hardware_status = detect_hardware_status()

    # Get PyTorch info
    pytorch_info = check_pytorch_cuda_availability()

    # Determine provider availability based on hardware tier
    providers_status = {
        "ollama": {
            "available": hardware_status.tier in ["GREEN", "YELLOW"],
            "status": "ready" if hardware_status.tier == "GREEN" else
                     "experimental" if hardware_status.tier == "YELLOW" else "disabled",
            "warning": hardware_status.recommendation if hardware_status.tier == "YELLOW" else None
        },
        "groq": {
            "available": True,
            "status": "ready",
            "warning": None
        },
        "openai": {
            "available": True,
            "status": "ready",
            "warning": None
        },
        "anthropic": {
            "available": True,
            "status": "ready",
            "warning": None
        }
    }

    return {
        "status": "healthy",
        "version": settings.VERSION,
        "hardware": {
            "tier": hardware_status.tier,
            "gpu_name": hardware_status.gpu_name,
            "compute_capability": hardware_status.compute_capability,
            "vram_gb": hardware_status.vram_gb,
            "driver_version": hardware_status.driver_version,
            "pytorch_mode": hardware_status.pytorch_mode,
            "message": hardware_status.message,
            "recommendation": hardware_status.recommendation
        },
        "pytorch": pytorch_info,
        "providers": providers_status
    }

@app.get("/providers")
def get_providers():
    """Get list of all available AI providers and their models"""
    return list_all_providers()

@app.get("/providers/{provider_name}/models")
def get_provider_models(provider_name: str):
    """Get available models for a specific provider"""
    providers = list_all_providers()
    if provider_name not in providers:
        raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")

    provider_info = providers[provider_name]
    return {
        "provider": provider_name,
        "available": provider_info["available"],
        "requires_api_key": provider_info["requires_api_key"],
        "models": provider_info["models"]
    }

# Background processing function
def process_project_background(project_id: int):
    """
    Background task to process uploaded file and generate dataset.
    Replaces Celery worker.
    """
    from src.finetuneme.core.database import SessionLocal

    db = SessionLocal()

    try:
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        # Update status
        project.status = ProjectStatus.PROCESSING
        project.progress = 0
        db.commit()

        # Step 1: Process document (20%)
        print(f"[Project {project_id}] Processing document...")
        # Use universal document processor
        chunks = ingestion.process_document(project.file_path)
        project.progress = 20
        db.commit()

        if not chunks:
            raise Exception("No text extracted from document")

        # Step 2: Generate dataset (20% -> 80%)
        print(f"[Project {project_id}] Generating dataset from {len(chunks)} chunks...")
        print(f"[Project {project_id}] Using provider: {project.provider_type}, model: {project.model_name}")

        def update_progress(current, total):
            progress = 20 + int((current / total) * 60)
            project.progress = progress
            db.commit()

        # Use new multi-provider system
        conversations = generation.generate_dataset_with_provider(
            chunks=chunks,
            provider_type=project.provider_type,
            role=project.role,
            api_key=project.api_key,
            model=project.model_name,
            custom_prompt=project.custom_prompt,
            progress_callback=update_progress
        )

        project.progress = 80
        db.commit()

        if not conversations:
            raise Exception("No conversations generated")

        # Step 3: Format and save (80% -> 100%)
        print(f"[Project {project_id}] Saving {len(conversations)} conversations...")

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"dataset_{timestamp}_{uuid.uuid4().hex[:8]}.jsonl"

        # Format to JSONL
        jsonl_content = formatter.format_conversations_to_jsonl(
            conversations,
            format_type=project.dataset_format
        )

        # Save to local filesystem
        dataset_path = storage.save_dataset(jsonl_content, filename)

        project.dataset_path = dataset_path
        project.progress = 90
        db.commit()

        # Delete original file (zero-retention)
        storage.delete_file(project.file_path)

        # Mark as completed
        project.status = ProjectStatus.COMPLETED
        project.progress = 100
        project.completed_at = datetime.utcnow()
        db.commit()

        print(f"[Project {project_id}] -> Completed successfully!")

    except Exception as e:
        print(f"[Project {project_id}] -> Error: {str(e)}")
        project.status = ProjectStatus.FAILED
        project.error_message = str(e)
        db.commit()

    finally:
        db.close()

# === API Endpoints ===

@app.post("/projects")
async def create_project(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    role: str = Form("teacher"),
    custom_prompt: str = Form(None),
    provider_type: str = Form("ollama"),
    api_key: str = Form(None),
    model_name: str = Form(None),
    dataset_format: str = Form("sharegpt"),
    # Legacy parameter for backward compatibility
    use_ollama: bool = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload file and create a new processing project.
    Processing happens in the background.

    Supports multiple file types: PDF, Word, Excel, CSV, HTML, text files, and code.
    Supports multiple AI providers: Ollama (local), Groq, OpenAI, Anthropic.
    """
    # Validate file type
    supported_extensions = {
        '.pdf', '.docx', '.xlsx', '.xls', '.csv',
        '.html', '.htm', '.xml', '.txt', '.md', '.markdown',
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cs',
        '.go', '.rs', '.php', '.rb', '.sql', '.json', '.yaml', '.yml',
        '.pptx', '.ppt', '.doc',
        '.png', '.jpg', '.jpeg', '.webp'
    }

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(sorted(supported_extensions))}"
        )

    # Handle legacy parameter
    if use_ollama is not None and provider_type == "ollama":
        provider_type = "ollama" if use_ollama else "openai"

    # Read and validate file size
    content = await file.read()
    file_size = len(content)
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
        )

    # Reset file pointer
    await file.seek(0)

    # Save file
    file_path = await storage.save_uploaded_file(file, file.filename)

    # Use default model if not specified
    if not model_name:
        # Get default model for the provider
        from finetuneme.services.providers import get_provider
        try:
            provider = get_provider(provider_type, api_key=api_key)
            model_name = provider.get_default_model()
        except:
            model_name = settings.DEFAULT_MODEL

    # Create project in database
    project = Project(
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        role=role,
        custom_prompt=custom_prompt if role == "custom" else None,
        model_name=model_name,
        provider_type=provider_type,
        api_key=api_key,
        use_ollama=int(provider_type == "ollama"),  # For backward compatibility
        dataset_format=dataset_format,
        status=ProjectStatus.QUEUED
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Start background processing
    background_tasks.add_task(process_project_background, project.id)

    return {
        "id": project.id,
        "status": project.status,
        "message": "Processing started in background"
    }

@app.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    """List all projects"""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects

@app.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project details"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.get("/projects/{project_id}/download")
def download_dataset(project_id: int, db: Session = Depends(get_db)):
    """Download generated dataset"""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProjectStatus.COMPLETED or not project.dataset_path:
        raise HTTPException(status_code=400, detail="Dataset not ready yet")

    dataset_path = Path(project.dataset_path)
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found")

    return FileResponse(
        path=dataset_path,
        filename=f"{project.original_filename.replace('.pdf', '')}_dataset.jsonl",
        media_type="application/jsonl"
    )

@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project and its associated files"""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete files
    if project.file_path:
        storage.delete_file(project.file_path)
    if project.dataset_path:
        storage.delete_file(project.dataset_path)

    # Delete from database
    db.delete(project)
    db.commit()

    return {"message": "Project deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
