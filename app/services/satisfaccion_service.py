"""
Servicio de Predicción de Satisfacción usando el modelo LightGBM

Este servicio implementa la predicción de satisfacción residencial
utilizando el modelo LightGBM entrenado con datos de propiedades en venta.

Características:
- Modelo LightGBM con R² = 0.8697
- 42 features (físicas, derivadas, distancias, comunas)
- Predicción en escala 0-10
- Interpretación automática del nivel de satisfacción

Autor: GeoInformática
Fecha: Enero 2025
"""
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from loguru import logger
import warnings
warnings.filterwarnings('ignore')

# Intentar importar LightGBM
try:
    import lightgbm as lgb
    LIGHTGBM_DISPONIBLE = True
except ImportError:
    LIGHTGBM_DISPONIBLE = False
    logger.warning("⚠️ LightGBM no instalado. Instalar con: pip install lightgbm")


class SatisfaccionService:
    """
    Servicio de predicción de satisfacción para propiedades inmobiliarias.
    
    Utiliza el modelo LightGBM entrenado en semana3_modelo_satisfaccion
    con R² = 0.8697 en el conjunto de test.
    
    Uso:
        service = SatisfaccionService()
        resultado = service.predecir_satisfaccion(
            superficie_util=80,
            dormitorios=3,
            banos=2,
            precio_uf=5000,
            comuna="Ñuñoa",
            tipo_propiedad="departamento",
            distancias={...}
        )
    """
    
    # Valor UF en CLP (actualizar periódicamente)
    VALOR_UF = 38500
    
    # Comunas válidas
    COMUNAS_VALIDAS = ['Estación Central', 'La Reina', 'Ñuñoa', 'Santiago']
    
    def __init__(self, modelo_path: Optional[Path] = None):
        """
        Inicializa el servicio cargando el modelo entrenado.
        
        Args:
            modelo_path: Ruta al archivo .pkl del modelo.
                        Si es None, busca en la ubicación por defecto.
        """
        # Determinar ruta del modelo
        if modelo_path is None:
            # Buscar en múltiples ubicaciones
            posibles_rutas = [
                Path(__file__).parent.parent / 'modelos' / 'modelo_satisfaccion_venta.pkl',
                Path('/home/felipe/Documentos/GeoInformatica/autocorrelacion_espacial/semana3_modelo_satisfaccion/modelos/modelo_satisfaccion_venta.pkl'),
                Path(__file__).parent.parent.parent / 'modelos' / 'modelo_satisfaccion_venta.pkl',
            ]
            
            for ruta in posibles_rutas:
                if ruta.exists():
                    modelo_path = ruta
                    break
            
            if modelo_path is None:
                raise FileNotFoundError(
                    "Modelo de satisfacción no encontrado. "
                    f"Buscado en: {[str(r) for r in posibles_rutas]}"
                )
        
        self.modelo_path = Path(modelo_path)
        self._cargar_modelo()
        
        logger.info(f"✅ SatisfaccionService inicializado")
        logger.info(f"   Modelo: {self.modelo_path.name}")
        logger.info(f"   Features: {len(self.features)}")
        logger.info(f"   R²: {self.metricas.get('r2_test', 'N/A')}")
    
    def _cargar_modelo(self):
        """Carga el modelo y sus componentes desde disco"""
        try:
            with open(self.modelo_path, 'rb') as f:
                data = pickle.load(f)
            
            self.modelo = data.get('modelo')
            self.scaler = data.get('scaler')
            self.features = data.get('features', [])
            self.metricas = data.get('metricas', {})
            self.perfiles = data.get('perfiles', {})
            
            if self.modelo is None:
                raise ValueError("El archivo pickle no contiene un modelo válido")
            
            logger.info(f"✅ Modelo cargado: {type(self.modelo).__name__}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            raise
    
    def _calcular_features_derivadas(
        self,
        superficie_util: float,
        dormitorios: int,
        banos: int,
        precio_uf: float
    ) -> Dict[str, float]:
        """
        Calcula features derivadas a partir de las características básicas.
        
        Args:
            superficie_util: Superficie útil en m²
            dormitorios: Número de dormitorios
            banos: Número de baños
            precio_uf: Precio en UF
        
        Returns:
            Dict con features derivadas calculadas
        """
        # Evitar división por cero
        dorms = max(1, dormitorios)
        sup = max(1, superficie_util)
        
        return {
            'precio_m2_uf': precio_uf / sup,
            'm2_por_dormitorio': superficie_util / dorms,
            'm2_por_habitante': superficie_util / (dorms * 2),  # Estimación: 2 personas por dormitorio
            'ratio_bano_dorm': banos / dorms,
            'total_habitaciones': dormitorios + banos,
        }
    
    def _preparar_features(
        self,
        superficie_util: float,
        dormitorios: int,
        banos: int,
        precio_uf: float,
        comuna: str,
        tipo_propiedad: str,
        distancias: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Prepara el vector de features para el modelo.
        
        Args:
            superficie_util: Superficie útil en m²
            dormitorios: Número de dormitorios
            banos: Número de baños
            precio_uf: Precio en UF
            comuna: Nombre de la comuna
            tipo_propiedad: 'departamento' o 'casa'
            distancias: Dict con distancias a servicios (en metros)
            **kwargs: Features adicionales
        
        Returns:
            DataFrame con las features preparadas
        """
        # Calcular features derivadas
        derivadas = self._calcular_features_derivadas(
            superficie_util, dormitorios, banos, precio_uf
        )
        
        # Construir diccionario de features
        feature_dict = {
            # Features básicas
            'superficie_util': superficie_util,
            'dormitorios': dormitorios,
            'banos': banos,
            'precio_uf': precio_uf,
            
            # Features derivadas
            **derivadas,
            
            # Tipo de propiedad
            'es_departamento': 1 if tipo_propiedad.lower() == 'departamento' else 0,
            'es_casa': 1 if tipo_propiedad.lower() == 'casa' else 0,
            
            # Comunas (one-hot encoding)
            'comuna_Estación Central': 1 if comuna == 'Estación Central' else 0,
            'comuna_La Reina': 1 if comuna == 'La Reina' else 0,
            'comuna_Ñuñoa': 1 if comuna == 'Ñuñoa' else 0,
            'comuna_Santiago': 1 if comuna == 'Santiago' else 0,
        }
        
        # Agregar distancias
        if distancias:
            for key, value in distancias.items():
                # Normalizar nombre de feature
                feat_name = key if key.startswith('dist_') else f'dist_{key}'
                feature_dict[feat_name] = value
        
        # Agregar kwargs adicionales
        feature_dict.update(kwargs)
        
        # Crear DataFrame con las features en el orden correcto
        X = pd.DataFrame([{feat: feature_dict.get(feat, 0) for feat in self.features}])
        
        # Rellenar NaN con 0
        X = X.fillna(0)
        
        return X
    
    def _interpretar_satisfaccion(self, satisfaccion: float) -> Tuple[str, str, str]:
        """
        Interpreta el nivel de satisfacción.
        
        Args:
            satisfaccion: Valor de satisfacción (0-10)
        
        Returns:
            Tupla (nivel, emoji, descripcion)
        """
        if satisfaccion >= 8:
            return "Excelente", "🌟", "Propiedad con características excepcionales"
        elif satisfaccion >= 6:
            return "Bueno", "✅", "Propiedad con buenas características"
        elif satisfaccion >= 4:
            return "Regular", "⚠️", "Propiedad con características promedio"
        else:
            return "Bajo", "❌", "Propiedad con características por debajo del promedio"
    
    def predecir_satisfaccion(
        self,
        superficie_util: float,
        dormitorios: int,
        banos: int,
        precio_uf: float,
        comuna: str = "Santiago",
        tipo_propiedad: str = "departamento",
        latitud: Optional[float] = None,
        longitud: Optional[float] = None,
        distancias: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> Dict:
        """
        Predice la satisfacción para una propiedad.
        
        Args:
            superficie_util: Superficie útil en m²
            dormitorios: Número de dormitorios (>= 1)
            banos: Número de baños (>= 1)
            precio_uf: Precio en UF
            comuna: Nombre de la comuna (default: Santiago)
            tipo_propiedad: 'departamento' o 'casa' (default: departamento)
            latitud: Latitud de la propiedad (opcional)
            longitud: Longitud de la propiedad (opcional)
            distancias: Dict con distancias a servicios en metros (opcional)
            **kwargs: Features adicionales
        
        Returns:
            Dict con:
                - satisfaccion: Valor numérico (0-10)
                - nivel: Texto interpretativo
                - emoji: Emoji representativo
                - descripcion: Descripción del nivel
                - confianza: Nivel de confianza del modelo
                - features_usadas: Número de features
                - detalles: Información adicional
        """
        try:
            # Validar inputs
            if superficie_util <= 0:
                raise ValueError("superficie_util debe ser > 0")
            if dormitorios < 1:
                raise ValueError("dormitorios debe ser >= 1")
            if banos < 1:
                raise ValueError("banos debe ser >= 1")
            if precio_uf <= 0:
                raise ValueError("precio_uf debe ser > 0")
            
            # Normalizar comuna
            if comuna not in self.COMUNAS_VALIDAS:
                logger.warning(f"Comuna '{comuna}' no reconocida, usando 'Santiago'")
                comuna = "Santiago"
            
            # Preparar features
            X = self._preparar_features(
                superficie_util=superficie_util,
                dormitorios=dormitorios,
                banos=banos,
                precio_uf=precio_uf,
                comuna=comuna,
                tipo_propiedad=tipo_propiedad,
                distancias=distancias,
                **kwargs
            )
            
            # Escalar features
            X_scaled = self.scaler.transform(X)
            
            # Predecir
            satisfaccion_raw = self.modelo.predict(X_scaled)[0]
            
            # Clampear a rango 0-10
            satisfaccion = float(np.clip(satisfaccion_raw, 0, 10))
            
            # Interpretar
            nivel, emoji, descripcion = self._interpretar_satisfaccion(satisfaccion)
            
            # Calcular features derivadas para respuesta
            derivadas = self._calcular_features_derivadas(
                superficie_util, dormitorios, banos, precio_uf
            )
            
            # Construir respuesta
            return {
                'satisfaccion': round(satisfaccion, 2),
                'nivel': nivel,
                'emoji': emoji,
                'descripcion': descripcion,
                'escala': '0-10',
                'confianza': round(self.metricas.get('r2_test', 0.87), 3),
                'features_usadas': len(self.features),
                'detalles': {
                    'precio_m2_uf': round(derivadas['precio_m2_uf'], 2),
                    'm2_por_dormitorio': round(derivadas['m2_por_dormitorio'], 2),
                    'ratio_bano_dorm': round(derivadas['ratio_bano_dorm'], 2),
                    'total_habitaciones': int(derivadas['total_habitaciones']),
                    'comuna': comuna,
                    'tipo': tipo_propiedad,
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error en predicción: {e}")
            raise
    
    def comparar_propiedades(self, propiedades: List[Dict]) -> pd.DataFrame:
        """
        Compara múltiples propiedades y genera un ranking.
        
        Args:
            propiedades: Lista de dicts con características de cada propiedad.
                        Cada dict debe tener al menos:
                        superficie_util, dormitorios, banos, precio_uf
        
        Returns:
            DataFrame con ranking ordenado por satisfacción
        """
        resultados = []
        
        for i, prop in enumerate(propiedades):
            try:
                pred = self.predecir_satisfaccion(**prop)
                resultados.append({
                    'id': prop.get('id', i + 1),
                    'direccion': prop.get('direccion', f'Propiedad {i + 1}'),
                    'satisfaccion': pred['satisfaccion'],
                    'nivel': pred['nivel'],
                    'emoji': pred['emoji'],
                    'precio_uf': prop.get('precio_uf', 0),
                    'superficie': prop.get('superficie_util', 0),
                    'dormitorios': prop.get('dormitorios', 0),
                    'banos': prop.get('banos', 0),
                    'comuna': prop.get('comuna', 'N/A'),
                    'tipo': prop.get('tipo_propiedad', 'N/A'),
                })
            except Exception as e:
                logger.warning(f"Error procesando propiedad {i}: {e}")
                continue
        
        if not resultados:
            return pd.DataFrame()
        
        df = pd.DataFrame(resultados)
        df = df.sort_values('satisfaccion', ascending=False)
        df['ranking'] = range(1, len(df) + 1)
        
        return df
    
    def get_info(self) -> Dict:
        """
        Retorna información sobre el modelo cargado.
        
        Returns:
            Dict con información del modelo
        """
        return {
            'modelo_tipo': type(self.modelo).__name__,
            'modelo_path': str(self.modelo_path),
            'num_features': len(self.features),
            'features': self.features,
            'metricas': {
                'r2_test': self.metricas.get('r2_test'),
                'rmse_test': self.metricas.get('rmse_test'),
                'mae_test': self.metricas.get('mae_test'),
            },
            'comunas_validas': self.COMUNAS_VALIDAS,
            'tipos_validos': ['departamento', 'casa'],
            'escala_prediccion': '0-10',
            'version': '1.0.0',
        }


# Instancia global para uso en la API
_satisfaccion_service: Optional[SatisfaccionService] = None


def get_satisfaccion_service() -> Optional[SatisfaccionService]:
    """
    Obtiene la instancia global del servicio de satisfacción.
    
    Returns:
        Instancia de SatisfaccionService o None si no está disponible
    """
    global _satisfaccion_service
    
    if _satisfaccion_service is None:
        try:
            _satisfaccion_service = SatisfaccionService()
        except Exception as e:
            logger.error(f"❌ No se pudo inicializar SatisfaccionService: {e}")
            return None
    
    return _satisfaccion_service


# Para inicialización automática al importar
def inicializar_servicio():
    """Intenta inicializar el servicio de satisfacción"""
    try:
        return get_satisfaccion_service()
    except Exception as e:
        logger.warning(f"Servicio de satisfacción no disponible: {e}")
        return None


# Inicializar al importar (silencioso si falla)
satisfaccion_service = inicializar_servicio()
