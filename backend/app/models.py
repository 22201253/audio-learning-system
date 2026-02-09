# ==================== UPDATES FOR models.py ====================
# Location: backend/models.py
# Add/Update these models

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# ==================== USER MODEL ====================
# ADD THESE FIELDS if not present:

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    surname = Column(String(50), default="")
    role = Column(String(20), nullable=False)  # 'student' or 'teacher'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = relationship("Subject", back_populates="teacher")
    progress = relationship("StudentProgress", back_populates="student")


# ==================== SUBJECT MODEL ====================
# ADD THESE FIELDS if not present:

class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_deleted = Column(Boolean, default=False)  # ADD THIS for soft delete
    deleted_at = Column(DateTime, nullable=True)  # ADD THIS for soft delete
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = relationship("User", back_populates="subjects")
    lessons = relationship("Lesson", back_populates="subject", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    name = Column(String)
    description = Column(String, nullable=True)
    order = Column(Integer, default=1)

# ==================== LESSON MODEL ====================
# Your existing Lesson model should work, but ensure it has these fields:

class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    duration = Column(String(50), default="15 min")
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subject = relationship("Subject", back_populates="lessons")
    quizzes = relationship("Quiz", back_populates="lesson", cascade="all, delete-orphan")
    progress = relationship("StudentProgress", back_populates="lesson")


# ==================== QUIZ MODEL ====================
# Your existing Quiz model should work:

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    question = Column(Text, nullable=False)
    option_a = Column(String(200), nullable=False)
    option_b = Column(String(200), nullable=False)
    option_c = Column(String(200), nullable=False)
    option_d = Column(String(200), nullable=False)
    correct_answer = Column(String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lesson = relationship("Lesson", back_populates="quizzes")


# ==================== DELETED ITEM MODEL ====================
# ADD THIS NEW MODEL for trash functionality:

class DeletedItem(Base):
    __tablename__ = "deleted_items"
    
    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(50), nullable=False)  # 'subject', 'lesson', 'quiz'
    item_id = Column(Integer, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_data = Column(Text, nullable=False)  # JSON string
    deleted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships (optional)
    teacher = relationship("User")


# ==================== STUDENT PROGRESS MODEL ====================
# Your existing StudentProgress model should work:

class StudentProgress(Base):
    __tablename__ = "student_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Integer)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")
