# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Persona Monitoreada
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, Date, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


# Valores válidos para gender (enum nativo en PostgreSQL)
GENDER_VALUES = ["male", "female", "other"]

# Valores válidos para blood_type (enum nativo en PostgreSQL)
BLOOD_TYPE_VALUES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


class MonitoredPerson(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Persona Monitoreada - Adultos mayores que usan el dispositivo
    """
    __tablename__ = "monitored_persons"

    # ═══════════════════════════════════════════════════════════════════════
    # RELACIÓN CON USUARIO (cuidador/familiar)
    # ═══════════════════════════════════════════════════════════════════════
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN PERSONAL
    # ═══════════════════════════════════════════════════════════════════════
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=True)
    # Usamos String para coincidir con enum nativo de PostgreSQL
    gender = Column(String(10), nullable=True)
    photo_url = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN MÉDICA BÁSICA
    # ═══════════════════════════════════════════════════════════════════════
    # Usamos String para coincidir con enum nativo de PostgreSQL
    blood_type = Column(String(5), nullable=True)
    weight = Column(Float, nullable=True)  # kg
    height = Column(Float, nullable=True)  # cm
    
    # Notas generales
    notes = Column(Text, nullable=True)
    
    # Relación con el cuidador (la columna en DB se llama "relationship")
    relationship_type = Column("relationship", String(50), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # UMBRALES PERSONALIZADOS DE SIGNOS VITALES
    # ═══════════════════════════════════════════════════════════════════════
    heart_rate_min = Column(Float, default=50, nullable=False)
    heart_rate_max = Column(Float, default=120, nullable=False)
    spo2_min = Column(Float, default=92, nullable=False)
    temperature_min = Column(Float, default=35.0, nullable=False)
    temperature_max = Column(Float, default=38.5, nullable=False)
    systolic_bp_min = Column(Float, default=90, nullable=False)
    systolic_bp_max = Column(Float, default=140, nullable=False)
    diastolic_bp_min = Column(Float, default=60, nullable=False)
    diastolic_bp_max = Column(Float, default=90, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO
    # ═══════════════════════════════════════════════════════════════════════
    is_active = Column(Boolean, default=True, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    user = relationship("User", back_populates="monitored_persons")
    
    device = relationship(
        "Device",
        back_populates="monitored_person",
        uselist=False  # Relación uno a uno
    )
    
    emergency_contacts = relationship(
        "EmergencyContact",
        back_populates="monitored_person",
        cascade="all, delete-orphan"
    )
    
    medical_conditions = relationship(
        "MedicalCondition",
        back_populates="monitored_person",
        cascade="all, delete-orphan"
    )
    
    geofences = relationship(
        "Geofence",
        back_populates="monitored_person",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MonitoredPerson {self.first_name} {self.last_name}>"
    
    @property
    def full_name(self) -> str:
        """Nombre completo de la persona monitoreada"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int | None:
        """Calcula la edad basada en la fecha de nacimiento"""
        if not self.birth_date:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
