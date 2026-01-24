# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelos de Ubicación y Geofence
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import Column, Float, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from datetime import datetime


class Location(Base, UUIDMixin):
    """
    Modelo de Ubicación - Coordenadas GPS del dispositivo
    """
    __tablename__ = "locations"

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
    # COORDENADAS
    # ═══════════════════════════════════════════════════════════════════════
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)  # metros sobre el nivel del mar
    
    # ═══════════════════════════════════════════════════════════════════════
    # PRECISIÓN Y VELOCIDAD
    # ═══════════════════════════════════════════════════════════════════════
    accuracy = Column(Float, nullable=True)  # metros
    speed = Column(Float, nullable=True)     # m/s
    heading = Column(Float, nullable=True)   # grados (0-360)
    
    # ═══════════════════════════════════════════════════════════════════════
    # DIRECCIÓN (GEOCODIFICACIÓN INVERSA)
    # ═══════════════════════════════════════════════════════════════════════
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
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
    device = relationship("Device", back_populates="locations")

    def __repr__(self):
        return f"<Location ({self.latitude}, {self.longitude})>"


class Geofence(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Geofence - Zonas seguras/permitidas para la persona monitoreada
    """
    __tablename__ = "geofences"

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
    # INFORMACIÓN DE LA ZONA
    # ═══════════════════════════════════════════════════════════════════════
    name = Column(String(100), nullable=False)  # Ej: "Casa", "Hospital"
    description = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # COORDENADAS Y RADIO
    # ═══════════════════════════════════════════════════════════════════════
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Float, nullable=False)  # metros
    
    # ═══════════════════════════════════════════════════════════════════════
    # DIRECCIÓN
    # ═══════════════════════════════════════════════════════════════════════
    address = Column(Text, nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    is_active = Column(Boolean, default=True, nullable=False)
    alert_on_exit = Column(Boolean, default=True, nullable=False)  # Alertar al salir
    alert_on_enter = Column(Boolean, default=False, nullable=False)  # Alertar al entrar
    
    # Color para mostrar en el mapa (hex)
    color = Column(String(7), default="#10B981", nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════
    monitored_person = relationship("MonitoredPerson", back_populates="geofences")

    def __repr__(self):
        return f"<Geofence {self.name}>"
    
    def contains_point(self, lat: float, lon: float) -> bool:
        """
        Verifica si un punto está dentro del geofence
        Usa la fórmula de Haversine para calcular distancia
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Radio de la Tierra en metros
        
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(lat), radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        
        return distance <= self.radius
