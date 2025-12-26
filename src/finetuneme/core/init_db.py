from finetuneme.core.database import engine, Base
from finetuneme.models import User, Project

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
