# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - User Service
# ═══════════════════════════════════════════════════════════════════════════

from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Servicio para gestión de usuarios"""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Obtener usuario por ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Obtener todos los usuarios"""
        result = await db.execute(
            select(User)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update(
        db: AsyncSession, 
        user_id: UUID, 
        user_update: UserUpdate
    ) -> Optional[User]:
        """Actualizar usuario"""
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def delete(db: AsyncSession, user_id: UUID) -> bool:
        """Eliminar usuario"""
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False
        
        await db.delete(user)
        await db.commit()
        return True
    
    @staticmethod
    async def get_with_monitored_persons(
        db: AsyncSession, 
        user_id: UUID
    ) -> Optional[User]:
        """Obtener usuario con sus personas monitoreadas"""
        result = await db.execute(
            select(User)
            .options(selectinload(User.monitored_persons))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
