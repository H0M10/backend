# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Tests de Health Check
# ═══════════════════════════════════════════════════════════════════════════

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests para endpoints de health check"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test endpoint raíz"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "NovaGuardian" in data["name"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
