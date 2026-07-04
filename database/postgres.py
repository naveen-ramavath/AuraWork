from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

# Create the database engine
engine = create_engine(
    Config.DATABASE_URL, 
    connect_args={"check_same_thread": False} if Config.DATABASE_URL.startswith("sqlite") else {}
)

# SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()

def get_db():
    """Dependency to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes the database, creating all tables."""
    Base.metadata.create_all(bind=engine)
