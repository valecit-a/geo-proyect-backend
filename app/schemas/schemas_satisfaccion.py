"""
Schemas Pydantic para el sistema de predicción de satisfacción

Define los modelos de request/response para la API de satisfacción.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List
from enum import Enum


class TipoPropiedad(str, Enum):
    """Tipos de propiedad válidos"""
    DEPARTAMENTO = "departamento"
    CASA = "casa"


class ComunaValida(str, Enum):
    """Comunas válidas para predicción"""
    ESTACION_CENTRAL = "Estación Central"
    LA_REINA = "La Reina"
    NUNOA = "Ñuñoa"
    SANTIAGO = "Santiago"


class SatisfaccionRequest(BaseModel):
    """
    Request para predicción de satisfacción.
    
    El modelo predice la satisfacción residencial en escala 0-10
    basándose en las características de la propiedad y su ubicación.
    """
    
    # Características físicas (requeridas)
    superficie_util: float = Field(
        ...,
        gt=0,
        le=1000,
        description="Superficie útil en m²",
        examples=[85.0]
    )
    
    dormitorios: int = Field(
        ...,
        ge=1,
        le=10,
        description="Número de dormitorios",
        examples=[3]
    )
    
    banos: int = Field(
        ...,
        ge=1,
        le=10,
        description="Número de baños",
        examples=[2]
    )
    
    # Precio (requerido)
    precio_uf: float = Field(
        ...,
        gt=0,
        le=100000,
        description="Precio en UF (Unidades de Fomento)",
        examples=[5000.0]
    )
    
    # Ubicación
    comuna: ComunaValida = Field(
        default=ComunaValida.SANTIAGO,
        description="Comuna donde se ubica la propiedad"
    )
    
    tipo_propiedad: TipoPropiedad = Field(
        default=TipoPropiedad.DEPARTAMENTO,
        description="Tipo de propiedad"
    )
    
    # Coordenadas (opcionales)
    latitud: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitud de la propiedad (WGS84)",
        examples=[-33.4489]
    )
    
    longitud: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitud de la propiedad (WGS84)",
        examples=[-70.6693]
    )
    
    # Distancias a servicios (opcionales, en metros)
    dist_transporte_min_m: Optional[float] = Field(
        None,
        ge=0,
        description="Distancia mínima a transporte público (metros)"
    )
    
    dist_educacion_min_m: Optional[float] = Field(
        None,
        ge=0,
        description="Distancia mínima a educación (metros)"
    )
    
    dist_salud_min_m: Optional[float] = Field(
        None,
        ge=0,
        description="Distancia mínima a salud (metros)"
    )
    
    dist_areas_verdes_m: Optional[float] = Field(
        None,
        ge=0,
        description="Distancia a áreas verdes (metros)"
    )
    
    dist_comercio_m: Optional[float] = Field(
        None,
        ge=0,
        description="Distancia a comercio/supermercados (metros)"
    )
    
    @field_validator('latitud')
    @classmethod
    def validar_latitud_santiago(cls, v):
        """Validar que la latitud está en rango razonable para Santiago"""
        if v is not None and not (-33.7 <= v <= -33.2):
            raise ValueError('Latitud fuera del rango de Santiago (-33.7 a -33.2)')
        return v
    
    @field_validator('longitud')
    @classmethod
    def validar_longitud_santiago(cls, v):
        """Validar que la longitud está en rango razonable para Santiago"""
        if v is not None and not (-71.0 <= v <= -70.4):
            raise ValueError('Longitud fuera del rango de Santiago (-71.0 a -70.4)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "superficie_util": 85.0,
                "dormitorios": 3,
                "banos": 2,
                "precio_uf": 5000.0,
                "comuna": "Ñuñoa",
                "tipo_propiedad": "departamento",
                "latitud": -33.4489,
                "longitud": -70.6693,
                "dist_transporte_min_m": 500,
                "dist_areas_verdes_m": 300
            }
        }


class SatisfaccionDetalles(BaseModel):
    """Detalles adicionales de la predicción"""
    precio_m2_uf: float = Field(..., description="Precio por m² en UF")
    m2_por_dormitorio: float = Field(..., description="m² por dormitorio")
    ratio_bano_dorm: float = Field(..., description="Ratio baños/dormitorios")
    total_habitaciones: int = Field(..., description="Total de habitaciones")
    comuna: str = Field(..., description="Comuna de la propiedad")
    tipo: str = Field(..., description="Tipo de propiedad")


class SatisfaccionResponse(BaseModel):
    """
    Respuesta de predicción de satisfacción.
    
    Incluye:
    - Satisfacción predicha (0-10)
    - Interpretación del nivel
    - Confianza del modelo (R²)
    - Detalles de features calculadas
    """
    
    satisfaccion: float = Field(
        ...,
        ge=0,
        le=10,
        description="Satisfacción predicha (escala 0-10)",
        examples=[7.5]
    )
    
    nivel: str = Field(
        ...,
        description="Nivel interpretativo (Excelente/Bueno/Regular/Bajo)",
        examples=["Bueno"]
    )
    
    emoji: str = Field(
        ...,
        description="Emoji representativo del nivel",
        examples=["✅"]
    )
    
    descripcion: str = Field(
        ...,
        description="Descripción del nivel de satisfacción"
    )
    
    escala: str = Field(
        default="0-10",
        description="Escala de la predicción"
    )
    
    confianza: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confianza del modelo (R² del test)",
        examples=[0.87]
    )
    
    features_usadas: int = Field(
        ...,
        description="Número de features utilizadas en la predicción"
    )
    
    detalles: SatisfaccionDetalles = Field(
        ...,
        description="Detalles de las features calculadas"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "satisfaccion": 7.5,
                "nivel": "Bueno",
                "emoji": "✅",
                "descripcion": "Propiedad con buenas características",
                "escala": "0-10",
                "confianza": 0.87,
                "features_usadas": 42,
                "detalles": {
                    "precio_m2_uf": 58.82,
                    "m2_por_dormitorio": 28.33,
                    "ratio_bano_dorm": 0.67,
                    "total_habitaciones": 5,
                    "comuna": "Ñuñoa",
                    "tipo": "departamento"
                }
            }
        }


class ModeloSatisfaccionInfo(BaseModel):
    """Información sobre el modelo de satisfacción"""
    
    modelo_tipo: str = Field(
        ...,
        description="Tipo de modelo (LightGBM, RandomForest, etc.)"
    )
    
    modelo_disponible: bool = Field(
        ...,
        description="Si el modelo está cargado y disponible"
    )
    
    num_features: int = Field(
        ...,
        description="Número de features que usa el modelo"
    )
    
    metricas: Dict[str, Optional[float]] = Field(
        ...,
        description="Métricas de evaluación del modelo"
    )
    
    comunas_validas: List[str] = Field(
        ...,
        description="Lista de comunas válidas para predicción"
    )
    
    tipos_validos: List[str] = Field(
        ...,
        description="Tipos de propiedad válidos"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Versión del servicio"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "modelo_tipo": "LGBMRegressor",
                "modelo_disponible": True,
                "num_features": 42,
                "metricas": {
                    "r2_test": 0.8697,
                    "rmse_test": 0.328,
                    "mae_test": 0.245
                },
                "comunas_validas": ["Estación Central", "La Reina", "Ñuñoa", "Santiago"],
                "tipos_validos": ["departamento", "casa"],
                "version": "1.0.0"
            }
        }


class ComparacionRequest(BaseModel):
    """Request para comparar múltiples propiedades"""
    
    propiedades: List[SatisfaccionRequest] = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Lista de propiedades a comparar (2-20)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "propiedades": [
                    {
                        "superficie_util": 85.0,
                        "dormitorios": 3,
                        "banos": 2,
                        "precio_uf": 5000.0,
                        "comuna": "Ñuñoa",
                        "tipo_propiedad": "departamento"
                    },
                    {
                        "superficie_util": 120.0,
                        "dormitorios": 4,
                        "banos": 3,
                        "precio_uf": 8000.0,
                        "comuna": "La Reina",
                        "tipo_propiedad": "casa"
                    }
                ]
            }
        }


class PropiedadRanking(BaseModel):
    """Propiedad en el ranking de comparación"""
    ranking: int = Field(..., description="Posición en el ranking")
    id: int = Field(..., description="ID de la propiedad")
    direccion: str = Field(..., description="Dirección o identificador")
    satisfaccion: float = Field(..., description="Satisfacción predicha")
    nivel: str = Field(..., description="Nivel interpretativo")
    emoji: str = Field(..., description="Emoji del nivel")
    precio_uf: float = Field(..., description="Precio en UF")
    superficie: float = Field(..., description="Superficie útil")
    dormitorios: int = Field(..., description="Número de dormitorios")
    banos: int = Field(..., description="Número de baños")
    comuna: str = Field(..., description="Comuna")
    tipo: str = Field(..., description="Tipo de propiedad")


class ComparacionResponse(BaseModel):
    """Respuesta de comparación de propiedades"""
    
    total_comparadas: int = Field(
        ...,
        description="Número de propiedades comparadas"
    )
    
    ranking: List[PropiedadRanking] = Field(
        ...,
        description="Lista de propiedades ordenadas por satisfacción"
    )
    
    mejor_opcion: PropiedadRanking = Field(
        ...,
        description="Propiedad con mayor satisfacción"
    )
    
    promedio_satisfaccion: float = Field(
        ...,
        description="Satisfacción promedio del conjunto"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_comparadas": 2,
                "ranking": [
                    {
                        "ranking": 1,
                        "id": 2,
                        "direccion": "Propiedad 2",
                        "satisfaccion": 8.2,
                        "nivel": "Excelente",
                        "emoji": "🌟",
                        "precio_uf": 8000.0,
                        "superficie": 120.0,
                        "dormitorios": 4,
                        "banos": 3,
                        "comuna": "La Reina",
                        "tipo": "casa"
                    },
                    {
                        "ranking": 2,
                        "id": 1,
                        "direccion": "Propiedad 1",
                        "satisfaccion": 7.1,
                        "nivel": "Bueno",
                        "emoji": "✅",
                        "precio_uf": 5000.0,
                        "superficie": 85.0,
                        "dormitorios": 3,
                        "banos": 2,
                        "comuna": "Ñuñoa",
                        "tipo": "departamento"
                    }
                ],
                "mejor_opcion": {
                    "ranking": 1,
                    "id": 2,
                    "direccion": "Propiedad 2",
                    "satisfaccion": 8.2,
                    "nivel": "Excelente",
                    "emoji": "🌟",
                    "precio_uf": 8000.0,
                    "superficie": 120.0,
                    "dormitorios": 4,
                    "banos": 3,
                    "comuna": "La Reina",
                    "tipo": "casa"
                },
                "promedio_satisfaccion": 7.65
            }
        }
