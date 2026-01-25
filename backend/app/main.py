from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models

# Create all database tables
# This line go create all the tables we define for models.py
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title="Audio Learning System API",
    description="Backend API for visually impaired students learning system",
    version="1.0.0"
)

# Allow frontend to connect to our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Welcome endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Audio Learning System API! 🎉",
        "status": "running",
        "version": "1.0.0",
        "description": "Backend for visually impaired students learning platform",
        "database": "Connected ✅"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "API dey work well! All systems operational ✅",
        "database": "Connected"
    }

# Info endpoint
@app.get("/info")
async def api_info():
    return {
        "api_name": "Audio Learning System",
        "purpose": "Assistive learning platform for visually impaired students",
        "features": [
            "User authentication",
            "Lesson management",
            "Quiz system",
            "Progress tracking",
            "Offline-first sync"
        ],
        "database_tables": [
            "users",
            "subjects",
            "topics",
            "lessons",
            "quizzes",
            "student_progress"
        ],
        "status": "In Development - Database Ready! 🎉"
    }
# Test endpoint - Add sample subject
@app.post("/test/add-subject")
async def add_test_subject(db: Session = Depends(get_db)):
    """
    Test endpoint - Add a sample subject to database
    """
    from .models import Subject
    
    # Create a test subject
    test_subject = Subject(
        name="Mathematics",
        description="Basic mathematics for students"
    )
    
    db.add(test_subject)
    db.commit()
    db.refresh(test_subject)
    
    return {
        "message": "Sample subject created!",
        "subject": {
            "id": test_subject.id,
            "name": test_subject.name,
            "description": test_subject.description
        }
    }