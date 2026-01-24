# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Modelo Base
# Clase base con campos comunes para todos los modelos
# ═══════════════════════════════════════════════════════════════════════════

from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid


class TimestampMixin:
    """Mixin que agrega campos de timestamp a los modelos"""
    
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class UUIDMixin:
    """Mixin que agrega ID tipo UUID"""
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )


def generate_uuid():
    """Genera un nuevo UUID"""
    return uuid.uuid4()
