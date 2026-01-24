# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Location Service
# ═══════════════════════════════════════════════════════════════════════════

from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.location import Location
from app.schemas.location import LocationCreate


class LocationService:
    """Servicio para gestión de ubicaciones"""
    
    @staticmethod
    async def create(
        db: AsyncSession, 
        location_data: LocationCreate
    ) -> Location:
        """Crear registro de ubicación"""
        location = Location(**location_data.model_dump())
        db.add(location)
        await db.commit()
        await db.refresh(location)
        return location
    
    @staticmethod
    async def get_by_device(
        db: AsyncSession, 
        device_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Location]:
        """Obtener ubicaciones por dispositivo"""
        result = await db.execute(
            select(Location)
            .where(Location.device_id == device_id)
            .order_by(Location.recorded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_latest_by_device(
        db: AsyncSession, 
        device_id: UUID
    ) -> Optional[Location]:
        """Obtener última ubicación"""
        result = await db.execute(
            select(Location)
            .where(Location.device_id == device_id)
            .order_by(Location.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_history(
        db: AsyncSession, 
        device_id: UUID,
        hours: int = 24
    ) -> List[Location]:
        """Obtener historial de ubicaciones"""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(Location)
            .where(Location.device_id == device_id)
            .where(Location.recorded_at >= since)
            .order_by(Location.recorded_at.asc())
        )
        return result.scalars().all()
