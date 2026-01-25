from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# User Model - For both Teachers and Students
class User(Base):
    """
    User table - store information about teachers and students
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # "teacher" or "student"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # If this user na student, e go get progress records
    progress = relationship("StudentProgress", back_populates="student")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# Subject Model - E.g., Mathematics, English, Science
class Subject(Base):
    """
    Subject table - store different subjects like Math, English, etc.
    """
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subject {self.name}>"


# Topic Model - E.g., Algebra, Grammar, Photosynthesis
class Topic(Base):
    """
    Topic table - store topics under each subject
    E.g., Mathematics > Algebra, English > Grammar
    """
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)  # For ordering topics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subject = relationship("Subject", back_populates="topics")
    lessons = relationship("Lesson", back_populates="topic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Topic {self.name}>"


# Lesson Model - The actual lesson content
class Lesson(Base):
    """
    Lesson table - store lesson content (text that TTS go read)
    """
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # The lesson text wey TTS go read
    duration_minutes = Column(Integer, default=10)  # Estimated lesson duration
    order = Column(Integer, default=0)  # For ordering lessons
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    topic = relationship("Topic", back_populates="lessons")
    quizzes = relationship("Quiz", back_populates="lesson", cascade="all, delete-orphan")
    progress = relationship("StudentProgress", back_populates="lesson")
    
    def __repr__(self):
        return f"<Lesson {self.title}>"


# Quiz Model - Quiz questions for each lesson
class Quiz(Base):
    """
    Quiz table - store quiz questions for lessons
    """
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    question = Column(Text, nullable=False)
    question_type = Column(String(20), default="multiple_choice")  # multiple_choice, true_false, short_answer
    option_a = Column(String(200), nullable=True)
    option_b = Column(String(200), nullable=True)
    option_c = Column(String(200), nullable=True)
    option_d = Column(String(200), nullable=True)
    correct_answer = Column(String(200), nullable=False)  # Store the correct answer
    explanation = Column(Text, nullable=True)  # Explanation for the answer
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    lesson = relationship("Lesson", back_populates="quizzes")
    
    def __repr__(self):
        return f"<Quiz {self.id} for Lesson {self.lesson_id}>"


# Student Progress Model - Track student's learning progress
class StudentProgress(Base):
    """
    Student Progress table - track which lessons student don complete and their quiz scores
    """
    __tablename__ = "student_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    quiz_score = Column(Float, nullable=True)  # Percentage score (0-100)
    quiz_attempts = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")
    
    def __repr__(self):
        return f"<Progress Student:{self.student_id} Lesson:{self.lesson_id}>"