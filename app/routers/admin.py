# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Administración
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.device import Device
from app.models.alert import Alert
from app.models.monitored_person import MonitoredPerson
from app.utils.security import get_current_user

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener estadísticas del dashboard de administración
    """
    try:
        # Contar usuarios totales
        users_result = await db.execute(select(func.count(User.id)))
        total_users = users_result.scalar() or 0
        
        # Contar dispositivos totales
        devices_result = await db.execute(select(func.count(Device.id)))
        total_devices = devices_result.scalar() or 0
        
        # Contar dispositivos activos
        active_devices_result = await db.execute(
            select(func.count(Device.id)).where(Device.is_active == True)
        )
        active_devices = active_devices_result.scalar() or 0
        
        # Contar alertas totales
        alerts_result = await db.execute(select(func.count(Alert.id)))
        total_alerts = alerts_result.scalar() or 0
        
        # Contar alertas no leídas
        unread_alerts_result = await db.execute(
            select(func.count(Alert.id)).where(Alert.is_read == False)
        )
        unread_alerts = unread_alerts_result.scalar() or 0
        
        # Contar personas monitoreadas
        monitored_result = await db.execute(select(func.count(MonitoredPerson.id)))
        total_monitored = monitored_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "total_devices": total_devices,
            "active_devices": active_devices,
            "total_alerts": total_alerts,
            "unread_alerts": unread_alerts,
            "total_monitored": total_monitored
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# APP USERS (Usuarios de la aplicación)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/app-users")
async def get_app_users(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener lista de usuarios de la aplicación
    """
    try:
        skip = (page - 1) * limit
        query = select(User)
        
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (User.email.ilike(search_filter)) |
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter))
            )
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Contar total
        count_query = select(func.count(User.id))
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            count_query = count_query.where(
                (User.email.ilike(search_filter)) |
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter))
            )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
                for user in users
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios: {str(e)}"
        )


@router.get("/app-users/{user_id}")
async def get_app_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener un usuario específico por ID
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuario: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# DEVICES (Dispositivos)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/devices")
async def get_admin_devices(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener lista de todos los dispositivos
    """
    try:
        skip = (page - 1) * limit
        query = select(Device)
        
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (Device.code.ilike(search_filter)) |
                (Device.name.ilike(search_filter)) |
                (Device.serial_number.ilike(search_filter))
            )
        
        if is_active is not None:
            query = query.where(Device.is_active == is_active)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        devices = result.scalars().all()
        
        # Contar total
        count_query = select(func.count(Device.id))
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            count_query = count_query.where(
                (Device.code.ilike(search_filter)) |
                (Device.name.ilike(search_filter)) |
                (Device.serial_number.ilike(search_filter))
            )
        if is_active is not None:
            count_query = count_query.where(Device.is_active == is_active)
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "id": str(device.id),
                    "code": device.code,
                    "model": device.model,
                    "name": device.name,
                    "is_active": device.is_active,
                    "battery_level": device.battery_level,
                    "firmware_version": device.firmware_version,
                    "serial_number": device.serial_number,
                    "monitored_person_id": str(device.monitored_person_id) if device.monitored_person_id else None,
                    "last_sync_at": device.last_sync_at.isoformat() if device.last_sync_at else None,
                    "created_at": device.created_at.isoformat() if device.created_at else None
                }
                for device in devices
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener dispositivos: {str(e)}"
        )


@router.get("/devices/{device_id}")
async def get_admin_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener un dispositivo específico por ID
    """
    try:
        result = await db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado"
            )
        
        return {
            "id": str(device.id),
            "code": device.code,
            "model": device.model,
            "name": device.name,
            "is_active": device.is_active,
            "battery_level": device.battery_level,
            "firmware_version": device.firmware_version,
            "serial_number": device.serial_number,
            "monitored_person_id": str(device.monitored_person_id) if device.monitored_person_id else None,
            "last_sync_at": device.last_sync_at.isoformat() if device.last_sync_at else None,
            "created_at": device.created_at.isoformat() if device.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener dispositivo: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# ALERTS (Alertas)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/alerts/pending")
async def get_pending_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener alertas pendientes (no leídas)
    """
    try:
        query = select(Alert).where(Alert.is_read == False).order_by(Alert.created_at.desc()).limit(10)
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        count_result = await db.execute(select(func.count(Alert.id)).where(Alert.is_read == False))
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "id": str(alert.id),
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "message": alert.message,
                    "is_read": alert.is_read,
                    "is_resolved": alert.is_resolved,
                    "device_id": str(alert.device_id) if alert.device_id else None,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                }
                for alert in alerts
            ],
            "total": total
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener alertas pendientes: {str(e)}"
        )


@router.get("/alerts")
async def get_admin_alerts(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener lista de todas las alertas
    """
    try:
        skip = (page - 1) * limit
        query = select(Alert)
        
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (Alert.title.ilike(search_filter)) |
                (Alert.message.ilike(search_filter))
            )
        
        if severity:
            query = query.where(Alert.severity == severity)
        if is_read is not None:
            query = query.where(Alert.is_read == is_read)
        
        query = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        # Contar total
        count_query = select(func.count(Alert.id))
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            count_query = count_query.where(
                (Alert.title.ilike(search_filter)) |
                (Alert.message.ilike(search_filter))
            )
        if severity:
            count_query = count_query.where(Alert.severity == severity)
        if is_read is not None:
            count_query = count_query.where(Alert.is_read == is_read)
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "id": str(alert.id),
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "message": alert.message,
                    "is_read": alert.is_read,
                    "is_resolved": alert.is_resolved,
                    "device_id": str(alert.device_id) if alert.device_id else None,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                }
                for alert in alerts
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener alertas: {str(e)}"
        )


