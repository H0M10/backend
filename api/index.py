# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Entry point para Vercel Serverless
# ═══════════════════════════════════════════════════════════════════════════

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "name": "NovaGuardian",
            "version": "1.0.0",
            "status": "online",
            "message": "Bienvenido a NovaGuardian API 🏥"
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
