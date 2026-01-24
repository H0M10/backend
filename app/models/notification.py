# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Notificaciones y Push Tokens
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
import enum
from datetime import datetime


class NotificationType(str, enum.Enum):
    """Tipos de notificación"""
    ALERT = "alert"
    INFO = "info"
    REMINDER = "reminder"
    SYSTEM = "system"


class Notification(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Notificación - Historial de notificaciones enviadas al usuario
    """
    __tablename__ = "notifications"

    # ═══════════════════════════════════════════════════════════════════════
    # RELACIÓN CON USUARIO
    # ═══════════════════════════════════════════════════════════════════════
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN DE LA NOTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    notification_type = Column(Enum(NotificationType), default=NotificationType.INFO, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    
    # Datos adicionales (JSON string)
    data = Column(Text, nullable=True)
    
    # ID de la alerta relacionada (si aplica)
    alert_id = Column(UUID(as_uuid=True), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO
    # ═══════════════════════════════════════════════════════════════════════
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CANALES DE ENVÍO
    # ═══════════════════════════════════════════════════════════════════════
    sent_push = Column(Boolean, default=False, nullable=False)
    sent_email = Column(Boolean, default=False, nullable=False)
    sent_sms = Column(Boolean, default=False, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"


class PushToken(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Push Token - Tokens de Expo/Firebase para notificaciones push
    """
    __tablename__ = "push_tokens"

    # ═══════════════════════════════════════════════════════════════════════
    # RELACIÓN CON USUARIO
    # ═══════════════════════════════════════════════════════════════════════
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # TOKEN
    # ═══════════════════════════════════════════════════════════════════════
    token = Column(String(255), unique=True, nullable=False)
    
    # Plataforma del dispositivo
    platform = Column(String(20), nullable=True)  # ios, android, web
    
    # Información del dispositivo
    device_name = Column(String(100), nullable=True)
    device_model = Column(String(100), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO
    # ═══════════════════════════════════════════════════════════════════════
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    user = relationship("User", back_populates="push_tokens")

    def __repr__(self):
        return f"<PushToken {self.token[:20]}...>"
