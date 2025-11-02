#!/usr/bin/env python3
"""
Script de inicialización de la base de datos
Crea tablas y datos iniciales (comunas)
"""
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine, Base, SessionLocal
from app.models.models import Comuna
from sqlalchemy import text
from loguru import logger


def init_database():
    """Inicializa la base de datos"""
    
    logger.info("=" * 70)
    logger.info("🗄️  INICIALIZACIÓN DE BASE DE DATOS")
    logger.info("=" * 70)
    
    # 1. Crear extensión PostGIS
    logger.info("📍 Creando extensión PostGIS...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
        logger.info("✅ PostGIS habilitado")
    except Exception as e:
        logger.warning(f"⚠️  PostGIS: {e}")
    
    # 2. Crear todas las tablas
    logger.info("📦 Creando tablas...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas")
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        return False
    
    # 3. Insertar comunas iniciales
    logger.info("🏘️  Insertando comunas...")
    db = SessionLocal()
    try:
        comunas_existentes = db.query(Comuna).count()
        
        if comunas_existentes == 0:
            comunas = [
                Comuna(nombre="Estación Central", codigo="EST"),
                Comuna(nombre="Santiago", codigo="SAN"),
                Comuna(nombre="Ñuñoa", codigo="ÑUÑ"),
                Comuna(nombre="La Reina", codigo="LRE"),
            ]
            
            for comuna in comunas:
                db.add(comuna)
            
            db.commit()
            logger.info(f"✅ {len(comunas)} comunas insertadas")
        else:
            logger.info(f"ℹ️  {comunas_existentes} comunas ya existen")
        
    except Exception as e:
        logger.error(f"❌ Error insertando comunas: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    logger.info("=" * 70)
    logger.info("✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
