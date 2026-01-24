# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Signos Vitales
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.vital_signs import (
    VitalSignsResponse, VitalSignsHistoryResponse,
    CurrentVitalsResponse, VitalSignsStats
)
from app.services.vital_signs_service import VitalSignsService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/current", response_model=List[CurrentVitalsResponse])
async def get_current_vitals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener signos vitales actuales de todas las personas monitoreadas
    
    Retorna el último registro de signos vitales de cada dispositivo
    """
    service = VitalSignsService(db)
    vitals = await service.get_current_vitals_for_user(current_user.id)
    return vitals


@router.get("/device/{device_id}/current", response_model=CurrentVitalsResponse)
async def get_device_current_vitals(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener signos vitales actuales de un dispositivo específico
    """
    service = VitalSignsService(db)
    vitals = await service.get_current_vitals(device_id, current_user.id)
    return vitals


@router.get("/device/{device_id}/history", response_model=VitalSignsHistoryResponse)
async def get_vitals_history(
    device_id: UUID,
    period: str = Query("day", description="Periodo: day, week, month"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener historial de signos vitales de un dispositivo
    
    - **period**: day (último día), week (última semana), month (último mes)
    - **start_date**: Fecha de inicio personalizada (opcional)
    - **end_date**: Fecha de fin personalizada (opcional)
    """
    service = VitalSignsService(db)
    
    # Si no se especifican fechas, calcular según el periodo
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(weeks=1)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=1)
    
    history = await service.get_history(
        device_id=device_id,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        period=period
    )
    return history


@router.get("/device/{device_id}/stats", response_model=List[VitalSignsStats])
async def get_vitals_stats(
    device_id: UUID,
    period: str = Query("day", description="Periodo: day, week, month"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener estadísticas de signos vitales (min, max, promedio)
    """
    service = VitalSignsService(db)
    stats = await service.get_stats(device_id, current_user.id, period)
    return stats


@router.get("/device/{device_id}/heart-rate", response_model=VitalSignsHistoryResponse)
async def get_heart_rate_history(
    device_id: UUID,
    period: str = Query("day", description="Periodo: day, week, month"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener historial de ritmo cardíaco
    """
    service = VitalSignsService(db)
    return await service.get_vital_history(device_id, current_user.id, "heart_rate", period)


@router.get("/device/{device_id}/spo2", response_model=VitalSignsHistoryResponse)
async def get_spo2_history(
    device_id: UUID,
    period: str = Query("day", description="Periodo: day, week, month"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener historial de saturación de oxígeno
    """
    service = VitalSignsService(db)
    return await service.get_vital_history(device_id, current_user.id, "spo2", period)


@router.get("/device/{device_id}/temperature", response_model=VitalSignsHistoryResponse)
async def get_temperature_history(
    device_id: UUID,
    period: str = Query("day", description="Periodo: day, week, month"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener historial de temperatura
    """
    service = VitalSignsService(db)
    return await service.get_vital_history(device_id, current_user.id, "temperature", period)
