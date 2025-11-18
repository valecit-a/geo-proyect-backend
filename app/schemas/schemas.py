"""
Schemas Pydantic para validación y serialización
Request/Response models
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================================
# SCHEMAS DE PROPIEDAD
# ============================================================================

class PropiedadCreate(BaseModel):
    """Schema para crear una propiedad"""
    comuna: str
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    
    superficie_total: float = Field(..., gt=0)
    superficie_construida: Optional[float] = None
    dormitorios: int = Field(..., ge=1)
    banos: int = Field(..., ge=1)
    estacionamientos: int = Field(0, ge=0)
    
    dist_metro: Optional[float] = None
    dist_supermercado: Optional[float] = None
    dist_area_verde: Optional[float] = None
    dist_colegio: Optional[float] = None
    dist_hospital: Optional[float] = None
    dist_mall: Optional[float] = None
    
    precio: Optional[float] = None
    fuente: Optional[str] = "manual"
    descripcion: Optional[str] = None


class PropiedadResponse(BaseModel):
    """Schema de respuesta de propiedad"""
    id: int
    comuna: str
    direccion: Optional[str]
    superficie_total: float
    dormitorios: int
    banos: int
    precio: Optional[float]
    precio_predicho: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS DE COMUNA
# ============================================================================

class ComunaStats(BaseModel):
    """Estadísticas de una comuna"""
    nombre: str
    total_propiedades: int
    precio_promedio: Optional[float]
    precio_m2_promedio: Optional[float]
    
    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS GENERALES
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str
    modelo: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response estándar"""
    detail: str
    timestamp: datetime


# ============================================================================
# SCHEMAS DE PREDICCIÓN ML
# ============================================================================

class PrediccionRequest(BaseModel):
    """Request para predicción de precio"""
    superficie: float = Field(..., gt=0)
    dormitorios: int = Field(..., ge=1)
    banos: int = Field(..., ge=1)
    comuna: str
    dist_metro: Optional[float] = None
    dist_supermercado: Optional[float] = None
    dist_area_verde: Optional[float] = None
    dist_colegio: Optional[float] = None
    dist_hospital: Optional[float] = None
    dist_mall: Optional[float] = None


# ============================================================================
# SCHEMAS DE RECOMENDACIÓN (SISTEMA ANTIGUO)
# ============================================================================

class PreferenciasUsuario(BaseModel):
    """Preferencias del usuario para recomendaciones"""
    presupuesto_min: Optional[float] = None
    presupuesto_max: Optional[float] = None
    dormitorios_min: int = 1
    dormitorios_max: Optional[int] = None
    banos_min: int = 1
    superficie_min: float = 30.0
    superficie_max: Optional[float] = None
    # Legacy single/multi-comuna fields
    comunas: Optional[List[str]] = None
    comunas_preferidas: Optional[List[str]] = None
    comuna_seleccionada: Optional[str] = None
    # Tipo de inmueble preferido (ej: 'Casa', 'Departamento', 'Bungalow', ...)
    tipo_inmueble_preferido: Optional[str] = None
    # Ruido ambiente: bajo/medio/alto
    ruido_ambiente: Optional['RuidoAmbiente'] = None
    # Preferencias urbanas más detalladas (cercanía a comercio, transporte, parques, tranquilidad)
    preferencias_urbanas: Optional['PreferenciasUrbanas'] = None
    dist_metro_max: Optional[float] = None
    dist_supermercado_max: Optional[float] = None
    
    # Prioridades (0-10) - si no se especifican, se asume 5 por defecto
    # Si usuario NO responde una categoría, debe ser 0 para no afectar scoring
    prioridad_precio: int = Field(5, ge=0, le=10)
    prioridad_ubicacion: int = Field(5, ge=0, le=10)
    prioridad_transporte: int = Field(0, ge=0, le=10)  # 0 si usuario no respondió
    prioridad_educacion: int = Field(0, ge=0, le=10)   # 0 si usuario no respondió
    prioridad_salud: int = Field(0, ge=0, le=10)       # 0 si usuario no respondió
    prioridad_areas_verdes: int = Field(0, ge=0, le=10)  # 0 si usuario no respondió
    prioridad_tamano: int = Field(5, ge=0, le=10)
    
    # Características a EVITAR (opcional)
    evitar_colegios: bool = False
    evitar_hospitales: bool = False
    evitar_metro: bool = False
    evitar_areas_verdes: bool = False
    
    # Requisitos específicos
    requiere_estacionamiento: bool = False
    piso_maximo: Optional[int] = None

    @validator('comunas_preferidas', pre=True, always=False)
    def _copy_legacy_comunas(cls, v, values):
        """Compatibilidad: si el cliente envía `comunas` antiguo, copiarlo a `comunas_preferidas`."""
        if v is None and values.get('comunas'):
            return values.get('comunas')
        return v


class ScoreDetallado(BaseModel):
    """Detalles del score de una propiedad"""
    score_total: float
    score_precio: float
    score_ubicacion: float
    score_caracteristicas: float


class PropiedadRecomendada(BaseModel):
    """Propiedad con score de recomendación"""
    id: int
    comuna: str
    superficie_total: float
    dormitorios: int
    banos: int
    precio: Optional[float]
    score: ScoreDetallado
    
    class Config:
        from_attributes = True


class RuidoAmbiente(str, Enum):
    """Enum para nivel de ruido"""
    BAJO = 'bajo'
    MEDIO = 'medio'
    ALTO = 'alto'


class PreferenciasUrbanas(BaseModel):
    """Preferencias relacionadas con la urbanidad del entorno"""
    cerca_comercio: Optional[bool] = None
    cerca_transporte: Optional[bool] = None
    cerca_areas_verdes: Optional[bool] = None
    tranquilo: Optional[bool] = None
    # Permite pasar pesos/orden de prioridad por categoría
    prioridad: Optional[Dict[str, float]] = None


# Resolver forward refs (ruido y urbanas se referenciaban antes de ser declaradas)
PreferenciasUsuario.update_forward_refs()


# ============================================================================
# SCHEMAS DE PUNTOS DE INTERÉS
# ============================================================================

class PuntoInteresBase(BaseModel):
    """Schema base para punto de interés"""
    tipo: str
    nombre: str
    latitud: float
    longitud: float
    direccion: Optional[str] = None
    distancia: Optional[float] = None  # Distancia en metros desde punto de consulta


class PuntoInteresResponse(PuntoInteresBase):
    """Schema de respuesta para punto de interés"""
    id: int
    
    class Config:
        from_attributes = True


class PuntosInteresCercanosResponse(BaseModel):
    """Schema de respuesta para puntos de interés cercanos"""
    metros: List[PuntoInteresResponse] = []
    colegios: List[PuntoInteresResponse] = []
    centros_medicos: List[PuntoInteresResponse] = []
    supermercados: List[PuntoInteresResponse] = []
    parques: List[PuntoInteresResponse] = []
    farmacias: List[PuntoInteresResponse] = []
    comisarias: List[PuntoInteresResponse] = []
    bomberos: List[PuntoInteresResponse] = []
    total_encontrados: int = 0
