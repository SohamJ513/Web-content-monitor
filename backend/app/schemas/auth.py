# backend/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password endpoint"""
    email: EmailStr

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        """Additional email validation"""
        if not re.match(r'[^@]+@[^@]+\.[^@]+', v):
            raise ValueError('Invalid email format')
        return v.lower().strip()  # Normalize email

class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password endpoint"""
    message: str = Field(
        default="If the email exists, a reset link has been sent",
        description="Always returns success message for security"
    )

class ResetPasswordRequest(BaseModel):
    """Request schema for reset password endpoint"""
    token: str = Field(
        min_length=32,
        max_length=255,
        description="Password reset token from email link"
    )
    new_password: str = Field(
        min_length=6,
        max_length=128,
        description="New password (min 6 characters)"
    )

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Basic password strength validation"""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        
        # Optional: Add more password strength checks
        # if not any(char.isdigit() for char in v):
        #     raise ValueError('Password must contain at least one number')
        # if not any(char.isupper() for char in v):
        #     raise ValueError('Password must contain at least one uppercase letter')
        # if not any(char.islower() for char in v):
        #     raise ValueError('Password must contain at least one lowercase letter')
        
        return v

class ResetPasswordResponse(BaseModel):
    """Response schema for reset password endpoint"""
    message: str = Field(
        default="Password reset successfully",
        description="Confirmation message"
    )

# Optional: Additional auth-related schemas you might need later
class ChangePasswordRequest(BaseModel):
    """Schema for changing password while logged in"""
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters long')
        return v

class ChangePasswordResponse(BaseModel):
    """Response for password change"""
    message: str = "Password changed successfully"