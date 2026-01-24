# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Schemas Comunes
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List
from datetime import datetime

T = TypeVar("T")


class ResponseBase(BaseModel):
    """Respuesta base para todos los endpoints"""
    success: bool = True
    message: str = "Operación exitosa"


class ResponseData(ResponseBase, Generic[T]):
    """Respuesta con datos genéricos"""
    data: Optional[T] = None


class PaginatedResponse(ResponseBase, Generic[T]):
    """Respuesta paginada"""
    data: List[T] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 1


class ErrorResponse(BaseModel):
    """Respuesta de error"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None


class HealthCheck(BaseModel):
    """Respuesta de health check"""
    status: str = "healthy"
    version: str
    environment: str
    timestamp: datetime
