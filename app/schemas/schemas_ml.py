"""
Schemas para sistema de recomendaciones con Machine Learning
Sistema avanzado de preferencias y feedback del usuario
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class TipoFeedback(str, Enum):
    """Tipo de feedback del usuario"""
    ME_GUSTA = "me_gusta"
    NO_ME_GUSTA = "no_me_gusta"
    CONTACTADO = "contactado"
    VISITADO = "visitado"


class NivelImportancia(int, Enum):
    """Niveles de importancia para características"""
    EVITAR_MUCHO = -10
    EVITAR = -7
    EVITAR_POCO = -3
    NEUTRO = 0
    POCO_IMPORTANTE = 3
    IMPORTANTE = 7
    MUY_IMPORTANTE = 10


# ============================================================================
# PREFERENCIAS DETALLADAS
# ============================================================================

class PreferenciasTransporte(BaseModel):
    """Preferencias específicas de transporte"""
    importancia_metro: int = Field(0, ge=-10, le=10, description="Importancia del metro (-10: evitar, 0: neutro, 10: muy importante)")
    distancia_maxima_metro_m: Optional[int] = Field(1000, description="Distancia máxima aceptable al metro en metros")
    
    importancia_buses: int = Field(0, ge=-10, le=10, description="Importancia de paraderos de buses")
    distancia_maxima_buses_m: Optional[int] = Field(500, description="Distancia máxima a paraderos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "importancia_metro": 9,
                "distancia_maxima_metro_m": 500,
                "importancia_buses": 3,
                "distancia_maxima_buses_m": 300
            }
        }


class PreferenciasEducacion(BaseModel):
    """Preferencias específicas de educación"""
    importancia_colegios: int = Field(0, ge=-10, le=10, description="Importancia de cercanía a colegios")
    distancia_maxima_colegios_m: Optional[int] = Field(1000, description="Distancia máxima a colegios")
    
    importancia_universidades: int = Field(0, ge=-10, le=10, description="Importancia de universidades")
    distancia_maxima_universidades_m: Optional[int] = Field(3000, description="Distancia máxima a universidades")
    
    class Config:
        json_schema_extra = {
            "example": {
                "importancia_colegios": -8,  # Usuario NO quiere colegios cerca (ruido)
                "distancia_maxima_colegios_m": 500,
                "importancia_universidades": 0,
                "distancia_maxima_universidades_m": 3000
            }
        }


class PreferenciasSalud(BaseModel):
    """Preferencias específicas de salud"""
    importancia_hospitales: int = Field(0, ge=-10, le=10, description="Importancia de hospitales")
    distancia_maxima_hospitales_m: Optional[int] = Field(2000, description="Distancia máxima a hospitales")
    
    importancia_consultorios: int = Field(0, ge=-10, le=10, description="Importancia de consultorios")
    distancia_maxima_consultorios_m: Optional[int] = Field(1000, description="Distancia máxima a consultorios")
    
    importancia_farmacias: int = Field(0, ge=-10, le=10, description="Importancia de farmacias")
    distancia_maxima_farmacias_m: Optional[int] = Field(500, description="Distancia máxima a farmacias")
    
    class Config:
        json_schema_extra = {
            "example": {
                "importancia_hospitales": 8,
                "distancia_maxima_hospitales_m": 1500,
                "importancia_consultorios": 10,
                "distancia_maxima_consultorios_m": 800,
                "importancia_farmacias": 5,
                "distancia_maxima_farmacias_m": 400
            }
        }


class PreferenciasServicios(BaseModel):
    """Preferencias de servicios y comercio"""
    importancia_supermercados: int = Field(0, ge=-10, le=10, description="Importancia de supermercados")
    distancia_maxima_supermercados_m: Optional[int] = Field(1000, description="Distancia máxima a supermercados")
    
    importancia_malls: int = Field(0, ge=-10, le=10, description="Importancia de malls")
    distancia_maxima_malls_m: Optional[int] = Field(3000, description="Distancia máxima a malls")
    
    importancia_restaurantes: int = Field(0, ge=-10, le=10, description="Importancia de restaurantes")
    distancia_maxima_restaurantes_m: Optional[int] = Field(500, description="Distancia máxima a restaurantes")
    
    importancia_gimnasios: int = Field(0, ge=-10, le=10, description="Importancia de gimnasios")
    distancia_maxima_gimnasios_m: Optional[int] = Field(1000, description="Distancia máxima a gimnasios")


class PreferenciasAreasVerdes(BaseModel):
    """Preferencias de áreas verdes y recreación"""
    importancia_parques: int = Field(0, ge=-10, le=10, description="Importancia de parques")
    distancia_maxima_parques_m: Optional[int] = Field(800, description="Distancia máxima a parques")
    
    importancia_plazas: int = Field(0, ge=-10, le=10, description="Importancia de plazas")
    distancia_maxima_plazas_m: Optional[int] = Field(500, description="Distancia máxima a plazas")
    
    importancia_ciclovias: int = Field(0, ge=-10, le=10, description="Importancia de ciclovías")


class PreferenciasSeguridad(BaseModel):
    """Preferencias relacionadas con seguridad"""
    importancia_comisarias: int = Field(0, ge=-10, le=10, description="Importancia de comisarías")
    distancia_maxima_comisarias_m: Optional[int] = Field(2000, description="Distancia máxima a comisarías")
    
    importancia_bomberos: int = Field(0, ge=-10, le=10, description="Importancia de bomberos")
    distancia_maxima_bomberos_m: Optional[int] = Field(3000, description="Distancia máxima a bomberos")
    
    importancia_iluminacion: int = Field(0, ge=-10, le=10, description="Importancia de buena iluminación")
    importancia_vigilancia: int = Field(0, ge=-10, le=10, description="Importancia de vigilancia/conserje")


class PreferenciasEdificio(BaseModel):
    """Preferencias del edificio y características físicas"""
    
    # Gastos comunes
    gastos_comunes_max: Optional[float] = Field(None, description="Presupuesto máximo de gastos comunes en CLP")
    importancia_gastos_bajos: int = Field(0, ge=-10, le=10, description="Importancia de gastos comunes bajos (10 = muy importante)")
    
    # Piso y altura
    importancia_piso_alto: int = Field(0, ge=-10, le=10, description="Preferencia por pisos altos (+10) o bajos (-10)")
    piso_minimo: Optional[int] = Field(None, ge=1, le=30, description="Piso mínimo aceptable")
    piso_maximo: Optional[int] = Field(None, ge=1, le=30, description="Piso máximo aceptable")
    
    # Orientación
    importancia_orientacion: int = Field(0, ge=-10, le=10, description="Importancia de la orientación")
    orientaciones_preferidas: Optional[List[str]] = Field(
        None, 
        description="Orientaciones preferidas: ['norte', 'sur', 'este', 'oeste']"
    )
    
    # Terraza
    necesita_terraza: bool = Field(False, description="Si requiere terraza obligatoriamente")
    terraza_minima_m2: Optional[float] = Field(None, ge=0, description="Superficie mínima de terraza en m²")
    importancia_terraza: int = Field(0, ge=-10, le=10, description="Importancia de tener terraza")
    
    # Tipo de departamento
    tipo_preferido: Optional[str] = Field(None, description="'interior' o 'exterior'")
    importancia_tipo: int = Field(0, ge=-10, le=10, description="Importancia del tipo de departamento")
    
    # Privacidad/Densidad
    departamentos_por_piso_max: Optional[int] = Field(None, ge=1, description="Máximo número de deptos por piso")
    importancia_privacidad: int = Field(0, ge=-10, le=10, description="Importancia de privacidad (menos deptos/piso)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gastos_comunes_max": 100000,
                "importancia_gastos_bajos": 8,
                "importancia_piso_alto": 7,
                "piso_minimo": 5,
                "piso_maximo": 20,
                "importancia_orientacion": 8,
                "orientaciones_preferidas": ["norte", "este"],
                "necesita_terraza": True,
                "terraza_minima_m2": 15,
                "importancia_terraza": 10
            }
        }


class PreferenciasDetalladas(BaseModel):
    """Preferencias detalladas del usuario - Sistema avanzado"""
    
    # ===== HARD CONSTRAINTS (Filtros obligatorios) =====
    precio_min: Optional[float] = Field(None, description="Precio mínimo en UF")
    precio_max: Optional[float] = Field(None, description="Precio máximo en UF")
    
    superficie_min: Optional[float] = Field(None, description="Superficie útil mínima en m²")
    superficie_max: Optional[float] = Field(None, description="Superficie útil máxima en m²")
    
    dormitorios_min: Optional[int] = Field(None, ge=1, le=10, description="Mínimo número de dormitorios")
    dormitorios_max: Optional[int] = Field(None, ge=1, le=10, description="Máximo número de dormitorios")
    
    banos_min: Optional[int] = Field(None, ge=1, le=10, description="Mínimo número de baños")
    estacionamientos_min: Optional[int] = Field(0, ge=0, description="Mínimo número de estacionamientos")
    
    # ===== UBICACIÓN =====
    comunas_preferidas: Optional[List[str]] = Field(None, description="Lista de comunas preferidas")
    comunas_evitar: Optional[List[str]] = Field(None, description="Lista de comunas a evitar")
    
    # ===== PREFERENCIAS DETALLADAS POR CATEGORÍA =====
    transporte: Optional[PreferenciasTransporte] = Field(None, description="Preferencias de transporte")
    educacion: Optional[PreferenciasEducacion] = Field(None, description="Preferencias de educación")
    salud: Optional[PreferenciasSalud] = Field(None, description="Preferencias de salud")
    servicios: Optional[PreferenciasServicios] = Field(None, description="Preferencias de servicios")
    areas_verdes: Optional[PreferenciasAreasVerdes] = Field(None, description="Preferencias de áreas verdes")
    seguridad: Optional[PreferenciasSeguridad] = Field(None, description="Preferencias de seguridad")
    edificio: Optional[PreferenciasEdificio] = Field(None, description="Preferencias del edificio y características físicas")
    
    # ===== PESOS GLOBALES DE CATEGORÍAS =====
    peso_precio: float = Field(0.20, ge=0, le=1, description="Peso de la importancia del precio")
    peso_ubicacion: float = Field(0.12, ge=0, le=1, description="Peso de la ubicación/comuna")
    peso_tamano: float = Field(0.08, ge=0, le=1, description="Peso del tamaño de la propiedad")
    peso_transporte: float = Field(0.15, ge=0, le=1, description="Peso global del transporte")
    peso_educacion: float = Field(0.10, ge=0, le=1, description="Peso global de educación")
    peso_salud: float = Field(0.10, ge=0, le=1, description="Peso global de salud")
    peso_servicios: float = Field(0.08, ge=0, le=1, description="Peso global de servicios")
    peso_areas_verdes: float = Field(0.05, ge=0, le=1, description="Peso global de áreas verdes")
    peso_edificio: float = Field(0.12, ge=0, le=1, description="Peso global de características del edificio")
    
    @validator('precio_min', 'precio_max', 'superficie_min', 'superficie_max')
    def validar_valores_positivos(cls, v):
        """Valida que los valores numéricos sean positivos si están presentes"""
        if v is not None and v <= 0:
            raise ValueError(f'El valor debe ser mayor que 0 si se proporciona')
        return v
    
    @validator('precio_max')
    def validar_rango_precio(cls, v, values):
        """Valida que precio_max sea mayor que precio_min"""
        if v is not None and values.get('precio_min') is not None:
            if v <= values.get('precio_min'):
                raise ValueError('precio_max debe ser mayor que precio_min')
        return v
    
    @validator('peso_edificio')
    def validar_suma_pesos(cls, v, values):
        """Valida que la suma de pesos sea aproximadamente 1.0"""
        suma = (
            values.get('peso_precio', 0) +
            values.get('peso_ubicacion', 0) +
            values.get('peso_tamano', 0) +
            values.get('peso_transporte', 0) +
            values.get('peso_educacion', 0) +
            values.get('peso_salud', 0) +
            values.get('peso_servicios', 0) +
            values.get('peso_areas_verdes', 0) +
            v  # peso_edificio
        )
        if abs(suma - 1.0) > 0.05:  # Tolerancia de 5%
            raise ValueError(f'La suma de pesos debe ser cercana a 1.0 (actual: {suma:.2f})')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "precio_min": 250000,
                "precio_max": 350000,
                "dormitorios_min": 2,
                "dormitorios_max": 3,
                "banos_min": 2,
                "comunas_preferidas": ["Santiago", "Ñuñoa"],
                "transporte": {
                    "importancia_metro": 9,
                    "distancia_maxima_metro_m": 600
                },
                "educacion": {
                    "importancia_colegios": -8,  # NO quiere colegios cerca
                    "distancia_maxima_colegios_m": 500
                },
                "salud": {
                    "importancia_consultorios": 10,
                    "distancia_maxima_consultorios_m": 1000
                },
                "areas_verdes": {
                    "importancia_parques": 10,
                    "distancia_maxima_parques_m": 500
                }
            }
        }


# ============================================================================
# FEEDBACK Y APRENDIZAJE
# ============================================================================

class FeedbackPropiedad(BaseModel):
    """Feedback del usuario sobre una propiedad recomendada"""
    propiedad_id: int = Field(..., description="ID de la propiedad")
    tipo_feedback: TipoFeedback = Field(..., description="Tipo de feedback")
    score_original: float = Field(..., description="Score que tenía la recomendación")
    comentario: Optional[str] = Field(None, max_length=500, description="Comentario opcional del usuario")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Context de la búsqueda
    preferencias_usadas: Optional[Dict[str, Any]] = Field(None, description="Preferencias que se usaron")
    
    class Config:
        json_schema_extra = {
            "example": {
                "propiedad_id": 123,
                "tipo_feedback": "me_gusta",
                "score_original": 87.5,
                "comentario": "Perfecta, justo lo que buscaba",
                "preferencias_usadas": {}
            }
        }


class HistorialBusqueda(BaseModel):
    """Historial de búsquedas del usuario"""
    id: Optional[int] = None
    usuario_id: Optional[str] = Field(None, description="ID del usuario (puede ser anónimo)")
    preferencias: PreferenciasDetalladas
    resultados_obtenidos: int = Field(..., description="Cantidad de resultados")
    feedback_positivos: int = Field(0, description="Cantidad de me gusta")
    feedback_negativos: int = Field(0, description="Cantidad de no me gusta")
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# RESPUESTAS CON ML
# ============================================================================

class ScoreML(BaseModel):
    """Score detallado con explicación del modelo ML"""
    categoria: str = Field(..., description="Categoría del score")
    score: float = Field(..., ge=0, le=100, description="Score de 0-100")
    peso: float = Field(..., description="Peso de esta categoría")
    contribucion: float = Field(..., description="Contribución al score total")
    explicacion: str = Field(..., description="Explicación de por qué ese score")
    factores_positivos: List[str] = Field(default_factory=list, description="Factores que sumaron")
    factores_negativos: List[str] = Field(default_factory=list, description="Factores que restaron")


class PropiedadRecomendadaML(BaseModel):
    """Propiedad recomendada con scoring avanzado y predicción de satisfacción LightGBM"""
    # Info básica
    id: int
    direccion: str
    comuna: str
    precio: float  # Siempre en CLP (normalizado desde el backend)
    divisa: str = 'CLP'  # Divisa normalizada
    superficie_util: Optional[float] = 0.0
    dormitorios: int
    banos: int
    estacionamientos: Optional[int] = 0
    latitud: Optional[float] = 0.0
    longitud: Optional[float] = 0.0
    
    # Scoring
    score_total: float = Field(..., ge=0, le=100, description="Score total (0-100)")
    score_confianza: float = Field(..., ge=0, le=1, description="Confianza del modelo (0-1)")
    scores_por_categoria: List[ScoreML] = Field(..., description="Desglose por categoría")
    
    # Satisfacción ML (LightGBM R²=0.86)
    satisfaccion_score: Optional[float] = Field(None, ge=0, le=10, description="Satisfacción predicha por LightGBM (0-10)")
    satisfaccion_nivel: Optional[str] = Field(None, description="Nivel de satisfacción: Excelente, Bueno, Regular, Bajo")
    
    # Explicación
    resumen_explicacion: str = Field(..., description="Resumen de por qué se recomienda")
    puntos_fuertes: List[str] = Field(..., description="Top 3-5 puntos fuertes")
    puntos_debiles: List[str] = Field(..., description="Top 3-5 puntos débiles")
    
    # Distancias relevantes
    distancias: Dict[str, float] = Field(default_factory=dict, description="Distancias a servicios clave")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "direccion": "Av. Grecia 5678, Ñuñoa",
                "comuna": "Ñuñoa",
                "precio": 285000,
                "superficie_util": 65.0,
                "dormitorios": 2,
                "banos": 2,
                "estacionamientos": 1,
                "latitud": -33.4372,
                "longitud": -70.6506,
                "score_total": 89.5,
                "score_confianza": 0.92,
                "scores_por_categoria": [],
                "resumen_explicacion": "Excelente ubicación con acceso a metro y áreas verdes, sin colegios cercanos como preferiste",
                "puntos_fuertes": [
                    "🚇 Metro a 250m - ideal para transporte",
                    "🌳 Parque Bustamante a 400m",
                    "🏥 Consultorio a 600m",
                    "💰 Precio excelente para la zona",
                    "📍 Sin colegios en 800m de radio"
                ],
                "puntos_debiles": [
                    "🚗 Solo 1 estacionamiento",
                    "📏 Superficie menor a promedio"
                ],
                "distancias": {
                    "metro_m": 250,
                    "parque_m": 400,
                    "colegio_m": 850,
                    "consultorio_m": 600
                }
            }
        }


class RecomendacionesResponseML(BaseModel):
    """Response del endpoint de recomendaciones con ML"""
    total_encontradas: int = Field(..., description="Total de propiedades que cumplen filtros")
    total_analizadas: int = Field(..., description="Total de propiedades analizadas")
    recomendaciones: List[PropiedadRecomendadaML] = Field(..., description="Lista de recomendaciones")
    
    # Metadata
    preferencias_aplicadas: Dict[str, Any] = Field(..., description="Preferencias usadas")
    modelo_version: str = Field(..., description="Versión del modelo ML usado")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Sugerencias para mejorar búsqueda
    sugerencias: Optional[List[str]] = Field(None, description="Sugerencias para obtener mejores resultados")
