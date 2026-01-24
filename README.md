# 🏥 NovaGuardian Backend API

Sistema de monitoreo de salud geriátrico con IoT - Backend API en Python/FastAPI.

## 📋 Descripción

NovaGuardian es una solución integral para el monitoreo de personas de la tercera edad mediante dispositivos IoT (pulseras inteligentes). Este backend proporciona la API REST para:

- 👤 Gestión de usuarios y autenticación
- 📱 Vinculación de dispositivos IoT
- 💓 Monitoreo de signos vitales en tiempo real
- 📍 Rastreo de ubicación GPS
- 🚨 Sistema de alertas inteligentes
- 🔔 Notificaciones push

## 🛠️ Tecnologías

- **Framework**: FastAPI 0.104+
- **Base de datos**: PostgreSQL con SQLAlchemy Async
- **Autenticación**: JWT (python-jose)
- **Migraciones**: Alembic
- **Validación**: Pydantic v2
- **Servidor**: Uvicorn ASGI
- **Push Notifications**: Expo Push API

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada FastAPI
│   ├── config.py            # Configuración de la app
│   ├── database.py          # Conexión a PostgreSQL
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── device.py
│   │   ├── monitored_person.py
│   │   ├── vital_signs.py
│   │   ├── location.py
│   │   ├── alert.py
│   │   └── notification.py
│   ├── schemas/             # Schemas Pydantic
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── device.py
│   │   └── ...
│   ├── routers/             # Endpoints API
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── devices.py
│   │   └── ...
│   ├── services/            # Lógica de negocio
│   │   ├── auth_service.py
│   │   ├── alert_service.py
│   │   └── ...
│   └── utils/               # Utilidades
│       └── security.py
├── alembic/                 # Migraciones de BD
├── tests/                   # Tests unitarios
├── .env.example             # Plantilla de variables de entorno
├── requirements.txt         # Dependencias Python
├── Dockerfile               # Imagen Docker
└── README.md
```

## 🚀 Instalación

### Prerrequisitos

- Python 3.11+
- PostgreSQL 15+
- pip o poetry

### 1. Clonar y configurar entorno virtual

```bash
cd INTEGRADORA_WEB/backend

# Crear entorno virtual
python -m venv venv

# Activar (Windows)
.\venv\Scripts\activate

# Activar (Linux/Mac)
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
# Copiar plantilla
copy .env.example .env

# Editar .env con tus valores
notepad .env
```

Variables importantes:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/novaguardian
SECRET_KEY=tu-secret-key-muy-segura-aqui
DEBUG=true
```

### 4. Crear base de datos

```sql
-- En PostgreSQL
CREATE DATABASE novaguardian;
```

### 5. Ejecutar migraciones

```bash
# Generar migración inicial
alembic revision --autogenerate -m "Initial migration"

# Aplicar migraciones
alembic upgrade head
```

### 6. Iniciar servidor

```bash
# Desarrollo
uvicorn app.main:app --reload --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📚 Documentación API

Una vez iniciado el servidor:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔐 Autenticación

La API usa JWT Bearer tokens:

1. Obtén token en `POST /api/v1/auth/login`
2. Incluye en headers: `Authorization: Bearer <token>`

```bash
# Ejemplo con curl
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "password": "contraseña123"}'
```

## 📡 Endpoints Principales

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/register` | Registrar usuario |
| POST | `/auth/login` | Iniciar sesión |
| POST | `/auth/refresh` | Refrescar token |
| POST | `/auth/forgot-password` | Solicitar reset |

### Usuarios
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/users/me` | Perfil actual |
| PUT | `/users/me` | Actualizar perfil |
| PUT | `/users/me/password` | Cambiar contraseña |

### Dispositivos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/devices` | Listar dispositivos |
| POST | `/devices/link` | Vincular dispositivo |
| POST | `/devices/data` | Recibir datos IoT |

### Signos Vitales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/vital-signs/current` | Vitales actuales |
| GET | `/vital-signs/history` | Historial |
| GET | `/vital-signs/stats` | Estadísticas |

### Alertas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/alerts` | Listar alertas |
| PUT | `/alerts/{id}/attend` | Atender alerta |
| GET | `/alerts/stats` | Estadísticas |

## 🐳 Docker

```bash
# Construir imagen
docker build -t novaguardian-api .

# Ejecutar
docker run -d -p 8000:8000 --env-file .env novaguardian-api

# Con docker-compose
docker-compose up -d
```

## 🧪 Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app tests/

# Tests específicos
pytest tests/test_auth.py -v
```

## 📄 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de PostgreSQL | - |
| `SECRET_KEY` | Clave para JWT | - |
| `DEBUG` | Modo debug | `false` |
| `PORT` | Puerto del servidor | `8000` |
| `CORS_ORIGINS` | Orígenes permitidos | `*` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración access token | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Expiración refresh token | `7` |

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📝 Licencia

Este proyecto es parte de un proyecto universitario - Integradora 2

---

**NovaGuardian** - Sistema de Monitoreo Geriátrico IoT 🏥💓
