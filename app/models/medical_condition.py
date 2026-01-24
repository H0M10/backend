# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Condiciones Médicas
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, Date, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
import enum


class ConditionType(str, enum.Enum):
    """Tipos de condición médica"""
    DISEASE = "disease"           # Enfermedad
    ALLERGY = "allergy"           # Alergia
    MEDICATION = "medication"     # Medicamento actual
    SURGERY = "surgery"           # Cirugía previa
    DISABILITY = "disability"     # Discapacidad
    OTHER = "other"               # Otro


class Severity(str, enum.Enum):
    """Niveles de severidad"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MedicalCondition(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Condición Médica - Historial médico de la persona monitoreada
    """
    __tablename__ = "medical_conditions"

    # ═══════════════════════════════════════════════════════════════════════
    # RELACIÓN CON PERSONA MONITOREADA
    # ═══════════════════════════════════════════════════════════════════════
    monitored_person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitored_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN DE LA CONDICIÓN
    # ═══════════════════════════════════════════════════════════════════════
    condition_type = Column(Enum(ConditionType), nullable=False)
    name = Column(String(200), nullable=False)  # Nombre de la condición
    description = Column(Text, nullable=True)
    
    # Severidad
    severity = Column(Enum(Severity), default=Severity.MEDIUM, nullable=False)
    
    # Fecha de diagnóstico (para enfermedades) o fecha de cirugía
    diagnosis_date = Column(Date, nullable=True)
    
    # Para medicamentos: dosis y frecuencia
    dosage = Column(String(100), nullable=True)  # Ej: "500mg"
    frequency = Column(String(100), nullable=True)  # Ej: "Cada 8 horas"
    
    # Médico que diagnosticó/prescribió
    doctor_name = Column(String(200), nullable=True)
    
    # Notas adicionales
    notes = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO
    # ═══════════════════════════════════════════════════════════════════════
    is_active = Column(Boolean, default=True, nullable=False)  # Condición activa/tratamiento en curso
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    monitored_person = relationship("MonitoredPerson", back_populates="medical_conditions")

    def __repr__(self):
        return f"<MedicalCondition {self.name}>"
