# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Autenticación
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.auth import (
    LoginRequest, LoginResponse, 
    RegisterRequest, RegisterResponse,
    RefreshTokenRequest, RefreshTokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest
)
from app.schemas.common import ResponseBase
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar un nuevo usuario
    
    - **email**: Email único del usuario
    - **password**: Contraseña (mínimo 8 caracteres)
    - **first_name**: Nombre
    - **last_name**: Apellido
    - **phone**: Teléfono (opcional)
    """
    auth_service = AuthService(db)
    user = await auth_service.register(request)
    return RegisterResponse(
        message="Usuario registrado exitosamente. Por favor verifica tu email.",
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Iniciar sesión
    
    - **email**: Email del usuario
    - **password**: Contraseña
    
    Retorna tokens de acceso y refresh
    """
    auth_service = AuthService(db)
    return await auth_service.login(request.email, request.password)


@router.post("/login/form", response_model=LoginResponse)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Iniciar sesión usando formulario OAuth2 (para Swagger UI)
    """
    auth_service = AuthService(db)
    return await auth_service.login(form_data.username, form_data.password)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refrescar token de acceso usando refresh token
    """
    auth_service = AuthService(db)
    return await auth_service.refresh_token(request.refresh_token)


@router.post("/logout", response_model=ResponseBase)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cerrar sesión (invalidar tokens)
    """
    # En una implementación completa, aquí invalidaríamos el token en Redis
    return ResponseBase(message="Sesión cerrada exitosamente")


@router.post("/forgot-password", response_model=ResponseBase)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Solicitar recuperación de contraseña
    
    Envía un email con link de recuperación
    """
    auth_service = AuthService(db)
    await auth_service.request_password_reset(request.email)
    return ResponseBase(message="Si el email existe, recibirás instrucciones para recuperar tu contraseña")


@router.post("/reset-password", response_model=ResponseBase)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resetear contraseña con token de recuperación
    """
    auth_service = AuthService(db)
    await auth_service.reset_password(request.token, request.new_password)
    return ResponseBase(message="Contraseña actualizada exitosamente")


@router.post("/verify-email", response_model=ResponseBase)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verificar email con token
    """
    auth_service = AuthService(db)
    await auth_service.verify_email(request.token)
    return ResponseBase(message="Email verificado exitosamente")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener información del usuario autenticado
    """
    return UserResponse.model_validate(current_user)
