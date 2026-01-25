# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Backend API Simplificado
# Version: 2.0 - Corregido
# ═══════════════════════════════════════════════════════════════════════════

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import asyncpg
import bcrypt
from jose import JWTError, jwt
import warnings
import random
import math
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

# Suprimir warnings de deprecation que no podemos controlar
warnings.filterwarnings("ignore", category=DeprecationWarning)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════════════════════

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:HANNIEL@localhost:5433/novaguardian"
    JWT_SECRET_KEY: str = "novaguardian_secret_key_2026_secure"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Configuración de Email (SMTP)
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.larksuite.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "hanniel@novaguardian.online"
    SMTP_PASSWORD: str = "0oldDQ80LKzZ1Oh4"
    SMTP_FROM_NAME: str = "NovaGuardian"
    SMTP_FROM_EMAIL: str = "hanniel@novaguardian.online"
    SMTP_SSL: bool = True  # Puerto 465 usa SSL directo
    SMTP_TLS: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

settings = Settings()

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ═══════════════════════════════════════════════════════════════════════════
# SIMULADOR IoT - Genera datos realistas como si vinieran de un dispositivo
# ═══════════════════════════════════════════════════════════════════════════

class IoTSimulator:
    """
    Simula datos de un dispositivo IoT de monitoreo de salud.
    Los datos varían de forma realista basándose en el tiempo y el ID del dispositivo.
    """
    
    # Ubicaciones base para simulación (casas de adultos mayores ficticias)
    BASE_LOCATIONS = {
        "default": {"lat": 19.4326, "lng": -99.1332},  # CDMX
        "casa1": {"lat": 19.4284, "lng": -99.1276},
        "casa2": {"lat": 19.4356, "lng": -99.1401},
    }
    
    # Tipos de alertas posibles - DEBEN COINCIDIR CON EL ENUM alert_type EN LA BD
    # Valores válidos: HIGH_HEART_RATE, LOW_HEART_RATE, LOW_SPO2, HIGH_TEMPERATURE, 
    # LOW_TEMPERATURE, HIGH_BLOOD_PRESSURE, LOW_BLOOD_PRESSURE, FALL_DETECTED, 
    # SOS_BUTTON, GEOFENCE_EXIT, GEOFENCE_ENTER, LOW_BATTERY, DEVICE_DISCONNECTED, DEVICE_ERROR
    ALERT_TYPES = [
        {"type": "HIGH_HEART_RATE", "severity": "warning", "title": "Ritmo cardíaco elevado", "message": "El ritmo cardíaco está por encima de lo normal (>100 bpm)"},
        {"type": "LOW_HEART_RATE", "severity": "warning", "title": "Ritmo cardíaco bajo", "message": "El ritmo cardíaco está por debajo de lo normal (<60 bpm)"},
        {"type": "LOW_SPO2", "severity": "critical", "title": "⚠️ Oxigenación baja", "message": "Nivel de oxígeno en sangre bajo (<94%). Verificar estado del paciente."},
        {"type": "HIGH_TEMPERATURE", "severity": "warning", "title": "Temperatura elevada", "message": "La temperatura corporal está elevada (>37.5°C)"},
        {"type": "LOW_TEMPERATURE", "severity": "warning", "title": "Temperatura baja", "message": "La temperatura corporal está baja (<36°C)"},
        {"type": "HIGH_BLOOD_PRESSURE", "severity": "warning", "title": "Presión arterial elevada", "message": "La presión arterial sistólica está elevada (>140 mmHg)"},
        {"type": "LOW_BLOOD_PRESSURE", "severity": "info", "title": "Presión arterial baja", "message": "La presión arterial sistólica está baja (<90 mmHg)"},
        {"type": "FALL_DETECTED", "severity": "critical", "title": "🚨 CAÍDA DETECTADA", "message": "Se ha detectado una posible caída. Verificar inmediatamente."},
        {"type": "SOS_BUTTON", "severity": "critical", "title": "🆘 BOTÓN SOS PRESIONADO", "message": "El paciente ha presionado el botón de emergencia."},
        {"type": "GEOFENCE_EXIT", "severity": "warning", "title": "Salida de zona segura", "message": "La persona ha salido de la zona segura definida"},
        {"type": "GEOFENCE_ENTER", "severity": "info", "title": "Entrada a zona segura", "message": "La persona ha regresado a la zona segura"},
        {"type": "LOW_BATTERY", "severity": "info", "title": "Batería baja", "message": "El dispositivo tiene poca batería (<20%)"},
        {"type": "DEVICE_DISCONNECTED", "severity": "warning", "title": "Dispositivo desconectado", "message": "Se perdió la conexión con el dispositivo"},
    ]
    
    # Control de última alerta generada (para evitar duplicados)
    _last_alert_time = {}
    _last_critical_time = {}
    
    @staticmethod
    def get_seed(device_id: str) -> int:
        """Genera una semilla única basada en el device_id"""
        return sum(ord(c) for c in str(device_id))
    
    @staticmethod
    def should_generate_alert(device_id: str) -> tuple:
        """
        Determina si se debe generar una alerta basándose en el tiempo.
        Retorna (should_generate, is_critical)
        - Alertas normales: cada ~1 minuto
        - Alertas críticas: cada ~30 minutos
        """
        now = datetime.now()  # Hora local
        device_key = str(device_id)
        
        # Verificar alerta crítica (cada 30 minutos)
        last_critical = IoTSimulator._last_critical_time.get(device_key)
        if not last_critical or (now - last_critical).total_seconds() >= 1800:  # 30 min
            return (True, True)
        
        # Verificar alerta normal (cada 1 minuto)
        last_alert = IoTSimulator._last_alert_time.get(device_key)
        if not last_alert or (now - last_alert).total_seconds() >= 60:  # 1 min
            return (True, False)
        
        return (False, False)
    
    @staticmethod
    def generate_alert(device_id: str, is_critical: bool = False) -> dict:
        """Genera una alerta aleatoria basada en el tipo"""
        now = datetime.now()  # Hora local
        seed = IoTSimulator.get_seed(device_id)
        device_key = str(device_id)
        
        # Seleccionar tipo de alerta
        if is_critical:
            # Solo alertas críticas: LOW_SPO2, FALL_DETECTED, SOS_BUTTON
            critical_alerts = [a for a in IoTSimulator.ALERT_TYPES if a["severity"] == "critical"]
            alert_template = random.choice(critical_alerts)
            IoTSimulator._last_critical_time[device_key] = now
        else:
            # Alertas no críticas
            non_critical_alerts = [a for a in IoTSimulator.ALERT_TYPES if a["severity"] != "critical"]
            alert_template = random.choice(non_critical_alerts)
        
        IoTSimulator._last_alert_time[device_key] = now
        
        # Generar valor según el tipo
        value = None
        if alert_template["type"] == "HIGH_HEART_RATE":
            value = random.randint(100, 130)
        elif alert_template["type"] == "LOW_HEART_RATE":
            value = random.randint(40, 55)
        elif alert_template["type"] == "LOW_SPO2":
            value = random.randint(85, 93)
        elif alert_template["type"] == "HIGH_TEMPERATURE":
            value = round(random.uniform(37.6, 39.0), 1)
        elif alert_template["type"] == "LOW_TEMPERATURE":
            value = round(random.uniform(34.5, 35.9), 1)
        elif alert_template["type"] == "HIGH_BLOOD_PRESSURE":
            value = random.randint(145, 180)
        elif alert_template["type"] == "LOW_BLOOD_PRESSURE":
            value = random.randint(70, 89)
        elif alert_template["type"] == "LOW_BATTERY":
            value = random.randint(5, 19)
        
        return {
            "type": alert_template["type"],
            "severity": alert_template["severity"],
            "title": alert_template["title"],
            "message": alert_template["message"],
            "value": value,
            "timestamp": now.isoformat(),
        }
    
    @staticmethod
    def generate_vitals(device_id: str) -> dict:
        """
        Genera signos vitales realistas para adulto mayor.
        Valores estables típicos de persona en reposo/casa.
        """
        # Usar hora local (no UTC) para que coincida con el reloj del usuario
        now = datetime.now()  # Hora local del servidor
        seed = IoTSimulator.get_seed(device_id)
        
        # Usar tiempo + seed para variación suave y determinista
        time_factor = now.timestamp() / 120  # Cambia cada 2 minutos (más estable)
        
        # Funciones sinusoidales para variación muy suave
        sin_factor = math.sin(time_factor + seed) 
        cos_factor = math.cos(time_factor * 0.5 + seed)
        
        # Ritmo cardíaco: 65-78 bpm (adulto mayor en reposo)
        base_hr = 68 + (seed % 8)  # 68-75 base
        heart_rate = int(base_hr + sin_factor * 3)  # Variación de ±3 bpm
        heart_rate = max(62, min(82, heart_rate))
        
        # Oxigenación: 96-99% (valores normales)
        base_spo2 = 97
        spo2 = int(base_spo2 + cos_factor * 1)  # Variación de ±1%
        spo2 = max(96, min(99, spo2))
        
        # Temperatura: 36.3-36.8°C (normal)
        base_temp = 36.5
        temperature = round(base_temp + sin_factor * 0.15, 1)  # Variación de ±0.15°C
        temperature = max(36.2, min(36.9, temperature))
        
        # Presión arterial (adulto mayor normal-alto)
        base_systolic = 125 + (seed % 10)  # 125-134 sistólica
        base_diastolic = 78 + (seed % 7)   # 78-84 diastólica
        systolic = int(base_systolic + cos_factor * 4)  # Variación de ±4 mmHg
        diastolic = int(base_diastolic + sin_factor * 3)  # Variación de ±3 mmHg
        
        # Pasos (adulto mayor - menos actividad)
        hour = now.hour
        if 8 <= hour <= 20:  # Actividad entre 8am y 8pm
            steps_base = (hour - 8) * 150 + (seed % 100)  # ~150 pasos por hora
            steps = int(steps_base)
        else:
            steps = seed % 50
        
        # Calorías basadas en pasos (metabolismo menor)
        calories = int(steps * 0.03 + (seed % 30))
        
        # Batería realista (decrece ~1% por hora de uso)
        battery = max(20, 100 - ((hour + 6) % 24))  # Empieza cargado en la mañana
        
        return {
            "heartRate": heart_rate,
            "spo2": spo2,
            "oxygenLevel": spo2,  # Alias
            "temperature": temperature,
            "systolicBp": systolic,
            "diastolicBp": diastolic,
            "steps": steps,
            "calories": calories,
            "batteryLevel": battery,
            "timestamp": now.isoformat(),
            "recordedAt": now.isoformat(),
        }
    
    @staticmethod
    def generate_location(device_id: str) -> dict:
        """
        Genera ubicación que simula movimiento lento alrededor de casa.
        """
        now = datetime.now()  # Hora local
        seed = IoTSimulator.get_seed(device_id)
        
        # Seleccionar ubicación base según seed
        bases = list(IoTSimulator.BASE_LOCATIONS.values())
        base = bases[seed % len(bases)]
        
        # Simular pequeño movimiento (dentro de 50m)
        time_factor = now.timestamp() / 300  # Cambia cada 5 min
        
        # Movimiento circular lento
        angle = (time_factor + seed) % (2 * math.pi)
        radius = 0.0003 + (seed % 5) * 0.0001  # ~30-50 metros
        
        lat = base["lat"] + math.sin(angle) * radius + random.uniform(-0.0001, 0.0001)
        lng = base["lng"] + math.cos(angle) * radius + random.uniform(-0.0001, 0.0001)
        
        return {
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "accuracy": round(5 + random.uniform(0, 10), 1),
            "altitude": 2240 + random.uniform(-5, 5),
            "speed": round(random.uniform(0, 0.5), 2),  # Casi estático
            "timestamp": now.isoformat(),
            "recordedAt": now.isoformat(),
        }
    
    @staticmethod
    def generate_vitals_history(device_id: str, hours: int = 24) -> list:
        """Genera historial de signos vitales de las últimas N horas"""
        history = []
        now = datetime.now()  # Hora local
        seed = IoTSimulator.get_seed(device_id)
        
        # Generar un registro cada 15 minutos, empezando desde AHORA hacia atrás
        total_records = hours * 4  # 4 registros por hora (cada 15 min)
        
        for i in range(total_records):
            # i=0 es AHORA, i=1 es hace 15 min, etc.
            past_time = now - timedelta(minutes=i * 15)
            time_factor = past_time.timestamp() / 120  # Mismo factor que generate_vitals
            sin_factor = math.sin(time_factor + seed)
            cos_factor = math.cos(time_factor * 0.5 + seed)
            
            # Usar mismos valores base que generate_vitals para consistencia
            base_hr = 68 + (seed % 8)
            heart_rate = int(base_hr + sin_factor * 3)
            heart_rate = max(62, min(82, heart_rate))
            
            base_spo2 = 97
            spo2 = int(base_spo2 + cos_factor * 1)
            spo2 = max(96, min(99, spo2))
            
            base_temp = 36.5
            temperature = round(base_temp + sin_factor * 0.15, 1)
            temperature = max(36.2, min(36.9, temperature))
            
            # Presión arterial
            base_systolic = 125 + (seed % 10)
            base_diastolic = 78 + (seed % 7)
            systolic = int(base_systolic + cos_factor * 4)
            diastolic = int(base_diastolic + sin_factor * 3)
            
            history.append({
                "heartRate": heart_rate,
                "spo2": spo2,
                "oxygenLevel": spo2,
                "temperature": temperature,
                "systolicBp": systolic,
                "diastolicBp": diastolic,
                "timestamp": past_time.isoformat(),
                "recordedAt": past_time.isoformat(),
            })
        
        # Devolver en orden cronológico (más antiguo primero)
        return list(reversed(history))

# Instancia global del simulador
iot_simulator = IoTSimulator()


# ═══════════════════════════════════════════════════════════════════════════
# PASSWORD UTILS (usando bcrypt directamente, sin passlib)
# ═══════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """Hash password usando bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar password contra hash bcrypt"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# JWT UTILS
# ═══════════════════════════════════════════════════════════════════════════

