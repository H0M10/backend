# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas de Signos Vitales
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class VitalSignsBase(BaseModel):
    """Schema base para signos vitales"""
    heart_rate: Optional[float] = Field(None, ge=0, le=300)
    spo2: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=25, le=45)
    systolic_bp: Optional[float] = Field(None, ge=50, le=300)
    diastolic_bp: Optional[float] = Field(None, ge=30, le=200)
    steps: int = 0
    calories: float = 0
    distance: float = 0


class VitalSignsCreate(VitalSignsBase):
    """Schema para crear registro de signos vitales"""
    device_id: UUID
    recorded_at: Optional[datetime] = None


class VitalSignsResponse(VitalSignsBase):
    """Schema de respuesta de signos vitales"""
    id: UUID
    device_id: UUID
    recorded_at: datetime

    class Config:
        from_attributes = True


class VitalSignsHistoryResponse(BaseModel):
    """Schema de respuesta para historial de signos vitales"""
    data: List[VitalSignsResponse]
    period: str
    device_id: UUID
    start_date: datetime
    end_date: datetime
    total_records: int


class CurrentVitalsResponse(BaseModel):
    """Schema de respuesta para signos vitales actuales"""
    device_id: UUID
    monitored_person_id: UUID
    monitored_person_name: str
    
    # Últimos signos vitales
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    steps: int = 0
    calories: float = 0
    
    # Timestamp del último registro
    last_updated: Optional[datetime] = None
    
    # Estado del dispositivo
    device_status: str
    battery_level: float
    is_connected: bool


class VitalSignsStats(BaseModel):
    """Estadísticas de signos vitales"""
    vital_type: str
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    latest_value: Optional[float]
    total_readings: int
    period: str
