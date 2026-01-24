# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Signos Vitales
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from datetime import datetime


class VitalSigns(Base, UUIDMixin):
    """
    Modelo de Signos Vitales - Datos capturados por el dispositivo
    """
    __tablename__ = "vital_signs"

    # ═══════════════════════════════════════════════════════════════════════
    # RELACIÓN CON DISPOSITIVO
    # ═══════════════════════════════════════════════════════════════════════
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # SIGNOS VITALES
    # ═══════════════════════════════════════════════════════════════════════
    
    # Ritmo cardíaco (BPM - latidos por minuto)
    heart_rate = Column(Float, nullable=True)
    
    # Saturación de oxígeno (SpO2 - porcentaje)
    spo2 = Column(Float, nullable=True)
    
    # Temperatura corporal (°C)
    temperature = Column(Float, nullable=True)
    
    # Presión arterial
    systolic_bp = Column(Float, nullable=True)   # Sistólica (mmHg)
    diastolic_bp = Column(Float, nullable=True)  # Diastólica (mmHg)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ACTIVIDAD
    # ═══════════════════════════════════════════════════════════════════════
    steps = Column(Integer, default=0, nullable=False)
    calories = Column(Float, default=0, nullable=False)
    distance = Column(Float, default=0, nullable=False)  # metros
    
    # ═══════════════════════════════════════════════════════════════════════
    # CALIDAD DE LOS DATOS
    # ═══════════════════════════════════════════════════════════════════════
    heart_rate_quality = Column(Float, nullable=True)  # 0-100
    spo2_quality = Column(Float, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIMESTAMP
    # ═══════════════════════════════════════════════════════════════════════
    recorded_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    device = relationship("Device", back_populates="vital_signs")

    def __repr__(self):
        return f"<VitalSigns device={self.device_id} recorded_at={self.recorded_at}>"
    
    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario"""
        return {
            "id": str(self.id),
            "device_id": str(self.device_id),
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "temperature": self.temperature,
            "systolic_bp": self.systolic_bp,
            "diastolic_bp": self.diastolic_bp,
            "steps": self.steps,
            "calories": self.calories,
            "distance": self.distance,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