@router.get("/alerts/{alert_id}")
async def get_admin_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener una alerta específica por ID
    """
    try:
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alerta no encontrada"
            )
        
        return {
            "id": str(alert.id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "is_read": alert.is_read,
            "is_resolved": alert.is_resolved,
            "device_id": str(alert.device_id) if alert.device_id else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener alerta: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# MONITORED PERSONS (Personas Monitoreadas)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/monitored")
async def get_admin_monitored(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener lista de todas las personas monitoreadas
    """
    try:
        skip = (page - 1) * limit
        query = select(MonitoredPerson)
        
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (MonitoredPerson.first_name.ilike(search_filter)) |
                (MonitoredPerson.last_name.ilike(search_filter))
            )
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        persons = result.scalars().all()
        
        # Contar total
        count_query = select(func.count(MonitoredPerson.id))
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            count_query = count_query.where(
                (MonitoredPerson.first_name.ilike(search_filter)) |
                (MonitoredPerson.last_name.ilike(search_filter))
            )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "id": str(person.id),
                    "first_name": person.first_name,
                    "last_name": person.last_name,
                    "birth_date": person.birth_date.isoformat() if person.birth_date else None,
                    "gender": person.gender,
                    "blood_type": person.blood_type,
                    "user_id": str(person.user_id) if person.user_id else None,
                    "is_active": person.is_active,
                    "created_at": person.created_at.isoformat() if person.created_at else None
                }
                for person in persons
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener personas monitoreadas: {str(e)}"
        )


@router.get("/monitored/{person_id}")
async def get_admin_monitored_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener una persona monitoreada específica por ID
    """
    try:
        result = await db.execute(select(MonitoredPerson).where(MonitoredPerson.id == person_id))
        person = result.scalar_one_or_none()
        
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona monitoreada no encontrada"
            )
        
        return {
            "id": str(person.id),
            "first_name": person.first_name,
            "last_name": person.last_name,
            "birth_date": person.birth_date.isoformat() if person.birth_date else None,
            "gender": person.gender,
            "blood_type": person.blood_type,
            "user_id": str(person.user_id) if person.user_id else None,
            "is_active": person.is_active,
            "created_at": person.created_at.isoformat() if person.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener persona monitoreada: {str(e)}"
        )
