"""
Aplicación principal FastAPI
Configuración, middlewares, y startup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.api import router

# Configurar logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger.remove()  # Remover handler por defecto
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level=settings.LOG_LEVEL
)
logger.add(
    settings.LOG_FILE,
    rotation="10 MB",
    retention="1 week",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level=settings.LOG_LEVEL
)

# Crear aplicación
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EVENTOS DE STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Evento de inicio"""
    logger.info("=" * 70)
    logger.info(f"🚀 Iniciando {settings.API_TITLE}")
    logger.info("=" * 70)
    logger.info(f"📌 Versión: {settings.API_VERSION}")
    logger.info(f"📌 Debug: {settings.DEBUG}")
    logger.info(f"📌 Database: {settings.DB_NAME}")
    logger.info(f"📌 Modelo ML: {settings.MODEL_PATH}")
    
    # Inicializar base de datos
    try:
        init_db()
        logger.info("✅ Base de datos inicializada")
    except Exception as e:
        logger.error(f"❌ Error iniciando base de datos: {e}")
    
    logger.info("=" * 70)
    logger.info(f"✅ Servidor listo en http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"📚 Documentación: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    logger.info("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre"""
    logger.info("🛑 Cerrando aplicación...")


# ============================================================================
# RUTAS
# ============================================================================

# Incluir router principal
app.include_router(router, prefix="/api/v1")


# Ruta raíz
@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "message": "🏠 API Inmobiliaria - Predicción de Precios",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# Manejador de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones"""
    logger.error(f"❌ Error no manejado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )
