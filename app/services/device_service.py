# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Servicio de Dispositivos IoT
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import secrets
import string

from fastapi import HTTPException, status

from app.models.device import Device, DeviceStatus
from app.models.monitored_person import MonitoredPerson
from app.models.vital_signs import VitalSigns
from app.models.location import Location
from app.models.alert import Alert, AlertType, AlertSeverity


class DeviceService:
    """Servicio para gestión de dispositivos IoT"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_devices(self, user_id: UUID) -> List[Device]:
        """Obtener todos los dispositivos del usuario"""
        result = await self.db.execute(
            select(Device)
            .join(MonitoredPerson, Device.monitored_person_id == MonitoredPerson.id)
            .where(MonitoredPerson.user_id == user_id)
            .options(
                joinedload(Device.monitored_person),
                joinedload(Device.latest_vital_signs),
                joinedload(Device.latest_location)
            )
        )
        return result.unique().scalars().all()
    
    async def get_by_id(self, device_id: UUID, user_id: UUID) -> Device:
        """Obtener dispositivo por ID (verificando pertenencia)"""
        result = await self.db.execute(
            select(Device)
            .join(MonitoredPerson, Device.monitored_person_id == MonitoredPerson.id)
            .where(
                and_(
                    Device.id == device_id,
                    MonitoredPerson.user_id == user_id
                )
            )
            .options(
                joinedload(Device.monitored_person),
                joinedload(Device.latest_vital_signs),
                joinedload(Device.latest_location)
            )
        )
        device = result.unique().scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado"
            )
        
        return device
    
    async def get_by_code(self, code: str) -> Optional[Device]:
        """Obtener dispositivo por código de vinculación"""
        result = await self.db.execute(
            select(Device).where(Device.link_code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_serial(self, serial_number: str) -> Optional[Device]:
        """Obtener dispositivo por número de serie"""
        result = await self.db.execute(
            select(Device).where(Device.serial_number == serial_number)
        )
        return result.scalar_one_or_none()
    
    async def create(
        self,
        name: str,
        monitored_person_id: UUID,
        user_id: UUID,
        serial_number: Optional[str] = None,
        model: Optional[str] = None
    ) -> Device:
        """Crear un nuevo dispositivo"""
        # Verificar que la persona monitoreada pertenece al usuario
        result = await self.db.execute(
            select(MonitoredPerson).where(
                and_(
                    MonitoredPerson.id == monitored_person_id,
                    MonitoredPerson.user_id == user_id
                )
            )
        )
        person = result.scalar_one_or_none()
        
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona monitoreada no encontrada"
            )
        
        # Generar código de vinculación único
        link_code = self._generate_link_code()
        
        device = Device(
            name=name,
            serial_number=serial_number or self._generate_serial(),
            model=model or "NovaGuardian Bracelet V1",
            monitored_person_id=monitored_person_id,
            link_code=link_code,
            status=DeviceStatus.INACTIVE
        )
        
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        
        return device
    
    async def update(
        self,
        device_id: UUID,
        user_id: UUID,
        **kwargs
    ) -> Device:
        """Actualizar dispositivo"""
        device = await self.get_by_id(device_id, user_id)
        
        for key, value in kwargs.items():
            if hasattr(device, key) and value is not None:
                setattr(device, key, value)
        
        device.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(device)
        
        return device
    
    async def delete(self, device_id: UUID, user_id: UUID) -> None:
        """Eliminar dispositivo"""
        device = await self.get_by_id(device_id, user_id)
        await self.db.delete(device)
        await self.db.commit()
    
    async def link_device(
        self,
        code: str,
        monitored_person_id: UUID,
        user_id: UUID
    ) -> Device:
        """Vincular dispositivo usando código"""
        # Verificar que la persona pertenece al usuario
        result = await self.db.execute(
            select(MonitoredPerson).where(
                and_(
                    MonitoredPerson.id == monitored_person_id,
                    MonitoredPerson.user_id == user_id
                )
            )
        )
        person = result.scalar_one_or_none()
        
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona monitoreada no encontrada"
            )
        
        # Buscar dispositivo por código
        device = await self.get_by_code(code)
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código de dispositivo inválido"
            )
        
        if device.monitored_person_id and device.monitored_person_id != monitored_person_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dispositivo ya vinculado a otra persona"
            )
        
        # Vincular
        device.monitored_person_id = monitored_person_id
        device.status = DeviceStatus.ACTIVE
        device.linked_at = datetime.utcnow()
        device.link_code = None  # Invalidar código
        
        await self.db.commit()
        await self.db.refresh(device)
        
        return device
    
    async def unlink_device(self, device_id: UUID, user_id: UUID) -> Device:
        """Desvincular dispositivo"""
        device = await self.get_by_id(device_id, user_id)
        
        device.monitored_person_id = None
        device.status = DeviceStatus.INACTIVE
        device.link_code = self._generate_link_code()  # Generar nuevo código
        
        await self.db.commit()
        await self.db.refresh(device)
        
        return device
    
    async def process_iot_data(
        self,
        serial_number: str,
        data: dict
    ) -> dict:
        """
        Procesar datos recibidos del dispositivo IoT
        
        Args:
            serial_number: Número de serie del dispositivo
            data: Datos del sensor (vital_signs, location, battery, etc.)
        
        Returns:
            Resumen del procesamiento
        """
        # Buscar dispositivo
        device = await self.get_by_serial(serial_number)
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no registrado"
            )
        
        result = {
            "device_id": str(device.id),
            "processed": [],
            "alerts": []
        }
        
        # Actualizar estado del dispositivo
        device.last_connection = datetime.utcnow()
        device.is_online = True
        
        if "battery" in data:
            device.battery_level = data["battery"]
            result["processed"].append("battery")
            
            # Alerta de batería baja
            if device.battery_level < 20:
                alert = await self._create_battery_alert(device)
                result["alerts"].append(str(alert.id))
        
        # Procesar signos vitales
        if "vital_signs" in data:
            vs_data = data["vital_signs"]
            vital_signs = VitalSigns(
                device_id=device.id,
                heart_rate=vs_data.get("heart_rate"),
                spo2=vs_data.get("spo2"),
                temperature=vs_data.get("temperature"),
                systolic_bp=vs_data.get("systolic_bp"),
                diastolic_bp=vs_data.get("diastolic_bp"),
                steps=vs_data.get("steps"),
                calories=vs_data.get("calories")
            )
            self.db.add(vital_signs)
            result["processed"].append("vital_signs")
            
            # Verificar umbrales y generar alertas
            alerts = await self._check_vital_thresholds(device, vital_signs)
            result["alerts"].extend([str(a.id) for a in alerts])
        
        # Procesar ubicación
        if "location" in data:
            loc_data = data["location"]
            location = Location(
                device_id=device.id,
                latitude=loc_data.get("latitude"),
                longitude=loc_data.get("longitude"),
                altitude=loc_data.get("altitude"),
                accuracy=loc_data.get("accuracy"),
                address=loc_data.get("address"),
                speed=loc_data.get("speed")
            )
            self.db.add(location)
            result["processed"].append("location")
            
            # TODO: Verificar geofences
        
        await self.db.commit()
        
        return result
    
    async def _check_vital_thresholds(
        self,
        device: Device,
        vital_signs: VitalSigns
    ) -> List[Alert]:
        """Verificar umbrales y crear alertas si es necesario"""
        alerts = []
        person = device.monitored_person
        
        if not person:
            return alerts
        
        # Obtener umbrales de la persona
        thresholds = {
            "heart_rate_min": person.heart_rate_min,
            "heart_rate_max": person.heart_rate_max,
            "spo2_min": person.spo2_min,
            "temperature_min": person.temperature_min,
            "temperature_max": person.temperature_max,
            "systolic_bp_min": person.systolic_bp_min,
            "systolic_bp_max": person.systolic_bp_max,
            "diastolic_bp_min": person.diastolic_bp_min,
            "diastolic_bp_max": person.diastolic_bp_max,
        }
        
        # Verificar ritmo cardíaco
        if vital_signs.heart_rate:
            if vital_signs.heart_rate < thresholds["heart_rate_min"]:
                alert = Alert(
                    device_id=device.id,
                    alert_type=AlertType.LOW_HEART_RATE,
                    severity=AlertSeverity.WARNING,
                    title="Ritmo cardíaco bajo",
                    message=f"Ritmo cardíaco: {vital_signs.heart_rate} bpm (mínimo: {thresholds['heart_rate_min']})",
                    value=vital_signs.heart_rate,
                    threshold=thresholds["heart_rate_min"]
                )
                self.db.add(alert)
                alerts.append(alert)
            elif vital_signs.heart_rate > thresholds["heart_rate_max"]:
                alert = Alert(
                    device_id=device.id,
                    alert_type=AlertType.HIGH_HEART_RATE,
                    severity=AlertSeverity.WARNING,
                    title="Ritmo cardíaco alto",
                    message=f"Ritmo cardíaco: {vital_signs.heart_rate} bpm (máximo: {thresholds['heart_rate_max']})",
                    value=vital_signs.heart_rate,
                    threshold=thresholds["heart_rate_max"]
                )
                self.db.add(alert)
                alerts.append(alert)
        
        # Verificar SpO2
        if vital_signs.spo2 and vital_signs.spo2 < thresholds["spo2_min"]:
            severity = AlertSeverity.CRITICAL if vital_signs.spo2 < 90 else AlertSeverity.WARNING
            alert = Alert(
                device_id=device.id,
                alert_type=AlertType.LOW_SPO2,
                severity=severity,
                title="Oxigenación baja",
                message=f"SpO2: {vital_signs.spo2}% (mínimo: {thresholds['spo2_min']}%)",
                value=vital_signs.spo2,
                threshold=thresholds["spo2_min"]
            )
            self.db.add(alert)
            alerts.append(alert)
        
        # Verificar temperatura
        if vital_signs.temperature:
            if vital_signs.temperature < thresholds["temperature_min"]:
                alert = Alert(
                    device_id=device.id,
                    alert_type=AlertType.LOW_TEMPERATURE,
                    severity=AlertSeverity.WARNING,
                    title="Temperatura baja",
                    message=f"Temperatura: {vital_signs.temperature}°C (mínimo: {thresholds['temperature_min']}°C)",
                    value=vital_signs.temperature,
                    threshold=thresholds["temperature_min"]
                )
                self.db.add(alert)
                alerts.append(alert)
            elif vital_signs.temperature > thresholds["temperature_max"]:
                severity = AlertSeverity.CRITICAL if vital_signs.temperature > 39 else AlertSeverity.WARNING
                alert = Alert(
                    device_id=device.id,
                    alert_type=AlertType.HIGH_TEMPERATURE,
                    severity=severity,
                    title="Temperatura alta",
                    message=f"Temperatura: {vital_signs.temperature}°C (máximo: {thresholds['temperature_max']}°C)",
                    value=vital_signs.temperature,
                    threshold=thresholds["temperature_max"]
                )
                self.db.add(alert)
                alerts.append(alert)
        
        return alerts
    
    async def _create_battery_alert(self, device: Device) -> Alert:
        """Crear alerta de batería baja"""
        severity = AlertSeverity.CRITICAL if device.battery_level < 10 else AlertSeverity.WARNING
        alert = Alert(
            device_id=device.id,
            alert_type=AlertType.LOW_BATTERY,
            severity=severity,
            title="Batería baja",
            message=f"Nivel de batería: {device.battery_level}%",
            value=device.battery_level,
            threshold=20
        )
        self.db.add(alert)
        return alert
    
    def _generate_link_code(self, length: int = 8) -> str:
        """Generar código de vinculación aleatorio"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def _generate_serial(self) -> str:
        """Generar número de serie"""
        return f"NG-{secrets.token_hex(8).upper()}"
