# 🏠 Servicio de Predicción ML - Integración Semana 3

## 📌 Descripción

Este servicio integra los modelos de Machine Learning de la Semana 3 (Random Forest + GWRF + Stacking) en el backend para predecir el **precio por m²** de propiedades.

## 🚀 Endpoints Disponibles

### 1. POST `/api/v1/predecir-precio`

Predice el precio por m² de una propiedad.

**Request:**
```json
{
  "superficie_util": 85.0,
  "dormitorios": 3,
  "banos": 2,
  "estacionamientos": 1,
  "bodegas": 1,
  "latitud": -33.4489,
  "longitud": -70.6693,
  "cant_max_habitantes": 6,
  "usar_stacking": true
}
```

**Response:**
```json
{
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
```

**Ejemplo con curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/predecir-precio" \
  -H "Content-Type: application/json" \
  -d '{
    "superficie_util": 85.0,
    "dormitorios": 3,
    "banos": 2,
    "estacionamientos": 1,
    "bodegas": 1,
    "latitud": -33.4489,
    "longitud": -70.6693
  }'
```

### 2. GET `/api/v1/modelo-info`

Retorna información sobre los modelos ML disponibles.

**Response:**
```json
{
  "modelos_disponibles": {
    "stacking": true,
    "gwrf_cluster": true,
    "gwrf_densidad": false
  },
  "version": "1.0.0",
  "metricas": {
    "stacking": {
      "r2": 0.489,
      "rmse": 25288.0,
      "mae": 4173.0
    },
    "gwrf_cluster": {
      "r2": 0.039,
      "rmse": 34677.0,
      "mae": 4719.0
    }
  }
}
```

## 📂 Archivos Creados

```
geo-proyect-backend/
├── app/
│   ├── services/
│   │   └── ml_prediccion_service.py    # ✅ NUEVO: Servicio de predicción
│   ├── schemas/
│   │   └── schemas_prediccion.py       # ✅ NUEVO: Schemas request/response
│   └── api/
│       └── routes.py                   # ✅ MODIFICADO: +2 endpoints
└── modelos/                            # ✅ NUEVA CARPETA
    ├── gwrf_por_cluster.pkl           # Modelo GWRF por cluster
    ├── meta_model_stack.pkl           # Meta-modelo stacking
    └── README.md                      # Este archivo
