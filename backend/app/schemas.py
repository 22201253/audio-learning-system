from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
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