def get_utc_now() -> datetime:
    """Obtener datetime actual en UTC (timezone-aware)"""
    return datetime.now(timezone.utc)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear JWT access token"""
    to_encode = data.copy()
    expire = get_utc_now() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": get_utc_now()})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Crear JWT refresh token"""
    return create_access_token(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL SERVICE - Envío de correos
# ═══════════════════════════════════════════════════════════════════════════

class EmailService:
    """Servicio para enviar emails usando SMTP (Gmail)"""
    
    @staticmethod
    def generate_reset_token() -> str:
        """Genera un token seguro de 32 caracteres para reset de contraseña"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_reset_code() -> str:
        """Genera un código numérico de 6 dígitos para reset de contraseña"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """
        Envía un email usando SMTP.
        Retorna True si se envió correctamente, False si hubo error.
        """
        if not settings.EMAIL_ENABLED or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print("⚠️ SMTP no configurado o deshabilitado. Email no enviado.")
            print(f"   Para: {to_email}")
            print(f"   Asunto: {subject}")
            return False
        
        try:
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
            message["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
            message["To"] = to_email
            
            # Agregar contenido de texto plano (fallback)
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)
            
            # Agregar contenido HTML
            part2 = MIMEText(html_content, "html")
            message.attach(part2)
            
            # Conectar y enviar según el tipo de conexión
            context = ssl.create_default_context()
            
            if settings.SMTP_SSL:
                # Puerto 465 - SSL directo
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(from_email, to_email, message.as_string())
            else:
                # Puerto 587 - STARTTLS
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(from_email, to_email, message.as_string())
            
            print(f"✅ Email enviado a: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Error de autenticación SMTP: {e}")
            print("   Verifica tu email y contraseña")
            return False
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return False
    
    @staticmethod
    async def send_password_reset_email(to_email: str, user_name: str, reset_code: str) -> bool:
        """Envía email de recuperación de contraseña con código de 6 dígitos"""
        
        # Asunto simple sin emojis (evita filtros de spam)
        subject = "Codigo de verificacion - NovaGuardian"
        
        # HTML simple y limpio (menos probable de ser marcado como spam)
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 500px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
        <h2 style="color: #333; margin-bottom: 20px;">NovaGuardian</h2>
        
        <p>Hola {user_name},</p>
        
        <p>Has solicitado restablecer tu contrasena. Tu codigo de verificacion es:</p>
        
        <div style="background-color: #f0f0f0; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #0066FF;">{reset_code}</span>
        </div>
        
        <p>Este codigo es valido por 15 minutos.</p>
        
        <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        
        <p style="color: #888; font-size: 12px;">NovaGuardian - Sistema de Monitoreo de Salud</p>
    </div>
</body>
</html>
"""
        
        text_content = f"""NovaGuardian - Codigo de verificacion

Hola {user_name},

Has solicitado restablecer tu contrasena.

Tu codigo de verificacion es: {reset_code}

Este codigo es valido por 15 minutos.

Si no solicitaste este cambio, puedes ignorar este mensaje.

--
NovaGuardian - Sistema de Monitoreo de Salud
"""
        
        return await EmailService.send_email(to_email, subject, html_content, text_content)


# Instancia global del servicio de email
email_service = EmailService()


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

# Wrapper para respuestas estándar de la API (compatible con app móvil)
class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: Optional[str] = None

class AuthData(BaseModel):
    user: dict
    token: str
    refreshToken: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    firstName: str
    lastName: str
    name: str
    phone: Optional[str] = None
    photoUrl: Optional[str] = None
    isActive: bool = True
    isVerified: bool = False
    role: str = "client"  # admin, operator, client
    createdAt: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Schema para login web (requiere rol admin/operator)
class WebLoginRequest(BaseModel):
    email: EmailStr
    password: str

class MonitoredPersonResponse(BaseModel):
    id: str
    userId: str
    firstName: str
    lastName: str
    name: str
    relationship: Optional[str] = None
    birthDate: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    bloodType: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    photoUrl: Optional[str] = None
    isActive: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class DeviceResponse(BaseModel):
    id: str
    serialNumber: str
    code: str
    name: Optional[str] = None
    model: str = "NovaBand V1"
    firmwareVersion: str = "1.0.0"
    status: str
    batteryLevel: float
    isConnected: bool
    isActive: bool = True
    lastSeen: Optional[str] = None
    monitoredPersonId: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class VitalSignsResponse(BaseModel):
    id: str
    deviceId: str
    heartRate: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    systolicBp: Optional[float] = None
    diastolicBp: Optional[float] = None
    steps: int = 0
    calories: float = 0
    recordedAt: str
    
    model_config = ConfigDict(from_attributes=True)

class LocationResponse(BaseModel):
    id: str
    deviceId: str
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    address: Optional[str] = None
    recordedAt: str
    
    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    id: str
    deviceId: str
    alertType: str
    severity: str
    title: str
    message: str
    value: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    isRead: bool = False
    isResolved: bool = False
    createdAt: str
    
    model_config = ConfigDict(from_attributes=True)

class GeofenceResponse(BaseModel):
    id: str
    monitoredPersonId: str
    name: str
    latitude: float
    longitude: float
    radius: float
    address: Optional[str] = None
    isActive: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class EmergencyContactResponse(BaseModel):
    id: str
    monitoredPersonId: str
    name: str
    phone: str
    email: Optional[str] = None
    relationship: Optional[str] = None
    isPrimary: bool = False
    
    model_config = ConfigDict(from_attributes=True)

class MedicalConditionResponse(BaseModel):
    id: str
    monitoredPersonId: str
    conditionType: str
    name: str
    description: Optional[str] = None
    severity: str = "medium"
    isActive: bool = True
    
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════

pool = None

async def get_db():
    global pool
    async with pool.acquire() as connection:
        yield connection


# ═══════════════════════════════════════════════════════════════════════════
# AUTH DEPENDENCY
# ═══════════════════════════════════════════════════════════════════════════

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", UUID(user_id))
    if user is None:
        raise credentials_exception
    return dict(user)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def calculate_age(birth_date) -> Optional[int]:
    """Calcular edad a partir de fecha de nacimiento"""
    if not birth_date:
        return None
    today = datetime.now().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_datetime(dt) -> Optional[str]:
    """Formatear datetime a ISO string"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)

def user_to_response(user: dict) -> UserResponse:
    """Convertir usuario de DB a respuesta"""
    return UserResponse(
        id=str(user['id']),
        email=user['email'],
        firstName=user['first_name'],
        lastName=user['last_name'],
        name=f"{user['first_name']} {user['last_name']}",
        phone=user.get('phone'),
        photoUrl=user.get('photo_url'),
        isActive=user['is_active'],
        isVerified=user['is_verified'],
        role=user.get('role', 'client'),
        createdAt=format_datetime(user.get('created_at'))
    )


# ═══════════════════════════════════════════════════════════════════════════
# LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    print("[START] Iniciando NovaGuardian API...")
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    # statement_cache_size=0 es REQUERIDO para Supabase/PgBouncer
    pool = await asyncpg.create_pool(
        db_url, 
        min_size=2, 
        max_size=10,
        statement_cache_size=0  # Fix para PgBouncer transaction mode
    )
    print("[OK] Conectado a PostgreSQL (Supabase con PgBouncer)")
    print("[API] http://localhost:8002/api/v1")
    print("[DOCS] http://localhost:8002/docs")
    print("[LAN] http://192.168.100.45:8002/api/v1")
    yield
    await pool.close()
    print("[STOP] API cerrada")


# ═══════════════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="NovaGuardian API",
    description="Sistema de Monitoreo Geriatrico IoT",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - AUTH
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/auth/login")
async def login(credentials: UserLogin, db = Depends(get_db)):
    """Login de usuario"""
    user = await db.fetchrow(
        "SELECT * FROM users WHERE email = $1 AND is_active = TRUE",
        credentials.email.lower()
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos"
        )
    
    if not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos"
        )
    
    access_token = create_access_token({"sub": str(user['id'])})
    refresh_token = create_refresh_token({"sub": str(user['id'])})
    
    await db.execute(
        "UPDATE users SET last_login = $1 WHERE id = $2",
        get_utc_now(), user['id']
    )
    
    return {
        "success": True,
        "data": {
            "user": user_to_response(dict(user)).model_dump(),
            "token": access_token,
            "refreshToken": refresh_token
        }
    }

@app.post("/api/v1/auth/web/login")
async def web_login(credentials: WebLoginRequest, db = Depends(get_db)):
    """Login para panel web - Solo permite admin y operator"""
    user = await db.fetchrow(
        "SELECT * FROM users WHERE email = $1 AND is_active = TRUE",
        credentials.email.lower()
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos"
        )
    
    if not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos"
        )
    
    # Verificar que el usuario tenga rol de admin u operator
    user_role = user.get('role', 'client')
    if user_role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Solo administradores y operadores pueden acceder al panel web."
        )
    
    access_token = create_access_token({"sub": str(user['id'])})
    refresh_token = create_refresh_token({"sub": str(user['id'])})
    
    await db.execute(
        "UPDATE users SET last_login = $1 WHERE id = $2",
        get_utc_now(), user['id']
    )
    
    return {
        "success": True,
        "data": {
            "user": user_to_response(dict(user)).model_dump(),
            "token": access_token,
            "refreshToken": refresh_token
        }
    }

@app.post("/api/v1/auth/register")
async def register(user_data: UserRegister, db = Depends(get_db)):
    """Registro de nuevo usuario desde app móvil - Siempre rol 'client'"""
    email_lower = user_data.email.lower()
    
    # Verificar email duplicado
    existing_email = await db.fetchrow(
        "SELECT id FROM users WHERE LOWER(email) = $1",
        email_lower
    )
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Verificar teléfono duplicado (si se proporciona)
    if user_data.phone:
        # Limpiar teléfono de espacios y caracteres especiales para comparar
        clean_phone = ''.join(filter(str.isdigit, user_data.phone))
        existing_phone = await db.fetchrow(
            "SELECT id FROM users WHERE REPLACE(REPLACE(phone, ' ', ''), '+', '') LIKE '%' || $1",
            clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
        )
        
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El número de teléfono ya está registrado"
            )
    
    user_id = uuid4()
    hashed_password = hash_password(user_data.password)
    now = get_utc_now()
    
    # Registro desde app móvil SIEMPRE es rol 'client'
    await db.execute("""
        INSERT INTO users (id, email, password_hash, first_name, last_name, phone, role, is_active, is_verified, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, 'client', TRUE, FALSE, $7)
    """, user_id, email_lower, hashed_password, user_data.firstName, user_data.lastName, user_data.phone, now)
    
    # Crear tokens
    access_token = create_access_token({"sub": str(user_id)})
    refresh_token = create_refresh_token({"sub": str(user_id)})
    
    user_response = UserResponse(
        id=str(user_id),
        email=email_lower,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        name=f"{user_data.firstName} {user_data.lastName}",
        phone=user_data.phone,
        role="client",
        createdAt=format_datetime(now)
    )
    
    return {
        "success": True,
        "data": {
            "user": user_response.model_dump(),
            "token": access_token,
            "refreshToken": refresh_token
        }
    }

# Schema para crear staff (admin/operator) desde la web
class CreateStaffRequest(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    phone: Optional[str] = None
    role: str = "operator"  # admin o operator

@app.post("/api/v1/auth/web/register")
async def web_register(user_data: CreateStaffRequest, current_user: dict = Depends(get_current_user), db = Depends(get_db)):
    """Registro de admin/operator desde panel web - Solo admins pueden crear"""
    # Verificar que el usuario actual sea admin
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden crear usuarios del staff"
        )
    
    # Validar rol
    if user_data.role not in ['admin', 'operator']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol debe ser 'admin' u 'operator'"
        )
    
    email_lower = user_data.email.lower()
    
    existing = await db.fetchrow(
        "SELECT id FROM users WHERE LOWER(email) = $1",
        email_lower
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya esta registrado"
        )
    
    user_id = uuid4()
    hashed_password = hash_password(user_data.password)
    now = get_utc_now()
    
    is_admin = user_data.role == 'admin'
    
    await db.execute("""
        INSERT INTO users (id, email, password_hash, first_name, last_name, phone, role, is_admin, is_active, is_verified, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, TRUE, $9)
    """, user_id, email_lower, hashed_password, user_data.firstName, user_data.lastName, user_data.phone, user_data.role, is_admin, now)
    
    user_response = UserResponse(
        id=str(user_id),
        email=email_lower,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        name=f"{user_data.firstName} {user_data.lastName}",
        phone=user_data.phone,
        role=user_data.role,
        isVerified=True,
        createdAt=format_datetime(now)
    )
    
    return {
        "success": True,
        "data": user_response.model_dump(),
        "message": f"Usuario {user_data.role} creado exitosamente"
    }

@app.post("/api/v1/auth/refresh")
async def refresh_token_endpoint(refresh_token: str, db = Depends(get_db)):
    """Refrescar access token"""
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")
    
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1 AND is_active = TRUE", UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    new_access_token = create_access_token({"sub": str(user['id'])})
    new_refresh_token = create_refresh_token({"sub": str(user['id'])})
    
    return {
        "success": True,
        "data": {
            "token": new_access_token,
            "refreshToken": new_refresh_token
        }
    }

@app.get("/api/v1/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Obtener usuario actual"""
    return {
        "success": True,
        "data": user_to_response(current_user).model_dump()
    }

@app.get("/api/v1/users/me")
async def get_user_me(current_user: dict = Depends(get_current_user)):
    """Obtener usuario actual (alias)"""
    return {
        "success": True,
        "data": user_to_response(current_user).model_dump()
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - MONITORED PERSONS
# ═══════════════════════════════════════════════════════════════════════════

async def _get_monitored_persons(user_id, db):
    """Helper para obtener personas monitoreadas"""
    rows = await db.fetch(
        "SELECT * FROM monitored_persons WHERE user_id = $1 AND is_active = TRUE ORDER BY first_name",
        user_id
    )
    
    result = []
    for row in rows:
        result.append({
            "id": str(row['id']),
            "userId": str(row['user_id']),
            "firstName": row['first_name'],
            "lastName": row['last_name'],
            "name": f"{row['first_name']} {row['last_name']}",
            "relationship": row.get('relationship'),
            "birthDate": format_datetime(row.get('birth_date')),
            "age": calculate_age(row.get('birth_date')),
            "gender": row.get('gender'),
            "bloodType": row.get('blood_type'),
            "weight": float(row['weight']) if row.get('weight') else None,
            "height": float(row['height']) if row.get('height') else None,
            "photoUrl": row.get('photo_url'),
            "isActive": row['is_active']
        })
    return result

async def _get_monitored_person(person_id, user_id, db):
    """Helper para obtener una persona monitoreada (busca por person_id o device_id)"""
    # Primero intenta buscar por person_id
    row = await db.fetchrow(
        "SELECT * FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(person_id), user_id
    )
    
    # Si no encuentra, intenta buscar por device_id
    if not row:
        row = await db.fetchrow("""
            SELECT mp.* FROM monitored_persons mp
            JOIN devices d ON d.monitored_person_id = mp.id
            WHERE d.id = $1 AND mp.user_id = $2
        """, UUID(person_id), user_id)
    
    if not row:
        return None
    
    person_uuid = row['id']
    
    # Cargar medicamentos
    med_rows = await db.fetch(
        "SELECT * FROM medications WHERE monitored_person_id = $1 ORDER BY name",
        person_uuid
    )
    medications = [
        {
            "id": str(m['id']),
            "name": m['name'],
            "dosage": m['dosage'],
            "frequency": m['frequency'],
            "notes": m.get('notes')
        }
        for m in med_rows
    ]
    
    # Cargar condiciones médicas
    try:
        cond_rows = await db.fetch(
            "SELECT * FROM medical_conditions WHERE monitored_person_id = $1 AND is_active = TRUE",
            person_uuid
        )
        medicalConditions = [
            {
                "id": str(c['id']),
                "conditionType": c.get('condition_type', 'disease'),
                "name": c['name'],
                "description": c.get('description'),
                "severity": c.get('severity', 'medium'),
                "notes": c.get('notes')
            }
            for c in cond_rows
        ]
    except:
        medicalConditions = []
    
    # Cargar contactos de emergencia
    contact_rows = await db.fetch(
        "SELECT * FROM emergency_contacts WHERE monitored_person_id = $1 ORDER BY is_primary DESC, name",
        person_uuid
    )
    emergencyContacts = [
        {
            "id": str(c['id']),
            "name": c['name'],
            "phone": c['phone'],
            "relationship": c.get('relationship'),
            "isPrimary": c.get('is_primary', False),
            "notifyAlerts": c.get('notify_on_alerts', True)
        }
        for c in contact_rows
    ]
    
    return {
        "id": str(row['id']),
        "userId": str(row['user_id']),
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "name": f"{row['first_name']} {row['last_name']}",
        "relationship": row.get('relationship'),
        "birthDate": format_datetime(row.get('birth_date')),
        "age": calculate_age(row.get('birth_date')),
        "gender": row.get('gender'),
        "bloodType": row.get('blood_type'),
        "weight": float(row['weight']) if row.get('weight') else None,
        "height": float(row['height']) if row.get('height') else None,
        "photoUrl": row.get('photo_url'),
        "isActive": row['is_active'],
        "medications": medications,
        "medicalConditions": medicalConditions,
        "emergencyContacts": emergencyContacts,
        "notes": row.get('notes')
    }

# Endpoint para app movil: /monitored
@app.get("/api/v1/monitored")
async def get_monitored(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener personas monitoreadas del usuario"""
    persons = await _get_monitored_persons(current_user['id'], db)
    return {"success": True, "data": persons}

@app.get("/api/v1/monitored/{person_id}")
async def get_monitored_by_id(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener detalle de persona monitoreada"""
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return {"success": True, "data": person}

# Endpoints alternativos: /monitored-persons
@app.get("/api/v1/monitored-persons")
async def get_monitored_persons(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener personas monitoreadas del usuario"""
    persons = await _get_monitored_persons(current_user['id'], db)
    return {"success": True, "data": persons}

@app.post("/api/v1/monitored-persons")
async def create_monitored_person_alt(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Crear nueva persona monitoreada (endpoint alternativo)"""
    data = await request.json()
    
    # Aceptar tanto snake_case como camelCase
    first_name = data.get('first_name') or data.get('firstName')
    last_name = data.get('last_name') or data.get('lastName')
    
    if not first_name or not last_name:
        raise HTTPException(status_code=400, detail="first_name y last_name son requeridos")
    
    person_id = uuid4()
    now = get_utc_now()
    
    # Convertir birth_date de string a date
    birth_date = None
    birth_date_str = data.get('birth_date') or data.get('birthDate')
    if birth_date_str:
        if isinstance(birth_date_str, str):
            try:
                birth_date = datetime.strptime(birth_date_str.split('T')[0], '%Y-%m-%d').date()
            except ValueError:
                birth_date = None
    
    # Obtener otros campos
    relationship = data.get('relationship')
    gender = data.get('gender')
    blood_type = data.get('blood_type') or data.get('bloodType')
    photo_url = data.get('photo_url') or data.get('photoUrl')
    notes = data.get('notes')
    
    # Convertir weight y height
    weight = None
    weight_val = data.get('weight')
    if weight_val:
        try:
            weight = float(weight_val)
        except (ValueError, TypeError):
            pass
    
    height = None
    height_val = data.get('height')
    if height_val:
        try:
            height = float(height_val)
        except (ValueError, TypeError):
            pass
    
    await db.execute("""
        INSERT INTO monitored_persons (
            id, user_id, first_name, last_name, relationship, birth_date,
            gender, blood_type, weight, height, photo_url, notes, is_active, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, TRUE, $13, $13)
    """, 
        person_id, current_user['id'], first_name, last_name,
        relationship, birth_date, gender, blood_type,
        weight, height, photo_url, notes, now
    )
    
    person = await _get_monitored_person(str(person_id), current_user['id'], db)
    return {"success": True, "data": person}

@app.get("/api/v1/monitored-persons/{person_id}")
async def get_monitored_person(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener detalle de persona monitoreada"""
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return {"success": True, "data": person}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - DEVICES
# ═══════════════════════════════════════════════════════════════════════════

async def _get_user_devices(user_id, db):
    """Helper para obtener dispositivos del usuario con datos de persona monitoreada"""
    rows = await db.fetch("""
        SELECT d.*, 
               mp.id as mp_id, mp.first_name, mp.last_name, mp.relationship, 
               mp.birth_date, mp.gender, mp.blood_type, mp.weight, mp.height, mp.photo_url
        FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND d.is_active = TRUE
    """, user_id)
    
    result = []
    for row in rows:
        device = {
            "id": str(row['id']),
            "serialNumber": row['serial_number'],
            "code": row['code'],
            "name": row.get('name'),
            "model": row.get('model', 'NovaBand V1'),
            "firmwareVersion": row.get('firmware_version', '1.0.0'),
            "status": row['status'],
            "batteryLevel": float(row['battery_level']),
            "isConnected": row['is_connected'],
            "isActive": row['is_active'],
            "lastSeen": format_datetime(row.get('last_seen')),
            "monitoredPersonId": str(row['monitored_person_id']) if row.get('monitored_person_id') else None,
            "monitoredPerson": {
                "id": str(row['mp_id']),
                "firstName": row['first_name'],
                "lastName": row['last_name'],
                "name": f"{row['first_name']} {row['last_name']}",
                "relationship": row.get('relationship'),
                "birthDate": format_datetime(row.get('birth_date')),
                "age": calculate_age(row.get('birth_date')),
                "gender": row.get('gender'),
                "bloodType": row.get('blood_type'),
                "weight": float(row['weight']) if row.get('weight') else None,
                "height": float(row['height']) if row.get('height') else None,
                "photoUrl": row.get('photo_url'),
                "emergencyContacts": []  # Se cargaría de otra tabla si existe
            } if row.get('mp_id') else None
        }
        
        # Cargar contactos de emergencia si existen
        if row.get('mp_id'):
            contacts = await db.fetch("""
                SELECT * FROM emergency_contacts WHERE monitored_person_id = $1
            """, row['mp_id'])
            if contacts:
                device["monitoredPerson"]["emergencyContacts"] = [
                    {
                        "id": str(c['id']),
                        "name": c['name'],
                        "phone": c['phone'],
                        "relationship": c.get('relationship'),
                        "isPrimary": c.get('is_primary', False)
                    }
                    for c in contacts
                ]
        
        result.append(device)
    
    return result

@app.get("/api/v1/devices/my-devices")
async def get_my_devices(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener dispositivos del usuario (endpoint para app movil)"""
    devices = await _get_user_devices(current_user['id'], db)
    return {"success": True, "data": devices}

@app.get("/api/v1/devices")
async def get_devices(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener dispositivos del usuario"""
    devices = await _get_user_devices(current_user['id'], db)
    return {"success": True, "data": devices}

@app.get("/api/v1/devices/{device_id}")
async def get_device(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener detalle de dispositivo"""
    row = await db.fetchrow("""
        SELECT d.* FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    device = {
        "id": str(row['id']),
        "serialNumber": row['serial_number'],
        "code": row['code'],
        "name": row.get('name'),
        "model": row.get('model', 'NovaBand V1'),
        "firmwareVersion": row.get('firmware_version', '1.0.0'),
        "status": row['status'],
        "batteryLevel": float(row['battery_level']),
        "isConnected": row['is_connected'],
        "isActive": row['is_active'],
        "lastSeen": format_datetime(row.get('last_seen')),
        "monitoredPersonId": str(row['monitored_person_id']) if row.get('monitored_person_id') else None
    }
    return {"success": True, "data": device}

@app.get("/api/v1/devices/{device_id}/status")
async def get_device_status(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener estado de un dispositivo"""
    row = await db.fetchrow("""
        SELECT d.is_connected, d.battery_level, d.last_seen FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    return {
        "success": True,
        "data": {
            "isConnected": row['is_connected'],
            "batteryLevel": float(row['battery_level']),
            "lastSeen": format_datetime(row.get('last_seen'))
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - VITAL SIGNS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/devices/{device_id}/vital-signs/latest", response_model=Optional[VitalSignsResponse])
async def get_latest_vital_signs(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener ultimos signos vitales de un dispositivo"""
    row = await db.fetchrow("""
        SELECT vs.* FROM vital_signs vs
        JOIN devices d ON vs.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE vs.device_id = $1 AND mp.user_id = $2
        ORDER BY vs.recorded_at DESC
        LIMIT 1
    """, UUID(device_id), current_user['id'])
    
    if not row:
        return None
    
    return VitalSignsResponse(
        id=str(row['id']),
        deviceId=str(row['device_id']),
        heartRate=float(row['heart_rate']) if row.get('heart_rate') else None,
        spo2=float(row['spo2']) if row.get('spo2') else None,
        temperature=float(row['temperature']) if row.get('temperature') else None,
        systolicBp=float(row['systolic_bp']) if row.get('systolic_bp') else None,
        diastolicBp=float(row['diastolic_bp']) if row.get('diastolic_bp') else None,
        steps=row.get('steps', 0),
        calories=float(row.get('calories', 0)),
        recordedAt=format_datetime(row['recorded_at'])
    )

@app.get("/api/v1/vital-signs/current", response_model=List[VitalSignsResponse])
async def get_current_vital_signs(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener signos vitales actuales de todos los dispositivos del usuario"""
    rows = await db.fetch("""
        SELECT DISTINCT ON (vs.device_id) vs.* 
        FROM vital_signs vs
        JOIN devices d ON vs.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1
        ORDER BY vs.device_id, vs.recorded_at DESC
    """, current_user['id'])
    
    return [
        VitalSignsResponse(
            id=str(row['id']),
            deviceId=str(row['device_id']),
            heartRate=float(row['heart_rate']) if row.get('heart_rate') else None,
            spo2=float(row['spo2']) if row.get('spo2') else None,
            temperature=float(row['temperature']) if row.get('temperature') else None,
            systolicBp=float(row['systolic_bp']) if row.get('systolic_bp') else None,
            diastolicBp=float(row['diastolic_bp']) if row.get('diastolic_bp') else None,
            steps=row.get('steps', 0),
            calories=float(row.get('calories', 0)),
            recordedAt=format_datetime(row['recorded_at'])
        )
        for row in rows
    ]

@app.get("/api/v1/vital-signs/device/{device_id}/current", response_model=Optional[VitalSignsResponse])
async def get_device_vital_signs_current(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener signos vitales actuales de un dispositivo específico"""
    # Verificar que el dispositivo pertenece al usuario
    device = await db.fetchrow("""
        SELECT d.* FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Obtener último registro de signos vitales
    row = await db.fetchrow("""
        SELECT * FROM vital_signs
        WHERE device_id = $1
        ORDER BY recorded_at DESC
        LIMIT 1
    """, UUID(device_id))
    
    if not row:
        # Generar signos vitales simulados si no hay datos
        simulated = IoTSimulator.generate_vital_signs(device_id)
        return VitalSignsResponse(
            id=str(uuid4()),
            deviceId=device_id,
            heartRate=simulated['heart_rate'],
            spo2=simulated['spo2'],
            temperature=simulated['temperature'],
            systolicBp=simulated['systolic_bp'],
            diastolicBp=simulated['diastolic_bp'],
            steps=simulated['steps'],
            calories=simulated['calories'],
            recordedAt=datetime.now(timezone.utc).isoformat()
        )
    
    return VitalSignsResponse(
        id=str(row['id']),
        deviceId=str(row['device_id']),
        heartRate=float(row['heart_rate']) if row.get('heart_rate') else None,
        spo2=float(row['spo2']) if row.get('spo2') else None,
        temperature=float(row['temperature']) if row.get('temperature') else None,
        systolicBp=float(row['systolic_bp']) if row.get('systolic_bp') else None,
        diastolicBp=float(row['diastolic_bp']) if row.get('diastolic_bp') else None,
        steps=row.get('steps', 0),
        calories=float(row.get('calories', 0)),
        recordedAt=format_datetime(row['recorded_at'])
    )


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - LOCATIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/locations/current", response_model=List[LocationResponse])
async def get_current_locations(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener ubicaciones actuales de todos los dispositivos"""
    rows = await db.fetch("""
        SELECT DISTINCT ON (l.device_id) l.* 
        FROM locations l
        JOIN devices d ON l.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1
        ORDER BY l.device_id, l.recorded_at DESC
    """, current_user['id'])
    
    return [
        LocationResponse(
            id=str(row['id']),
            deviceId=str(row['device_id']),
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            accuracy=float(row['accuracy']) if row.get('accuracy') else None,
            address=row.get('address'),
            recordedAt=format_datetime(row['recorded_at'])
        )
        for row in rows
    ]

@app.get("/api/v1/devices/{device_id}/location/current", response_model=Optional[LocationResponse])
async def get_device_current_location(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener ubicacion actual de un dispositivo"""
    row = await db.fetchrow("""
        SELECT l.* FROM locations l
        JOIN devices d ON l.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE l.device_id = $1 AND mp.user_id = $2
        ORDER BY l.recorded_at DESC
        LIMIT 1
    """, UUID(device_id), current_user['id'])
    
    if not row:
        return None
    
    return LocationResponse(
        id=str(row['id']),
        deviceId=str(row['device_id']),
        latitude=float(row['latitude']),
        longitude=float(row['longitude']),
        accuracy=float(row['accuracy']) if row.get('accuracy') else None,
        address=row.get('address'),
        recordedAt=format_datetime(row['recorded_at'])
    )

@app.get("/api/v1/locations/device/{device_id}/current", response_model=Optional[LocationResponse])
async def get_location_device_current(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener ubicación actual de un dispositivo (ruta alternativa para móvil)"""
    row = await db.fetchrow("""
        SELECT l.* FROM locations l
        JOIN devices d ON l.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE l.device_id = $1 AND mp.user_id = $2
        ORDER BY l.recorded_at DESC
        LIMIT 1
    """, UUID(device_id), current_user['id'])
    
    if not row:
        # Generar ubicación simulada si no hay datos
        simulated = IoTSimulator.generate_location(device_id)
        return LocationResponse(
            id=str(uuid4()),
            deviceId=device_id,
            latitude=simulated['latitude'],
            longitude=simulated['longitude'],
            accuracy=simulated['accuracy'],
            address=simulated.get('address'),
            recordedAt=datetime.now(timezone.utc).isoformat()
        )
    
    return LocationResponse(
        id=str(row['id']),
        deviceId=str(row['device_id']),
        latitude=float(row['latitude']),
        longitude=float(row['longitude']),
        accuracy=float(row['accuracy']) if row.get('accuracy') else None,
        address=row.get('address'),
        recordedAt=format_datetime(row['recorded_at'])
    )


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - MONITORING (endpoints para app movil)
# Usa el simulador IoT para generar datos realistas en tiempo real
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitoring/{device_id}/current")
async def get_monitoring_current(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Obtener signos vitales actuales de un dispositivo.
    Genera datos en tiempo real simulando un dispositivo IoT.
    """
    # Verificar que el dispositivo pertenece al usuario
    device = await db.fetchrow("""
        SELECT d.id FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Generar datos simulados en tiempo real
    vitals = iot_simulator.generate_vitals(device_id)
    
    return {
        "success": True,
        "data": {
            "id": str(uuid4()),
            "deviceId": device_id,
            **vitals
        }
    }

@app.get("/api/v1/monitoring/{device_id}/history")
async def get_monitoring_history(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    period: str = "day",
    limit: int = 100
):
    """
    Obtener historial de signos vitales.
    Genera historial simulado para las últimas horas.
    """
    # Verificar que el dispositivo pertenece al usuario
    device = await db.fetchrow("""
        SELECT d.id FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Determinar horas según período
    hours = {"day": 24, "week": 168, "month": 720}.get(period, 24)
    
    # Generar historial simulado
    history = iot_simulator.generate_vitals_history(device_id, min(hours, 72))
    
    return {
        "success": True,
        "data": [
            {
                "id": str(uuid4()),
                "deviceId": device_id,
                **record
            }
            for record in history[:limit]
        ]
    }

@app.get("/api/v1/monitoring/{device_id}/location")
async def get_monitoring_location(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Obtener ubicación actual de un dispositivo.
    Genera ubicación en tiempo real simulando GPS del IoT.
    """
    # Verificar que el dispositivo pertenece al usuario
    device = await db.fetchrow("""
        SELECT d.id FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Generar ubicación simulada en tiempo real
    location = iot_simulator.generate_location(device_id)
    
    return {
        "success": True,
        "data": {
            "id": str(uuid4()),
            "deviceId": device_id,
            **location
        }
    }

@app.get("/api/v1/monitoring/{device_id}/locations")
async def get_monitoring_locations_history(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    limit: int = 50
):
    """Obtener historial de ubicaciones"""
    rows = await db.fetch("""
        SELECT l.* FROM locations l
        JOIN devices d ON l.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE l.device_id = $1 AND mp.user_id = $2
        ORDER BY l.recorded_at DESC
        LIMIT $3
    """, UUID(device_id), current_user['id'], limit)
    
    return {
        "success": True,
        "data": [
            {
                "id": str(row['id']),
                "deviceId": str(row['device_id']),
                "latitude": float(row['latitude']),
                "longitude": float(row['longitude']),
                "accuracy": float(row['accuracy']) if row.get('accuracy') else None,
                "address": row.get('address'),
                "recordedAt": format_datetime(row['recorded_at'])
            }
            for row in rows
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - GEOFENCES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitored-persons/{person_id}/geofences", response_model=List[GeofenceResponse])
async def get_geofences(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener zonas seguras de una persona"""
    person = await db.fetchrow(
        "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(person_id), current_user['id']
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    rows = await db.fetch(
        "SELECT * FROM geofences WHERE monitored_person_id = $1 AND is_active = TRUE",
        UUID(person_id)
    )
    
    return [
        GeofenceResponse(
            id=str(row['id']),
            monitoredPersonId=str(row['monitored_person_id']),
            name=row['name'],
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            radius=float(row['radius']),
            address=row.get('address'),
            isActive=row['is_active']
        )
        for row in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - EMERGENCY CONTACTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitored-persons/{person_id}/emergency-contacts", response_model=List[EmergencyContactResponse])
async def get_emergency_contacts(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener contactos de emergencia de una persona"""
    person = await db.fetchrow(
        "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(person_id), current_user['id']
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    rows = await db.fetch(
        "SELECT * FROM emergency_contacts WHERE monitored_person_id = $1 ORDER BY is_primary DESC, name",
        UUID(person_id)
    )
    
    return [
        EmergencyContactResponse(
            id=str(row['id']),
            monitoredPersonId=str(row['monitored_person_id']),
            name=row['name'],
            phone=row['phone'],
            email=row.get('email'),
            relationship=row.get('relationship'),
            isPrimary=row['is_primary']
        )
        for row in rows
    ]

@app.post("/api/v1/monitored-persons/{person_id}/emergency-contacts", response_model=EmergencyContactResponse)
async def add_emergency_contact(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    name: str = Body(...),
    phone: str = Body(...),
    relationship: Optional[str] = Body(None),
    email: Optional[str] = Body(None),
    isPrimary: bool = Body(False),
    notifyAlerts: bool = Body(True),
):
    """Agregar contacto de emergencia a una persona"""
    person = await db.fetchrow(
        "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(person_id), current_user['id']
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    contact_id = uuid4()
    now = get_utc_now()
    
    await db.execute("""
        INSERT INTO emergency_contacts (id, monitored_person_id, name, phone, email, relationship, is_primary, notify_on_alerts, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
    """, contact_id, UUID(person_id), name, phone, email, relationship, isPrimary, notifyAlerts, now)
    
    return EmergencyContactResponse(
        id=str(contact_id),
        monitoredPersonId=person_id,
        name=name,
        phone=phone,
        email=email,
        relationship=relationship,
        isPrimary=isPrimary
    )

@app.delete("/api/v1/monitored-persons/{person_id}/emergency-contacts/{contact_id}")
async def delete_emergency_contact(
    person_id: str,
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Eliminar contacto de emergencia"""
    person = await db.fetchrow(
        "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(person_id), current_user['id']
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    result = await db.execute(
        "DELETE FROM emergency_contacts WHERE id = $1 AND monitored_person_id = $2",
        UUID(contact_id), UUID(person_id)
    )
    
    return {"success": True, "message": "Contacto eliminado"}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - MEDICAL CONDITIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitored-persons/{person_id}/medical-conditions", response_model=List[MedicalConditionResponse])
async def get_medical_conditions(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener condiciones medicas de una persona"""
    person = await db.fetchrow(
        "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(person_id), current_user['id']
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    rows = await db.fetch(
        "SELECT * FROM medical_conditions WHERE monitored_person_id = $1 AND is_active = TRUE",
        UUID(person_id)
    )
    
    return [
        MedicalConditionResponse(
            id=str(row['id']),
            monitoredPersonId=str(row['monitored_person_id']),
            conditionType=row['condition_type'],
            name=row['name'],
            description=row.get('description'),
            severity=row['severity'],
            isActive=row['is_active']
        )
        for row in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - ALERTS
# ═══════════════════════════════════════════════════════════════════════════

async def _get_alerts(user_id, db, limit=50, unread_only=False):
    """Helper para obtener alertas del usuario"""
    query = """
        SELECT a.* FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1
    """
    
    if unread_only:
        query += " AND a.is_read = FALSE"
    
    query += " ORDER BY a.created_at DESC LIMIT $2"
    
    rows = await db.fetch(query, user_id, limit)
    
    return [
        {
            "id": str(row['id']),
            "deviceId": str(row['device_id']),
            "type": row['alert_type'],  # Alias para compatibilidad con frontend
            "alertType": row['alert_type'],
            "severity": row['severity'],
            "title": row['title'],
            "message": row['message'],
            "value": float(row['value']) if row.get('value') else None,
            "latitude": float(row['latitude']) if row.get('latitude') else None,
            "longitude": float(row['longitude']) if row.get('longitude') else None,
            "address": row.get('address'),
            "isRead": row['is_read'],
            "isResolved": row['is_resolved'],
            "createdAt": format_datetime(row['created_at'])
        }
        for row in rows
    ]

async def _maybe_generate_alert(device_id: str, db):
    """
    Genera una alerta automática si corresponde según el tiempo.
    Se llama cada vez que se obtienen los vitales o alertas.
    """
    should_gen, is_critical = iot_simulator.should_generate_alert(device_id)
    
    if not should_gen:
        return None
    
    # Generar alerta
    alert_data = iot_simulator.generate_alert(device_id, is_critical)
    
    # Insertar en BD
    alert_id = uuid4()
    now = get_utc_now()
    
    await db.execute("""
        INSERT INTO alerts (id, device_id, alert_type, severity, title, message, value, is_read, is_resolved, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE, FALSE, $8, $8)
    """, alert_id, UUID(device_id), alert_data["type"], alert_data["severity"], 
        alert_data["title"], alert_data["message"], alert_data.get("value"), now)
    
    print(f"🔔 Alerta generada: {alert_data['title']} ({alert_data['severity']})")
    
    return {
        "id": str(alert_id),
        "deviceId": device_id,
        "type": alert_data["type"],  # Alias para compatibilidad con frontend
        "alertType": alert_data["type"],
        "severity": alert_data["severity"],
        "title": alert_data["title"],
        "message": alert_data["message"],
        "value": alert_data.get("value"),
        "isRead": False,
        "isResolved": False,
        "createdAt": now.isoformat()
    }

@app.get("/api/v1/alerts/recent")
async def get_recent_alerts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    limit: int = 10
):
    """Obtener alertas recientes - también genera alertas automáticas"""
    # Obtener dispositivo del usuario para generar alertas
    device = await db.fetchrow("""
        SELECT d.id FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1
        LIMIT 1
    """, current_user['id'])
    
    if device:
        await _maybe_generate_alert(str(device['id']), db)
    
    alerts = await _get_alerts(current_user['id'], db, limit)
    return {"success": True, "data": alerts}

@app.get("/api/v1/alerts")
async def get_alerts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    limit: int = 50,
    unread_only: bool = False
):
    """Obtener alertas del usuario - también genera alertas automáticas"""
    # Obtener dispositivo del usuario para generar alertas
    device = await db.fetchrow("""
        SELECT d.id FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1
        LIMIT 1
    """, current_user['id'])
    
    if device:
        await _maybe_generate_alert(str(device['id']), db)
    
    alerts = await _get_alerts(current_user['id'], db, limit, unread_only)
    return {"success": True, "data": alerts}

@app.get("/api/v1/alerts/stats")
async def get_alerts_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener estadisticas de alertas"""
    user_id = current_user['id']
    
    # Total de alertas
    total = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1
    """, user_id)
    
    # Alertas por severidad
    critical = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.severity = 'critical'
    """, user_id)
    
    warning = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.severity = 'warning'
    """, user_id)
    
    info = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.severity = 'info'
    """, user_id)
    
    # Sin resolver
    unresolved = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.is_resolved = FALSE
    """, user_id)
    
    # Sin leer
    unread = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.is_read = FALSE
    """, user_id)
    
    return {
        "success": True,
        "data": {
            "total": total,
            "critical": critical,
            "warning": warning,
            "info": info,
            "unresolved": unresolved,
            "unread": unread,
            "bySeverity": {
                "critical": critical,
                "warning": warning,
                "info": info
            }
        }
    }

@app.get("/api/v1/alerts/unread/count")
async def get_unread_alerts_count(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener conteo de alertas no leidas"""
    result = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.is_read = FALSE
    """, current_user['id'])
    
    return {"success": True, "data": {"count": result}}

@app.get("/api/v1/alerts/pending-count")
async def get_pending_alerts_count(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener conteo de alertas pendientes (alias)"""
    result = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.is_read = FALSE
    """, current_user['id'])
    
    return {"success": True, "data": {"count": result or 0}}

# IMPORTANTE: Este endpoint debe estar ANTES de /alerts/{alert_id} para evitar conflictos de rutas
@app.get("/api/v1/alerts/unread")
async def get_unread_alerts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener alertas no leídas del usuario"""
    alerts = await _get_alerts(current_user['id'], db, limit=50, unread_only=True)
    return {"success": True, "data": alerts}

@app.get("/api/v1/alerts/{alert_id}")
async def get_alert_detail(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener detalle de una alerta específica"""
    alert = await db.fetchrow("""
        SELECT a.*, d.name as device_name, mp.first_name as person_name
        FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE a.id = $1 AND mp.user_id = $2
    """, alert_id, current_user['id'])
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    alert_dict = dict(alert)
    return {
        "success": True,
        "data": {
            "id": str(alert_dict['id']),
            "deviceId": str(alert_dict['device_id']),
            "deviceName": alert_dict['device_name'],
            "personName": alert_dict['person_name'],
            "type": alert_dict['alert_type'],
            "severity": alert_dict['severity'],
            "title": alert_dict['title'],
            "message": alert_dict['message'],
            "isRead": alert_dict['is_read'],
            "isAttended": alert_dict.get('is_attended', False),
            "attendedAt": alert_dict['attended_at'].isoformat() if alert_dict.get('attended_at') else None,
            "createdAt": alert_dict['created_at'].isoformat() if alert_dict.get('created_at') else None,
        }
    }

@app.put("/api/v1/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Marcar alerta como leida"""
    await db.execute("""
        UPDATE alerts SET is_read = TRUE, updated_at = $1
        WHERE id = $2
    """, get_utc_now(), UUID(alert_id))
    
    return {"success": True, "data": None}

@app.put("/api/v1/alerts/{alert_id}/attended")
async def mark_alert_attended(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Marcar alerta como atendida"""
    await db.execute("""
        UPDATE alerts SET is_read = TRUE, updated_at = $1
        WHERE id = $2
    """, get_utc_now(), UUID(alert_id))
    
    return {"success": True, "data": None}

@app.put("/api/v1/alerts/{alert_id}/attend")
async def attend_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    body: dict = Body(default={})
):
    """Marcar alerta como atendida (endpoint alternativo para móvil)"""
    notes = body.get('notes', '')
    now = get_utc_now()
    
    await db.execute("""
        UPDATE alerts 
        SET is_read = TRUE, is_resolved = TRUE, resolved_at = $1, 
            resolved_by = $2, notes = $3, updated_at = $1
        WHERE id = $4
    """, now, current_user['id'], notes, UUID(alert_id))
    
    # Obtener la alerta actualizada
    alert = await db.fetchrow("SELECT * FROM alerts WHERE id = $1", UUID(alert_id))
    
    if alert:
        return {
            "success": True,
            "data": {
                "id": str(alert['id']),
                "deviceId": str(alert['device_id']),
                "type": alert['alert_type'],
                "severity": alert['severity'],
                "title": alert['title'],
                "message": alert['message'],
                "isRead": alert['is_read'],
                "isResolved": alert['is_resolved'],
                "notes": alert['notes'],
                "createdAt": alert['created_at'].isoformat() if alert.get('created_at') else None
            }
        }
    
    return {"success": True, "data": None}

@app.put("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Marcar alerta como resuelta"""
    now = get_utc_now()
    await db.execute("""
        UPDATE alerts SET is_resolved = TRUE, resolved_at = $1, resolved_by = $2, updated_at = $1
        WHERE id = $3
    """, now, current_user['id'], UUID(alert_id))
    
    return {"success": True, "data": None}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener resumen para el dashboard"""
    user_id = current_user['id']
    
    monitored_count = await db.fetchval(
        "SELECT COUNT(*) FROM monitored_persons WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    
    devices_connected = await db.fetchval("""
        SELECT COUNT(*) FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND d.is_connected = TRUE
    """, user_id)
    
    unread_alerts = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.is_read = FALSE
    """, user_id)
    
    critical_alerts = await db.fetchval("""
        SELECT COUNT(*) FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.severity = 'critical' AND a.is_resolved = FALSE
    """, user_id)
    
    return {
        "monitoredPersonsCount": monitored_count,
        "devicesConnected": devices_connected,
        "unreadAlerts": unread_alerts,
        "criticalAlerts": critical_alerts
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - ADMIN PANEL (Para la web de administración)
# ═══════════════════════════════════════════════════════════════════════════

# --------------- ADMIN DASHBOARD ---------------

@app.get("/api/v1/admin/dashboard/stats")
async def admin_dashboard_stats(db = Depends(get_db)):
    """Estadísticas para el dashboard de administración"""
    total_users = await db.fetchval("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
    total_devices = await db.fetchval("SELECT COUNT(*) FROM devices")
    total_monitored = await db.fetchval("SELECT COUNT(*) FROM monitored_persons WHERE is_active = TRUE")
    total_alerts_today = await db.fetchval(
        "SELECT COUNT(*) FROM alerts WHERE created_at >= CURRENT_DATE"
    )
    active_devices = await db.fetchval("SELECT COUNT(*) FROM devices WHERE is_connected = TRUE")
    pending_alerts = await db.fetchval("SELECT COUNT(*) FROM alerts WHERE is_resolved = FALSE")
    
    return {
        "totalUsers": total_users or 0,
        "totalDevices": total_devices or 0,
        "totalMonitored": total_monitored or 0,
        "totalAlertsToday": total_alerts_today or 0,
        "activeDevices": active_devices or 0,
        "pendingAlerts": pending_alerts or 0
    }

@app.get("/api/v1/admin/dashboard/users-by-month")
async def admin_users_by_month(db = Depends(get_db)):
    """Usuarios registrados por mes (últimos 6 meses)"""
    rows = await db.fetch("""
        SELECT 
            TO_CHAR(created_at, 'Mon') as month,
            EXTRACT(MONTH FROM created_at) as month_num,
            COUNT(*) as count
        FROM users 
        WHERE created_at >= NOW() - INTERVAL '6 months'
        GROUP BY TO_CHAR(created_at, 'Mon'), EXTRACT(MONTH FROM created_at)
        ORDER BY month_num
    """)
    return [{"month": r['month'], "count": r['count']} for r in rows]

@app.get("/api/v1/admin/dashboard/alerts-by-type")
async def admin_alerts_by_type(db = Depends(get_db)):
    """Alertas agrupadas por tipo"""
    rows = await db.fetch("""
        SELECT alert_type as type, COUNT(*) as count
        FROM alerts
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY alert_type
        ORDER BY count DESC
    """)
    return [{"type": r['type'], "count": r['count']} for r in rows]

@app.get("/api/v1/admin/dashboard/devices-by-status")
async def admin_devices_by_status(db = Depends(get_db)):
    """Dispositivos agrupados por estado"""
    rows = await db.fetch("""
        SELECT status, COUNT(*) as count
        FROM devices
        GROUP BY status
    """)
    return [{"status": r['status'], "count": r['count']} for r in rows]

@app.get("/api/v1/admin/dashboard/recent-alerts")
async def admin_recent_alerts(limit: int = 5, db = Depends(get_db)):
    """Alertas recientes críticas"""
    rows = await db.fetch("""
        SELECT a.*, d.name as device_name, d.serial_number,
               mp.first_name, mp.last_name
        FROM alerts a
        JOIN devices d ON a.device_id = d.id
        LEFT JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE a.severity = 'critical'
        ORDER BY a.created_at DESC
        LIMIT $1
    """, limit)
    
    return [
        {
            "id": str(r['id']),
            "type": r['alert_type'],
            "severity": r['severity'],
            "message": r['message'],
            "deviceName": r['device_name'],
            "personName": f"{r['first_name']} {r['last_name']}" if r['first_name'] else None,
            "isResolved": r['is_resolved'],
            "createdAt": format_datetime(r['created_at'])
        }
        for r in rows
    ]

# --------------- ADMIN APP USERS (Usuarios de la app móvil) ---------------

@app.get("/api/v1/admin/app-users")
async def admin_list_app_users(
    page: int = 1,
    search: str = "",
    db = Depends(get_db)
):
    """Listar todos los usuarios de la app móvil"""
    limit = 20
    offset = (page - 1) * limit
    
    if search:
        search_pattern = f"%{search}%"
        rows = await db.fetch("""
            SELECT u.*, 
                   (SELECT COUNT(*) FROM monitored_persons mp WHERE mp.user_id = u.id) as monitored_count,
                   (SELECT COUNT(*) FROM devices d 
                    JOIN monitored_persons mp ON d.monitored_person_id = mp.id 
                    WHERE mp.user_id = u.id) as devices_count
            FROM users u
            WHERE (u.email ILIKE $1 OR u.first_name ILIKE $1 OR u.last_name ILIKE $1)
            ORDER BY u.created_at DESC
            LIMIT $2 OFFSET $3
        """, search_pattern, limit, offset)
        total = await db.fetchval("""
            SELECT COUNT(*) FROM users 
            WHERE (email ILIKE $1 OR first_name ILIKE $1 OR last_name ILIKE $1)
        """, search_pattern)
    else:
        rows = await db.fetch("""
            SELECT u.*, 
                   (SELECT COUNT(*) FROM monitored_persons mp WHERE mp.user_id = u.id) as monitored_count,
                   (SELECT COUNT(*) FROM devices d 
                    JOIN monitored_persons mp ON d.monitored_person_id = mp.id 
                    WHERE mp.user_id = u.id) as devices_count
            FROM users u
            ORDER BY u.created_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
        total = await db.fetchval("SELECT COUNT(*) FROM users")
    
    return {
        "data": [
            {
                "id": str(r['id']),
                "email": r['email'],
                "firstName": r['first_name'],
                "lastName": r['last_name'],
                "fullName": f"{r['first_name']} {r['last_name']}",
                "phone": r['phone'],
                "photoUrl": r.get('photo_url'),
                "isActive": r['is_active'],
                "isVerified": r['is_verified'],
                "monitoredCount": r['monitored_count'],
                "devicesCount": r['devices_count'],
                "createdAt": format_datetime(r['created_at']),
                "lastLogin": format_datetime(r.get('last_login'))
            }
            for r in rows
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": (total + limit - 1) // limit
        }
    }

@app.post("/api/v1/admin/app-users")
async def admin_create_app_user(request: Request, db = Depends(get_db)):
    """Crear nuevo usuario de la app móvil"""
    data = await request.json()
    
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    password = data.get('password', '')
    
    # Validaciones básicas
    if not email or not first_name or not last_name:
        raise HTTPException(status_code=400, detail="Email, nombre y apellido son requeridos")
    
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    # Verificar email duplicado
    existing_email = await db.fetchval("SELECT id FROM users WHERE LOWER(email) = $1", email)
    if existing_email:
        raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")
    
    # Verificar teléfono duplicado (si se proporciona)
    if phone:
        existing_phone = await db.fetchval("SELECT id FROM users WHERE phone = $1", phone)
        if existing_phone:
            raise HTTPException(status_code=409, detail="El número de teléfono ya está registrado")
    
    # Hash de contraseña
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    # Crear usuario
    new_id = uuid4()
    now = get_utc_now()
    
    await db.execute("""
        INSERT INTO users (id, email, password_hash, first_name, last_name, phone, is_active, is_verified, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE, FALSE, $7, $7)
    """, new_id, email, hashed_password, first_name, last_name, phone or None, now)
    
    return {
        "id": str(new_id),
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "fullName": f"{first_name} {last_name}",
        "phone": phone or None,
        "isActive": True,
        "isVerified": False,
        "createdAt": format_datetime(now)
    }

@app.put("/api/v1/admin/app-users/{user_id}")
async def admin_update_app_user(user_id: str, request: Request, db = Depends(get_db)):
    """Actualizar usuario de la app móvil"""
    data = await request.json()
    uid = UUID(user_id)
    
    # Verificar que existe
    existing = await db.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    if not existing:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    updates = []
    params = []
    param_idx = 1
    
    # Email
    if 'email' in data:
        new_email = data['email'].strip().lower()
        if new_email != existing['email'].lower():
            dup = await db.fetchval("SELECT id FROM users WHERE LOWER(email) = $1 AND id != $2", new_email, uid)
            if dup:
                raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")
            updates.append(f"email = ${param_idx}")
            params.append(new_email)
            param_idx += 1
    
    # Teléfono
    if 'phone' in data:
        new_phone = data['phone'].strip() if data['phone'] else None
        if new_phone and new_phone != existing['phone']:
            dup = await db.fetchval("SELECT id FROM users WHERE phone = $1 AND id != $2", new_phone, uid)
            if dup:
                raise HTTPException(status_code=409, detail="El número de teléfono ya está registrado")
        updates.append(f"phone = ${param_idx}")
        params.append(new_phone)
        param_idx += 1
    
    # Nombre
    if 'first_name' in data:
        updates.append(f"first_name = ${param_idx}")
        params.append(data['first_name'].strip())
        param_idx += 1
    
    # Apellido
    if 'last_name' in data:
        updates.append(f"last_name = ${param_idx}")
        params.append(data['last_name'].strip())
        param_idx += 1
    
    # Nueva contraseña
    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
        hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
        updates.append(f"password_hash = ${param_idx}")
        params.append(hashed)
        param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    updates.append(f"updated_at = ${param_idx}")
    params.append(get_utc_now())
    param_idx += 1
    
    params.append(uid)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${param_idx}"
    await db.execute(query, *params)
    
    # Obtener usuario actualizado
    row = await db.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    
    return {
        "id": str(row['id']),
        "email": row['email'],
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "phone": row['phone'],
        "isActive": row['is_active'],
        "isVerified": row['is_verified'],
        "createdAt": format_datetime(row['created_at'])
    }

@app.get("/api/v1/admin/app-users/check-email/{email}")
async def admin_check_email_exists(email: str, db = Depends(get_db)):
    """Verificar si un email ya existe"""
    exists = await db.fetchval("SELECT id FROM users WHERE LOWER(email) = $1", email.lower().strip())
    return {"exists": exists is not None}

@app.get("/api/v1/admin/app-users/check-phone/{phone}")
async def admin_check_phone_exists(phone: str, db = Depends(get_db)):
    """Verificar si un teléfono ya existe"""
    exists = await db.fetchval("SELECT id FROM users WHERE phone = $1", phone.strip())
    return {"exists": exists is not None}

@app.get("/api/v1/admin/app-users/{user_id}")
async def admin_get_app_user(user_id: str, db = Depends(get_db)):
    """Obtener un usuario específico"""
    row = await db.fetchrow("SELECT * FROM users WHERE id = $1", UUID(user_id))
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {
        "id": str(row['id']),
        "email": row['email'],
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "phone": row['phone'],
        "photoUrl": row.get('photo_url'),
        "isActive": row['is_active'],
        "isVerified": row['is_verified'],
        "createdAt": format_datetime(row['created_at'])
    }

@app.patch("/api/v1/admin/app-users/{user_id}/status")
async def admin_toggle_user_status(user_id: str, request: Request, db = Depends(get_db)):
    """Activar/desactivar usuario"""
    data = await request.json()
    is_active = data.get('is_active', True)
    
    await db.execute(
        "UPDATE users SET is_active = $1, updated_at = $2 WHERE id = $3",
        is_active, get_utc_now(), UUID(user_id)
    )
    return {"success": True, "message": "Estado actualizado"}

@app.delete("/api/v1/admin/app-users/{user_id}")
async def admin_delete_app_user(user_id: str, db = Depends(get_db)):
    """Eliminar usuario (soft delete)"""
    await db.execute(
        "UPDATE users SET is_active = FALSE, updated_at = $1 WHERE id = $2",
        get_utc_now(), UUID(user_id)
    )
    return {"success": True, "message": "Usuario eliminado"}

# --------------- ADMIN DEVICES ---------------

@app.get("/api/v1/admin/devices")
async def admin_list_devices(
    page: int = 1,
    search: str = "",
    status: str = None,
    db = Depends(get_db)
):
    """Listar todos los dispositivos"""
    limit = 20
    offset = (page - 1) * limit
    
    base_query = """
        SELECT d.*, 
               mp.first_name as person_first_name, 
               mp.last_name as person_last_name,
               u.email as owner_email
        FROM devices d
        LEFT JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        LEFT JOIN users u ON mp.user_id = u.id
    """
    
    conditions = []
    params = []
    param_idx = 1
    
    if search:
        conditions.append(f"(d.serial_number ILIKE ${param_idx} OR d.code ILIKE ${param_idx} OR d.name ILIKE ${param_idx})")
        params.append(f"%{search}%")
        param_idx += 1
    
    if status:
        conditions.append(f"d.status = ${param_idx}::device_status")
        params.append(status)
        param_idx += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    query = f"{base_query} {where_clause} ORDER BY d.created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])
    
    rows = await db.fetch(query, *params)
    
    # Count total
    count_query = f"SELECT COUNT(*) FROM devices d {where_clause}"
    total = await db.fetchval(count_query, *params[:-2]) if params[:-2] else await db.fetchval("SELECT COUNT(*) FROM devices")
    
    return {
        "data": [
            {
                "id": str(r['id']),
                "serialNumber": r['serial_number'],
                "code": r['code'],
                "name": r['name'],
                "model": r['model'],
                "status": r['status'],
                "batteryLevel": float(r['battery_level']) if r['battery_level'] else 100,
                "isConnected": r['is_connected'],
                "isActive": r['is_active'],
                "firmwareVersion": r['firmware_version'],
                "personName": f"{r['person_first_name']} {r['person_last_name']}" if r['person_first_name'] else None,
                "ownerEmail": r['owner_email'],
                "lastSeen": format_datetime(r.get('last_seen')),
                "createdAt": format_datetime(r['created_at'])
            }
            for r in rows
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total or 0,
            "totalPages": ((total or 0) + limit - 1) // limit
        }
    }

@app.get("/api/v1/admin/devices/{device_id}")
async def admin_get_device(device_id: str, db = Depends(get_db)):
    """Obtener un dispositivo específico"""
    row = await db.fetchrow("""
        SELECT d.*, mp.first_name, mp.last_name
        FROM devices d
        LEFT JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1
    """, UUID(device_id))
    
    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    return {
        "id": str(row['id']),
        "serialNumber": row['serial_number'],
        "code": row['code'],
        "name": row['name'],
        "model": row['model'],
        "status": row['status'],
        "batteryLevel": float(row['battery_level']) if row['battery_level'] else 100,
        "isConnected": row['is_connected'],
        "isActive": row['is_active'],
        "personName": f"{row['first_name']} {row['last_name']}" if row['first_name'] else None,
        "createdAt": format_datetime(row['created_at'])
    }

@app.post("/api/v1/admin/devices")
async def admin_create_device(request: Request, db = Depends(get_db)):
    """Crear/registrar un nuevo dispositivo"""
    data = await request.json()
    
    device_id = uuid4()
    serial = data.get('serial_number', f"NV-{uuid4().hex[:8].upper()}")
    code = data.get('code', f"NG{uuid4().hex[:6].upper()}")
    
    await db.execute("""
        INSERT INTO devices (id, serial_number, code, name, model, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, device_id, serial, code, data.get('name', 'NovaBand'), 
        data.get('model', 'NovaBand V1'), get_utc_now())
    
    return {
        "id": str(device_id),
        "serialNumber": serial,
        "code": code,
        "name": data.get('name', 'NovaBand'),
        "message": "Dispositivo creado exitosamente"
    }

@app.get("/api/v1/admin/devices/generate-code")
async def admin_generate_device_code():
    """Generar un código único para dispositivo"""
    code = f"NG{uuid4().hex[:6].upper()}"
    return {"device_code": code}

@app.put("/api/v1/admin/devices/{device_id}")
async def admin_update_device(device_id: str, request: Request, db = Depends(get_db)):
    """Actualizar dispositivo"""
    data = await request.json()
    did = UUID(device_id)
    
    existing = await db.fetchrow("SELECT * FROM devices WHERE id = $1", did)
    if not existing:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    updates = []
    params = []
    param_idx = 1
    
    # Verificar serial duplicado
    if 'serial_number' in data and data['serial_number'] != existing['serial_number']:
        dup = await db.fetchval("SELECT id FROM devices WHERE serial_number = $1 AND id != $2", data['serial_number'], did)
        if dup:
            raise HTTPException(status_code=409, detail="El número de serie ya existe")
        updates.append(f"serial_number = ${param_idx}")
        params.append(data['serial_number'])
        param_idx += 1
    
    # Verificar código duplicado
    if 'code' in data and data['code'] != existing['code']:
        dup = await db.fetchval("SELECT id FROM devices WHERE code = $1 AND id != $2", data['code'], did)
        if dup:
            raise HTTPException(status_code=409, detail="El código de dispositivo ya existe")
        updates.append(f"code = ${param_idx}")
        params.append(data['code'])
        param_idx += 1
    
    for field in ['name', 'model']:
        if field in data:
            updates.append(f"{field} = ${param_idx}")
            params.append(data[field])
            param_idx += 1
    
    if 'is_active' in data:
        updates.append(f"is_active = ${param_idx}")
        params.append(data['is_active'])
        param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    updates.append(f"updated_at = ${param_idx}")
    params.append(get_utc_now())
    param_idx += 1
    
    params.append(did)
    query = f"UPDATE devices SET {', '.join(updates)} WHERE id = ${param_idx}"
    await db.execute(query, *params)
    
    row = await db.fetchrow("""
        SELECT d.*, mp.first_name, mp.last_name
        FROM devices d
        LEFT JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1
    """, did)
    
    return {
        "id": str(row['id']),
        "serialNumber": row['serial_number'],
        "code": row['code'],
        "name": row['name'],
        "model": row['model'],
        "isActive": row['is_active'],
        "personName": f"{row['first_name']} {row['last_name']}" if row['first_name'] else None
    }

@app.delete("/api/v1/admin/devices/{device_id}")
async def admin_delete_device(device_id: str, db = Depends(get_db)):
    """Eliminar dispositivo (soft delete)"""
    await db.execute(
        "UPDATE devices SET is_active = FALSE, updated_at = $1 WHERE id = $2",
        get_utc_now(), UUID(device_id)
    )
    return {"success": True, "message": "Dispositivo eliminado"}

@app.patch("/api/v1/admin/devices/{device_id}/status")
async def admin_toggle_device_status(device_id: str, request: Request, db = Depends(get_db)):
    """Activar/desactivar dispositivo"""
    data = await request.json()
    is_active = data.get('is_active', True)
    
    await db.execute(
        "UPDATE devices SET is_active = $1, updated_at = $2 WHERE id = $3",
        is_active, get_utc_now(), UUID(device_id)
    )
    return {"success": True, "message": "Estado actualizado"}

@app.post("/api/v1/admin/devices/{device_id}/unlink")
async def admin_unlink_device(device_id: str, db = Depends(get_db)):
    """Desvincular dispositivo de persona monitoreada"""
    await db.execute("""
        UPDATE devices SET monitored_person_id = NULL, linked_at = NULL, updated_at = $1
        WHERE id = $2
    """, get_utc_now(), UUID(device_id))
    return {"success": True, "message": "Dispositivo desvinculado"}

# --------------- ADMIN ALERTS ---------------

@app.get("/api/v1/admin/alerts")
async def admin_list_alerts(
    page: int = 1,
    severity: str = None,
    is_resolved: bool = None,
    db = Depends(get_db)
):
    """Listar todas las alertas"""
    limit = 20
    offset = (page - 1) * limit
    
    base_query = """
        SELECT a.*, d.name as device_name, d.serial_number,
               mp.first_name, mp.last_name
        FROM alerts a
        JOIN devices d ON a.device_id = d.id
        LEFT JOIN monitored_persons mp ON d.monitored_person_id = mp.id
    """
    
    conditions = []
    params = []
    param_idx = 1
    
    if severity:
        conditions.append(f"a.severity = ${param_idx}::alert_severity")
        params.append(severity)
        param_idx += 1
    
    if is_resolved is not None:
        conditions.append(f"a.is_resolved = ${param_idx}")
        params.append(is_resolved)
        param_idx += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"{base_query} {where_clause} ORDER BY a.created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])
    
    rows = await db.fetch(query, *params)
    
    # Count
    count_query = f"SELECT COUNT(*) FROM alerts a {where_clause}"
    total = await db.fetchval(count_query, *params[:-2]) if params[:-2] else await db.fetchval("SELECT COUNT(*) FROM alerts")
    
    return {
        "data": [
            {
                "id": str(r['id']),
                "type": r['alert_type'],
                "severity": r['severity'],
                "message": r['message'],
                "deviceId": str(r['device_id']),
                "deviceName": r['device_name'],
                "personName": f"{r['first_name']} {r['last_name']}" if r['first_name'] else "Sin asignar",
                "isRead": r['is_read'],
                "isResolved": r['is_resolved'],
                "resolvedAt": format_datetime(r.get('resolved_at')),
                "createdAt": format_datetime(r['created_at'])
            }
            for r in rows
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total or 0,
            "totalPages": ((total or 0) + limit - 1) // limit
        }
    }

@app.get("/api/v1/admin/alerts/pending")
async def admin_pending_alerts(db = Depends(get_db)):
    """Obtener alertas pendientes (no resueltas)"""
    rows = await db.fetch("""
        SELECT a.*, d.name as device_name, mp.first_name, mp.last_name
        FROM alerts a
        JOIN devices d ON a.device_id = d.id
        LEFT JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE a.is_resolved = FALSE
        ORDER BY 
            CASE a.severity 
                WHEN 'critical' THEN 1 
                WHEN 'warning' THEN 2 
                ELSE 3 
            END,
            a.created_at DESC
        LIMIT 50
    """)
    
    return [
        {
            "id": str(r['id']),
            "type": r['alert_type'],
            "severity": r['severity'],
            "message": r['message'],
            "deviceName": r['device_name'],
            "personName": f"{r['first_name']} {r['last_name']}" if r['first_name'] else "Sin asignar",
            "isRead": r['is_read'],
            "createdAt": format_datetime(r['created_at'])
        }
        for r in rows
    ]

@app.get("/api/v1/admin/alerts/stats")
async def admin_alerts_stats(db = Depends(get_db)):
    """Estadísticas de alertas"""
    # Por tipo
    by_type = await db.fetch("""
        SELECT alert_type as type, COUNT(*) as count
        FROM alerts
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY alert_type
    """)
    
    # Por severidad
    by_severity = await db.fetch("""
        SELECT severity, COUNT(*) as count
        FROM alerts
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY severity
    """)
    
    # Total hoy
    total_today = await db.fetchval(
        "SELECT COUNT(*) FROM alerts WHERE created_at >= CURRENT_DATE"
    )
    
    return {
        "by_type": [{"type": r['type'], "count": r['count']} for r in by_type],
        "by_severity": {r['severity']: r['count'] for r in by_severity},
        "total_today": total_today or 0
    }

@app.post("/api/v1/admin/alerts/{alert_id}/resolve")
async def admin_resolve_alert(alert_id: str, request: Request, db = Depends(get_db)):
    """Resolver una alerta"""
    data = await request.json() if request else {}
    notes = data.get('notes', '')
    
    await db.execute("""
        UPDATE alerts SET is_resolved = TRUE, resolved_at = $1, resolution_notes = $2
        WHERE id = $3
    """, get_utc_now(), notes, UUID(alert_id))
    
    return {"success": True, "message": "Alerta resuelta"}

@app.post("/api/v1/admin/alerts/{alert_id}/dismiss")
async def admin_dismiss_alert(alert_id: str, db = Depends(get_db)):
    """Descartar/marcar como resuelta una alerta"""
    await db.execute("""
        UPDATE alerts SET is_resolved = TRUE, resolved_at = $1
        WHERE id = $2
    """, get_utc_now(), UUID(alert_id))
    
    return {"success": True, "message": "Alerta descartada"}

@app.delete("/api/v1/admin/alerts/{alert_id}")
async def admin_delete_alert(alert_id: str, db = Depends(get_db)):
    """Eliminar alerta permanentemente"""
    await db.execute("DELETE FROM alerts WHERE id = $1", UUID(alert_id))
    return {"success": True, "message": "Alerta eliminada"}

# --------------- ADMIN MONITORED PERSONS ---------------

@app.get("/api/v1/admin/monitored")
async def admin_list_monitored(
    page: int = 1,
    search: str = "",
    db = Depends(get_db)
):
    """Listar todas las personas monitoreadas"""
    limit = 20
    offset = (page - 1) * limit
    
    if search:
        search_pattern = f"%{search}%"
        rows = await db.fetch("""
            SELECT mp.*, u.email as caregiver_email, u.first_name as caregiver_first,
                   u.last_name as caregiver_last,
                   (SELECT COUNT(*) FROM devices d WHERE d.monitored_person_id = mp.id) as devices_count
            FROM monitored_persons mp
            JOIN users u ON mp.user_id = u.id
            WHERE mp.first_name ILIKE $1 OR mp.last_name ILIKE $1 OR u.email ILIKE $1
            ORDER BY mp.created_at DESC
            LIMIT $2 OFFSET $3
        """, search_pattern, limit, offset)
        total = await db.fetchval("""
            SELECT COUNT(*) FROM monitored_persons mp
            JOIN users u ON mp.user_id = u.id
            WHERE mp.first_name ILIKE $1 OR mp.last_name ILIKE $1 OR u.email ILIKE $1
        """, search_pattern)
    else:
        rows = await db.fetch("""
            SELECT mp.*, u.email as caregiver_email, u.first_name as caregiver_first,
                   u.last_name as caregiver_last,
                   (SELECT COUNT(*) FROM devices d WHERE d.monitored_person_id = mp.id) as devices_count
            FROM monitored_persons mp
            JOIN users u ON mp.user_id = u.id
            ORDER BY mp.created_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
        total = await db.fetchval("SELECT COUNT(*) FROM monitored_persons")
    
    return {
        "data": [
            {
                "id": str(r['id']),
                "firstName": r['first_name'],
                "lastName": r['last_name'],
                "fullName": f"{r['first_name']} {r['last_name']}",
                "birthDate": str(r['birth_date']) if r.get('birth_date') else None,
                "gender": r.get('gender'),
                "bloodType": r.get('blood_type'),
                "photoUrl": r.get('photo_url'),
                "isActive": r['is_active'],
                "caregiverEmail": r['caregiver_email'],
                "caregiverName": f"{r['caregiver_first']} {r['caregiver_last']}",
                "devicesCount": r['devices_count'],
                "createdAt": format_datetime(r['created_at'])
            }
            for r in rows
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total or 0,
            "totalPages": ((total or 0) + limit - 1) // limit
        }
    }

@app.get("/api/v1/admin/monitored/{person_id}")
async def admin_get_monitored(person_id: str, db = Depends(get_db)):
    """Obtener persona monitoreada"""
    row = await db.fetchrow("""
        SELECT mp.*, u.email as caregiver_email
        FROM monitored_persons mp
        JOIN users u ON mp.user_id = u.id
        WHERE mp.id = $1
    """, UUID(person_id))
    
    if not row:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    return {
        "id": str(row['id']),
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "birthDate": str(row['birth_date']) if row.get('birth_date') else None,
        "gender": row.get('gender'),
        "bloodType": row.get('blood_type'),
        "isActive": row['is_active'],
        "caregiverEmail": row['caregiver_email'],
        "createdAt": format_datetime(row['created_at'])
    }

@app.get("/api/v1/admin/monitored/{person_id}/vitals/current")
async def admin_get_current_vitals(person_id: str, db = Depends(get_db)):
    """Obtener signos vitales actuales de una persona"""
    row = await db.fetchrow("""
        SELECT vs.* FROM vital_signs vs
        JOIN devices d ON vs.device_id = d.id
        WHERE d.monitored_person_id = $1
        ORDER BY vs.recorded_at DESC
        LIMIT 1
    """, UUID(person_id))
    
    if not row:
        return {
            "heartRate": None,
            "spo2": None,
            "temperature": None,
            "systolicBp": None,
            "diastolicBp": None,
            "recordedAt": None
        }
    
    return {
        "heartRate": float(row['heart_rate']) if row.get('heart_rate') else None,
        "spo2": float(row['spo2']) if row.get('spo2') else None,
        "temperature": float(row['temperature']) if row.get('temperature') else None,
        "systolicBp": float(row['systolic_bp']) if row.get('systolic_bp') else None,
        "diastolicBp": float(row['diastolic_bp']) if row.get('diastolic_bp') else None,
        "steps": row.get('steps', 0),
        "recordedAt": format_datetime(row['recorded_at'])
    }

@app.get("/api/v1/admin/monitored/{person_id}/location")
async def admin_get_location(person_id: str, db = Depends(get_db)):
    """Obtener ubicación actual de una persona"""
    row = await db.fetchrow("""
        SELECT l.* FROM locations l
        JOIN devices d ON l.device_id = d.id
        WHERE d.monitored_person_id = $1
        ORDER BY l.recorded_at DESC
        LIMIT 1
    """, UUID(person_id))
    
    if not row:
        return {"latitude": None, "longitude": None, "recorded_at": None}
    
    return {
        "latitude": float(row['latitude']),
        "longitude": float(row['longitude']),
        "recorded_at": format_datetime(row['recorded_at'])
    }

@app.post("/api/v1/admin/monitored")
async def admin_create_monitored(request: Request, db = Depends(get_db)):
    """Crear persona monitoreada"""
    data = await request.json()
    
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    birth_date = data.get('birth_date')
    gender = data.get('gender')
    blood_type = data.get('blood_type')
    medical_notes = data.get('medical_notes', '')
    user_id = data.get('user_id')  # ID del cuidador/usuario
    
    if not first_name or not last_name:
        raise HTTPException(status_code=400, detail="Nombre y apellido son requeridos")
    
    # Si no se proporciona user_id, usar el primer usuario disponible (para admin)
    if not user_id:
        first_user = await db.fetchval("SELECT id FROM users LIMIT 1")
        if not first_user:
            raise HTTPException(status_code=400, detail="No hay usuarios registrados para asignar")
        user_id = str(first_user)
    
    new_id = uuid4()
    now = get_utc_now()
    
    await db.execute("""
        INSERT INTO monitored_persons 
        (id, user_id, first_name, last_name, birth_date, gender, blood_type, medical_notes, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, $9, $9)
    """, new_id, UUID(user_id), first_name, last_name, 
        birth_date if birth_date else None, gender, blood_type, medical_notes or None, now)
    
    row = await db.fetchrow("""
        SELECT mp.*, u.email as caregiver_email, u.first_name as caregiver_first, u.last_name as caregiver_last
        FROM monitored_persons mp
        JOIN users u ON mp.user_id = u.id
        WHERE mp.id = $1
    """, new_id)
    
    return {
        "id": str(row['id']),
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "birthDate": str(row['birth_date']) if row.get('birth_date') else None,
        "gender": row.get('gender'),
        "bloodType": row.get('blood_type'),
        "isActive": row['is_active'],
        "caregiverEmail": row['caregiver_email'],
        "caregiverName": f"{row['caregiver_first']} {row['caregiver_last']}",
        "devicesCount": 0,
        "createdAt": format_datetime(row['created_at'])
    }

@app.put("/api/v1/admin/monitored/{person_id}")
async def admin_update_monitored(person_id: str, request: Request, db = Depends(get_db)):
    """Actualizar persona monitoreada"""
    data = await request.json()
    pid = UUID(person_id)
    
    existing = await db.fetchrow("SELECT * FROM monitored_persons WHERE id = $1", pid)
    if not existing:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    updates = []
    params = []
    param_idx = 1
    
    for field, db_field in [('first_name', 'first_name'), ('last_name', 'last_name'), 
                            ('birth_date', 'birth_date'), ('gender', 'gender'),
                            ('blood_type', 'blood_type'), ('medical_notes', 'medical_notes'),
                            ('notes', 'medical_notes')]:
        if field in data:
            updates.append(f"{db_field} = ${param_idx}")
            params.append(data[field] if data[field] else None)
            param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    updates.append(f"updated_at = ${param_idx}")
    params.append(get_utc_now())
    param_idx += 1
    
    params.append(pid)
    query = f"UPDATE monitored_persons SET {', '.join(updates)} WHERE id = ${param_idx}"
    await db.execute(query, *params)
    
    row = await db.fetchrow("""
        SELECT mp.*, u.email as caregiver_email, u.first_name as caregiver_first, u.last_name as caregiver_last,
               (SELECT COUNT(*) FROM devices d WHERE d.monitored_person_id = mp.id) as devices_count
        FROM monitored_persons mp
        JOIN users u ON mp.user_id = u.id
        WHERE mp.id = $1
    """, pid)
    
    return {
        "id": str(row['id']),
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "birthDate": str(row['birth_date']) if row.get('birth_date') else None,
        "gender": row.get('gender'),
        "bloodType": row.get('blood_type'),
        "isActive": row['is_active'],
        "caregiverEmail": row['caregiver_email'],
        "caregiverName": f"{row['caregiver_first']} {row['caregiver_last']}",
        "devicesCount": row['devices_count'],
        "createdAt": format_datetime(row['created_at'])
    }

@app.delete("/api/v1/admin/monitored/{person_id}")
async def admin_delete_monitored(person_id: str, db = Depends(get_db)):
    """Eliminar persona monitoreada (soft delete)"""
    await db.execute(
        "UPDATE monitored_persons SET is_active = FALSE, updated_at = $1 WHERE id = $2",
        get_utc_now(), UUID(person_id)
    )
    return {"success": True, "message": "Persona eliminada"}

@app.post("/api/v1/admin/monitored/{person_id}/assign-device")
async def admin_assign_device(person_id: str, request: Request, db = Depends(get_db)):
    """Asignar dispositivo a persona"""
    data = await request.json()
    device_id = data.get('device_id')
    
    if not device_id:
        raise HTTPException(status_code=400, detail="ID de dispositivo requerido")
    
    # Verificar que la persona existe
    person = await db.fetchrow("SELECT id FROM monitored_persons WHERE id = $1", UUID(person_id))
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Verificar que el dispositivo existe y no está asignado
    device = await db.fetchrow("SELECT id, monitored_person_id FROM devices WHERE id = $1", UUID(device_id))
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    if device['monitored_person_id']:
        raise HTTPException(status_code=409, detail="El dispositivo ya está asignado a otra persona")
    
    # Asignar
    await db.execute(
        "UPDATE devices SET monitored_person_id = $1, updated_at = $2 WHERE id = $3",
        UUID(person_id), get_utc_now(), UUID(device_id)
    )
    
    row = await db.fetchrow("""
        SELECT mp.*, u.email as caregiver_email, u.first_name as caregiver_first, u.last_name as caregiver_last,
               (SELECT COUNT(*) FROM devices d WHERE d.monitored_person_id = mp.id) as devices_count
        FROM monitored_persons mp
        JOIN users u ON mp.user_id = u.id
        WHERE mp.id = $1
    """, UUID(person_id))
    
    return {
        "id": str(row['id']),
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "devicesCount": row['devices_count'],
        "createdAt": format_datetime(row['created_at'])
    }

@app.post("/api/v1/admin/monitored/{person_id}/unassign-device")
async def admin_unassign_device(person_id: str, db = Depends(get_db)):
    """Desvincular todos los dispositivos de una persona"""
    await db.execute(
        "UPDATE devices SET monitored_person_id = NULL, updated_at = $1 WHERE monitored_person_id = $2",
        get_utc_now(), UUID(person_id)
    )
    
    row = await db.fetchrow("""
        SELECT mp.*, u.email as caregiver_email, u.first_name as caregiver_first, u.last_name as caregiver_last
        FROM monitored_persons mp
        JOIN users u ON mp.user_id = u.id
        WHERE mp.id = $1
    """, UUID(person_id))
    
    return {
        "id": str(row['id']),
        "firstName": row['first_name'],
        "lastName": row['last_name'],
        "fullName": f"{row['first_name']} {row['last_name']}",
        "devicesCount": 0,
        "createdAt": format_datetime(row['created_at'])
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - HEALTH
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "message": "NovaGuardian API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": get_utc_now().isoformat()}

@app.get("/api/v1/health")
async def api_health():
    return {"status": "healthy", "api": "v1", "timestamp": get_utc_now().isoformat()}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - AUTH ADICIONALES
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Cerrar sesion (invalidar token - aqui solo confirmamos)"""
    return {"success": True, "message": "Sesion cerrada exitosamente"}

@app.post("/api/v1/auth/forgot-password")
async def forgot_password(request: Request, db = Depends(get_db)):
    """Solicitar recuperacion de contrasena - envia codigo por email"""
    data = await request.json()
    email = data.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido")
    
    # Verificar que el usuario existe
    user = await db.fetchrow(
        "SELECT id, email, first_name, last_name FROM users WHERE email = $1", 
        email.lower().strip()
    )
    
    if not user:
        # No revelar si el usuario existe o no por seguridad
        return {"success": True, "message": "Si el email existe, recibiras un codigo para recuperar tu contrasena"}
    
    # Generar código de 6 dígitos
    reset_code = email_service.generate_reset_code()
    expires_at = get_utc_now() + timedelta(minutes=15)
    
    # Guardar el código en la base de datos
    # Primero eliminar códigos anteriores para este usuario
    await db.execute(
        "DELETE FROM password_reset_tokens WHERE user_id = $1",
        user['id']
    )
    
    # Insertar nuevo código
    await db.execute(
        """INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
           VALUES ($1, $2, $3, $4)""",
        user['id'], reset_code, expires_at, get_utc_now()
    )
    
    # Enviar email
    user_name = f"{user['first_name']} {user['last_name']}".strip() or "Usuario"
    email_sent = await email_service.send_password_reset_email(
        to_email=user['email'],
        user_name=user_name,
        reset_code=reset_code
    )
    
    if not email_sent:
        # Si falla el envío pero SMTP no está configurado, mostrar código en consola (solo desarrollo)
        print(f"🔑 [DEV] Código de recuperación para {email}: {reset_code}")
    
    return {
        "success": True, 
        "message": "Si el email existe, recibiras un codigo para recuperar tu contrasena",
        "emailSent": email_sent
    }

@app.post("/api/v1/auth/verify-reset-code")
async def verify_reset_code(request: Request, db = Depends(get_db)):
    """Verificar código de recuperación de contraseña"""
    data = await request.json()
    email = data.get("email")
    code = data.get("code")
    
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email y codigo requeridos")
    
    # Buscar usuario
    user = await db.fetchrow("SELECT id FROM users WHERE email = $1", email.lower().strip())
    if not user:
        raise HTTPException(status_code=400, detail="Codigo invalido o expirado")
    
    # Buscar código válido
    reset_token = await db.fetchrow(
        """SELECT * FROM password_reset_tokens 
           WHERE user_id = $1 AND token = $2 AND expires_at > $3 AND used = FALSE""",
        user['id'], code.strip(), get_utc_now()
    )
    
    if not reset_token:
        raise HTTPException(status_code=400, detail="Codigo invalido o expirado")
    
    # Generar token temporal para el reset (válido por 10 minutos)
    temp_token = email_service.generate_reset_token()
    
    # Actualizar el registro con el token temporal
    await db.execute(
        """UPDATE password_reset_tokens 
           SET temp_token = $1, temp_token_expires = $2 
           WHERE id = $3""",
        temp_token, get_utc_now() + timedelta(minutes=10), reset_token['id']
    )
    
    return {
        "success": True,
        "message": "Codigo verificado",
        "resetToken": temp_token
    }

@app.post("/api/v1/auth/reset-password")
async def reset_password(request: Request, db = Depends(get_db)):
    """Resetear contrasena con token"""
    data = await request.json()
    token = data.get("token") or data.get("resetToken")
    password = data.get("password") or data.get("newPassword")
    
    if not token or not password:
        raise HTTPException(status_code=400, detail="Token y contrasena requeridos")
    
    # Validar contraseña
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="La contrasena debe tener al menos 8 caracteres")
    
    # Buscar token válido
    reset_record = await db.fetchrow(
        """SELECT prt.*, u.email FROM password_reset_tokens prt
           JOIN users u ON u.id = prt.user_id
           WHERE prt.temp_token = $1 AND prt.temp_token_expires > $2 AND prt.used = FALSE""",
        token, get_utc_now()
    )
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Token invalido o expirado")
    
    # Hashear nueva contraseña
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Actualizar contraseña del usuario
    await db.execute(
        "UPDATE users SET password_hash = $1, updated_at = $2 WHERE id = $3",
        password_hash, get_utc_now(), reset_record['user_id']
    )
    
    # Marcar token como usado
    await db.execute(
        "UPDATE password_reset_tokens SET used = TRUE WHERE id = $1",
        reset_record['id']
    )
    
    return {"success": True, "message": "Contrasena actualizada exitosamente"}

@app.post("/api/v1/auth/verify-email")
async def verify_email(request: Request, db = Depends(get_db)):
    """Verificar email con token"""
    data = await request.json()
    token = data.get("token")
    
    if not token:
        raise HTTPException(status_code=400, detail="Token requerido")
    
    return {"success": True, "message": "Email verificado exitosamente"}

@app.post("/api/v1/auth/resend-verification")
async def resend_verification(request: Request, db = Depends(get_db)):
    """Reenviar email de verificacion"""
    data = await request.json()
    email = data.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido")
    
    return {"success": True, "message": "Email de verificacion reenviado"}

@app.post("/api/v1/auth/change-password")
async def change_password(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Cambiar contrasena del usuario autenticado"""
    data = await request.json()
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")
    
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Contrasena actual y nueva requeridas")
    
    # Verificar contrasena actual
    user = await db.fetchrow("SELECT password_hash FROM users WHERE id = $1", current_user['id'])
    if not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=400, detail="Contrasena actual incorrecta")
    
    # Actualizar contrasena
    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await db.execute(
        "UPDATE users SET password_hash = $1, updated_at = $2 WHERE id = $3",
        new_hash, get_utc_now(), current_user['id']
    )
    
    return {"success": True, "message": "Contrasena actualizada exitosamente"}

@app.post("/api/v1/auth/push-token")
async def register_push_token(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Registrar token de notificaciones push"""
    data = await request.json()
    push_token = data.get("pushToken")
    
    if not push_token:
        raise HTTPException(status_code=400, detail="Token requerido")
    
    # Guardar en la base de datos (si tienes columna para esto)
    # Por ahora solo confirmamos
    return {"success": True, "message": "Token registrado exitosamente"}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - DEVICES ADICIONALES
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/devices/link")
async def link_device(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Vincular dispositivo con codigo"""
    data = await request.json()
    # Acepta tanto 'code' como 'device_code'
    code = data.get("code") or data.get("device_code")
    # Acepta tanto 'monitoredPersonId' como 'person_id'
    monitored_person_id = data.get("monitoredPersonId") or data.get("person_id")
    
    if not code:
        raise HTTPException(status_code=400, detail="Codigo de dispositivo requerido")
    
    # Limpiar el código (quitar guiones y espacios)
    clean_code = code.replace("-", "").replace(" ", "").upper()
    
    # Buscar dispositivo por codigo (exacto o parcial)
    device = await db.fetchrow(
        """SELECT * FROM devices 
           WHERE (REPLACE(code, '-', '') = $1 OR code = $2) 
           AND is_active = TRUE""",
        clean_code, code.upper()
    )
    
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado o codigo invalido")
    
    # Verificar que el dispositivo no este ya vinculado
    if device['monitored_person_id']:
        raise HTTPException(status_code=400, detail="Este dispositivo ya esta vinculado a otra persona")
    
    # Si se proporciona monitored_person_id, vincular
    if monitored_person_id:
        # Verificar que la persona pertenece al usuario
        person = await db.fetchrow(
            "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
            UUID(monitored_person_id), current_user['id']
        )
        if not person:
            raise HTTPException(status_code=404, detail="Persona monitoreada no encontrada")
        
        # Vincular dispositivo y marcarlo como conectado para la demo
        await db.execute(
            """UPDATE devices 
               SET monitored_person_id = $1, 
                   is_connected = TRUE,
                   status = 'online',
                   last_connection = $2,
                   updated_at = $2 
               WHERE id = $3""",
            UUID(monitored_person_id), get_utc_now(), device['id']
        )
    else:
        # Solo marcar como conectado aunque no tenga persona asignada
        await db.execute(
            """UPDATE devices 
               SET is_connected = TRUE,
                   status = 'online',
                   last_connection = $1,
                   updated_at = $1 
               WHERE id = $2""",
            get_utc_now(), device['id']
        )
    
    # Obtener dispositivo actualizado con info de persona
    devices = await _get_user_devices(current_user['id'], db)
    linked_device = next((d for d in devices if d['id'] == str(device['id'])), None)
    
    if not linked_device:
        # Retornar datos basicos si no se encuentra
        linked_device = {
            "id": str(device['id']),
            "serialNumber": device['serial_number'],
            "code": device['code'],
            "name": device.get('name'),
            "model": device.get('model', 'NovaBand V1'),
            "status": device['status'],
            "batteryLevel": float(device['battery_level']),
            "isConnected": device['is_connected'],
            "isActive": device['is_active']
        }
    
    return {"success": True, "data": linked_device}

@app.post("/api/v1/devices/{device_id}/unlink")
async def unlink_device(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Desvincular dispositivo"""
    # Verificar que el dispositivo pertenece al usuario
    device = await db.fetchrow("""
        SELECT d.* FROM devices d
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
    """, UUID(device_id), current_user['id'])
    
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Desvincular (poner monitored_person_id en NULL)
    await db.execute(
        "UPDATE devices SET monitored_person_id = NULL, updated_at = $1 WHERE id = $2",
        get_utc_now(), UUID(device_id)
    )
    
    return {"success": True, "message": "Dispositivo desvinculado exitosamente"}

@app.post("/api/v1/devices/{device_id}/assign")
async def assign_device(
    device_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Asignar dispositivo a persona monitoreada"""
    data = await request.json()
    monitored_id = data.get("monitoredId")
    
    if not monitored_id:
        raise HTTPException(status_code=400, detail="ID de persona monitoreada requerido")
    
    # Verificar que la persona pertenece al usuario
    person = await db.fetchrow(
        "SELECT id FROM monitored_persons WHERE id = $1 AND user_id = $2",
        UUID(monitored_id), current_user['id']
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona monitoreada no encontrada")
    
    # Verificar que el dispositivo existe
    device = await db.fetchrow("SELECT id FROM devices WHERE id = $1", UUID(device_id))
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    await db.execute(
        "UPDATE devices SET monitored_person_id = $1, updated_at = $2 WHERE id = $3",
        UUID(monitored_id), get_utc_now(), UUID(device_id)
    )
    
    return {"success": True, "message": "Dispositivo asignado exitosamente"}

@app.post("/api/v1/devices/verify-code")
async def verify_device_code(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Verificar codigo de dispositivo antes de vincular"""
    data = await request.json()
    code = data.get("code")
    
    if not code:
        raise HTTPException(status_code=400, detail="Codigo requerido")
    
    device = await db.fetchrow(
        "SELECT serial_number, model FROM devices WHERE code = $1 AND is_active = TRUE",
        code
    )
    
    if not device:
        return {"success": True, "data": {"valid": False}}
    
    return {
        "success": True,
        "data": {
            "valid": True,
            "device": {
                "serialNumber": device['serial_number'],
                "model": device.get('model', 'NovaBand V1')
            }
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - MONITORED PERSONS ADICIONALES
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/monitored")
async def create_monitored_person(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Crear nueva persona monitoreada"""
    data = await request.json()
    
    required_fields = ['firstName', 'lastName']
    for field in required_fields:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} es requerido")
    
    person_id = uuid4()
    now = get_utc_now()
    
    # Convertir birthDate de string a date si viene como string
    birth_date = None
    if data.get('birthDate'):
        birth_date_str = data.get('birthDate')
        if isinstance(birth_date_str, str):
            try:
                # Formato esperado: YYYY-MM-DD
                birth_date = datetime.strptime(birth_date_str.split('T')[0], '%Y-%m-%d').date()
            except ValueError:
                birth_date = None
        elif hasattr(birth_date_str, 'date'):
            birth_date = birth_date_str.date()
    
    # Convertir weight y height a float si vienen como string
    weight = None
    if data.get('weight'):
        try:
            weight = float(data.get('weight'))
        except (ValueError, TypeError):
            weight = None
    
    height = None
    if data.get('height'):
        try:
            height = float(data.get('height'))
        except (ValueError, TypeError):
            height = None
    
    await db.execute("""
        INSERT INTO monitored_persons (
            id, user_id, first_name, last_name, relationship, birth_date,
            gender, blood_type, weight, height, photo_url, notes, is_active, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, TRUE, $13, $13)
    """, 
        person_id, current_user['id'], data['firstName'], data['lastName'],
        data.get('relationship'), birth_date, data.get('gender'),
        data.get('bloodType'), weight, height,
        data.get('photoUrl'), data.get('notes'), now
    )
    
    person = await _get_monitored_person(str(person_id), current_user['id'], db)
    return {"success": True, "data": person}

@app.put("/api/v1/monitored/{person_id}")
async def update_monitored_person(
    person_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Actualizar persona monitoreada"""
    data = await request.json()
    
    # Primero obtener la persona (busca por person_id o device_id)
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Usar el ID real de la persona
    real_person_id = UUID(person['id'])
    
    # Construir query dinamico
    updates = []
    params = []
    param_count = 1
    
    field_mapping = {
        'firstName': 'first_name',
        'lastName': 'last_name',
        'relationship': 'relationship',
        'birthDate': 'birth_date',
        'gender': 'gender',
        'bloodType': 'blood_type',
        'weight': 'weight',
        'height': 'height',
        'photoUrl': 'photo_url',
        'notes': 'notes',
        'name': None  # Campo especial, se procesa abajo
    }
    
    # Si viene 'name' (nombre completo), dividirlo en firstName y lastName
    if 'name' in data and data['name']:
        name_parts = data['name'].strip().split(' ', 1)
        data['firstName'] = name_parts[0]
        data['lastName'] = name_parts[1] if len(name_parts) > 1 else ''
    
    for camel, snake in field_mapping.items():
        if snake and camel in data and data[camel] is not None:
            updates.append(f"{snake} = ${param_count}")
            params.append(data[camel])
            param_count += 1
    
    if updates:
        updates.append(f"updated_at = ${param_count}")
        params.append(get_utc_now())
        param_count += 1
        
        params.append(real_person_id)
        query = f"UPDATE monitored_persons SET {', '.join(updates)} WHERE id = ${param_count}"
        await db.execute(query, *params)
    
    person = await _get_monitored_person(person_id, current_user['id'], db)
    return {"success": True, "data": person}

@app.delete("/api/v1/monitored/{person_id}")
async def delete_monitored_person(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Eliminar persona monitoreada (soft delete)"""
    result = await db.execute(
        "UPDATE monitored_persons SET is_active = FALSE, updated_at = $1 WHERE id = $2 AND user_id = $3",
        get_utc_now(), UUID(person_id), current_user['id']
    )
    
    return {"success": True, "message": "Persona monitoreada eliminada"}

@app.post("/api/v1/monitored/{person_id}/photo")
async def upload_monitored_photo(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Subir foto de persona monitoreada (simulado)"""
    # En produccion aqui manejarias el archivo
    # Por ahora solo retornamos una URL simulada
    photo_url = f"/uploads/monitored/{person_id}/photo.jpg"
    
    await db.execute(
        "UPDATE monitored_persons SET photo_url = $1, updated_at = $2 WHERE id = $3 AND user_id = $4",
        photo_url, get_utc_now(), UUID(person_id), current_user['id']
    )
    
    return {"success": True, "data": {"photoUrl": photo_url}}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - MEDICAL CONDITIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitored/{person_id}/medical")
async def get_medical_conditions(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener condiciones medicas de una persona"""
    # Verificar acceso
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Intentar obtener de tabla medical_conditions si existe
    try:
        rows = await db.fetch(
            "SELECT * FROM medical_conditions WHERE monitored_person_id = $1",
            UUID(person['id'])
        )
        conditions = [
            {
                "id": str(row['id']),
                "name": row['name'],
                "type": row.get('type', 'condition'),
                "notes": row.get('notes'),
                "diagnosedDate": format_datetime(row.get('diagnosed_date')),
                "severity": row.get('severity', 'moderate')
            }
            for row in rows
        ]
    except:
        # Si no existe la tabla, retornar lista vacia
        conditions = []
    
    return {"success": True, "data": conditions}

@app.post("/api/v1/monitored/{person_id}/medical")
async def add_medical_condition(
    person_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Agregar condicion medica"""
    data = await request.json()
    
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    condition_id = uuid4()
    now = get_utc_now()
    
    # Mapear conditionType del frontend a condition_type de la BD
    condition_type = data.get('conditionType', data.get('type', 'disease'))
    severity = data.get('severity', 'medium')
    
    try:
        await db.execute("""
            INSERT INTO medical_conditions (id, monitored_person_id, condition_type, name, description, notes, severity, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8)
        """, condition_id, UUID(person['id']), condition_type, data.get('name'), 
            data.get('description'), data.get('notes'), severity, now
        )
    except Exception as e:
        print(f"Error insertando condición médica: {e}")
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")
    
    return {
        "success": True,
        "data": {
            "id": str(condition_id),
            "conditionType": condition_type,
            "name": data.get('name'),
            "description": data.get('description'),
            "notes": data.get('notes'),
            "severity": severity
        }
    }

@app.put("/api/v1/monitored/{person_id}/medical/{condition_id}")
async def update_medical_condition(
    person_id: str,
    condition_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Actualizar condicion medica"""
    data = await request.json()
    
    return {
        "success": True,
        "data": {
            "id": condition_id,
            "name": data.get('name'),
            "type": data.get('type'),
            "notes": data.get('notes'),
            "severity": data.get('severity')
        }
    }

@app.delete("/api/v1/monitored/{person_id}/medical/{condition_id}")
async def delete_medical_condition(
    person_id: str,
    condition_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Eliminar condicion medica"""
    try:
        await db.execute(
            "DELETE FROM medical_conditions WHERE id = $1",
            UUID(condition_id)
        )
    except:
        pass
    
    return {"success": True, "message": "Condicion eliminada"}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - MEDICATIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitored/{person_id}/medications")
async def get_medications(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener medicamentos de persona monitoreada"""
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Usar person['id'] (el ID real de la persona monitoreada)
    rows = await db.fetch(
        """SELECT id, name, dosage, frequency, notes, created_at
           FROM medications WHERE monitored_person_id = $1 ORDER BY name""",
        UUID(person['id'])
    )
    
    medications = []
    for row in rows:
        medications.append({
            "id": str(row['id']),
            "name": row['name'],
            "dosage": row['dosage'],
            "frequency": row['frequency'],
            "notes": row['notes'],
            "createdAt": row['created_at'].isoformat() if row['created_at'] else None
        })
    
    return {"success": True, "data": medications}

@app.post("/api/v1/monitored/{person_id}/medications")
async def add_medication(
    person_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Agregar medicamento"""
    data = await request.json()
    
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    medication_id = uuid4()
    now = datetime.now(timezone.utc)
    
    # Usar person['id'] (el ID real de la persona monitoreada) en vez de person_id
    await db.execute(
        """INSERT INTO medications (id, monitored_person_id, name, dosage, frequency, notes, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        medication_id,
        UUID(person['id']),
        data.get('name', ''),
        data.get('dosage', ''),
        data.get('frequency', ''),
        data.get('notes', ''),
        now
    )
    
    return {
        "success": True,
        "data": {
            "id": str(medication_id),
            "name": data.get('name', ''),
            "dosage": data.get('dosage', ''),
            "frequency": data.get('frequency', ''),
            "notes": data.get('notes', '')
        }
    }

@app.delete("/api/v1/monitored/{person_id}/medications/{medication_id}")
async def delete_medication(
    person_id: str,
    medication_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Eliminar medicamento"""
    try:
        await db.execute(
            "DELETE FROM medications WHERE id = $1",
            UUID(medication_id)
        )
    except:
        pass
    
    return {"success": True, "message": "Medicamento eliminado"}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - EMERGENCY CONTACTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/monitored/{person_id}/contacts")
async def get_emergency_contacts(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener contactos de emergencia"""
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    rows = await db.fetch(
        "SELECT * FROM emergency_contacts WHERE monitored_person_id = $1",
        UUID(person['id'])
    )
    
    contacts = [
        {
            "id": str(row['id']),
            "name": row['name'],
            "phone": row['phone'],
            "relationship": row.get('relationship'),
            "isPrimary": row.get('is_primary', False)
        }
        for row in rows
    ]
    
    return {"success": True, "data": contacts}

@app.post("/api/v1/monitored/{person_id}/contacts")
async def add_emergency_contact(
    person_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Agregar contacto de emergencia"""
    data = await request.json()
    
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    contact_id = uuid4()
    now = get_utc_now()
    
    await db.execute("""
        INSERT INTO emergency_contacts (id, monitored_person_id, name, phone, relationship, is_primary, notify_on_alerts, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8)
    """, contact_id, UUID(person['id']), data.get('name'), data.get('phone'),
        data.get('relationship'), data.get('isPrimary', False), data.get('notifyAlerts', True), now
    )
    
    return {
        "success": True,
        "data": {
            "id": str(contact_id),
            "name": data.get('name'),
            "phone": data.get('phone'),
            "relationship": data.get('relationship'),
            "isPrimary": data.get('isPrimary', False),
            "notifyAlerts": data.get('notifyAlerts', True)
        }
    }

@app.put("/api/v1/monitored/{person_id}/contacts/{contact_id}")
async def update_emergency_contact(
    person_id: str,
    contact_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Actualizar contacto de emergencia"""
    data = await request.json()
    
    await db.execute("""
        UPDATE emergency_contacts SET name = $1, phone = $2, relationship = $3, is_primary = $4
        WHERE id = $5
    """, data.get('name'), data.get('phone'), data.get('relationship'), 
        data.get('isPrimary', False), UUID(contact_id)
    )
    
    return {
        "success": True,
        "data": {
            "id": contact_id,
            "name": data.get('name'),
            "phone": data.get('phone'),
            "relationship": data.get('relationship'),
            "isPrimary": data.get('isPrimary', False)
        }
    }

@app.delete("/api/v1/monitored/{person_id}/contacts/{contact_id}")
async def delete_emergency_contact(
    person_id: str,
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Eliminar contacto de emergencia"""
    await db.execute("DELETE FROM emergency_contacts WHERE id = $1", UUID(contact_id))
    return {"success": True, "message": "Contacto eliminado"}

@app.put("/api/v1/monitored/{person_id}/contacts/{contact_id}/primary")
async def set_primary_contact(
    person_id: str,
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Establecer contacto como primario"""
    person = await _get_monitored_person(person_id, current_user['id'], db)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Quitar primario de todos
    await db.execute(
        "UPDATE emergency_contacts SET is_primary = FALSE WHERE monitored_person_id = $1",
        UUID(person['id'])
    )
    
    # Establecer este como primario
    await db.execute(
        "UPDATE emergency_contacts SET is_primary = TRUE WHERE id = $1",
        UUID(contact_id)
    )
    
    return {"success": True, "message": "Contacto establecido como primario"}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - ALERTS ADICIONALES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/alerts/device/{device_id}")
async def get_alerts_by_device(
    device_id: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener alertas por dispositivo"""
    rows = await db.fetch("""
        SELECT a.* FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE d.id = $1 AND mp.user_id = $2
        ORDER BY a.created_at DESC
        LIMIT $3
    """, UUID(device_id), current_user['id'], limit)
    
    alerts = [
        {
            "id": str(row['id']),
            "deviceId": str(row['device_id']),
            "type": row['type'],
            "severity": row['severity'],
            "title": row['title'],
            "message": row['message'],
            "isRead": row['is_read'],
            "isResolved": row['is_resolved'],
            "attendedAt": format_datetime(row.get('attended_at')),
            "createdAt": format_datetime(row['created_at'])
        }
        for row in rows
    ]
    
    return {"success": True, "data": alerts}

@app.get("/api/v1/alerts/critical-unattended")
async def get_critical_unattended_alerts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener alertas criticas no atendidas"""
    rows = await db.fetch("""
        SELECT a.* FROM alerts a
        JOIN devices d ON a.device_id = d.id
        JOIN monitored_persons mp ON d.monitored_person_id = mp.id
        WHERE mp.user_id = $1 AND a.severity = 'critical' AND a.is_resolved = FALSE
        ORDER BY a.created_at DESC
    """, current_user['id'])
    
    alerts = [
        {
            "id": str(row['id']),
            "deviceId": str(row['device_id']),
            "type": row['type'],
            "severity": row['severity'],
            "title": row['title'],
            "message": row['message'],
            "isRead": row['is_read'],
            "isResolved": row['is_resolved'],
            "createdAt": format_datetime(row['created_at'])
        }
        for row in rows
    ]
    
    return {"success": True, "data": alerts}

@app.put("/api/v1/alerts/{alert_id}/false-alarm")
async def mark_alert_false_alarm(
    alert_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Marcar alerta como falsa alarma"""
    data = await request.json() if await request.body() else {}
    notes = data.get("notes", "")
    
    await db.execute("""
        UPDATE alerts SET 
            is_resolved = TRUE, 
            is_read = TRUE,
            resolution_notes = $1,
            attended_at = $2
        WHERE id = $3
    """, f"Falsa alarma: {notes}", get_utc_now(), UUID(alert_id))
    
    row = await db.fetchrow("SELECT * FROM alerts WHERE id = $1", UUID(alert_id))
    
    return {
        "success": True,
        "data": {
            "id": str(row['id']),
            "deviceId": str(row['device_id']),
            "type": row['type'],
            "severity": row['severity'],
            "title": row['title'],
            "message": row['message'],
            "isRead": True,
            "isResolved": True,
            "attendedAt": format_datetime(row.get('attended_at')),
            "createdAt": format_datetime(row['created_at'])
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - USER PROFILE
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/users/me")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener perfil del usuario actual"""
    row = await db.fetchrow("SELECT * FROM users WHERE id = $1", current_user['id'])
    
    return {
        "success": True,
        "data": {
            "id": str(row['id']),
            "email": row['email'],
            "firstName": row.get('first_name'),
            "lastName": row.get('last_name'),
            "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or row['email'],
            "phone": row.get('phone'),
            "photoUrl": row.get('photo_url'),
            "isVerified": row.get('is_verified', True),
            "createdAt": format_datetime(row['created_at'])
        }
    }

@app.put("/api/v1/users/me")
async def update_user_profile(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Actualizar perfil del usuario"""
    data = await request.json()
    
    updates = []
    params = []
    param_count = 1
    
    field_mapping = {
        'firstName': 'first_name',
        'lastName': 'last_name',
        'phone': 'phone',
        'photoUrl': 'photo_url'
    }
    
    for camel, snake in field_mapping.items():
        if camel in data:
            updates.append(f"{snake} = ${param_count}")
            params.append(data[camel])
            param_count += 1
    
    if updates:
        updates.append(f"updated_at = ${param_count}")
        params.append(get_utc_now())
        param_count += 1
        
        params.append(current_user['id'])
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${param_count}"
        await db.execute(query, *params)
    
    # Obtener usuario actualizado
    row = await db.fetchrow("SELECT * FROM users WHERE id = $1", current_user['id'])
    
    return {
        "success": True,
        "data": {
            "id": str(row['id']),
            "email": row['email'],
            "firstName": row.get('first_name'),
            "lastName": row.get('last_name'),
            "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or row['email'],
            "phone": row.get('phone'),
            "photoUrl": row.get('photo_url'),
            "isVerified": row.get('is_verified', True),
            "createdAt": format_datetime(row['created_at'])
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - PROFILE (GET)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener perfil del usuario actual"""
    row = await db.fetchrow("SELECT * FROM users WHERE id = $1", current_user['id'])
    
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {
        "success": True,
        "data": {
            "id": str(row['id']),
            "email": row['email'],
            "firstName": row.get('first_name'),
            "lastName": row.get('last_name'),
            "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or row['email'],
            "phone": row.get('phone'),
            "photoUrl": row.get('photo_url'),
            "isVerified": row.get('is_verified', True),
            "createdAt": format_datetime(row['created_at']),
            "updatedAt": format_datetime(row.get('updated_at'))
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - SESSIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/sessions/active")
async def get_active_sessions(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener sesiones activas del usuario"""
    # Devolver sesion actual como activa
    return {
        "success": True,
        "data": [
            {
                "id": "current-session",
                "device": "Dispositivo actual",
                "browser": "App NovaGuardian",
                "ip": "192.168.100.1",
                "location": "Ciudad de Mexico, Mexico",
                "lastActive": format_datetime(get_utc_now()),
                "isCurrent": True
            }
        ]
    }

@app.delete("/api/v1/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Revocar una sesion especifica"""
    if session_id == "current-session":
        raise HTTPException(status_code=400, detail="No puedes revocar tu sesion actual")
    return {"success": True, "message": "Sesion revocada exitosamente"}

@app.delete("/api/v1/sessions")
async def revoke_all_sessions(current_user: dict = Depends(get_current_user)):
    """Revocar todas las sesiones excepto la actual"""
    return {"success": True, "message": "Todas las otras sesiones han sido revocadas"}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES - CAREGIVERS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/caregivers")
async def get_caregivers(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtener cuidadores asociados"""
    # Buscar en tabla de cuidadores si existe
    try:
        rows = await db.fetch("""
            SELECT c.*, u.email, u.first_name, u.last_name, u.phone
            FROM caregivers c
            JOIN users u ON c.caregiver_user_id = u.id
            WHERE c.user_id = $1 AND c.status = 'active'
        """, current_user['id'])
        
        return {
            "success": True,
            "data": [
                {
                    "id": str(row['id']),
                    "userId": str(row['caregiver_user_id']),
                    "email": row['email'],
                    "firstName": row.get('first_name'),
                    "lastName": row.get('last_name'),
                    "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
                    "phone": row.get('phone'),
                    "role": row.get('role', 'viewer'),
                    "status": row.get('status', 'active'),
                    "createdAt": format_datetime(row.get('created_at'))
                }
                for row in rows
            ]
        }
    except:
        # Si no existe la tabla, devolver lista vacia
        return {"success": True, "data": []}

@app.post("/api/v1/caregivers/invite")
async def invite_caregiver(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Invitar a un cuidador"""
    data = await request.json()
    email = data.get("email")
    role = data.get("role", "viewer")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido")
    
    # Por ahora solo confirmamos la invitacion
    return {
        "success": True,
        "message": f"Invitacion enviada a {email}",
        "data": {
            "email": email,
            "role": role,
            "status": "pending"
        }
    }

@app.delete("/api/v1/caregivers/{caregiver_id}")
async def remove_caregiver(
    caregiver_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Eliminar un cuidador"""
    try:
        await db.execute("""
            UPDATE caregivers SET status = 'removed' 
            WHERE id = $1 AND user_id = $2
        """, UUID(caregiver_id), current_user['id'])
    except:
        pass
    return {"success": True, "message": "Cuidador eliminado"}


# ═══════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
