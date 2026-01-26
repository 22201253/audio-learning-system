from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from .database import get_db
from .models import StudentProgress, User, Lesson, Topic, Subject
from .schemas import ProgressResponse, StudentProgressReport
from .auth import get_current_active_user

router = APIRouter(prefix="/progress", tags=["Progress Tracking"])


@router.get("/my-progress", response_model=List[ProgressResponse])
async def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current student's learning progress (Students only)
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can check their progress!"
        )
    
    progress = db.query(StudentProgress).filter(
        StudentProgress.student_id == current_user.id
    ).all()
    
    return progress


@router.get("/lesson/{lesson_id}", response_model=ProgressResponse)
async def get_lesson_progress(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get student's progress for specific lesson
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can check progress!"
        )
    
    progress = db.query(StudentProgress).filter(
        StudentProgress.student_id == current_user.id,
        StudentProgress.lesson_id == lesson_id
    ).first()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not started this lesson!"
        )
    
    return progress


@router.post("/start-lesson/{lesson_id}")
async def start_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark that student has started a lesson
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can start lessons!"
        )
    
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} does not exist!"
        )
    
    # Check if progress already exists
    existing = db.query(StudentProgress).filter(
        StudentProgress.student_id == current_user.id,
        StudentProgress.lesson_id == lesson_id
    ).first()
    
    if existing:
        # Just update last_accessed
        existing.last_accessed = datetime.utcnow()
        db.commit()
        return {"message": "Lesson progress updated!", "progress": existing}
    
    # Create new progress
    progress = StudentProgress(
        student_id=current_user.id,
        lesson_id=lesson_id,
        is_completed=False
    )
    
    db.add(progress)
    db.commit()
    db.refresh(progress)
    
    return {"message": "Lesson has started!", "progress": progress}


@router.get("/report", response_model=StudentProgressReport)
async def get_progress_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed progress report for student
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can get progress report!"
        )
    
    # Get all progress
    all_progress = db.query(StudentProgress).filter(
        StudentProgress.student_id == current_user.id
    ).all()
    
    total_lessons_started = len(all_progress)
    completed_lessons = len([p for p in all_progress if p.is_completed])
    total_quiz_attempts = sum([p.quiz_attempts for p in all_progress])
    
    # Calculate average score
    scores = [p.quiz_score for p in all_progress if p.quiz_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0
    
    return {
        "student_id": current_user.id,
        "student_name": f"{current_user.first_name} {current_user.surname}",
        "total_lessons_started": total_lessons_started,
        "completed_lessons": completed_lessons,
        "completion_rate": (completed_lessons / total_lessons_started * 100) if total_lessons_started > 0 else 0,
        "average_score": round(average_score, 2),
        "total_quiz_attempts": total_quiz_attempts,
        "lessons": all_progress
    }


@router.get("/students/{student_id}/report", response_model=StudentProgressReport)
async def get_student_report(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get progress report for any student (Teachers only)
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view student reports!"
        )
    
    # Check if student exists
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} does not exist!"
        )
    
    # Get student progress
    all_progress = db.query(StudentProgress).filter(
        StudentProgress.student_id == student_id
    ).all()
    
    total_lessons_started = len(all_progress)
    completed_lessons = len([p for p in all_progress if p.is_completed])
    total_quiz_attempts = sum([p.quiz_attempts for p in all_progress])
    
    scores = [p.quiz_score for p in all_progress if p.quiz_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0
    
    return {
        "student_id": student.id,
        "student_name": f"{student.first_name} {student.surname}",
        "total_lessons_started": total_lessons_started,
        "completed_lessons": completed_lessons,
        "completion_rate": (completed_lessons / total_lessons_started * 100) if total_lessons_started > 0 else 0,
        "average_score": round(average_score, 2),
        "total_quiz_attempts": total_quiz_attempts,
        "lessons": all_progress
    }


@router.get("/all-students")
async def get_all_students_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get progress summary for all students (Teachers only)
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view all students progress!"
        )
    
    # Get all students
    students = db.query(User).filter(User.role == "student").all()
    
    reports = []
    for student in students:
        progress = db.query(StudentProgress).filter(
            StudentProgress.student_id == student.id
        ).all()
        
        total_started = len(progress)
        completed = len([p for p in progress if p.is_completed])
        scores = [p.quiz_score for p in progress if p.quiz_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        reports.append({
            "student_id": student.id,
            "student_name": f"{student.first_name} {student.surname}",
            "email": student.email,
            "lessons_started": total_started,
            "lessons_completed": completed,
            "average_score": round(avg_score, 2)
        })
    
    return {
        "total_students": len(students),
        "students": reports
    }