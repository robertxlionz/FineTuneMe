"""
Entry point for running FineTuneMe as a module.
Usage: python -m src.finetuneme
"""
import uvicorn
from finetuneme.main import app

if __name__ == "__main__":
    print("=" * 60)
    print("FineTuneMe Local - Dataset Generation Tool")
    print("=" * 60)
    print("\nStarting server at http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Frontend (if running): http://localhost:3000")
    print("\nPress CTRL+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
