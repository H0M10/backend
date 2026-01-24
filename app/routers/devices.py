# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Dispositivos
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.device import (
    DeviceResponse, DeviceWithPersonResponse, DeviceUpdate,
    DeviceLinkRequest, DeviceDataPayload
)
from app.schemas.common import ResponseBase, PaginatedResponse
from app.services.device_service import DeviceService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[DeviceWithPersonResponse])
async def get_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener todos los dispositivos del usuario
    
    Retorna dispositivos vinculados a personas monitoreadas del usuario
    """
    device_service = DeviceService(db)
    devices = await device_service.get_user_devices(current_user.id)
    return devices


@router.get("/{device_id}", response_model=DeviceWithPersonResponse)
async def get_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener un dispositivo por ID
    """
    device_service = DeviceService(db)
    device = await device_service.get_by_id(device_id, current_user.id)
    return device


@router.post("/link", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def link_device(
    request: DeviceLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Vincular un dispositivo a una persona monitoreada
    
    - **code**: Código del dispositivo (QR o manual)
    - **monitored_person_id**: ID de la persona monitoreada
    """
    device_service = DeviceService(db)
    device = await device_service.link_device(
        code=request.code,
        monitored_person_id=request.monitored_person_id,
        user_id=current_user.id
    )
    return DeviceResponse.model_validate(device)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    request: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar configuración de un dispositivo
    """
    device_service = DeviceService(db)
    device = await device_service.update(device_id, request, current_user.id)
    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", response_model=ResponseBase)
async def unlink_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Desvincular un dispositivo
    """
    device_service = DeviceService(db)
    await device_service.unlink_device(device_id, current_user.id)
    return ResponseBase(message="Dispositivo desvinculado exitosamente")


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS PARA IOT (Sin autenticación de usuario, usa código de dispositivo)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/data", response_model=ResponseBase, tags=["IoT"])
async def receive_device_data(
    payload: DeviceDataPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Recibir datos del dispositivo IoT
    
    Este endpoint es llamado por el dispositivo físico para enviar:
    - Signos vitales
    - Ubicación GPS
    - Estado de batería
    - Eventos (caídas, SOS)
    """
    device_service = DeviceService(db)
    await device_service.process_device_data(payload)
    return ResponseBase(message="Datos recibidos correctamente")


@router.get("/code/{code}", response_model=DeviceResponse, tags=["IoT"])
async def get_device_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener información de un dispositivo por su código
    
    Usado para verificar si un dispositivo existe antes de vincularlo
    """
    device_service = DeviceService(db)
    device = await device_service.get_by_code(code)
    return DeviceResponse.model_validate(device)
