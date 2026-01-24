# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Vital Signs Service
# ═══════════════════════════════════════════════════════════════════════════

from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.vital_signs import VitalSigns
from app.schemas.vital_signs import VitalSignsCreate


class VitalSignsService:
    """Servicio para gestión de signos vitales"""
    
    @staticmethod
    async def create(
        db: AsyncSession, 
        vital_data: VitalSignsCreate
    ) -> VitalSigns:
        """Crear registro de signos vitales"""
        vital = VitalSigns(**vital_data.model_dump())
        db.add(vital)
        await db.commit()
        await db.refresh(vital)
        return vital
    
    @staticmethod
    async def get_by_device(
        db: AsyncSession, 
        device_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[VitalSigns]:
        """Obtener signos vitales por dispositivo"""
        result = await db.execute(
            select(VitalSigns)
            .where(VitalSigns.device_id == device_id)
            .order_by(VitalSigns.recorded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_latest_by_device(
        db: AsyncSession, 
        device_id: UUID
    ) -> Optional[VitalSigns]:
        """Obtener último registro de signos vitales"""
        result = await db.execute(
            select(VitalSigns)
            .where(VitalSigns.device_id == device_id)
            .order_by(VitalSigns.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_history(
        db: AsyncSession, 
        device_id: UUID,
        hours: int = 24
    ) -> List[VitalSigns]:
        """Obtener historial de signos vitales"""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(VitalSigns)
            .where(VitalSigns.device_id == device_id)
            .where(VitalSigns.recorded_at >= since)
            .order_by(VitalSigns.recorded_at.asc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_averages(
        db: AsyncSession, 
        device_id: UUID,
        hours: int = 24
    ) -> dict:
        """Obtener promedios de signos vitales"""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(
                func.avg(VitalSigns.heart_rate).label('avg_heart_rate'),
                func.avg(VitalSigns.spo2).label('avg_spo2'),
                func.avg(VitalSigns.temperature).label('avg_temperature'),
                func.sum(VitalSigns.steps).label('total_steps'),
                func.sum(VitalSigns.calories).label('total_calories')
            )
            .where(VitalSigns.device_id == device_id)
            .where(VitalSigns.recorded_at >= since)
        )
        row = result.one()
        return {
            'avg_heart_rate': float(row.avg_heart_rate) if row.avg_heart_rate else None,
            'avg_spo2': float(row.avg_spo2) if row.avg_spo2 else None,
            'avg_temperature': float(row.avg_temperature) if row.avg_temperature else None,
            'total_steps': int(row.total_steps) if row.total_steps else 0,
            'total_calories': float(row.total_calories) if row.total_calories else 0
        }
