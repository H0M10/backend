# ═══════════════════════════════════════════════════════════════════════════
#  _   _                  _____                     _ _             
# | \ | | _____   ____ _ / ____|_   _  __ _ _ __ __| (_) __ _ _ __  
# |  \| |/ _ \ \ / / _` | |  __| | | |/ _` | '__/ _` | |/ _` | '_ \ 
# | |\  | (_) \ V / (_| | |_|_ | |_| | (_| | | | (_| | | (_| | | | |
# |_| \_|\___/ \_/ \__,_|\_____|  \__,_|\__,_|_|  \__,_|_|\__,_|_| |_|
#
# Backend API - Sistema de Monitoreo Geriátrico IoT
# ═══════════════════════════════════════════════════════════════════════════

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
from loguru import logger
import sys

from app.config import settings
from app.database import init_db, close_db
from app.routers import api_router


# ═══════════════════════════════════════════════════════════════════════════
# Configuración de Logging
# ═══════════════════════════════════════════════════════════════════════════

logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

if not settings.DEBUG:
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Lifecycle Events
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando NovaGuardian API...")
    await init_db()
    logger.info("✅ Base de datos conectada")
    logger.info(f"📍 API disponible en: http://localhost:{settings.PORT}{settings.API_V1_PREFIX}")
    logger.info(f"📚 Documentación: http://localhost:{settings.PORT}/docs")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando NovaGuardian API...")
    await close_db()
    logger.info("✅ Conexiones cerradas")


# ═══════════════════════════════════════════════════════════════════════════
# Crear aplicación FastAPI
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## 🏥 NovaGuardian API
    
    Sistema de monitoreo de salud geriátrico con IoT.
    
    ### 📱 Funcionalidades principales:
    
    * **Autenticación**: Registro, login, verificación de email
    * **Usuarios**: Gestión de perfil y preferencias
    * **Dispositivos**: Vinculación y gestión de pulseras IoT
    * **Personas Monitoreadas**: Registro y configuración
    * **Signos Vitales**: Monitoreo en tiempo real
    * **Alertas**: Sistema de alertas inteligentes
    * **Ubicación**: Rastreo GPS y geofences
    * **Notificaciones**: Push notifications
    
    ### 🔐 Autenticación:
    
    La API usa JWT Bearer tokens. Obtén tu token en `/auth/login` y 
    envíalo en el header `Authorization: Bearer <token>`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ═══════════════════════════════════════════════════════════════════════════
# Middlewares
# ═══════════════════════════════════════════════════════════════════════════

# CORS - Configuración para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Agregar tiempo de procesamiento a los headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log de requests
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    
    return response


# ═══════════════════════════════════════════════════════════════════════════
# Exception Handlers
# ═══════════════════════════════════════════════════════════════════════════

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejar errores de validación de Pydantic"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Error de validación",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejar excepciones no controladas"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Error interno del servidor" if not settings.DEBUG else str(exc)
        }
    )


# ═══════════════════════════════════════════════════════════════════════════
# Rutas
# ═══════════════════════════════════════════════════════════════════════════

# Incluir router de API
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Health check
@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz - Health check básico"""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "message": "Bienvenido a NovaGuardian API 🏥"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check detallado"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": "development" if settings.DEBUG else "production",
        "database": "connected"
    }


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard Summary (para compatibilidad con frontend)
# ═══════════════════════════════════════════════════════════════════════════
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.device import Device
from app.models.alert import Alert
from app.models.monitored_person import MonitoredPerson
from fastapi import Depends


@app.get(f"{settings.API_V1_PREFIX}/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Resumen general del dashboard (endpoint público para la app móvil)
    """
    from datetime import date
    
    try:
        # Total usuarios activos
        users_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        total_users = users_result.scalar() or 0
        
        # Total dispositivos
        devices_result = await db.execute(select(func.count(Device.id)))
        total_devices = devices_result.scalar() or 0
        
        # Dispositivos conectados
        connected_result = await db.execute(
            select(func.count(Device.id)).where(Device.is_connected == True)
        )
        connected_devices = connected_result.scalar() or 0
        
        # Total personas monitoreadas
        monitored_result = await db.execute(
            select(func.count(MonitoredPerson.id)).where(MonitoredPerson.is_active == True)
        )
        total_monitored = monitored_result.scalar() or 0
        
        # Alertas de hoy
        today = date.today()
        alerts_today_result = await db.execute(
            select(func.count(Alert.id)).where(
                func.date(Alert.created_at) == today
            )
        )
        alerts_today = alerts_today_result.scalar() or 0
        
        # Alertas pendientes
        pending_result = await db.execute(
            select(func.count(Alert.id)).where(Alert.is_resolved == False)
        )
        pending_alerts = pending_result.scalar() or 0
        
        # Alertas críticas
        critical_result = await db.execute(
            select(func.count(Alert.id)).where(Alert.severity == 'critical')
        )
        critical_alerts = critical_result.scalar() or 0
        
        return {
            "totalUsers": total_users,
            "totalDevices": total_devices,
            "connectedDevices": connected_devices,
            "disconnectedDevices": total_devices - connected_devices,
            "totalMonitored": total_monitored,
            "alertsToday": alerts_today,
            "pendingAlerts": pending_alerts,
            "criticalAlerts": critical_alerts
        }
    except Exception as e:
        logger.error(f"Error en dashboard summary: {e}")
        return {
            "totalUsers": 0,
            "totalDevices": 0,
            "connectedDevices": 0,
            "disconnectedDevices": 0,
            "totalMonitored": 0,
            "alertsToday": 0,
            "pendingAlerts": 0,
            "criticalAlerts": 0
        }


# ═══════════════════════════════════════════════════════════════════════════
# Punto de entrada
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4
    )
