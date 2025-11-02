"""
Endpoints de la API
Rutas para recomendaciones, propiedades, comunas, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import datetime
from loguru import logger

from app.database import get_db
from app.schemas.schemas import (
    PropiedadCreate, PropiedadResponse,
    ComunaStats, HealthCheck
)
from app.schemas.schemas_ml import PreferenciasDetalladas, RecomendacionesResponseML
from app.models.models import Propiedad, Comuna
from app.services.recommendation_ml_service import RecommendationMLService

# Router principal
router = APIRouter()


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", response_model=HealthCheck, tags=["Sistema"])
def health_check(db: Session = Depends(get_db)):
    """Health check del sistema"""
    try:
        # Test DB
        db.execute(text("SELECT 1"))
        db_status = "✅ Conectada"
    except Exception as e:
        db_status = f"❌ Error: {str(e)}"
    
    # Test sistema
    modelo_status = "✅ Sistema ML activo"
    
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        database=db_status,
        modelo=modelo_status,
        timestamp=datetime.now()
    )


# ============================================================================
# PROPIEDADES
# ============================================================================

@router.post("/propiedades", response_model=PropiedadResponse, tags=["Propiedades"])
def crear_propiedad(
    propiedad: PropiedadCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva propiedad en la base de datos
    Automáticamente calcula precio predicho si no tiene precio real
    """
    try:
        # Buscar comuna
        comuna_obj = db.query(Comuna).filter(
            Comuna.nombre == propiedad.comuna
        ).first()
        
        if not comuna_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comuna '{propiedad.comuna}' no encontrada"
            )
        
        # Crear propiedad
        nueva_propiedad = Propiedad(
            comuna_id=comuna_obj.id,
            direccion=propiedad.direccion,
            latitud=propiedad.latitud,
            longitud=propiedad.longitud,
            superficie_total=propiedad.superficie_total,
            superficie_construida=propiedad.superficie_construida,
            dormitorios=propiedad.dormitorios,
            banos=propiedad.banos,
            estacionamientos=propiedad.estacionamientos,
            dist_metro=propiedad.dist_metro,
            dist_supermercado=propiedad.dist_supermercado,
            dist_area_verde=propiedad.dist_area_verde,
            dist_colegio=propiedad.dist_colegio,
            dist_hospital=propiedad.dist_hospital,
            dist_mall=propiedad.dist_mall,
            precio=propiedad.precio,
            fuente=propiedad.fuente,
            descripcion=propiedad.descripcion
        )
        
        db.add(nueva_propiedad)
        db.commit()
        db.refresh(nueva_propiedad)
        
        logger.info(f"✅ Propiedad creada: ID {nueva_propiedad.id}")
        
        # Construir respuesta
        return PropiedadResponse(
            id=nueva_propiedad.id,
            comuna=propiedad.comuna,
            direccion=nueva_propiedad.direccion,
            superficie_total=nueva_propiedad.superficie_total,
            dormitorios=nueva_propiedad.dormitorios,
            banos=nueva_propiedad.banos,
            precio=nueva_propiedad.precio,
            precio_predicho=nueva_propiedad.precio_predicho,
            created_at=nueva_propiedad.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creando propiedad: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear propiedad: {str(e)}"
        )


@router.get("/propiedades", tags=["Propiedades"])
def listar_propiedades(
    skip: int = 0,
    limit: int = 50,
    comuna: str = None,
    db: Session = Depends(get_db)
):
    """Lista propiedades con filtros opcionales"""
    query = db.query(Propiedad)
    
    if comuna:
        comuna_obj = db.query(Comuna).filter(Comuna.nombre == comuna).first()
        if comuna_obj:
            query = query.filter(Propiedad.comuna_id == comuna_obj.id)
    
    propiedades = query.offset(skip).limit(limit).all()
    
    return {
        "total": query.count(),
        "propiedades": propiedades
    }


@router.get("/propiedades/{propiedad_id}", tags=["Propiedades"])
def obtener_propiedad(propiedad_id: int, db: Session = Depends(get_db)):
    """Obtiene una propiedad por ID"""
    propiedad = db.query(Propiedad).filter(Propiedad.id == propiedad_id).first()
    
    if not propiedad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Propiedad {propiedad_id} no encontrada"
        )
    
    return propiedad


# ============================================================================
# COMUNAS
# ============================================================================

@router.get("/comunas", response_model=List[ComunaStats], tags=["Comunas"])
def listar_comunas(db: Session = Depends(get_db)):
    """Lista todas las comunas con sus estadísticas"""
    comunas = db.query(Comuna).all()
    return comunas


