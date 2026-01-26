from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50, 
                         description="Unique username for login")
    email: EmailStr = Field(..., description="Valid email address")
    first_name: str = Field(..., min_length=1, max_length=50, 
                           description="First name")
    middle_name: Optional[str] = Field(None, max_length=50, 
                                      description="Middle name (optional - fit empty)")
    surname: str = Field(..., min_length=1, max_length=50, 
                        description="Surname/Last name")
    role: str = Field(..., pattern="^(teacher|student)$", 
                     description="User role - either 'teacher' or 'student'")
    
     # 🔥 FIX FOR EMPTY STRING FROM SWAGGER (PYDANTIC v1)
@field_validator("middle_name", mode="before")
@classmethod
def empty_middle_name_to_none(cls, v):
    if v == "" or v is None:
        return None
    return v

class UserCreate(UserBase):
    """Schema for creating new user"""
    password: str = Field(..., min_length=6, max_length=100, 
                         description="Strong password (minimum 6 characters)")


class UserResponse(UserBase):
    """Schema for user response (what we return to client)"""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str = Field(..., description="Your username")
    password: str = Field(..., description="Your password")


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token data"""
    username: Optional[str] = None


# Subject Schemas
class SubjectBase(BaseModel):
    """Base subject schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class SubjectCreate(SubjectBase):
    """Schema for creating subject"""
    pass


class SubjectResponse(SubjectBase):
    """Schema for subject response"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

        # Topic Schemas
class TopicBase(BaseModel):
    """Base topic schema"""
    subject_id: int = Field(..., description="ID of the subject this topic belong to")
    name: str = Field(..., min_length=1, max_length=100, description="Topic name (e.g., Algebra, Grammar)")
    description: Optional[str] = Field(None, description="Topic description")
    order: int = Field(default=0, description="Order for displaying topics")


class TopicCreate(TopicBase):
    """Schema for creating topic"""
    pass


class TopicResponse(TopicBase):
    """Schema for topic response"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Lesson Schemas
class LessonBase(BaseModel):
    """Base lesson schema"""
    topic_id: int = Field(..., description="ID of the topic this lesson belong to")
    title: str = Field(..., min_length=1, max_length=200, description="Lesson title")
    content: str = Field(..., min_length=10, description="Lesson content TTS will read")
    duration_minutes: int = Field(default=10, description="Estimated lesson duration (minutes)")
    order: int = Field(default=0, description="Order for displaying lessons")
    is_published: bool = Field(default=False, description="Is this lesson ready for students?")


class LessonCreate(LessonBase):
    """Schema for creating lesson"""
    pass


class LessonResponse(LessonBase):
    """Schema for lesson response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

        # Quiz Schemas
class QuizBase(BaseModel):
    """Base quiz schema"""
    lesson_id: int = Field(..., description="ID of the lesson this quiz belong to")
    question: str = Field(..., min_length=10, description="Quiz question")
    question_type: str = Field(default="multiple_choice", 
                               pattern="^(multiple_choice|true_false|short_answer)$",
                               description="Type of question")
    option_a: Optional[str] = Field(None, max_length=200, description="Option A (for multiple choice)")
    option_b: Optional[str] = Field(None, max_length=200, description="Option B (for multiple choice)")
    option_c: Optional[str] = Field(None, max_length=200, description="Option C (for multiple choice)")
    option_d: Optional[str] = Field(None, max_length=200, description="Option D (for multiple choice)")
    correct_answer: str = Field(..., max_length=200, description="The correct answer")
    explanation: Optional[str] = Field(None, description="Explanation of the answer")
    order: int = Field(default=0, description="Order for displaying questions")


class QuizCreate(QuizBase):
    """Schema for creating quiz"""
    pass


class QuizResponse(QuizBase):
    """Schema for quiz response"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Quiz Submission Schemas
class QuizSubmission(BaseModel):
    """Schema for student submitting quiz answers"""
    lesson_id: int = Field(..., description="ID of the lesson")
    answers: dict = Field(..., description="Dictionary of quiz_id: answer pairs")
    # Example: {"1": "A", "2": "B", "3": "True"}


class QuizResult(BaseModel):
    """Schema for quiz result"""
    lesson_id: int
    total_questions: int
    correct_answers: int
    score_percentage: float
    passed: bool
    pass_mark: int
    attempts: int
    results: List[dict]

    # Progress Schemas
class ProgressResponse(BaseModel):
    """Schema for progress response"""
    id: int
    student_id: int
    lesson_id: int
    is_completed: bool
    completion_date: Optional[datetime]
    quiz_score: Optional[float]
    quiz_attempts: int
    last_accessed: datetime
    
    class Config:
        from_attributes = True

class StudentProgressReport(BaseModel):
    """Schema for detailed student progress report"""
    student_id: int
    student_name: str
    total_lessons_started: int
    completed_lessons: int
    completion_rate: float
    average_score: float
    total_quiz_attempts: int
    lessons: List[ProgressResponse]