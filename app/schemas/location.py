# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas de Ubicación y Geofence
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class LocationBase(BaseModel):
    """Schema base para ubicación"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None


class LocationCreate(LocationBase):
    """Schema para crear registro de ubicación"""
    device_id: UUID
    recorded_at: Optional[datetime] = None


class LocationResponse(LocationBase):
    """Schema de respuesta de ubicación"""
    id: UUID
    device_id: UUID
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class LocationHistoryResponse(BaseModel):
    """Schema de respuesta para historial de ubicaciones"""
    data: List[LocationResponse]
    device_id: UUID
    start_date: datetime
    end_date: datetime
    total_records: int


class CurrentLocationResponse(BaseModel):
    """Schema de respuesta para ubicación actual"""
    device_id: UUID
    monitored_person_id: UUID
    monitored_person_name: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    recorded_at: datetime
    is_inside_geofence: bool = True
    current_geofence: Optional[str] = None  # Nombre del geofence actual


class GeofenceBase(BaseModel):
    """Schema base para geofence"""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius: float = Field(..., ge=10, le=10000)  # 10m a 10km
    address: Optional[str] = None
    alert_on_exit: bool = True
    alert_on_enter: bool = False
    color: str = Field(default="#10B981", max_length=7)


class GeofenceCreate(GeofenceBase):
    """Schema para crear geofence"""
    monitored_person_id: UUID


class GeofenceUpdate(BaseModel):
    """Schema para actualizar geofence"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius: Optional[float] = Field(None, ge=10, le=10000)
    address: Optional[str] = None
    is_active: Optional[bool] = None
    alert_on_exit: Optional[bool] = None
    alert_on_enter: Optional[bool] = None
    color: Optional[str] = Field(None, max_length=7)


class GeofenceResponse(GeofenceBase):
    """Schema de respuesta de geofence"""
    id: UUID
    monitored_person_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GeofenceCheckResponse(BaseModel):
    """Schema de respuesta para verificar si está dentro del geofence"""
    is_inside: bool
    geofence: Optional[GeofenceResponse] = None
    distance_to_center: Optional[float] = None  # metros
