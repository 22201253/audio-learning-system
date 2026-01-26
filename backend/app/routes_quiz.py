from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .database import get_db
from .models import Quiz, Lesson, User, StudentProgress
from .schemas import (
    QuizCreate, QuizResponse,
    QuizSubmission, QuizResult
)
from .auth import get_current_active_user

# Create router for quiz management
router = APIRouter(prefix="/quizzes", tags=["Quiz System"])


# ============ QUIZ CREATION (Teachers Only) ============

@router.post("/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create new quiz question for a lesson (Only teachers)
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create quiz questions!"
        )
    
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == quiz.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {quiz.lesson_id} does not exist!"
        )
    
    new_quiz = Quiz(**quiz.dict())
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    
    return new_quiz


@router.get("/lessons/{lesson_id}", response_model=List[QuizResponse])
async def get_quizzes_by_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """
    Get all quiz questions for a specific lesson
    """
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} does not exist!"
        )
    
    quizzes = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).order_by(Quiz.order).all()
    return quizzes


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    """
    Get single quiz question by ID
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} does not exist!"
        )
    return quiz


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete quiz question (Only teachers)
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete quiz questions!"
        )
    
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} does not exist!"
        )
    
    db.delete(quiz)
    db.commit()
    
    return {"message": "Quiz question deleted successfully!"}


# ============ QUIZ SUBMISSION (Students) ============

@router.post("/submit", response_model=QuizResult)
async def submit_quiz(
    submission: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit quiz answers and get score (Students only)
    Student will answer all questions for one lesson, then submit
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit quiz answers!"
        )
    
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == submission.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {submission.lesson_id} does not exist!"
        )
    
    # Get all quizzes for this lesson
    quizzes = db.query(Quiz).filter(Quiz.lesson_id == submission.lesson_id).all()
    
    if not quizzes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quiz questions for this lesson!"
        )
    
    # Calculate score
    total_questions = len(quizzes)
    correct_answers = 0
    results = []
    
    for quiz in quizzes:
        # Get student's answer for this quiz
        student_answer = submission.answers.get(str(quiz.id))
        
        if student_answer:
            # Check if answer correct (case-insensitive)
            is_correct = student_answer.strip().lower() == quiz.correct_answer.strip().lower()
            
            if is_correct:
                correct_answers += 1
            
            results.append({
                "quiz_id": quiz.id,
                "question": quiz.question,
                "your_answer": student_answer,
                "correct_answer": quiz.correct_answer,
                "is_correct": is_correct,
                "explanation": quiz.explanation
            })
    
    # Calculate percentage score
    score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Save or update student progress
    progress = db.query(StudentProgress).filter(
        StudentProgress.student_id == current_user.id,
        StudentProgress.lesson_id == submission.lesson_id
    ).first()
    
    if progress:
        # Update existing progress
        progress.quiz_score = score_percentage
        progress.quiz_attempts += 1
        progress.is_completed = score_percentage >= 60  # Pass mark is 60%
        if score_percentage >= 60:
            from datetime import datetime
            progress.completion_date = datetime.utcnow()
    else:
        # Create new progress record
        from datetime import datetime
        progress = StudentProgress(
            student_id=current_user.id,
            lesson_id=submission.lesson_id,
            quiz_score=score_percentage,
            quiz_attempts=1,
            is_completed=score_percentage >= 60,
            completion_date=datetime.utcnow() if score_percentage >= 60 else None
        )
        db.add(progress)
    
    db.commit()
    
    # Return result
    return {
        "lesson_id": submission.lesson_id,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "score_percentage": round(score_percentage, 2),
        "passed": score_percentage >= 60,
        "pass_mark": 60,
        "attempts": progress.quiz_attempts,
        "results": results
    }