# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Servicio de Autenticación
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, LoginResponse,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_token_pair,
    create_password_reset_token,
    verify_password_reset_token,
    create_email_verification_token,
    verify_email_token
)


class AuthService:
    """Servicio de autenticación"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register(self, data: RegisterRequest) -> User:
        """
        Registrar un nuevo usuario
        """
        # Verificar si el email ya existe
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Verificar si el teléfono ya existe (si se proporciona)
        if data.phone:
            result = await self.db.execute(
                select(User).where(User.phone == data.phone)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El teléfono ya está registrado"
                )
        
        # Crear usuario
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def login(self, email: str, password: str) -> LoginResponse:
        """
        Iniciar sesión
        """
        # Buscar usuario por email
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Verificar contraseña
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Verificar si está activo
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )
        
        # Actualizar último login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        # Generar tokens
        tokens = create_token_pair(str(user.id))
        
        return LoginResponse(
            **tokens,
            user={
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "photo_url": user.photo_url,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_email_verified": user.is_verified,
                "language": user.language,
                "timezone": user.timezone,
                "push_notifications_enabled": user.push_notifications_enabled,
                "email_notifications_enabled": user.email_notifications_enabled,
                "sms_notifications_enabled": user.sms_notifications_enabled,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else user.created_at.isoformat()
            }
        )
    
    async def refresh_tokens(self, user_id: UUID) -> dict:
        """
        Refrescar tokens
        """
        # Verificar que el usuario existe y está activo
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )
        
        return create_token_pair(str(user.id))
    
    async def forgot_password(self, email: str) -> str:
        """
        Generar token para restablecer contraseña
        
        Returns:
            Token de restablecimiento
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Por seguridad, no indicamos si el email existe o no
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Si el email está registrado, recibirás instrucciones"
            )
        
        token = create_password_reset_token(email)
        
        # TODO: Enviar email con el token
        # En desarrollo, devolvemos el token directamente
        
        return token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Restablecer contraseña con token
        """
        email = verify_password_reset_token(token)
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado"
            )
        
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario no encontrado"
            )
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()
        
        return True
    
    async def verify_email(self, token: str) -> bool:
        """
        Verificar email con token
        """
        email = verify_email_token(token)
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado"
            )
        
        result = await self.db.execute(
            update(User)
            .where(User.email == email)
            .values(is_email_verified=True, email_verified_at=datetime.utcnow())
        )
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario no encontrado"
            )
        
        await self.db.commit()
        
        return True
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Obtener usuario por ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
