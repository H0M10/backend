# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas de Alertas
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class AlertType(str, Enum):
    HIGH_HEART_RATE = "HIGH_HEART_RATE"
    LOW_HEART_RATE = "LOW_HEART_RATE"
    LOW_SPO2 = "LOW_SPO2"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    LOW_TEMPERATURE = "LOW_TEMPERATURE"
    HIGH_BLOOD_PRESSURE = "HIGH_BLOOD_PRESSURE"
    LOW_BLOOD_PRESSURE = "LOW_BLOOD_PRESSURE"
    FALL_DETECTED = "FALL_DETECTED"
    SOS_BUTTON = "SOS_BUTTON"
    GEOFENCE_EXIT = "GEOFENCE_EXIT"
    GEOFENCE_ENTER = "GEOFENCE_ENTER"
    LOW_BATTERY = "LOW_BATTERY"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    DEVICE_ERROR = "DEVICE_ERROR"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertResponse(BaseModel):
    """Schema de respuesta de alerta"""
    id: UUID
    device_id: UUID
    monitored_person_id: UUID
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    value: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    is_read: bool
    is_attended: bool
    attended_at: Optional[datetime] = None
    is_false_alarm: bool
    notes: Optional[str] = None
    created_at: datetime

    # Información adicional
    monitored_person_name: Optional[str] = None
    device_name: Optional[str] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema de respuesta para lista de alertas"""
    data: List[AlertResponse]
    total: int
    unread_count: int
    critical_count: int
    page: int
    per_page: int
    total_pages: int


class AlertAttendRequest(BaseModel):
    """Schema para atender una alerta"""
    notes: Optional[str] = None
    is_false_alarm: bool = False


class AlertMarkReadRequest(BaseModel):
    """Schema para marcar alertas como leídas"""
    alert_ids: List[UUID]


class AlertStatsResponse(BaseModel):
    """Estadísticas de alertas"""
    total_alerts: int
    unread_alerts: int
    critical_alerts: int
    attended_alerts: int
    false_alarms: int
    alerts_by_type: dict
    alerts_by_severity: dict
    alerts_today: int
    alerts_this_week: int
    alerts_this_month: int
