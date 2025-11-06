# backend/routers/auth.py
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
import secrets
import os
import logging
from typing import Optional

from ..database import (
    get_user_by_email, 
    create_password_reset_token,
    get_valid_password_reset_token,
    mark_password_reset_token_used,
    update_user_password
)
# ✅ FIXED: Import from schemas.auth instead of models
from ..schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, ForgotPasswordResponse, ResetPasswordResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiate password reset process.
    Always returns success to prevent email enumeration attacks.
    """
    user = get_user_by_email(request.email)
    
    # Always return success to prevent email enumeration
    if not user:
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return ForgotPasswordResponse(
            message="If the email exists, a reset link has been sent"
        )
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
    
    # Save token to database
    token_created = create_password_reset_token(
        token=reset_token,
        user_id=user["_id"],
        expires_at=expires_at
    )
    
    if not token_created:
        logger.error(f"Failed to create password reset token for user: {user['email']}")
        # Still return success for security
        return ForgotPasswordResponse(
            message="If the email exists, a reset link has been sent"
        )
    
    # Send reset email
    try:
        await send_reset_email(user["email"], reset_token)
        logger.info(f"Password reset email sent to: {user['email']}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {user['email']}: {e}")
        # Still return success for security
    
    return ForgotPasswordResponse(
        message="If the email exists, a reset link has been sent"
    )

@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset user password using a valid reset token.
    """
    # Find valid token
    token_record = get_valid_password_reset_token(request.token)
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update user password
    password_updated = update_user_password(
        user_id=token_record["user_id"],
        new_password=request.new_password
    )
    
    if not password_updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
    
    # Mark token as used
    mark_password_reset_token_used(request.token)
    
    logger.info(f"Password reset successful for user ID: {token_record['user_id']}")
    
    return ResetPasswordResponse(
        message="Password reset successfully"
    )

async def send_reset_email(email: str, token: str):
    """
    Send password reset email to user.
    For now, this just prints the reset link to console.
    In production, you would integrate with an email service.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{frontend_url}/reset-password/{token}"
    
    # For testing - print to console
    print("=" * 60)
    print("📧 PASSWORD RESET EMAIL (TEST MODE)")
    print("=" * 60)
    print(f"To: {email}")
    print(f"Reset URL: {reset_url}")
    print(f"Token: {token}")
    print("=" * 60)