# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Entry point para Vercel Serverless
# ═══════════════════════════════════════════════════════════════════════════

from mangum import Mangum
from app.main import app

# Mangum es el adaptador que convierte ASGI (FastAPI) a formato serverless
handler = Mangum(app, lifespan="off")
