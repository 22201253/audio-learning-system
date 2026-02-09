from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json
from .database import get_db
from .models import Subject, Lesson, Quiz, DeletedItem, User
from .schemas import SubjectCreate, SubjectResponse, LessonCreate, LessonResponse
from .routes_auth import get_current_user

router = APIRouter(prefix="/lessons", tags=["Lessons"])

# ==================== SUBJECT ROUTES ====================

@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).filter(Subject.is_deleted == False).all()


@router.get("/subjects/trash", response_model=List[SubjectResponse])
async def get_trash_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Subject).filter(
        Subject.is_deleted == True,
        Subject.teacher_id == current_user.id
    ).all()


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.is_deleted == False
    ).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    return subject


@router.post("/subjects", response_model=SubjectResponse, status_code=201)
async def create_subject(
    subject_data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = Subject(
        name=subject_data.name,
        description=subject_data.description or "",
        teacher_id=current_user.id,
        is_deleted=False
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.is_deleted == False
    ).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    subject.is_deleted = True
    subject.deleted_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Subject moved to trash"}


@router.post("/subjects/{subject_id}/undo")
async def restore_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.is_deleted == True
    ).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    subject.is_deleted = False
    subject.deleted_at = None
    db.commit()

    return {"success": True, "message": "Subject restored"}


# ==================== LESSON ROUTES ====================
# ⚠️ CRITICAL: Route order matters! Specific routes BEFORE generic ones

# ✅ SPECIFIC routes first (with literal path segments like "by-subject")
@router.get("/by-subject/{subject_id}", response_model=List[LessonResponse])
async def get_lessons_by_subject(
    subject_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all lessons for a specific subject
    """
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.is_deleted == False
    ).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    return db.query(Lesson).filter(Lesson.topic_id == subject_id).all()


# ✅ ROOT routes AFTER specific routes
@router.get("/", response_model=List[LessonResponse])
async def get_all_lessons(
    topic_id: int = None,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all lessons, optionally filtered by topic_id
    """
    query = db.query(Lesson)
    
    if topic_id:
        query = query.filter(Lesson.topic_id == topic_id)
    
    lessons = query.offset(skip).limit(limit).all()
    return lessons


@router.post("/", response_model=LessonResponse, status_code=201)
async def create_lesson(
    lesson_data: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new lesson
    """
    subject = db.query(Subject).filter(
        Subject.id == lesson_data.topic_id,
        Subject.is_deleted == False
    ).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    lesson = Lesson(
        topic_id=lesson_data.topic_id,
        title=lesson_data.title,
        content=lesson_data.content,
        duration=lesson_data.duration or "15 min",
        order=lesson_data.order or 0
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# ✅ DYNAMIC routes with {id} LAST
@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a lesson
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    db.delete(lesson)
    db.commit()
    return {"success": True, "message": "Lesson deleted"}