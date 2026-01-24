# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas de Persona Monitoreada
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodType(str, Enum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class MonitoredPersonBase(BaseModel):
    """Schema base para Persona Monitoreada"""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None
    photo_url: Optional[str] = None
    blood_type: Optional[BloodType] = None
    weight: Optional[float] = Field(None, ge=0, le=500)
    height: Optional[float] = Field(None, ge=0, le=300)
    notes: Optional[str] = None


class MonitoredPersonCreate(MonitoredPersonBase):
    """Schema para crear persona monitoreada"""
    pass


class MonitoredPersonUpdate(BaseModel):
    """Schema para actualizar persona monitoreada"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None
    photo_url: Optional[str] = None
    blood_type: Optional[BloodType] = None
    weight: Optional[float] = Field(None, ge=0, le=500)
    height: Optional[float] = Field(None, ge=0, le=300)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class VitalThresholdsUpdate(BaseModel):
    """Schema para actualizar umbrales de signos vitales"""
    heart_rate_min: Optional[float] = Field(None, ge=30, le=100)
    heart_rate_max: Optional[float] = Field(None, ge=60, le=200)
    spo2_min: Optional[float] = Field(None, ge=70, le=100)
    temperature_min: Optional[float] = Field(None, ge=30, le=40)
    temperature_max: Optional[float] = Field(None, ge=35, le=45)
    systolic_bp_min: Optional[float] = Field(None, ge=60, le=200)
    systolic_bp_max: Optional[float] = Field(None, ge=80, le=250)
    diastolic_bp_min: Optional[float] = Field(None, ge=40, le=150)
    diastolic_bp_max: Optional[float] = Field(None, ge=50, le=180)


class MonitoredPersonResponse(MonitoredPersonBase):
    """Schema de respuesta de persona monitoreada"""
    id: UUID
    user_id: UUID
    is_active: bool
    heart_rate_min: float
    heart_rate_max: float
    spo2_min: float
    temperature_min: float
    temperature_max: float
    systolic_bp_min: float
    systolic_bp_max: float
    diastolic_bp_min: float
    diastolic_bp_max: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmergencyContactBase(BaseModel):
    """Schema base para contacto de emergencia"""
    name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=8, max_length=20)
    email: Optional[str] = None
    relationship_type: Optional[str] = Field(None, max_length=50)
    is_primary: bool = False
    notify_push: bool = True
    notify_sms: bool = True
    notify_email: bool = True
    only_critical: bool = False
    notes: Optional[str] = None


class EmergencyContactCreate(EmergencyContactBase):
    """Schema para crear contacto de emergencia"""
    pass


class EmergencyContactUpdate(BaseModel):
    """Schema para actualizar contacto de emergencia"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = Field(None, min_length=8, max_length=20)
    email: Optional[str] = None
    relationship_type: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    notify_push: Optional[bool] = None
    notify_sms: Optional[bool] = None
    notify_email: Optional[bool] = None
    only_critical: Optional[bool] = None
    notes: Optional[str] = None


class EmergencyContactResponse(EmergencyContactBase):
    """Schema de respuesta de contacto de emergencia"""
    id: UUID
    monitored_person_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicalConditionBase(BaseModel):
    """Schema base para condición médica"""
    condition_type: str
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    severity: str = "medium"
    diagnosis_date: Optional[date] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    doctor_name: Optional[str] = None
    notes: Optional[str] = None


class MedicalConditionCreate(MedicalConditionBase):
    """Schema para crear condición médica"""
    pass


class MedicalConditionResponse(MedicalConditionBase):
    """Schema de respuesta de condición médica"""
    id: UUID
    monitored_person_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MonitoredPersonFullResponse(MonitoredPersonResponse):
    """Schema completo de persona monitoreada con relaciones"""
    emergency_contacts: List[EmergencyContactResponse] = []
    medical_conditions: List[MedicalConditionResponse] = []
    device: Optional["DeviceBasic"] = None


class DeviceBasic(BaseModel):
    """Schema básico de dispositivo"""
    id: UUID
    serial_number: str
    code: str
    name: Optional[str]
    status: str
    battery_level: float
    is_connected: bool
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


# Actualizar forward references
MonitoredPersonFullResponse.model_rebuild()
