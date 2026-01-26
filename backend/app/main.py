from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models
from .routes_auth import router as auth_router
from .routes_lessons import router as lessons_router
from .routes_quiz import router as quiz_router
from .routes_progress import router as progress_router

# Create all database tables
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

# Include authentication routes
app.include_router(auth_router)
app.include_router(lessons_router)
app.include_router(quiz_router)
app.include_router(progress_router)

# Welcome endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Audio Learning System API! 🎉",
        "status": "running",
        "version": "1.0.0",
        "description": "Backend for visually impaired students learning platform",
        "database": "Connected ✅",
        "authentication": "Active 🔐"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "API works well! All systems operational ✅",
        "database": "Connected",
        "authentication": "Ready"
    }

# Info endpoint
@app.get("/info")
async def api_info():
    return {
        "api_name": "Audio Learning System",
        "purpose": "Assistive learning platform for visually impaired students",
        "features": [
            "User authentication ✅",
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
        "auth_endpoints": [
            "POST /auth/register - Create new user",
            "POST /auth/login - Login and get token",
            "GET /auth/me - Get current user info"
        ],
        "status": "In Development - Authentication Ready! 🔐"
    }

# Test endpoint - Add sample subject
@app.post("/test/add-subject")
async def add_test_subject(db: Session = Depends(get_db)):
    """
    Test endpoint - Add a sample subject to database
    """
    from .models import Subject
    
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

# Test endpoint - Get all subjects
@app.get("/test/subjects")
async def get_all_subjects(db: Session = Depends(get_db)):
    """
    Test endpoint - Get all subjects from database
    """
    from .models import Subject
    
    subjects = db.query(Subject).all()
    
    return {
        "total": len(subjects),
        "subjects": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description
            }
            for s in subjects
        ]
    }