
import uvicorn
import sys
import logging
import asyncio
from pathlib import Path

# Add src to sys.path to resolve 'finetuneme' package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finetuneme.main import app

class ShutdownFilter(logging.Filter):
    """Filter to suppress asyncio.CancelledError tracebacks during shutdown"""
    def filter(self, record):
        # Suppress "Exception in ASGI application" caused by cancellation
        if record.exc_info and isinstance(record.exc_info[1], asyncio.CancelledError):
            return False
        # Suppress other cancellation noises
        if "CancelledError" in str(record.msg):
            return False
        return True

def setup_logging():
    """Configure basic logging with the shutdown filter"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:     %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Filter uvicorn.error
    error_logger = logging.getLogger("uvicorn.error")
    error_logger.addFilter(ShutdownFilter())
    
    # Filter uvicorn.access
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

if __name__ == "__main__":
    print("=" * 60)
    print("FineTuneMe Local - Dataset Generation Tool")
    print("=" * 60)
    print("\nStarting server at http://localhost:8001")
    print("API Docs: http://localhost:8001/docs")
    print("Frontend (if running): http://localhost:3000")
    print("\nPress CTRL+C to stop\n")

    # Configure our robust logging
    setup_logging()

    # Run server
    # We pass log_config=None to prevent uvicorn from overwriting our config
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8001, 
            log_config=None, 
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
        sys.exit(0)
    except asyncio.CancelledError:
        print("\n[INFO] Server stopped (cancelled).")
        sys.exit(0)