```

## 🔧 Configuración

### 1. Copiar Modelos Entrenados

Los modelos entrenados deben estar en `geo-proyect-backend/modelos/`:

```bash
# Desde el directorio raíz del proyecto
cp autocorrelacion_espacial/semana3_modelo_satisfaccion/resultados/gwrf/*.pkl \
   geo-proyect-backend/modelos/
```

**Archivos requeridos:**
- `gwrf_por_cluster.pkl` - Modelos GWRF por cluster + KMeans
- `meta_model_stack.pkl` - Meta-modelo stacking (Ridge)

### 2. Instalar Dependencias

El servicio requiere las siguientes librerías:

```bash
cd geo-proyect-backend
pip install scikit-learn==1.3.0 pandas numpy
```

O agregar a `requirements.txt`:
```
scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
```

### 3. Iniciar el Backend

```bash
cd geo-proyect-backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verificar Funcionamiento

```bash
# Verificar que los modelos están cargados
curl http://localhost:8000/api/v1/modelo-info

# Hacer una predicción de prueba
curl -X POST "http://localhost:8000/api/v1/predecir-precio" \
  -H "Content-Type: application/json" \
  -d '{
    "superficie_util": 85.0,
    "dormitorios": 3,
    "banos": 2,
    "latitud": -33.4489,
    "longitud": -70.6693
  }'
```

## 📊 Modelos Utilizados

### Arquitectura

```
┌─────────────────┐
│  Propiedad      │
│  (superficie,   │
│   dormitorios,  │
│   lat, lon)     │
└────────┬────────┘
         │
         ├─────────────────────┐
         │                     │
         v                     v
┌────────────────┐    ┌─────────────────┐
│ Features       │    │ Densidades      │
│ Derivadas      │    │ Espaciales      │
│ (auto)         │    │ (42 features)   │
└────────┬───────┘    └────────┬────────┘
         │                     │
         └──────────┬──────────┘
                    │
         ┌──────────v──────────┐
         │  RF Global          │
         │  GWRF Cluster       │
         │  GWRF Densidad      │
         └──────────┬──────────┘
                    │
         ┌──────────v──────────┐
         │  Meta-Modelo        │
         │  (Stacking)         │
         └──────────┬──────────┘
                    │
                    v
         ┌──────────────────────┐
         │  Precio por m²       │
         │  + Confianza         │
         └──────────────────────┘
```

### Métricas de Evaluación

| Modelo | R² | RMSE (UF/m²) | MAE (UF/m²) |
|--------|-----|--------------|-------------|
| RF Global | 0.028 | 34,876 | 4,839 |
| GWRF Cluster | 0.039 | 34,677 | 4,719 |
| GWRF Densidad | 0.027 | 34,893 | 4,781 |
| **Stacking** | **0.489** | **25,288** | **4,173** |

### Features Utilizadas

**Base (5):**
- superficie_util
- dormitorios
- banos
- estacionamientos
- bodegas

**Derivadas (3):**
- m2_por_habitante = superficie_util / cant_max_habitantes
- total_habitaciones = dormitorios + banos
- ratio_bano_dorm = banos / dormitorios

**Espaciales (42 densidades):**
- Educación: básica, superior, parvularia (3 categorías × 3 radios = 9)
- Salud: general, clínicas (2 × 3 = 6)
- Transporte: metro, carga (2 × 3 = 6)
- Seguridad: PDI, cuarteles, bomberos (3 × 3 = 9)
- Amenidades: áreas verdes, ocio, turismo (3 × 3 = 9)
- Total: (3 × 3 = 9)

**Radios:** 300m, 600m, 1000m

## 🎯 Cómo Funciona

### Flujo de Predicción

1. **Usuario envía request** con características de la propiedad
2. **Servicio calcula features derivadas** automáticamente
3. **Servicio calcula densidades espaciales** desde lat/lon (42 features)
4. **Modelos base predicen** precio_m2:
   - RF Global
   - GWRF por Cluster (usando KMeans)
   - GWRF por Densidad
5. **Meta-modelo combina** predicciones base
6. **Retorna** precio final + confianza + detalles

### Niveles de Confianza

- **0.7 - 1.0 (Alta):** Predicción confiable, basada en modelos bien entrenados
- **0.3 - 0.7 (Media):** Predicción razonable, puede tener variabilidad
- **0.0 - 0.3 (Baja):** Usar con precaución, pocos datos en ese cluster

## ⚠️ Limitaciones Actuales

### 1. Cálculo de Densidades

**Actual:** Usa valores mock basados en ubicación general (centro/oriente/otras zonas).

**Producción:** Debe:
1. Cargar servicios georreferenciados (GeoJSON)
2. Usar cKDTree para distancias
3. Contar servicios en buffers reales
4. Normalizar por área del buffer

### 2. Modelos No Cargados

Si los archivos `.pkl` no existen, el servicio usa predicción **fallback**:
- Regla simple basada en características
- Confianza = 0.2 (baja)
- Método = 'fallback_simple'

### 3. Validación de Coordenadas

Solo valida rango de Santiago:
- Latitud: -33.7 a -33.2
- Longitud: -71.0 a -70.4

## 🚀 Próximos Pasos

### Sprint 1: Mejorar Cálculo de Densidades
- [ ] Cargar GeoJSON de servicios
- [ ] Implementar cKDTree para distancias
- [ ] Calcular densidades reales en buffers
- [ ] Cachear resultados por coordenadas

### Sprint 2: Reentrenar Modelos
- [ ] Agregar más datos de entrenamiento
- [ ] Feature engineering adicional
- [ ] Probar XGBoost/LightGBM
- [ ] Validación cruzada estratificada

### Sprint 3: Producción
- [ ] Agregar logging detallado
- [ ] Implementar monitoreo de drift
- [ ] A/B testing de versiones
- [ ] Documentación completa

## 📚 Referencias

- **Documentación completa:** Ver `ANALISIS_INTEGRACION_BACKEND_FRONTEND.md`
- **Modelos de Semana 3:** `autocorrelacion_espacial/semana3_modelo_satisfaccion/`
- **API Docs:** `http://localhost:8000/docs` (cuando el servidor esté corriendo)

## 📧 Soporte

Para problemas o preguntas:
1. Verificar logs del servidor
2. Probar endpoint `/modelo-info` para ver modelos disponibles
3. Revisar documentación en `/docs`
