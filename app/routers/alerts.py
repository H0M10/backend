# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Alertas
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.schemas.alert import (
    AlertResponse, AlertListResponse, AlertAttendRequest,
    AlertMarkReadRequest, AlertStatsResponse
)
from app.schemas.common import ResponseBase
from app.services.alert_service import AlertService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    is_read: Optional[bool] = None,
    is_attended: Optional[bool] = None,
    device_id: Optional[UUID] = None,
    person_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener lista de alertas con filtros y paginación
    
    - **severity**: Filtrar por severidad (info, warning, critical)
    - **alert_type**: Filtrar por tipo de alerta
    - **is_read**: Filtrar por leídas/no leídas
    - **is_attended**: Filtrar por atendidas/no atendidas
    - **device_id**: Filtrar por dispositivo
    - **person_id**: Filtrar por persona monitoreada
    """
    service = AlertService(db)
    alerts = await service.get_alerts(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        severity=severity,
        alert_type=alert_type,
        is_read=is_read,
        is_attended=is_attended,
        device_id=device_id,
        person_id=person_id,
        start_date=start_date,
        end_date=end_date
    )
    return alerts


@router.get("/recent", response_model=List[AlertResponse])
async def get_recent_alerts(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener alertas más recientes
    """
    service = AlertService(db)
    alerts = await service.get_recent_alerts(current_user.id, limit)
    return alerts


@router.get("/unread", response_model=List[AlertResponse])
async def get_unread_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener alertas no leídas
    """
    service = AlertService(db)
    alerts = await service.get_unread_alerts(current_user.id)
    return alerts


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener estadísticas de alertas
    """
    service = AlertService(db)
    stats = await service.get_stats(current_user.id)
    return stats


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener una alerta por ID
    """
    service = AlertService(db)
    alert = await service.get_by_id(alert_id, current_user.id)
    return alert


@router.put("/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marcar una alerta como leída
    """
    service = AlertService(db)
    alert = await service.mark_as_read(alert_id, current_user.id)
    return alert


@router.put("/mark-read", response_model=ResponseBase)
async def mark_alerts_read(
    request: AlertMarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marcar múltiples alertas como leídas
    """
    service = AlertService(db)
    await service.mark_multiple_as_read(request.alert_ids, current_user.id)
    return ResponseBase(message=f"{len(request.alert_ids)} alertas marcadas como leídas")


@router.put("/mark-all-read", response_model=ResponseBase)
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marcar todas las alertas como leídas
    """
    service = AlertService(db)
    count = await service.mark_all_as_read(current_user.id)
    return ResponseBase(message=f"{count} alertas marcadas como leídas")


@router.put("/{alert_id}/attend", response_model=AlertResponse)
async def attend_alert(
    alert_id: UUID,
    request: AlertAttendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Atender una alerta
    
    - **notes**: Notas sobre la atención de la alerta
    - **is_false_alarm**: Marcar como falsa alarma
    """
    service = AlertService(db)
    alert = await service.attend_alert(
        alert_id=alert_id,
        user_id=current_user.id,
        notes=request.notes,
        is_false_alarm=request.is_false_alarm
    )
    return alert


@router.delete("/{alert_id}", response_model=ResponseBase)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar una alerta
    """
    service = AlertService(db)
    await service.delete(alert_id, current_user.id)
    return ResponseBase(message="Alerta eliminada exitosamente")
