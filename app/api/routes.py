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
    ComunaStats, HealthCheck,
    PuntosInteresCercanosResponse, PuntoInteresResponse
)
from app.schemas.schemas_ml import PreferenciasDetalladas, RecomendacionesResponseML
from app.schemas.schemas_prediccion import (
    PrediccionRequest, PrediccionResponse, ModeloInfo
)
from app.models.models import Propiedad, Comuna, PuntoInteres
from app.services.recommendation_ml_service import RecommendationMLService
from app.services.ml_prediccion_service import MLPrediccionService

# Router principal
router = APIRouter()

# Instanciar servicio de predicción ML (singleton)
try:
    ml_prediccion_service = MLPrediccionService()
except Exception as e:
    logger.warning(f"⚠️  No se pudo inicializar MLPrediccionService: {e}")
    ml_prediccion_service = None


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


# ============================================================================
# PREDICCIÓN DE PRECIOS (Modelos Semana 3)
# ============================================================================

@router.post(
    "/predecir-precio",
    response_model=PrediccionResponse,
    tags=["Predicción ML"],
    summary="Predice precio por m² usando modelos de Semana 3",
    description="""
    Predice el precio por m² de una propiedad usando el sistema avanzado de:
    
    - **Random Forest Global** (baseline)
    - **GWRF por Cluster** (modelos locales por zona espacial)
    - **GWRF por Densidad** (modelos por nivel de urbanización)
    - **Stacking** (meta-modelo que combina los anteriores) - **MEJOR R²=0.489**
    
    **Features utilizadas:**
    - Características físicas: superficie, dormitorios, baños, estacionamientos, bodegas
    - Features derivadas: m2/habitante, total habitaciones, ratio baño/dormitorio
    - **42 densidades espaciales** calculadas automáticamente desde lat/lon
    
    **Confianza del modelo:**
    - 0.0 - 0.3: Baja (usar con precaución)
    - 0.3 - 0.7: Media
    - 0.7 - 1.0: Alta
    
    **Ejemplo de uso:**
    ```json
    {
      "superficie_util": 85.0,
      "dormitorios": 3,
      "banos": 2,
      "estacionamientos": 1,
      "bodegas": 1,
      "latitud": -33.4489,
      "longitud": -70.6693,
      "usar_stacking": true
    }
    ```
    """
)
def predecir_precio(request: PrediccionRequest):
    """
    Predice el precio por m² de una propiedad.
    
    El sistema calcula automáticamente:
    - Features derivadas (m2_por_habitante, etc.)
    - 42 densidades espaciales usando lat/lon
    - Predicción con modelo stacking (mejor R²=0.489)
    
    Args:
        request: Datos de la propiedad (superficie, dormitorios, baños, ubicación)
    
    Returns:
        PrediccionResponse: Precio predicho + confianza + detalles
    """
    try:
        logger.info(f"🏠 Solicitud predicción de precio")
        logger.info(f"   Superficie: {request.superficie_util}m², Dorms: {request.dormitorios}, Baños: {request.banos}")
        logger.info(f"   Ubicación: ({request.latitud}, {request.longitud})")
        
        # Validar que el servicio esté disponible
        if ml_prediccion_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servicio de predicción ML no disponible. Modelos no cargados."
            )
        
        # Realizar predicción
        resultado = ml_prediccion_service.predecir_precio_m2(
            superficie_util=request.superficie_util,
            dormitorios=request.dormitorios,
            banos=request.banos,
            estacionamientos=request.estacionamientos,
            bodegas=request.bodegas,
            latitud=request.latitud,
            longitud=request.longitud,
            cant_max_habitantes=request.cant_max_habitantes,
            usar_stacking=request.usar_stacking
        )
        
        logger.info(f"✅ Predicción: UF {resultado['precio_m2_predicho']}/m² "
                   f"(Total: UF {resultado['precio_total_estimado']:,.0f}) "
                   f"| Confianza: {resultado['confianza']:.2f} "
                   f"| Método: {resultado['metodo']}")
        
        return PrediccionResponse(**resultado)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en predicción: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al predecir precio: {str(e)}"
        )


@router.get(
    "/modelo-info",
    response_model=ModeloInfo,
    tags=["Predicción ML"],
    summary="Información sobre modelos ML cargados"
)
def obtener_info_modelo():
    """
    Retorna información sobre los modelos ML disponibles.
    
    Útil para verificar qué modelos están cargados y sus métricas.
    """
    try:
        if ml_prediccion_service is None:
            return ModeloInfo(
                modelos_disponibles={
                    "stacking": False,
                    "gwrf_cluster": False,
                    "gwrf_densidad": False
                },
                version="1.0.0"
            )
        
        # Verificar qué modelos están disponibles
        modelos_disponibles = {
            "stacking": ml_prediccion_service.meta_model is not None,
            "gwrf_cluster": bool(ml_prediccion_service.modelos_cluster),
            "gwrf_densidad": False  # Por ahora no implementado
        }
        
        # Métricas de los modelos (de la documentación de Semana 3)
        metricas = {
            "stacking": {
                "r2": 0.489,
                "rmse": 25288.0,
                "mae": 4173.0
            },
            "gwrf_cluster": {
                "r2": 0.039,
                "rmse": 34677.0,
                "mae": 4719.0
            },
            "rf_global": {
                "r2": 0.028,
                "rmse": 34876.0,
                "mae": 4839.0
            }
        }
        
        return ModeloInfo(
            modelos_disponibles=modelos_disponibles,
            version="1.0.0",
            metricas=metricas
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo info de modelo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener información del modelo: {str(e)}"
        )


