# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Servicio de Notificaciones Push
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import json

from fastapi import HTTPException, status
import httpx

from app.models.notification import Notification, PushToken
from app.models.user import User
from app.config import settings


class NotificationService:
    """Servicio para envío de notificaciones push"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        notification_type: str,
        data: Optional[dict] = None,
        send_push: bool = True
    ) -> Notification:
        """
        Crear una notificación y opcionalmente enviar push
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            data=data
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Enviar push notification
        if send_push:
            await self.send_push_notification(user_id, title, body, data)
        
        return notification
    
    async def send_push_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> bool:
        """
        Enviar notificación push a todos los dispositivos del usuario
        """
        # Obtener tokens del usuario
        result = await self.db.execute(
            select(PushToken).where(
                and_(
                    PushToken.user_id == user_id,
                    PushToken.is_active == True
                )
            )
        )
        tokens = result.scalars().all()
        
        if not tokens:
            return False
        
        # Enviar a cada token
        success = False
        for token in tokens:
            try:
                sent = await self._send_to_token(
                    token=token.token,
                    platform=token.platform,
                    title=title,
                    body=body,
                    data=data
                )
                if sent:
                    success = True
                else:
                    # Token inválido, desactivar
                    token.is_active = False
            except Exception as e:
                print(f"Error sending push to {token.platform}: {e}")
        
        await self.db.commit()
        return success
    
    async def _send_to_token(
        self,
        token: str,
        platform: str,
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> bool:
        """
        Enviar notificación a un token específico usando Expo Push API
        """
        # Usar Expo Push Notifications (compatible con React Native/Expo)
        url = "https://exp.host/--/api/v2/push/send"
        
        message = {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
            "priority": "high",
        }
        
        if data:
            message["data"] = data
        
        # Para alertas críticas
        if data and data.get("severity") == "critical":
            message["priority"] = "high"
            message["channelId"] = "alerts"
            message["badge"] = 1
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=message,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Verificar si fue exitoso
                    if result.get("data", {}).get("status") == "ok":
                        return True
                    elif result.get("data", {}).get("status") == "error":
                        error = result.get("data", {}).get("message", "Unknown error")
                        if "DeviceNotRegistered" in error:
                            return False  # Token inválido
                
                return False
        except Exception as e:
            print(f"Push notification error: {e}")
            return False
    
    async def send_alert_notification(
        self,
        user_id: UUID,
        alert_type: str,
        severity: str,
        person_name: str,
        message: str,
        alert_id: Optional[UUID] = None
    ) -> Notification:
        """
        Enviar notificación de alerta
        """
        title_map = {
            "high_heart_rate": "⚠️ Ritmo cardíaco alto",
            "low_heart_rate": "⚠️ Ritmo cardíaco bajo",
            "low_spo2": "🚨 Oxigenación baja",
            "high_temperature": "🌡️ Temperatura alta",
            "low_temperature": "🌡️ Temperatura baja",
            "fall_detected": "🚨 Caída detectada",
            "sos_pressed": "🆘 Botón SOS presionado",
            "geofence_exit": "📍 Salió de zona segura",
            "low_battery": "🔋 Batería baja",
            "device_offline": "📡 Dispositivo desconectado"
        }
        
        title = f"{title_map.get(alert_type, '⚠️ Alerta')} - {person_name}"
        
        data = {
            "type": "alert",
            "alert_type": alert_type,
            "severity": severity,
            "person_name": person_name
        }
        
        if alert_id:
            data["alert_id"] = str(alert_id)
        
        return await self.create_notification(
            user_id=user_id,
            title=title,
            body=message,
            notification_type="alert",
            data=data,
            send_push=True
        )
    
    async def send_reminder_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        reminder_type: str,
        reminder_id: Optional[UUID] = None
    ) -> Notification:
        """
        Enviar notificación de recordatorio
        """
        data = {
            "type": "reminder",
            "reminder_type": reminder_type
        }
        
        if reminder_id:
            data["reminder_id"] = str(reminder_id)
        
        return await self.create_notification(
            user_id=user_id,
            title=f"⏰ {title}",
            body=message,
            notification_type="reminder",
            data=data,
            send_push=True
        )
    
    async def send_system_notification(
        self,
        user_id: UUID,
        title: str,
        message: str
    ) -> Notification:
        """
        Enviar notificación del sistema
        """
        return await self.create_notification(
            user_id=user_id,
            title=f"📢 {title}",
            body=message,
            notification_type="system",
            data={"type": "system"},
            send_push=True
        )
    
    async def register_token(
        self,
        user_id: UUID,
        token: str,
        platform: str,
        device_name: Optional[str] = None
    ) -> PushToken:
        """
        Registrar token de push notification
        """
        # Verificar si ya existe
        result = await self.db.execute(
            select(PushToken).where(PushToken.token == token)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.user_id = user_id
            existing.platform = platform
            existing.device_name = device_name
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            return existing
        
        push_token = PushToken(
            user_id=user_id,
            token=token,
            platform=platform,
            device_name=device_name
        )
        
        self.db.add(push_token)
        await self.db.commit()
        await self.db.refresh(push_token)
        
        return push_token
    
    async def unregister_token(self, token: str, user_id: UUID) -> bool:
        """
        Desregistrar token
        """
        result = await self.db.execute(
            select(PushToken).where(
                and_(
                    PushToken.token == token,
                    PushToken.user_id == user_id
                )
            )
        )
        push_token = result.scalar_one_or_none()
        
        if push_token:
            await self.db.delete(push_token)
            await self.db.commit()
            return True
        
        return False
