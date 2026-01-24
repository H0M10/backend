# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Monitored Person Service
# ═══════════════════════════════════════════════════════════════════════════

from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.monitored_person import MonitoredPerson
from app.schemas.monitored_person import MonitoredPersonCreate, MonitoredPersonUpdate


class MonitoredPersonService:
    """Servicio para gestión de personas monitoreadas"""
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession, 
        person_id: UUID
    ) -> Optional[MonitoredPerson]:
        """Obtener persona por ID"""
        result = await db.execute(
            select(MonitoredPerson).where(MonitoredPerson.id == person_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_user_id(
        db: AsyncSession, 
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[MonitoredPerson]:
        """Obtener personas monitoreadas por usuario"""
        result = await db.execute(
            select(MonitoredPerson)
            .where(MonitoredPerson.user_id == user_id)
            .where(MonitoredPerson.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def create(
        db: AsyncSession, 
        user_id: UUID,
        person_data: MonitoredPersonCreate
    ) -> MonitoredPerson:
        """Crear persona monitoreada"""
        person = MonitoredPerson(
            user_id=user_id,
            **person_data.model_dump()
        )
        db.add(person)
        await db.commit()
        await db.refresh(person)
        return person
    
    @staticmethod
    async def update(
        db: AsyncSession, 
        person_id: UUID,
        person_update: MonitoredPersonUpdate
    ) -> Optional[MonitoredPerson]:
        """Actualizar persona monitoreada"""
        person = await MonitoredPersonService.get_by_id(db, person_id)
        if not person:
            return None
        
        update_data = person_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(person, field, value)
        
        await db.commit()
        await db.refresh(person)
        return person
    
    @staticmethod
    async def delete(db: AsyncSession, person_id: UUID) -> bool:
        """Eliminar persona monitoreada (soft delete)"""
        person = await MonitoredPersonService.get_by_id(db, person_id)
        if not person:
            return False
        
        person.is_active = False
        await db.commit()
        return True
    
    @staticmethod
    async def get_with_device(
        db: AsyncSession, 
        person_id: UUID
    ) -> Optional[MonitoredPerson]:
        """Obtener persona con su dispositivo"""
        result = await db.execute(
            select(MonitoredPerson)
            .options(selectinload(MonitoredPerson.devices))
            .where(MonitoredPerson.id == person_id)
        )
        return result.scalar_one_or_none()
