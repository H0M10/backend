# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Servicio de Alertas
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import joinedload
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.device import Device
from app.models.monitored_person import MonitoredPerson
from app.schemas.alert import AlertListResponse, AlertResponse, AlertStatsResponse


class AlertService:
    """Servicio para gestión de alertas"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_alerts(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_attended: Optional[bool] = None,
        device_id: Optional[UUID] = None,
        person_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AlertListResponse:
        """
        Obtener alertas con filtros y paginación
        """
        # Obtener IDs de dispositivos del usuario
        device_ids = await self._get_user_device_ids(user_id)
        
        if not device_ids:
            return AlertListResponse(
                data=[],
                total=0,
                page=page,
                per_page=per_page,
                pages=0
            )
        
        # Construir query base
        query = select(Alert).where(Alert.device_id.in_(device_ids))
        count_query = select(func.count(Alert.id)).where(Alert.device_id.in_(device_ids))
        
        # Aplicar filtros
        if severity:
            try:
                sev = AlertSeverity(severity)
                query = query.where(Alert.severity == sev)
                count_query = count_query.where(Alert.severity == sev)
            except ValueError:
                pass
        
        if alert_type:
            try:
                at = AlertType(alert_type)
                query = query.where(Alert.alert_type == at)
                count_query = count_query.where(Alert.alert_type == at)
            except ValueError:
                pass
        
        if is_read is not None:
            query = query.where(Alert.is_read == is_read)
            count_query = count_query.where(Alert.is_read == is_read)
        
        if is_attended is not None:
            query = query.where(Alert.is_attended == is_attended)
            count_query = count_query.where(Alert.is_attended == is_attended)
        
        if device_id:
            query = query.where(Alert.device_id == device_id)
            count_query = count_query.where(Alert.device_id == device_id)
        
        if start_date:
            query = query.where(Alert.created_at >= start_date)
            count_query = count_query.where(Alert.created_at >= start_date)
        
        if end_date:
            query = query.where(Alert.created_at <= end_date)
            count_query = count_query.where(Alert.created_at <= end_date)
        
        # Contar total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Aplicar paginación y ordenamiento
        offset = (page - 1) * per_page
        query = (
            query
            .options(joinedload(Alert.device))
            .order_by(Alert.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        result = await self.db.execute(query)
        alerts = result.unique().scalars().all()
        
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        return AlertListResponse(
            data=[AlertResponse.model_validate(a) for a in alerts],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    
    async def get_recent_alerts(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Alert]:
        """Obtener alertas más recientes"""
        device_ids = await self._get_user_device_ids(user_id)
        
        if not device_ids:
            return []
        
        result = await self.db.execute(
            select(Alert)
            .where(Alert.device_id.in_(device_ids))
            .options(joinedload(Alert.device))
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        return result.unique().scalars().all()
    
    async def get_unread_alerts(self, user_id: UUID) -> List[Alert]:
        """Obtener alertas no leídas"""
        device_ids = await self._get_user_device_ids(user_id)
        
        if not device_ids:
            return []
        
        result = await self.db.execute(
            select(Alert)
            .where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.is_read == False
                )
            )
            .options(joinedload(Alert.device))
            .order_by(Alert.created_at.desc())
        )
        return result.unique().scalars().all()
    
    async def get_by_id(self, alert_id: UUID, user_id: UUID) -> Alert:
        """Obtener alerta por ID"""
        device_ids = await self._get_user_device_ids(user_id)
        
        result = await self.db.execute(
            select(Alert)
            .where(
                and_(
                    Alert.id == alert_id,
                    Alert.device_id.in_(device_ids)
                )
            )
            .options(joinedload(Alert.device))
        )
        alert = result.unique().scalar_one_or_none()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alerta no encontrada"
            )
        
        return alert
    
    async def mark_as_read(self, alert_id: UUID, user_id: UUID) -> Alert:
        """Marcar alerta como leída"""
        alert = await self.get_by_id(alert_id, user_id)
        alert.is_read = True
        alert.read_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(alert)
        
        return alert
    
    async def mark_multiple_as_read(
        self,
        alert_ids: List[UUID],
        user_id: UUID
    ) -> int:
        """Marcar múltiples alertas como leídas"""
        device_ids = await self._get_user_device_ids(user_id)
        
        result = await self.db.execute(
            update(Alert)
            .where(
                and_(
                    Alert.id.in_(alert_ids),
                    Alert.device_id.in_(device_ids)
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        
        await self.db.commit()
        return result.rowcount
    
    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Marcar todas las alertas como leídas"""
        device_ids = await self._get_user_device_ids(user_id)
        
        if not device_ids:
            return 0
        
        result = await self.db.execute(
            update(Alert)
            .where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.is_read == False
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        
        await self.db.commit()
        return result.rowcount
    
    async def attend_alert(
        self,
        alert_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None,
        is_false_alarm: bool = False
    ) -> Alert:
        """Atender una alerta"""
        alert = await self.get_by_id(alert_id, user_id)
        
        alert.is_attended = True
        alert.attended_at = datetime.utcnow()
        alert.attended_by_id = user_id
        alert.notes = notes
        alert.is_false_alarm = is_false_alarm
        
        # También marcar como leída si no lo está
        if not alert.is_read:
            alert.is_read = True
            alert.read_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(alert)
        
        return alert
    
    async def delete(self, alert_id: UUID, user_id: UUID) -> None:
        """Eliminar una alerta"""
        alert = await self.get_by_id(alert_id, user_id)
        await self.db.delete(alert)
        await self.db.commit()
    
    async def get_stats(self, user_id: UUID) -> AlertStatsResponse:
        """Obtener estadísticas de alertas"""
        device_ids = await self._get_user_device_ids(user_id)
        
        if not device_ids:
            return AlertStatsResponse(
                total=0,
                unread=0,
                unattended=0,
                critical=0,
                warning=0,
                info=0,
                today=0,
                this_week=0,
                by_type={}
            )
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        
        # Total
        total_result = await self.db.execute(
            select(func.count(Alert.id)).where(Alert.device_id.in_(device_ids))
        )
        total = total_result.scalar() or 0
        
        # No leídas
        unread_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.is_read == False
                )
            )
        )
        unread = unread_result.scalar() or 0
        
        # No atendidas
        unattended_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.is_attended == False
                )
            )
        )
        unattended = unattended_result.scalar() or 0
        
        # Por severidad
        critical_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.severity == AlertSeverity.CRITICAL
                )
            )
        )
        critical = critical_result.scalar() or 0
        
        warning_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.severity == AlertSeverity.WARNING
                )
            )
        )
        warning = warning_result.scalar() or 0
        
        info_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.severity == AlertSeverity.INFO
                )
            )
        )
        info = info_result.scalar() or 0
        
        # Hoy
        today_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.created_at >= today_start
                )
            )
        )
        today = today_result.scalar() or 0
        
        # Esta semana
        week_result = await self.db.execute(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.device_id.in_(device_ids),
                    Alert.created_at >= week_start
                )
            )
        )
        this_week = week_result.scalar() or 0
        
        # Por tipo
        type_result = await self.db.execute(
            select(
                Alert.alert_type,
                func.count(Alert.id).label('count')
            )
            .where(Alert.device_id.in_(device_ids))
            .group_by(Alert.alert_type)
        )
        by_type = {row.alert_type.value: row.count for row in type_result}
        
        return AlertStatsResponse(
            total=total,
            unread=unread,
            unattended=unattended,
            critical=critical,
            warning=warning,
            info=info,
            today=today,
            this_week=this_week,
            by_type=by_type
        )
    
    async def create_alert(
        self,
        device_id: UUID,
        alert_type: AlertType,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        value: Optional[float] = None,
        threshold: Optional[float] = None,
        data: Optional[dict] = None
    ) -> Alert:
        """Crear una nueva alerta"""
        alert = Alert(
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            value=value,
            threshold=threshold,
            data=data
        )
        
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        
        return alert
    
    async def _get_user_device_ids(self, user_id: UUID) -> List[UUID]:
        """Obtener IDs de dispositivos asociados al usuario"""
        # Obtener dispositivos de personas monitoreadas por el usuario
        result = await self.db.execute(
            select(Device.id)
            .join(MonitoredPerson, Device.monitored_person_id == MonitoredPerson.id)
            .where(MonitoredPerson.user_id == user_id)
        )
        return [row[0] for row in result.all()]
