# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Utilidades de Seguridad
# ═══════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta
from typing import Optional, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload


# ═══════════════════════════════════════════════════════════════════════════
# Configuración de Password Hashing
# ═══════════════════════════════════════════════════════════════════════════

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar si la contraseña coincide con el hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generar hash de contraseña"""
    return pwd_context.hash(password)


# ═══════════════════════════════════════════════════════════════════════════
# Configuración de JWT
# ═══════════════════════════════════════════════════════════════════════════

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login/form")


def create_access_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None
) -> str:
    """
    Crear token de acceso JWT
    
    Args:
        subject: ID del usuario o identificador único
        expires_delta: Tiempo de expiración personalizado
        extra_data: Datos adicionales para incluir en el payload
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow()
    }
    
    if extra_data:
        to_encode.update(extra_data)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear token de refresco JWT
    
    Args:
        subject: ID del usuario
        expires_delta: Tiempo de expiración personalizado
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_token_pair(user_id: str | UUID) -> dict:
    """Crear par de tokens (access + refresh)"""
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # en segundos
    }


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decodificar y validar un token JWT
    
    Returns:
        TokenPayload si es válido, None si no
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verificar un token y extraer el subject (user_id)
    
    Returns:
        user_id si es válido, None si no
    """
    token_data = decode_token(token)
    
    if token_data is None:
        return None
    
    if token_data.type != token_type:
        return None
    
    return token_data.sub


# ═══════════════════════════════════════════════════════════════════════════
# Dependencias de FastAPI
# ═══════════════════════════════════════════════════════════════════════════

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependencia para obtener el usuario actual desde el token JWT
    
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None:
            raise credentials_exception
        
        if token_type != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Buscar usuario en la base de datos
    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependencia para obtener el usuario actual activo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    return current_user


async def get_optional_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependencia opcional para obtener el usuario actual
    (no lanza excepción si no hay token)
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Tokens especiales
# ═══════════════════════════════════════════════════════════════════════════

def create_password_reset_token(email: str) -> str:
    """Crear token para restablecer contraseña"""
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hora
    to_encode = {
        "exp": expire,
        "sub": email,
        "type": "password_reset",
        "iat": datetime.utcnow()
    }
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verificar token de restablecimiento de contraseña
    
    Returns:
        email si es válido, None si no
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "password_reset":
            return None
        
        return payload.get("sub")
    except JWTError:
        return None


def create_email_verification_token(email: str) -> str:
    """Crear token para verificación de email"""
    expire = datetime.utcnow() + timedelta(days=7)  # 7 días
    to_encode = {
        "exp": expire,
        "sub": email,
        "type": "email_verification",
        "iat": datetime.utcnow()
    }
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def verify_email_token(token: str) -> Optional[str]:
    """
    Verificar token de verificación de email
    
    Returns:
        email si es válido, None si no
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "email_verification":
            return None
        
        return payload.get("sub")
    except JWTError:
        return None


def create_device_link_token(device_code: str) -> str:
    """Crear token para vincular dispositivo"""
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {
        "exp": expire,
        "sub": device_code,
        "type": "device_link",
        "iat": datetime.utcnow()
    }
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
