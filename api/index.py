# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Entry point para Vercel Serverless
# ═══════════════════════════════════════════════════════════════════════════

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        path = self.path
        
        # Health check endpoints
        if path == '/' or path == '':
            response = {
                "name": "NovaGuardian",
                "version": "1.0.0",
                "status": "online",
                "message": "Bienvenido a NovaGuardian API 🏥",
                "docs": "/docs (no disponible en serverless)",
                "note": "Para API completa, usar Railway o Render"
            }
        elif path == '/health':
            response = {
                "status": "healthy",
                "app": "NovaGuardian",
                "environment": "production",
                "platform": "vercel-serverless"
            }
        elif path == '/api/v1':
            response = {
                "message": "NovaGuardian API v1",
                "endpoints": [
                    "/api/v1/auth",
                    "/api/v1/users", 
                    "/api/v1/devices",
                    "/api/v1/vital-signs",
                    "/api/v1/alerts"
                ],
                "note": "FastAPI completa requiere hosting tradicional (Railway/Render)"
            }
        else:
            response = {
                "error": "Endpoint no encontrado",
                "path": path,
                "available": ["/", "/health", "/api/v1"]
            }
            self.send_response(404)
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        return
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "error": "POST no soportado en modo serverless",
            "message": "Para endpoints POST (login, register, etc), usa Railway o Render",
            "path": self.path
        }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        return
