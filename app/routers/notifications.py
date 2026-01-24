# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Notificaciones Push
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.schemas.common import ResponseBase, PaginatedResponse
from app.utils.security import get_current_user
from app.models.user import User
from app.models.notification import Notification, PushToken
from pydantic import BaseModel, Field


router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Schemas específicos de notificaciones
# ═══════════════════════════════════════════════════════════════════════════

class PushTokenRequest(BaseModel):
    """Solicitud para registrar token de notificaciones push"""
    token: str = Field(..., min_length=1, max_length=500)
    platform: str = Field(..., pattern="^(ios|android|web)$")
    device_name: Optional[str] = None


class NotificationResponse(BaseModel):
    """Respuesta de notificación"""
    id: UUID
    user_id: UUID
    title: str
    body: str
    notification_type: str
    data: Optional[dict] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Lista paginada de notificaciones"""
    success: bool = True
    data: List[NotificationResponse]
    total: int
    page: int
    per_page: int
    pages: int
    unread_count: int


class NotificationStatsResponse(BaseModel):
    """Estadísticas de notificaciones"""
    total: int
    read: int
    unread: int
    by_type: dict


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints de Push Tokens
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/push-token", response_model=ResponseBase)
async def register_push_token(
    request: PushTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar token de notificaciones push
    
    - **token**: Token de FCM o APNs
    - **platform**: Plataforma (ios, android, web)
    - **device_name**: Nombre del dispositivo (opcional)
    """
    # Verificar si el token ya existe
    result = await db.execute(
        select(PushToken).where(PushToken.token == request.token)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Actualizar si el token existe pero es de otro usuario
        existing.user_id = current_user.id
        existing.platform = request.platform
        existing.device_name = request.device_name
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
    else:
        # Crear nuevo token
        push_token = PushToken(
            user_id=current_user.id,
            token=request.token,
            platform=request.platform,
            device_name=request.device_name
        )
        db.add(push_token)
    
    await db.commit()
    return ResponseBase(message="Token registrado exitosamente")


@router.delete("/push-token", response_model=ResponseBase)
async def unregister_push_token(
    token: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Desregistrar token de notificaciones push
    """
    result = await db.execute(
        select(PushToken).where(
            and_(
                PushToken.token == token,
                PushToken.user_id == current_user.id
            )
        )
    )
    push_token = result.scalar_one_or_none()
    
    if not push_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token no encontrado"
        )
    
    await db.delete(push_token)
    await db.commit()
    
    return ResponseBase(message="Token eliminado exitosamente")


@router.delete("/push-token/all", response_model=ResponseBase)
async def unregister_all_push_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Desregistrar todos los tokens de notificaciones push del usuario
    """
    await db.execute(
        delete(PushToken).where(PushToken.user_id == current_user.id)
    )
    await db.commit()
    
    return ResponseBase(message="Todos los tokens eliminados exitosamente")


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints de Notificaciones
# ═══════════════════════════════════════════════════════════════════════════

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    notification_type: Optional[str] = None,
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener lista de notificaciones con paginación
    
    - **notification_type**: Filtrar por tipo de notificación
    - **is_read**: Filtrar por leídas/no leídas
    """
    # Construir query
    query = select(Notification).where(Notification.user_id == current_user.id)
    count_query = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id
    )
    
    # Aplicar filtros
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
        count_query = count_query.where(Notification.notification_type == notification_type)
    
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
        count_query = count_query.where(Notification.is_read == is_read)
    
    # Contar total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Contar no leídas
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        )
    )
    unread_count = unread_result.scalar() or 0
    
    # Aplicar paginación
    offset = (page - 1) * per_page
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    pages = (total + per_page - 1) // per_page
    
    return NotificationListResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        unread_count=unread_count
    )


@router.get("/unread", response_model=List[NotificationResponse])
async def get_unread_notifications(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener notificaciones no leídas
    """
    result = await db.execute(
        select(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    notifications = result.scalars().all()
    
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener conteo de notificaciones no leídas
    """
    result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        )
    )
    count = result.scalar() or 0
    
    return {"unread_count": count}


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener estadísticas de notificaciones
    """
    # Total
    total_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id
        )
    )
    total = total_result.scalar() or 0
    
    # Leídas
    read_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == True
            )
        )
    )
    read = read_result.scalar() or 0
    
    # Por tipo
    type_result = await db.execute(
        select(
            Notification.notification_type,
            func.count(Notification.id).label('count')
        )
        .where(Notification.user_id == current_user.id)
        .group_by(Notification.notification_type)
    )
    by_type = {row.notification_type: row.count for row in type_result}
    
    return NotificationStatsResponse(
        total=total,
        read=read,
        unread=total - read,
        by_type=by_type
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener una notificación por ID
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )
    
    return NotificationResponse.model_validate(notification)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marcar una notificación como leída
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()
    await db.refresh(notification)
    
    return NotificationResponse.model_validate(notification)


@router.put("/mark-all-read", response_model=ResponseBase)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marcar todas las notificaciones como leídas
    """
    result = await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            )
        )
        .values(is_read=True, read_at=datetime.utcnow())
    )
    
    await db.commit()
    
    return ResponseBase(message="Todas las notificaciones marcadas como leídas")


@router.delete("/{notification_id}", response_model=ResponseBase)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar una notificación
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )
    
    await db.delete(notification)
    await db.commit()
    
    return ResponseBase(message="Notificación eliminada exitosamente")


@router.delete("/all", response_model=ResponseBase)
async def delete_all_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar todas las notificaciones del usuario
    """
    await db.execute(
        delete(Notification).where(Notification.user_id == current_user.id)
    )
    await db.commit()
    
    return ResponseBase(message="Todas las notificaciones eliminadas")
