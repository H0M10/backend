# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Inicialización de Routers
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter
from app.routers import auth, users, devices, monitored_persons, vital_signs, locations, alerts, notifications

api_router = APIRouter()

# Incluir todos los routers
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(users.router, prefix="/users", tags=["Usuarios"])
api_router.include_router(devices.router, prefix="/devices", tags=["Dispositivos"])
api_router.include_router(monitored_persons.router, prefix="/monitored-persons", tags=["Personas Monitoreadas"])
api_router.include_router(vital_signs.router, prefix="/vital-signs", tags=["Signos Vitales"])
api_router.include_router(locations.router, prefix="/locations", tags=["Ubicaciones"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alertas"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notificaciones"])
