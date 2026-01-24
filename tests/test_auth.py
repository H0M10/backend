# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Tests de Autenticación
# ═══════════════════════════════════════════════════════════════════════════

import pytest
from httpx import AsyncClient


class TestAuth:
    """Tests para endpoints de autenticación"""
    
    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test registro de usuario"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "first_name": "New",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registro con email duplicado"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Email del test_user
                "password": "SecurePassword123!",
                "first_name": "Another",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "registrado" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test login exitoso"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login con contraseña incorrecta"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login con usuario inexistente"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "somepassword"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Test obtener usuario actual"""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test obtener usuario sin token"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        """Test refrescar token"""
        # Primero hacer login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refrescar token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
