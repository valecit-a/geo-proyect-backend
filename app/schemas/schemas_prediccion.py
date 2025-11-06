"""
Schemas para predicción de precios usando modelos ML de Semana 3
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict


class PrediccionRequest(BaseModel):
    """
    Request para predicción de precio por m².
    
    El sistema calcula automáticamente:
    - Features derivadas (m2_por_habitante, total_habitaciones, ratio_bano_dorm)
    - 42 densidades espaciales a partir de latitud/longitud
    - Predicción usando modelos RF + GWRF + Stacking
    """
    
    # Características físicas básicas
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
    
    estacionamientos: int = Field(
        default=0, 
        ge=0, 
        le=10,
        description="Número de estacionamientos"
    )
    
    bodegas: int = Field(
        default=0, 
        ge=0, 
        le=5,
        description="Número de bodegas"
    )
    
    # Ubicación (para calcular densidades espaciales)
    latitud: float = Field(
        ..., 
        ge=-90, 
        le=90,
        description="Latitud de la propiedad (WGS84)",
        examples=[-33.4489]
    )
    
    longitud: float = Field(
        ..., 
        ge=-180, 
        le=180,
        description="Longitud de la propiedad (WGS84)",
        examples=[-70.6693]
    )
    
    # Opcional
    cant_max_habitantes: Optional[int] = Field(
        None, 
        ge=1, 
        le=20,
        description="Habitantes máximos (si no se especifica, se estima como dormitorios × 2)"
    )
    
    usar_stacking: bool = Field(
        default=True,
        description="Si True, usa meta-modelo stacking (mejor R²=0.489). Si False, usa GWRF por cluster."
    )
    
    @field_validator('latitud')
    @classmethod
    def validar_latitud_santiago(cls, v):
        """Validar que la latitud está en rango razonable para Santiago"""
        if not (-33.7 <= v <= -33.2):
            raise ValueError('Latitud fuera del rango de Santiago (-33.7 a -33.2)')
        return v
    
    @field_validator('longitud')
    @classmethod
    def validar_longitud_santiago(cls, v):
        """Validar que la longitud está en rango razonable para Santiago"""
        if not (-71.0 <= v <= -70.4):
            raise ValueError('Longitud fuera del rango de Santiago (-71.0 a -70.4)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "superficie_util": 85.0,
                "dormitorios": 3,
                "banos": 2,
                "estacionamientos": 1,
                "bodegas": 1,
                "latitud": -33.4489,
                "longitud": -70.6693,
                "cant_max_habitantes": 6,
                "usar_stacking": True
            }
        }


class PrediccionResponse(BaseModel):
    """
    Respuesta de predicción de precio.
    
    Incluye:
    - Precio predicho por m² y total
    - Nivel de confianza del modelo
    - Método usado (stacking, gwrf_cluster, fallback)
    - Predicciones de modelos base
    - Features calculadas automáticamente
    """
    
    precio_m2_predicho: float = Field(
        ...,
        description="Precio predicho por m² (UF)",
        examples=[45.5]
    )
    
    precio_total_estimado: float = Field(
        ...,
        description="Precio total estimado (UF)",
        examples=[3867.5]
    )
    
    confianza: float = Field(
        ..., 
        ge=0, 
        le=1,
        description="Nivel de confianza del modelo (0=baja, 1=alta)"
    )
    
    metodo: str = Field(
        ...,
        description="Método de predicción usado",
        examples=["stacking", "gwrf_cluster", "fallback"]
    )
    
    cluster_asignado: int = Field(
        ...,
        description="ID del cluster espacial asignado (0-4)"
    )
    
    predicciones_base: Dict[str, float] = Field(
        ...,
        description="Predicciones de cada modelo base (rf_global, gwrf_cluster, gwrf_densidad)"
    )
    
    features_calculadas: Dict[str, float] = Field(
        ...,
        description="Features derivadas calculadas automáticamente"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "precio_m2_predicho": 45.5,
                "precio_total_estimado": 3867.5,
                "confianza": 0.75,
                "metodo": "stacking",
                "cluster_asignado": 2,
                "predicciones_base": {
                    "rf_global": 44.2,
                    "gwrf_cluster": 46.8,
                    "gwrf_densidad": 45.0
                },
                "features_calculadas": {
                    "m2_por_habitante": 14.17,
                    "total_habitaciones": 5,
                    "ratio_bano_dorm": 0.67
                }
            }
        }


class ModeloInfo(BaseModel):
    """Información sobre los modelos cargados"""
    
    modelos_disponibles: Dict[str, bool] = Field(
        ...,
        description="Indica qué modelos están cargados y disponibles"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Versión del servicio de predicción"
    )
    
    metricas: Optional[Dict[str, Dict[str, float]]] = Field(
        None,
        description="Métricas de evaluación de cada modelo (R², RMSE, MAE)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "modelos_disponibles": {
                    "stacking": True,
                    "gwrf_cluster": True,
                    "gwrf_densidad": False
                },
                "version": "1.0.0",
                "metricas": {
                    "stacking": {
                        "r2": 0.489,
                        "rmse": 25288,
                        "mae": 4173
                    },
                    "gwrf_cluster": {
                        "r2": 0.039,
                        "rmse": 34677,
                        "mae": 4719
                    }
                }
            }
        }
