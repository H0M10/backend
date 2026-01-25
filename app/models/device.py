# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Dispositivo IoT
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, DateTime, Float, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
import enum


class DeviceStatus(str, enum.Enum):
    """Estados posibles del dispositivo"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    LOW_BATTERY = "low_battery"
    ERROR = "error"
    CHARGING = "charging"


class DeviceModel(str, enum.Enum):
    """Modelos de dispositivo disponibles"""
    NOVA_BAND_V1 = "NovaBand V1"
    NOVA_BAND_V2 = "NovaBand V2"
    NOVA_BAND_PRO = "NovaBand Pro"


class Device(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Dispositivo IoT - Pulsera inteligente NovaGuardian
    """
    __tablename__ = "devices"

    # ═══════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN DEL DISPOSITIVO
    # ═══════════════════════════════════════════════════════════════════════
    serial_number = Column(String(50), unique=True, index=True, nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)  # Código QR/vinculación
    mac_address = Column(String(17), unique=True, nullable=True)  # AA:BB:CC:DD:EE:FF
    
    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN DEL DISPOSITIVO
    # ═══════════════════════════════════════════════════════════════════════
    name = Column(String(100), nullable=True)  # Nombre personalizado
    model = Column(Enum(DeviceModel), default=DeviceModel.NOVA_BAND_V1, nullable=False)
    firmware_version = Column(String(20), default="1.0.0", nullable=False)
    hardware_version = Column(String(20), default="1.0", nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIÓN CON PERSONA MONITOREADA
    # ═══════════════════════════════════════════════════════════════════════
    monitored_person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitored_persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO DEL DISPOSITIVO
    # ═══════════════════════════════════════════════════════════════════════
    status = Column(Enum(DeviceStatus), default=DeviceStatus.DISCONNECTED, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Batería (0-100)
    battery_level = Column(Float, default=100, nullable=False)
    is_charging = Column(Boolean, default=False, nullable=False)
    
    # Conexión
    is_connected = Column(Boolean, default=False, nullable=False)
    signal_strength = Column(Float, nullable=True)  # dBm
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIMESTAMPS DE ACTIVIDAD
    # ═══════════════════════════════════════════════════════════════════════
    last_seen = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    linked_at = Column(DateTime(timezone=True), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    # Intervalo de envío de datos (segundos)
    sync_interval = Column(Float, default=30, nullable=False)
    
    # Sensores habilitados
    heart_rate_enabled = Column(Boolean, default=True, nullable=False)
    spo2_enabled = Column(Boolean, default=True, nullable=False)
    temperature_enabled = Column(Boolean, default=True, nullable=False)
    gps_enabled = Column(Boolean, default=True, nullable=False)
    fall_detection_enabled = Column(Boolean, default=True, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    monitored_person = relationship("MonitoredPerson", back_populates="device")
    
    vital_signs = relationship(
        "VitalSigns",
        back_populates="device",
        cascade="all, delete-orphan"
    )
    
    locations = relationship(
        "Location",
        back_populates="device",
        cascade="all, delete-orphan"
    )
    
    alerts = relationship(
        "Alert",
        back_populates="device",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Device {self.serial_number}>"
    
    @property
    def is_low_battery(self) -> bool:
        """Verifica si la batería está baja (<20%)"""
        return self.battery_level < 20
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar del dispositivo"""
        return self.name or f"Dispositivo {self.code}"
