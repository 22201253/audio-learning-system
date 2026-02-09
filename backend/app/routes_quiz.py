# ==================== COMPLETE routes_quiz.py ====================
# This file handles ALL quiz operations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .database import get_db
from .models import Quiz, Lesson
from .schemas import QuizCreate, QuizResponse
from .routes_auth import get_current_user
from .models import User

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

# ==================== QUIZ ROUTES ====================

@router.get("/", response_model=List[QuizResponse])
async def get_quizzes(
    lesson_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Get all quizzes
    Optional filter by lesson_id
    """
    query = db.query(Quiz)
    
    if lesson_id:
        query = query.filter(Quiz.lesson_id == lesson_id)
    
    quizzes = query.all()
    return quizzes


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    """
    Get specific quiz by ID
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return quiz


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=QuizResponse)
async def create_quiz(
    quiz_data: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new quiz question
    Requires authentication
    """
    # Verify lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == quiz_data.lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Validate correct answer
    if quiz_data.correct_answer.upper() not in ["A", "B", "C", "D"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Correct answer must be A, B, C, or D"
        )
    
    new_quiz = Quiz(
        lesson_id=quiz_data.lesson_id,
        question=quiz_data.question,
        option_a=quiz_data.option_a,
        option_b=quiz_data.option_b,
        option_c=quiz_data.option_c,
        option_d=quiz_data.option_d,
        correct_answer=quiz_data.correct_answer.upper()
    )
    
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    
    return new_quiz


@router.put("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: int,
    quiz_data: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quiz question
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Validate correct answer
    if quiz_data.correct_answer.upper() not in ["A", "B", "C", "D"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Correct answer must be A, B, C, or D"
        )
    
    quiz.lesson_id = quiz_data.lesson_id
    quiz.question = quiz_data.question
    quiz.option_a = quiz_data.option_a
    quiz.option_b = quiz_data.option_b
    quiz.option_c = quiz_data.option_c
    quiz.option_d = quiz_data.option_d
    quiz.correct_answer = quiz_data.correct_answer.upper()
    
    db.commit()
    db.refresh(quiz)
    
    return quiz


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete quiz question
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    db.delete(quiz)
    db.commit()
    
    return {
        "message": "Quiz question deleted successfully",
        "success": True
    }


@router.get("/lessons/{lesson_id}", response_model=List[QuizResponse])
async def get_quizzes_by_lesson(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all quizzes for a specific lesson
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    quizzes = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).all()
    return quizzes