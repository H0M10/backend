# ═══════════════════════════════════════════════════════════════════════════
# NOVAGUARDIAN - Configuración de Base de Datos
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings

# ═══════════════════════════════════════════════════════════════════════════
# MOTOR DE BASE DE DATOS
# ═══════════════════════════════════════════════════════════════════════════

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    poolclass=NullPool,  # Mejor para aplicaciones async
)

# ═══════════════════════════════════════════════════════════════════════════
# SESIÓN DE BASE DE DATOS
# ═══════════════════════════════════════════════════════════════════════════

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ═══════════════════════════════════════════════════════════════════════════
# BASE PARA MODELOS
# ═══════════════════════════════════════════════════════════════════════════

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════
# DEPENDENCY PARA OBTENER SESIÓN
# ═══════════════════════════════════════════════════════════════════════════

async def get_db() -> AsyncSession:
    """
    Dependency que proporciona una sesión de base de datos.
    Se usa en los endpoints con Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════════════════

async def init_db():
    """Inicializar la base de datos creando todas las tablas"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Cerrar conexiones de la base de datos"""
    await engine.dispose()
