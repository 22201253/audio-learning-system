from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .database import get_db
from .models import Subject, Topic, Lesson, User
from .schemas import (
    SubjectCreate, SubjectResponse,
    TopicCreate, TopicResponse,
    LessonCreate, LessonResponse
)
from .auth import get_current_active_user

# Create router for lesson management
router = APIRouter(prefix="/lessons", tags=["Lesson Management"])


# ============ SUBJECT ENDPOINTS ============

@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create new subject (Only teachers can do this)
    Example: Mathematics, English, Science
    """
    # Check if user is a teacher
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create subjects!"
        )
    
    # Check if subject name already exists
    existing = db.query(Subject).filter(Subject.name == subject.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject '{subject.name}' already exist!"
        )
    
    new_subject = Subject(**subject.dict())
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    
    return new_subject


@router.get("/subjects", response_model=List[SubjectResponse])
async def get_all_subjects(db: Session = Depends(get_db)):
    """
    Get all subjects (Everyone fit can this - no need login)
    """
    subjects = db.query(Subject).all()
    return subjects


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: int, db: Session = Depends(get_db)):
    """
    Get one subject by ID
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with ID {subject_id} does not exist!"
        )
    return subject


# ============ TOPIC ENDPOINTS ============

@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create new topic under a subject (Only teachers)
    Example: Algebra under Mathematics, Grammar under English
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create topics!"
        )
    
    # Check if subject exists
    subject = db.query(Subject).filter(Subject.id == topic.subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with ID {topic.subject_id} does not exist!"
        )
    
    new_topic = Topic(**topic.dict())
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)
    
    return new_topic


@router.get("/subjects/{subject_id}/topics", response_model=List[TopicResponse])
async def get_topics_by_subject(subject_id: int, db: Session = Depends(get_db)):
    """
    Get all topics for a specific subject
    """
    topics = db.query(Topic).filter(Topic.subject_id == subject_id).order_by(Topic.order).all()
    return topics


# ============ LESSON ENDPOINTS ============

@router.post("/", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create new lesson (Only teachers)
    The content is what TTS reads for students
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create lessons!"
        )
    
    # Check if topic exists
    topic = db.query(Topic).filter(Topic.id == lesson.topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with ID {lesson.topic_id} does not  exist!"
        )
    
    new_lesson = Lesson(**lesson.dict())
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    
    return new_lesson


@router.get("/", response_model=List[LessonResponse])
async def get_all_lessons(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all lessons (with pagination)
    """
    lessons = db.query(Lesson).offset(skip).limit(limit).all()
    return lessons


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """
    Get single lesson by ID
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} does not exist!"
        )
    return lesson


@router.get("/topics/{topic_id}/lessons", response_model=List[LessonResponse])
async def get_lessons_by_topic(topic_id: int, db: Session = Depends(get_db)):
    """
    Get all lessons for a specific topic
    """
    lessons = db.query(Lesson).filter(Lesson.topic_id == topic_id).order_by(Lesson.order).all()
    return lessons


@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_update: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update lesson (Only teachers)
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can update lessons!"
        )
    
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} does not exist!"
        )
    
    for key, value in lesson_update.dict().items():
        setattr(lesson, key, value)
    
    db.commit()
    db.refresh(lesson)
    
    return lesson


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete lesson (Only teachers)
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete lessons!"
        )
    
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} does not exist!"
        )
    
    db.delete(lesson)
    db.commit()
    
    return {"message": f"Lesson '{lesson.title}' deleted successfully!"}