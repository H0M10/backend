# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Router de Personas Monitoreadas
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.database import get_db
from app.schemas.monitored_person import (
    MonitoredPersonCreate, MonitoredPersonUpdate, MonitoredPersonResponse,
    MonitoredPersonFullResponse, VitalThresholdsUpdate,
    EmergencyContactCreate, EmergencyContactUpdate, EmergencyContactResponse,
    MedicalConditionCreate, MedicalConditionResponse
)
from app.schemas.common import ResponseBase
from app.services.monitored_person_service import MonitoredPersonService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# CRUD DE PERSONAS MONITOREADAS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[MonitoredPersonFullResponse])
async def get_monitored_persons(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener todas las personas monitoreadas del usuario
    """
    service = MonitoredPersonService(db)
    persons = await service.get_all_by_user(current_user.id)
    return persons


@router.post("", response_model=MonitoredPersonResponse, status_code=status.HTTP_201_CREATED)
async def create_monitored_person(
    request: MonitoredPersonCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear una nueva persona monitoreada
    """
    service = MonitoredPersonService(db)
    person = await service.create(request, current_user.id)
    return MonitoredPersonResponse.model_validate(person)


@router.get("/{person_id}", response_model=MonitoredPersonFullResponse)
async def get_monitored_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener una persona monitoreada por ID
    """
    service = MonitoredPersonService(db)
    person = await service.get_by_id(person_id, current_user.id)
    return person


@router.put("/{person_id}", response_model=MonitoredPersonResponse)
async def update_monitored_person(
    person_id: UUID,
    request: MonitoredPersonUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar una persona monitoreada
    """
    service = MonitoredPersonService(db)
    person = await service.update(person_id, request, current_user.id)
    return MonitoredPersonResponse.model_validate(person)


@router.delete("/{person_id}", response_model=ResponseBase)
async def delete_monitored_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar una persona monitoreada
    """
    service = MonitoredPersonService(db)
    await service.delete(person_id, current_user.id)
    return ResponseBase(message="Persona monitoreada eliminada exitosamente")


@router.post("/{person_id}/photo", response_model=MonitoredPersonResponse)
async def upload_photo(
    person_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subir foto de la persona monitoreada
    """
    service = MonitoredPersonService(db)
    person = await service.upload_photo(person_id, file, current_user.id)
    return MonitoredPersonResponse.model_validate(person)


# ═══════════════════════════════════════════════════════════════════════════
# UMBRALES DE SIGNOS VITALES
# ═══════════════════════════════════════════════════════════════════════════

@router.put("/{person_id}/thresholds", response_model=MonitoredPersonResponse)
async def update_vital_thresholds(
    person_id: UUID,
    request: VitalThresholdsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar umbrales de signos vitales personalizados
    """
    service = MonitoredPersonService(db)
    person = await service.update_thresholds(person_id, request, current_user.id)
    return MonitoredPersonResponse.model_validate(person)


# ═══════════════════════════════════════════════════════════════════════════
# CONTACTOS DE EMERGENCIA
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/{person_id}/emergency-contacts", response_model=List[EmergencyContactResponse])
async def get_emergency_contacts(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener contactos de emergencia de una persona monitoreada
    """
    service = MonitoredPersonService(db)
    contacts = await service.get_emergency_contacts(person_id, current_user.id)
    return contacts


@router.post("/{person_id}/emergency-contacts", response_model=EmergencyContactResponse, status_code=status.HTTP_201_CREATED)
async def create_emergency_contact(
    person_id: UUID,
    request: EmergencyContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Agregar un contacto de emergencia
    """
    service = MonitoredPersonService(db)
    contact = await service.create_emergency_contact(person_id, request, current_user.id)
    return EmergencyContactResponse.model_validate(contact)


@router.put("/{person_id}/emergency-contacts/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(
    person_id: UUID,
    contact_id: UUID,
    request: EmergencyContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar un contacto de emergencia
    """
    service = MonitoredPersonService(db)
    contact = await service.update_emergency_contact(person_id, contact_id, request, current_user.id)
    return EmergencyContactResponse.model_validate(contact)


@router.delete("/{person_id}/emergency-contacts/{contact_id}", response_model=ResponseBase)
async def delete_emergency_contact(
    person_id: UUID,
    contact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar un contacto de emergencia
    """
    service = MonitoredPersonService(db)
    await service.delete_emergency_contact(person_id, contact_id, current_user.id)
    return ResponseBase(message="Contacto eliminado exitosamente")


# ═══════════════════════════════════════════════════════════════════════════
# CONDICIONES MÉDICAS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/{person_id}/medical-conditions", response_model=List[MedicalConditionResponse])
async def get_medical_conditions(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener condiciones médicas de una persona monitoreada
    """
    service = MonitoredPersonService(db)
    conditions = await service.get_medical_conditions(person_id, current_user.id)
    return conditions


@router.post("/{person_id}/medical-conditions", response_model=MedicalConditionResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_condition(
    person_id: UUID,
    request: MedicalConditionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Agregar una condición médica
    """
    service = MonitoredPersonService(db)
    condition = await service.create_medical_condition(person_id, request, current_user.id)
    return MedicalConditionResponse.model_validate(condition)


@router.delete("/{person_id}/medical-conditions/{condition_id}", response_model=ResponseBase)
async def delete_medical_condition(
    person_id: UUID,
    condition_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar una condición médica
    """
    service = MonitoredPersonService(db)
    await service.delete_medical_condition(person_id, condition_id, current_user.id)
    return ResponseBase(message="Condición médica eliminada exitosamente")
