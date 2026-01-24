# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Ubicaciones
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.location import (
    LocationResponse, LocationHistoryResponse, CurrentLocationResponse,
    GeofenceCreate, GeofenceUpdate, GeofenceResponse, GeofenceCheckResponse
)
from app.schemas.common import ResponseBase
from app.services.location_service import LocationService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# UBICACIONES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/current", response_model=List[CurrentLocationResponse])
async def get_current_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener ubicación actual de todas las personas monitoreadas
    """
    service = LocationService(db)
    locations = await service.get_current_locations_for_user(current_user.id)
    return locations


@router.get("/device/{device_id}/current", response_model=CurrentLocationResponse)
async def get_device_current_location(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener ubicación actual de un dispositivo específico
    """
    service = LocationService(db)
    location = await service.get_current_location(device_id, current_user.id)
    return location


@router.get("/device/{device_id}/history", response_model=LocationHistoryResponse)
async def get_location_history(
    device_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener historial de ubicaciones de un dispositivo
    
    - **start_date**: Fecha de inicio (por defecto: últimas 24 horas)
    - **end_date**: Fecha de fin (por defecto: ahora)
    - **limit**: Número máximo de registros
    """
    service = LocationService(db)
    
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=1)
    
    history = await service.get_history(
        device_id=device_id,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return history


# ═══════════════════════════════════════════════════════════════════════════
# GEOFENCES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/geofences", response_model=List[GeofenceResponse])
async def get_all_geofences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener todos los geofences del usuario
    """
    service = LocationService(db)
    geofences = await service.get_all_geofences_for_user(current_user.id)
    return geofences


@router.get("/person/{person_id}/geofences", response_model=List[GeofenceResponse])
async def get_person_geofences(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener geofences de una persona monitoreada
    """
    service = LocationService(db)
    geofences = await service.get_geofences_by_person(person_id, current_user.id)
    return geofences


@router.post("/geofences", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
async def create_geofence(
    request: GeofenceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear un nuevo geofence
    
    - **name**: Nombre de la zona (ej: "Casa", "Hospital")
    - **latitude/longitude**: Centro del geofence
    - **radius**: Radio en metros (10-10000)
    """
    service = LocationService(db)
    geofence = await service.create_geofence(request, current_user.id)
    return GeofenceResponse.model_validate(geofence)


@router.put("/geofences/{geofence_id}", response_model=GeofenceResponse)
async def update_geofence(
    geofence_id: UUID,
    request: GeofenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar un geofence
    """
    service = LocationService(db)
    geofence = await service.update_geofence(geofence_id, request, current_user.id)
    return GeofenceResponse.model_validate(geofence)


@router.delete("/geofences/{geofence_id}", response_model=ResponseBase)
async def delete_geofence(
    geofence_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar un geofence
    """
    service = LocationService(db)
    await service.delete_geofence(geofence_id, current_user.id)
    return ResponseBase(message="Geofence eliminado exitosamente")


@router.get("/geofences/{geofence_id}/check", response_model=GeofenceCheckResponse)
async def check_geofence(
    geofence_id: UUID,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verificar si una coordenada está dentro de un geofence
    """
    service = LocationService(db)
    result = await service.check_point_in_geofence(
        geofence_id=geofence_id,
        latitude=latitude,
        longitude=longitude,
        user_id=current_user.id
    )
    return result