# ============================================================================
# PUNTOS DE INTERÉS / SERVICIOS CERCANOS
# ============================================================================

@router.get(
    "/puntos-interes/cercanos",
    response_model=PuntosInteresCercanosResponse,
    tags=["Puntos de Interés"],
    summary="Obtiene puntos de interés cercanos a una ubicación"
)
def obtener_puntos_interes_cercanos(
    latitud: float,
    longitud: float,
    radio: int = 1500,  # Radio en metros (default 1.5km)
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los puntos de interés cercanos a una ubicación.
    
    **Parámetros:**
    - `latitud`: Latitud de la ubicación de referencia
    - `longitud`: Longitud de la ubicación de referencia
    - `radio`: Radio de búsqueda en metros (default: 1500m = 1.5km)
    
    **Retorna:**
    Puntos de interés organizados por tipo:
    - Metros (estaciones de metro)
    - Colegios (educación básica, media, superior)
    - Centros médicos (hospitales, clínicas, consultorios)
    - Supermercados
    - Parques (áreas verdes)
    - Farmacias
    - Comisarías (seguridad)
    - Bomberos
    
    Cada punto incluye su distancia en metros desde la ubicación consultada.
    """
    try:
        logger.info(f"🔍 Buscando puntos de interés cerca de ({latitud}, {longitud}) - Radio: {radio}m")
        
        # Query con ST_DWithin para buscar dentro del radio especificado
        # ST_DWithin usa metros cuando se trabaja con geography
        puntos_query = db.query(
            PuntoInteres,
            text(f"ST_Distance(geometria::geography, ST_SetSRID(ST_MakePoint({longitud}, {latitud}), 4326)::geography) as distancia")
        ).filter(
            text(f"ST_DWithin(geometria::geography, ST_SetSRID(ST_MakePoint({longitud}, {latitud}), 4326)::geography, {radio})")
        ).all()
        
        # Organizar por tipo
        puntos_por_tipo = {
            'metro': [],
            'colegio': [],
            'centro_medico': [],
            'supermercado': [],
            'parque': [],
            'farmacia': [],
            'comisaria': [],
            'bombero': []
        }
        
        for punto, distancia in puntos_query:
            punto_dict = {
                'id': punto.id,
                'tipo': punto.tipo,
                'nombre': punto.nombre,
                'latitud': punto.latitud,
                'longitud': punto.longitud,
                'direccion': punto.direccion,
                'distancia': round(distancia, 1)
            }
            
            if punto.tipo in puntos_por_tipo:
                puntos_por_tipo[punto.tipo].append(punto_dict)
        
        total = sum(len(v) for v in puntos_por_tipo.values())
        
        logger.info(f"✅ Encontrados {total} puntos de interés")
        
        return PuntosInteresCercanosResponse(
            metros=puntos_por_tipo['metro'],
            colegios=puntos_por_tipo['colegio'],
            centros_medicos=puntos_por_tipo['centro_medico'],
            supermercados=puntos_por_tipo['supermercado'],
            parques=puntos_por_tipo['parque'],
            farmacias=puntos_por_tipo['farmacia'],
            comisarias=puntos_por_tipo['comisaria'],
            bomberos=puntos_por_tipo['bombero'],
            total_encontrados=total
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo puntos de interés: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener puntos de interés: {str(e)}"
        )


@router.get(
    "/puntos-interes/tipo/{tipo}",
    response_model=List[PuntoInteresResponse],
    tags=["Puntos de Interés"],
    summary="Obtiene todos los puntos de interés de un tipo específico"
)
def obtener_puntos_por_tipo(
    tipo: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los puntos de interés de un tipo específico.
    
    **Tipos disponibles:**
    - metro
    - colegio
    - centro_medico
    - supermercado
    - parque
    - farmacia
    - comisaria
    - bombero
    """
    try:
        puntos = db.query(PuntoInteres).filter(PuntoInteres.tipo == tipo).all()
        
        return [
            PuntoInteresResponse(
                id=p.id,
                tipo=p.tipo,
                nombre=p.nombre,
                latitud=p.latitud,
                longitud=p.longitud,
                direccion=p.direccion
            )
            for p in puntos
        ]
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo puntos de tipo {tipo}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener puntos de tipo {tipo}: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error en recomendaciones ML: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando recomendaciones ML: {str(e)}"
        )


