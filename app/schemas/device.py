# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas de Dispositivo
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class DeviceStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    LOW_BATTERY = "low_battery"
    ERROR = "error"
    CHARGING = "charging"


class DeviceModel(str, Enum):
    NOVA_BAND_V1 = "NovaBand V1"
    NOVA_BAND_V2 = "NovaBand V2"
    NOVA_BAND_PRO = "NovaBand Pro"


class DeviceBase(BaseModel):
    """Schema base para Dispositivo"""
    name: Optional[str] = Field(None, max_length=100)


class DeviceLinkRequest(BaseModel):
    """Schema para vincular dispositivo"""
    code: str = Field(..., min_length=6, max_length=20)
    monitored_person_id: UUID


class DeviceUpdate(BaseModel):
    """Schema para actualizar dispositivo"""
    name: Optional[str] = Field(None, max_length=100)
    monitored_person_id: Optional[UUID] = None
    sync_interval: Optional[float] = Field(None, ge=10, le=300)
    heart_rate_enabled: Optional[bool] = None
    spo2_enabled: Optional[bool] = None
    temperature_enabled: Optional[bool] = None
    gps_enabled: Optional[bool] = None
    fall_detection_enabled: Optional[bool] = None


class DeviceResponse(BaseModel):
    """Schema de respuesta de dispositivo"""
    id: UUID
    serial_number: str
    code: str
    name: Optional[str]
    model: DeviceModel
    firmware_version: str
    status: DeviceStatus
    is_active: bool
    is_connected: bool
    battery_level: float
    is_charging: bool
    last_seen: Optional[datetime]
    last_sync: Optional[datetime]
    linked_at: Optional[datetime]
    monitored_person_id: Optional[UUID]
    sync_interval: float
    heart_rate_enabled: bool
    spo2_enabled: bool
    temperature_enabled: bool
    gps_enabled: bool
    fall_detection_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceWithPersonResponse(DeviceResponse):
    """Schema de dispositivo con información de persona monitoreada"""
    monitored_person: Optional["MonitoredPersonBasic"] = None


class MonitoredPersonBasic(BaseModel):
    """Schema básico de persona monitoreada (para evitar imports circulares)"""
    id: UUID
    first_name: str
    last_name: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


# Actualizar forward references
DeviceWithPersonResponse.model_rebuild()


class DeviceDataPayload(BaseModel):
    """
    Payload de datos enviados por el dispositivo IoT
    Este schema es para recibir datos del hardware
    """
    device_code: str
    timestamp: datetime
    
    # Signos vitales
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    
    # Actividad
    steps: Optional[int] = 0
    calories: Optional[float] = 0
    
    # Ubicación
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    
    # Estado del dispositivo
    battery_level: Optional[float] = None
    is_charging: Optional[bool] = None
    signal_strength: Optional[float] = None
    
    # Eventos
    fall_detected: Optional[bool] = False
    sos_pressed: Optional[bool] = False
