# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas de Autenticación
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """Schema para iniciar sesión"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema de respuesta de login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema para refrescar token"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Schema de respuesta de refresh token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseModel):
    """Schema para registrar usuario"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class RegisterResponse(BaseModel):
    """Schema de respuesta de registro"""
    message: str = "Usuario registrado exitosamente"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitar recuperación de contraseña"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema para resetear contraseña"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class VerifyEmailRequest(BaseModel):
    """Schema para verificar email"""
    token: str


class TokenPayload(BaseModel):
    """Payload del JWT"""
    sub: str  # user_id
    exp: int  # expiration timestamp
    type: str = "access"  # access o refresh
