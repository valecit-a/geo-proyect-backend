"""
Servicio de Machine Learning
Carga y usa el modelo Random Forest optimizado
"""
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from pathlib import Path
from loguru import logger
from app.config import settings
from app.schemas.schemas import PrediccionRequest


class MLService:
    """Servicio para predicciones con el modelo ML"""
    
    def __init__(self):
        self.model = None
        self.model_metadata = {}
        self.comunas_permitidas = [
            'Estación Central', 'Santiago', 'Ñuñoa', 'La Reina'
        ]
        self.load_model()
    
    def load_model(self):
        """Carga el modelo desde disco (o usa modo sin modelo para desarrollo)"""
        try:
            model_path = Path(settings.MODEL_PATH)
            if not model_path.exists():
                logger.warning(f"⚠️  Modelo no encontrado en: {model_path}")
                logger.warning("⚠️  MLService funcionando en MODO DE DESARROLLO sin modelo")
                logger.warning("⚠️  Las predicciones devolverán valores simulados")
                self.model = None
                self.model_metadata = {'mode': 'development', 'r2_score': 0.0}
                return
            
            # Cargar modelo
            model_data = joblib.load(model_path)
            
            # El archivo .pkl puede ser solo el modelo o un dict con metadata
            if isinstance(model_data, dict):
                self.model = model_data.get('modelo', model_data.get('model'))
                self.model_metadata = {
                    'r2_score': model_data.get('r2_test', 0.914),
                    'rmse': model_data.get('rmse_test', 0.1324),
                    'mae': model_data.get('mae_test', 0.0984),
                    'version': '20251101_175356',
                    'overfitting': model_data.get('overfitting', 6.19)
                }
            else:
                self.model = model_data
                self.model_metadata = {
                    'r2_score': 0.914,
                    'rmse': 0.1324,
                    'mae': 0.0984,
                    'version': '20251101_175356',
                    'overfitting': 6.19
                }
            
            logger.info(f"✅ Modelo cargado exitosamente: {model_path}")
            logger.info(f"   R² Score: {self.model_metadata['r2_score']:.4f}")
            logger.info(f"   RMSE: {self.model_metadata['rmse']:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            raise
    
    def preparar_features(self, request: PrediccionRequest) -> pd.DataFrame:
        """
        Prepara las features en el formato que espera el modelo
        
        Features esperadas por el modelo (formato del entrenamiento):
        - banos_num, dormitorios_num, superficie_util_num (numéricas)
        - dist_transporte_km, dist_turismo_km, dist_salud_km, etc. (distancias)
        - comuna_* (dummies para las 4 comunas)
        """
        # Features numéricas con nombres del entrenamiento
        features = {
            'banos_num': request.banos,
            'dormitorios_num': request.dormitorios,
            'superficie_util_num': request.superficie,
        }
        
        # Distancias en km (nombres del modelo entrenado)
        # Usar valores promedio si no se proporcionan
        features['dist_transporte_km'] = request.dist_metro or 1.5
        features['dist_turismo_km'] = request.dist_mall or 2.5
        features['dist_salud_km'] = request.dist_hospital or 2.0
        features['dist_educacion_basica_km'] = request.dist_colegio or 1.0
        features['dist_educacion_superior_km'] = request.dist_colegio or 1.5 if request.dist_colegio else 1.5
        features['dist_areas_verdes_km'] = request.dist_area_verde or 1.2
        
        # Dummies de comuna (drop_first=False, todas las comunas están presentes)
        # Comunas en el dataset ordenadas alfabéticamente
        comunas_modelo = {
            'Estación Central': 'Estación Central',
            'La Reina': 'La Reina',
            'Santiago': 'Santiago',
            'Ñuñoa': 'Ñuñoa'
        }
        
        for comuna_modelo, comuna_usuario in comunas_modelo.items():
            col_name = f'comuna_{comuna_modelo}'
            features[col_name] = 1 if request.comuna == comuna_usuario else 0
        
        # Crear DataFrame
        df = pd.DataFrame([features])
        
        # Asegurar orden de columnas (DEBE coincidir EXACTAMENTE con el modelo)
        columnas_ordenadas = [
            'banos_num',
            'dormitorios_num',
            'superficie_util_num',
            'dist_transporte_km',
            'dist_turismo_km',
            'dist_salud_km',
            'dist_educacion_basica_km',
            'dist_educacion_superior_km',
            'dist_areas_verdes_km',
            'comuna_Estación Central',
            'comuna_La Reina',
            'comuna_Santiago',
            'comuna_Ñuñoa'
        ]
        
        df = df[columnas_ordenadas]
        
        logger.debug(f"Features preparadas: {df.to_dict(orient='records')[0]}")
        return df
    
    def predecir(self, request: PrediccionRequest) -> Dict:
        """
        Realiza predicción de precio
        
        Returns:
            dict con precio_log, precio, precio_min, precio_max
        """
        if self.model is None:
            raise ValueError("Modelo no cargado")
        
        # Preparar features
        X = self.preparar_features(request)
        
        # Predicción (el modelo predice log(precio))
        precio_log_pred = self.model.predict(X)[0]
        
        # Convertir de log a escala original
        precio_pred = np.exp(precio_log_pred)
        
        # Calcular intervalo de confianza (aproximado)
        # Usar el RMSE del modelo (0.1324) como medida de incertidumbre
        rmse = self.model_metadata['rmse']
        
        # Intervalo de confianza del 95% (≈ 2 * RMSE)
        margen_log = 1.96 * rmse
        precio_min = np.exp(precio_log_pred - margen_log)
        precio_max = np.exp(precio_log_pred + margen_log)
        
        resultado = {
            'precio_log': float(precio_log_pred),
            'precio': float(precio_pred),
            'precio_min': float(precio_min),
            'precio_max': float(precio_max),
            'precio_m2': float(precio_pred / request.superficie),
            'modelo_r2': self.model_metadata['r2_score'],
            'modelo_version': f"RF_optimizado_{self.model_metadata['version']}"
        }
        
        logger.info(f"✅ Predicción exitosa: {precio_pred:,.0f} CLP")
        return resultado
    
    def predecir_batch(self, requests: list[PrediccionRequest]) -> list[Dict]:
        """Predicciones en batch"""
        return [self.predecir(req) for req in requests]


# Instancia global del servicio
ml_service = MLService()
