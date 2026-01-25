# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo de Alertas
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, String, Boolean, DateTime, Float, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
import enum
from datetime import datetime


class AlertType(str, enum.Enum):
    """Tipos de alerta"""
    # Signos vitales
    HIGH_HEART_RATE = "HIGH_HEART_RATE"
    LOW_HEART_RATE = "LOW_HEART_RATE"
    LOW_SPO2 = "LOW_SPO2"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    LOW_TEMPERATURE = "LOW_TEMPERATURE"
    HIGH_BLOOD_PRESSURE = "HIGH_BLOOD_PRESSURE"
    LOW_BLOOD_PRESSURE = "LOW_BLOOD_PRESSURE"
    
    # Emergencias
    FALL_DETECTED = "FALL_DETECTED"
    SOS_BUTTON = "SOS_BUTTON"
    
    # Ubicación
    GEOFENCE_EXIT = "GEOFENCE_EXIT"
    GEOFENCE_ENTER = "GEOFENCE_ENTER"
    
    # Dispositivo
    LOW_BATTERY = "LOW_BATTERY"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    DEVICE_ERROR = "DEVICE_ERROR"


class AlertSeverity(str, enum.Enum):
    """Niveles de severidad de la alerta"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# Mapeo de tipos de alerta a severidad y título
ALERT_CONFIG = {
    AlertType.HIGH_HEART_RATE: {
        "severity": AlertSeverity.WARNING,
        "title": "Ritmo cardíaco alto",
        "message": "Se detectó un ritmo cardíaco elevado: {value} BPM"
    },
    AlertType.LOW_HEART_RATE: {
        "severity": AlertSeverity.WARNING,
        "title": "Ritmo cardíaco bajo",
        "message": "Se detectó un ritmo cardíaco bajo: {value} BPM"
    },
    AlertType.LOW_SPO2: {
        "severity": AlertSeverity.CRITICAL,
        "title": "Oxígeno bajo",
        "message": "Saturación de oxígeno baja: {value}%"
    },
    AlertType.HIGH_TEMPERATURE: {
        "severity": AlertSeverity.WARNING,
        "title": "Temperatura alta",
        "message": "Temperatura corporal elevada: {value}°C"
    },
    AlertType.LOW_TEMPERATURE: {
        "severity": AlertSeverity.WARNING,
        "title": "Temperatura baja",
        "message": "Temperatura corporal baja: {value}°C"
    },
    AlertType.FALL_DETECTED: {
        "severity": AlertSeverity.CRITICAL,
        "title": "¡Caída detectada!",
        "message": "Se ha detectado una posible caída"
    },
    AlertType.SOS_BUTTON: {
        "severity": AlertSeverity.CRITICAL,
        "title": "¡SOS activado!",
        "message": "Se ha presionado el botón de emergencia"
    },
    AlertType.GEOFENCE_EXIT: {
        "severity": AlertSeverity.WARNING,
        "title": "Salida de zona segura",
        "message": "Ha salido de la zona: {zone_name}"
    },
    AlertType.LOW_BATTERY: {
        "severity": AlertSeverity.INFO,
        "title": "Batería baja",
        "message": "Nivel de batería: {value}%"
    },
    AlertType.DEVICE_DISCONNECTED: {
        "severity": AlertSeverity.INFO,
        "title": "Dispositivo desconectado",
        "message": "El dispositivo ha perdido conexión"
    },
}


class Alert(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Alerta - Notificaciones de eventos importantes
    """
    __tablename__ = "alerts"

    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # INFORMACIÓN DE LA ALERTA
    # ═══════════════════════════════════════════════════════════════════════
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, index=True)
    
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Valor que disparó la alerta (si aplica)
    value = Column(Float, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # UBICACIÓN (si la alerta tiene contexto geográfico)
    # ═══════════════════════════════════════════════════════════════════════
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADO DE LA ALERTA
    # ═══════════════════════════════════════════════════════════════════════
    is_read = Column(Boolean, default=False, nullable=False)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Si la alerta fue una falsa alarma
    is_false_alarm = Column(Boolean, default=False, nullable=False)
    false_alarm_notes = Column(Text, nullable=True)
    
    # Datos adicionales JSON
    data = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    device = relationship("Device", back_populates="alerts")

    def __repr__(self):
        return f"<Alert {self.alert_type.value} - {self.severity.value}>"
    
    @classmethod
    def create_from_type(
        cls,
        alert_type: AlertType,
        device_id: str,
        monitored_person_id: str,
        value: float = None,
        latitude: float = None,
        longitude: float = None,
        address: str = None,
        zone_name: str = None,
    ) -> "Alert":
        """
        Crea una alerta basada en el tipo con configuración predefinida
        """
        config = ALERT_CONFIG.get(alert_type, {
            "severity": AlertSeverity.INFO,
            "title": "Alerta",
            "message": "Se ha generado una alerta"
        })
        
        message = config["message"]
        if value is not None:
            message = message.format(value=value)
        if zone_name:
            message = message.format(zone_name=zone_name)
        
        return cls(
            device_id=device_id,
            monitored_person_id=monitored_person_id,
            alert_type=alert_type,
            severity=config["severity"],
            title=config["title"],
            message=message,
            value=value,
            latitude=latitude,
            longitude=longitude,
            address=address,
        )
