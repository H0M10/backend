# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Usuarios
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, UserChangePassword
from app.schemas.common import ResponseBase
from app.services.user_service import UserService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener perfil del usuario autenticado
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar perfil del usuario autenticado
    """
    user_service = UserService(db)
    updated_user = await user_service.update(current_user.id, request)
    return UserResponse.model_validate(updated_user)


@router.post("/me/change-password", response_model=ResponseBase)
async def change_password(
    request: UserChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cambiar contraseña del usuario autenticado
    """
    user_service = UserService(db)
    await user_service.change_password(
        current_user.id,
        request.current_password,
        request.new_password
    )
    return ResponseBase(message="Contraseña actualizada exitosamente")


@router.post("/me/photo", response_model=UserResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subir foto de perfil
    
    Formatos aceptados: JPG, PNG
    Tamaño máximo: 5MB
    """
    user_service = UserService(db)
    updated_user = await user_service.upload_photo(current_user.id, file)
    return UserResponse.model_validate(updated_user)


@router.delete("/me/photo", response_model=ResponseBase)
async def delete_photo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar foto de perfil
    """
    user_service = UserService(db)
    await user_service.delete_photo(current_user.id)
    return ResponseBase(message="Foto eliminada exitosamente")


@router.delete("/me", response_model=ResponseBase)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar cuenta del usuario (soft delete)
    """
    user_service = UserService(db)
    await user_service.deactivate(current_user.id)
    return ResponseBase(message="Cuenta desactivada exitosamente")
