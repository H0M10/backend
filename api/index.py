# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Entry point para Vercel Serverless
# ═══════════════════════════════════════════════════════════════════════════

from app.main import app

# Vercel busca una variable llamada 'app' o 'handler'
# FastAPI es compatible con ASGI, Vercel lo maneja automáticamente
handler = app