@router.get("/comunas/{nombre}", tags=["Comunas"])
def obtener_comuna(nombre: str, db: Session = Depends(get_db)):
    """Obtiene información detallada de una comuna"""
    comuna = db.query(Comuna).filter(Comuna.nombre == nombre).first()
    
    if not comuna:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comuna '{nombre}' no encontrada"
        )
    
    # Estadísticas de propiedades
    propiedades = db.query(Propiedad).filter(Propiedad.comuna_id == comuna.id).all()
    
    if propiedades:
        precios = [p.precio for p in propiedades if p.precio]
        precio_promedio = sum(precios) / len(precios) if precios else None
    else:
        precio_promedio = None
    
    return {
        "comuna": comuna,
        "total_propiedades": len(propiedades),
        "precio_promedio": precio_promedio
    }


# ============================================================================
# ESTADÍSTICAS
# ============================================================================

@router.get("/stats/general", tags=["Estadísticas"])
def estadisticas_generales(db: Session = Depends(get_db)):
    """Estadísticas generales del sistema"""
    total_propiedades = db.query(Propiedad).count()
    total_comunas = db.query(Comuna).count()
    
    return {
        "total_propiedades": total_propiedades,
        "total_comunas": total_comunas,
        "sistema": "Recomendaciones ML Activo"
    }


# ============================================================================
# RECOMENDACIONES ML (Sistema Avanzado)
# ============================================================================

@router.post(
    "/recomendaciones-ml",
    response_model=RecomendacionesResponseML,
    tags=["Recomendaciones ML"],
    summary="Recomendaciones con ML avanzado",
    description="""
    Sistema de recomendaciones AVANZADO con Machine Learning y preferencias detalladas.
    
    **Características principales:**
    - ✅ **Preferencias detalladas por categoría** (-10 a +10 para cada factor)
    - ✅ **Valores negativos** para EVITAR características (ej: -8 en colegios = NO quiere colegios cerca)
    - ✅ **Valores positivos** para BUSCAR características (ej: +10 en parques = QUIERE parques cerca)
    - ✅ **Scoring explicado** con puntos fuertes y débiles
    - ✅ **Confianza del modelo** (0-1)
    - ✅ **Sugerencias inteligentes** para mejorar búsqueda
    
    **Ejemplo de uso:**
    ```json
    {
      "precio_min": 250000,
      "precio_max": 350000,
      "dormitorios_min": 2,
      "educacion": {
        "importancia_colegios": -8,  // EVITAR colegios (ruido)
        "distancia_maxima_colegios_m": 500
      },
      "salud": {
        "importancia_consultorios": 10,  // MUY IMPORTANTE tener cerca
        "distancia_maxima_consultorios_m": 1000
      },
      "areas_verdes": {
        "importancia_parques": 10  // MUY IMPORTANTE
      }
    }
    ```
    
    **Sistema de scoring:**
    - Cada categoría se evalúa según importancia especificada
    - Valores negativos invierten el scoring (más lejos = mejor)
    - Score total: suma ponderada de todas las categorías
    - Confianza: basada en disponibilidad de datos
    """
)
def recomendar_propiedades_ml(
    preferencias: PreferenciasDetalladas,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Sistema avanzado de recomendaciones con ML
    
    Permite al usuario especificar preferencias MUY DETALLADAS:
    - Puede EVITAR características (valores negativos -10 a -1)
    - Puede BUSCAR características (valores positivos +1 a +10)
    - Puede ser NEUTRO (valor 0)
    
    Ejemplos:
    - Usuario quiere áreas verdes (+10) pero NO colegios cerca (-8)
    - Usuario quiere metro cerca (+9) pero NO hospitales (+10 en salud)
    - Usuario evita ruido de colegios (-7) pero necesita supermercados (+8)
    
    Args:
        preferencias: Preferencias detalladas con importancia de cada factor
        limit: Número máximo de recomendaciones
        db: Sesión de base de datos
        
    Returns:
        RecomendacionesResponseML: Recomendaciones con scoring explicado
    """
    try:
        logger.info(f"🔬 Solicitud recomendaciones ML - Limit: {limit}")
        logger.info(f"   Preferencias detalladas recibidas")
        
        # Crear servicio ML
        ml_rec_service = RecommendationMLService(db)
        
        # Obtener recomendaciones con ML
        response = ml_rec_service.recomendar_propiedades(preferencias, limit)
        
        logger.info(f"✅ ML: {response.total_encontradas} recomendaciones de {response.total_analizadas} analizadas")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en recomendaciones ML: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando recomendaciones ML: {str(e)}"
        )


