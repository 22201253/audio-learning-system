# ==================== UPDATES FOR schemas.py ====================
# Add/Update these schemas

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ==================== USER SCHEMAS ====================

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    username: str
    email: EmailStr
    password: str
    first_name: str
    surname: Optional[str] = ""
    role: str  # 'student' or 'teacher'

class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    first_name: str
    surname: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str
    user: UserResponse

class PasswordReset(BaseModel):
    """Schema for password reset"""
    new_password: str

# ==================== SUBJECT SCHEMAS ====================

class SubjectCreate(BaseModel):
    """Schema for creating a subject"""
    name: str
    description: Optional[str] = ""

class SubjectResponse(BaseModel):
    """Schema for subject response"""
    id: int
    name: str
    description: str
    teacher_id: int
    is_deleted: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== LESSON SCHEMAS ====================

class LessonCreate(BaseModel):
    """Schema for creating a lesson"""
    topic_id: int  # This is subject_id
    title: str
    content: str
    duration: Optional[str] = "15 min"
    order: Optional[int] = 0

class LessonResponse(BaseModel):
    """Schema for lesson response"""
    id: int
    topic_id: int
    title: str
    content: str
    duration: str
    order: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== QUIZ SCHEMAS ====================

class QuizCreate(BaseModel):
    """Schema for creating a quiz"""
    lesson_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str  # 'A', 'B', 'C', or 'D'

class QuizResponse(BaseModel):
    """Schema for quiz response"""
    id: int
    lesson_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== PROGRESS SCHEMAS ====================

class ProgressCreate(BaseModel):
    """Schema for creating progress record"""
    student_id: int
    lesson_id: int
    score: int
    total_questions: int
    percentage: Optional[int] = None

class ProgressResponse(BaseModel):
    """Schema for progress response"""
    id: int
    student_id: int
    lesson_id: int
    score: int
    total_questions: int
    percentage: int
    completed_at: datetime
    
class StudentProgressItem(BaseModel):
    lesson_id: int
    lesson_title: str
    completed: bool
    score: int | None = None

class StudentProgressReport(BaseModel):
    student_id: int
    username: str
    progress: List[StudentProgressItem]
    
    class Config:
        from_attributes = True