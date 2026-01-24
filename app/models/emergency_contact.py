# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Contactos de Emergencia
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class EmergencyContact(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Contacto de Emergencia - Personas a notificar en caso de alerta
    """
    __tablename__ = "emergency_contacts"

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
    # INFORMACIÓN DEL CONTACTO
    # ═══════════════════════════════════════════════════════════════════════
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    
    # Relación con la persona monitoreada
    relationship_type = Column(String(50), nullable=True)  # Hijo, Hija, Vecino, etc.
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    is_primary = Column(Boolean, default=False, nullable=False)  # Contacto principal
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Preferencias de notificación
    notify_push = Column(Boolean, default=True, nullable=False)
    notify_sms = Column(Boolean, default=True, nullable=False)
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_call = Column(Boolean, default=False, nullable=False)  # Llamada automática
    
    # Solo notificar alertas críticas
    only_critical = Column(Boolean, default=False, nullable=False)
    
    # Notas
    notes = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    monitored_person = relationship("MonitoredPerson", back_populates="emergency_contacts")

    def __repr__(self):
        return f"<EmergencyContact {self.name}>"
