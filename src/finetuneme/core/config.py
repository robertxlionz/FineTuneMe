from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FineTuneMe API"
    VERSION: str = "2.0.0"
    DATABASE_URL: str = "sqlite:///./finetuneme.db"
    # REDIS_URL: str = "redis://localhost:6379/0"  # Not required for local-first mode

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Ollama (Local AI)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "llama3.1"

    # OpenRouter / OpenAI
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Provider Keys (Optional - loaded from .env)
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Models
    FREE_MODEL: str = "meta-llama/llama-3-8b-instruct"
    PRO_MODEL: str = "qwen/qwen-2.5-72b-instruct"

    # Storage (S3/R2 compatible)
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "finetuneme-uploads"
    S3_REGION: str = "auto"

    # File retention & Storage
    FILE_RETENTION_HOURS: int = 48
    MAX_FILE_SIZE_MB: int = 500

    # Chunking
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    # Local paths
    UPLOAD_DIR: Path = Path("uploads")
    DATASET_DIR: Path = Path("datasets")

    class Config:
        env_file = ".env"

settings = Settings()
