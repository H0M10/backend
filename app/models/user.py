# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Usuario
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
import uuid


class User(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Usuario - Familiares/Cuidadores que usan la app móvil
    """
    __tablename__ = "users"

    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN BÁSICA
    # ═══════════════════════════════════════════════════════════════════════
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Nombre completo
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Contacto
    phone = Column(String(20), nullable=True)
    
    # Foto de perfil
    photo_url = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO DE LA CUENTA
    # ═══════════════════════════════════════════════════════════════════════
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Verificación de email
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Recuperación de contraseña
    reset_password_token = Column(String(255), nullable=True)
    reset_password_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Último acceso
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # PREFERENCIAS
    # ═══════════════════════════════════════════════════════════════════════
    language = Column(String(10), default="es", nullable=False)
    timezone = Column(String(50), default="America/Mexico_City", nullable=False)
    
    # Notificaciones
    push_notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)
    sms_notifications_enabled = Column(Boolean, default=False, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    monitored_persons = relationship(
        "MonitoredPerson",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    push_tokens = relationship(
        "PushToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"
    
    @property
    def full_name(self) -> str:
        """Nombre completo del usuario"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def hashed_password(self) -> str:
        """Alias para password_hash (compatibilidad con auth_service)"""
        return self.password_hash
    
    @hashed_password.setter
    def hashed_password(self, value: str):
        """Setter para hashed_password"""
        self.password_hash = value
