# 🏠 Backend Inmobiliario - API de Predicción de Precios y Satisfacción

Backend profesional en Python con FastAPI para predicción de precios y **satisfacción residencial** usando Machine Learning y datos geoespaciales.

## 🆕 Nuevo: Modelo de Satisfacción (LightGBM)

Se ha integrado un nuevo modelo de predicción de satisfacción residencial:

- **Algoritmo**: LightGBM
- **R² Test**: 0.8697 (86.97% de varianza explicada)
- **RMSE**: 0.3280
- **Features**: 42 características (físicas, derivadas, distancias, comunas)
- **Escala**: 0-10 (Excelente/Bueno/Regular/Bajo)

### Nuevos Endpoints
- `POST /api/v1/predecir-satisfaccion` - Predecir satisfacción de una propiedad
- `GET /api/v1/satisfaccion-info` - Información del modelo
- `POST /api/v1/comparar-propiedades` - Comparar múltiples propiedades

### Archivos Nuevos
- `app/services/satisfaccion_service.py` - Servicio de satisfacción
- `app/schemas/schemas_satisfaccion.py` - Schemas Pydantic
- `modelos/modelo_satisfaccion_venta.pkl` - Modelo LightGBM
- `scripts/cargar_datos_propiedades.py` - Cargar datos GeoJSON
- `scripts/migracion_satisfaccion.sql` - Migración de BD

---

## 📋 Características

- ✅ **API REST** con FastAPI
- ✅ **PostgreSQL + PostGIS** para datos geoespaciales
- ✅ **Machine Learning** con Random Forest optimizado (R² = 0.914)
- ✅ **Satisfacción** con LightGBM (R² = 0.87) - **NUEVO**
- ✅ **Validación de datos** con Pydantic
- ✅ **Documentación automática** con Swagger/ReDoc
- ✅ **Logging estructurado** con Loguru
- ✅ **CORS** configurado
- ✅ **Arquitectura limpia** y escalable

## 🗂️ Estructura del Proyecto

```
geo-proyect-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicación FastAPI principal
│   ├── config.py            # Configuración (variables de entorno)
│   ├── database.py          # Conexión a PostgreSQL/PostGIS
│   ├── models.py            # Modelos ORM (SQLAlchemy)
│   ├── schemas.py           # Schemas Pydantic (validación)
│   ├── routes.py            # Endpoints de la API
│   └── ml_service.py        # Servicio de Machine Learning
│
├── scripts/
│   ├── init_db.py           # Inicialización de base de datos
│   └── test_model.py        # Test del modelo ML
│
├── logs/                    # Logs de la aplicación
├── .env                     # Variables de entorno
├── .gitignore
├── requirements.txt         # Dependencias
├── run.sh                   # Script de inicio
└── README.md               # Este archivo
```

## 🚀 Instalación

### 1. Requisitos previos

- Python 3.12+
- PostgreSQL 14+ con PostGIS
- pgAdmin (opcional, para gestión visual)

### 2. Clonar y preparar

```bash
cd /home/felipe/Documentos/GeoInformatica/geo-proyect-backend
```

### 3. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar base de datos

#### Opción A: Usar PostgreSQL existente

Abre pgAdmin y crea la base de datos:

```sql
CREATE DATABASE inmobiliario_db;
```

#### Opción B: Crear desde terminal

```bash
psql -U postgres -c "CREATE DATABASE inmobiliario_db;"
```

### 6. Verificar configuración

Edita `.env` si necesitas cambiar credenciales:

```bash
nano .env
```

Variables principales:
- `DB_USER=postgres`
- `DB_PASSWORD=felipeb222`
- `DB_NAME=inmobiliario_db`
- `MODEL_PATH=../autocorrelacion_espacial/semana4_recoleccion_datos/modelo_rf_optimizado_20251101_175356.pkl`

### 7. Inicializar base de datos

```bash
python scripts/init_db.py
```

Esto creará:
- Extensión PostGIS
- Todas las tablas (propiedades, comunas, predicciones)
- 6 comunas iniciales

### 8. Probar el modelo ML

```bash
python scripts/test_model.py
```

Debe mostrar una predicción exitosa.

## 🎮 Uso

### Iniciar el servidor

```bash
# Opción 1: Con script
chmod +x run.sh
./run.sh

# Opción 2: Directo con uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en:
- **API**: http://localhost:8000
- **Documentación Swagger**: http://localhost:8000/docs
- **Documentación ReDoc**: http://localhost:8000/redoc

## 📡 Endpoints de la API

### 🏥 Sistema

#### `GET /api/v1/health`
Health check del sistema

```bash
curl http://localhost:8000/api/v1/health
```

### 🔮 Predicciones

#### `POST /api/v1/prediccion`
Predice el precio de una propiedad

**Request:**
```json
{
  "superficie": 85.0,
  "dormitorios": 2,
  "banos": 2,
  "comuna": "Providencia",
  "dist_metro": 0.5,
  "dist_supermercado": 0.3,
  "dist_area_verde": 0.8,
  "dist_colegio": 0.6,
  "dist_hospital": 1.2,
  "dist_mall": 1.5
}
```

**Response:**
```json
{
  "precio_predicho": 165000000,
  "precio_log": 18.92,
  "precio_min": 140000000,
  "precio_max": 190000000,
  "precio_m2": 1941176,
  "modelo_r2": 0.914,
  "modelo_version": "RF_optimizado_20251101",
  "timestamp": "2025-11-01T18:30:00",
  "inputs": { ... }
}
```

**Ejemplo con curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/prediccion" \
  -H "Content-Type: application/json" \
  -d '{
    "superficie": 85.0,
    "dormitorios": 2,
    "banos": 2,
    "comuna": "Providencia",
    "dist_metro": 0.5
  }'
```

#### `GET /api/v1/predicciones/historial`
Obtiene el historial de predicciones

```bash
curl "http://localhost:8000/api/v1/predicciones/historial?limit=10"
```

### 🏘️ Propiedades

#### `POST /api/v1/propiedades`
Crea una nueva propiedad

```bash
curl -X POST "http://localhost:8000/api/v1/propiedades" \
  -H "Content-Type: application/json" \
  -d '{
    "comuna": "Providencia",
    "direccion": "Av. Providencia 1234",
    "superficie_total": 85.0,
    "dormitorios": 2,
    "banos": 2
  }'
```

#### `GET /api/v1/propiedades`
Lista propiedades con filtros

```bash
# Todas
curl "http://localhost:8000/api/v1/propiedades"

# Filtrar por comuna
curl "http://localhost:8000/api/v1/propiedades?comuna=Providencia&limit=20"
```

#### `GET /api/v1/propiedades/{id}`
Obtiene una propiedad específica

```bash
curl "http://localhost:8000/api/v1/propiedades/1"
```

### 🗺️ Comunas

#### `GET /api/v1/comunas`
Lista todas las comunas con estadísticas

```bash
curl "http://localhost:8000/api/v1/comunas"
```

#### `GET /api/v1/comunas/{nombre}`
Obtiene información detallada de una comuna

```bash
curl "http://localhost:8000/api/v1/comunas/Providencia"
```

### 📊 Estadísticas

#### `GET /api/v1/stats/general`
Estadísticas generales del sistema

```bash
curl "http://localhost:8000/api/v1/stats/general"
```

## 🧪 Testing

### Test del modelo ML
```bash
python scripts/test_model.py
```

### Test de endpoints (con pytest)
```bash
pytest
```

## 📊 Modelo ML

El backend usa el modelo **Random Forest optimizado** entrenado previamente:

- **R² Score**: 0.914 (explica 91.4% de la varianza)
- **RMSE**: 0.1324 (error en log-precio)
- **MAE**: 0.0984
- **Features**: 16 (9 numéricas + 7 dummies de comuna)
- **Hiperparámetros optimizados**:
  - n_estimators: 200
  - max_depth: 20
  - max_features: 'log2'
  - bootstrap: False

### Comunas soportadas:
- Vitacura (referencia)
- Las Condes
- Providencia
- Santiago
- Ñuñoa
- La Reina

## 🗄️ Base de Datos

### Tablas principales:

1. **comunas**: Comunas de Santiago con geometría
2. **propiedades**: Propiedades inmobiliarias
3. **predicciones**: Historial de predicciones

### Acceder con pgAdmin:

1. Abrir pgAdmin
2. Conectar a servidor: localhost:5432
3. Usuario: postgres
4. Contraseña: felipeb222
5. Base de datos: inmobiliario_db

### Queries útiles:

```sql
-- Ver todas las comunas
SELECT * FROM comunas;

-- Ver propiedades recientes
SELECT id, comuna_id, superficie_total, dormitorios, banos, precio_predicho
FROM propiedades
ORDER BY created_at DESC
LIMIT 10;

-- Ver historial de predicciones
SELECT superficie, dormitorios, banos, comuna, precio_predicho, created_at
FROM predicciones
ORDER BY created_at DESC
LIMIT 10;

-- Estadísticas por comuna
SELECT 
    c.nombre,
    COUNT(p.id) as total_propiedades,
    AVG(p.precio_predicho) as precio_promedio
FROM comunas c
LEFT JOIN propiedades p ON c.id = p.comuna_id
GROUP BY c.nombre;
```

## 📝 Logging

Los logs se guardan en:
- **Consola**: Output colorizado en tiempo real
- **Archivo**: `logs/app.log` (rotación automática cada 10MB)

Niveles de log:
- INFO: Operaciones normales
- WARNING: Advertencias
- ERROR: Errores
- DEBUG: Información detallada (solo en desarrollo)

## 🔒 Seguridad

Para producción, recuerda:

1. Cambiar `SECRET_KEY` en `.env`
2. Cambiar contraseña de PostgreSQL
3. Configurar CORS apropiadamente
4. Usar HTTPS
5. Implementar autenticación (JWT)
6. Rate limiting

## 🚢 Despliegue

### Docker (próximamente)

```dockerfile
# Dockerfile incluido en futuras versiones
```

### Servicios cloud:

- **Render**: Deploy directo desde Git
- **Railway**: PostgreSQL + FastAPI automático
- **Heroku**: Con add-on PostgreSQL
- **AWS EC2 + RDS**: Más control y escalabilidad

## 🐛 Troubleshooting

### Error: "can't connect to database"
```bash
# Verificar que PostgreSQL está corriendo
sudo systemctl status postgresql

# Verificar credenciales en .env
cat .env | grep DB_
```

### Error: "modelo no encontrado"
```bash
# Verificar ruta del modelo en .env
ls -lh ../autocorrelacion_espacial/semana4_recoleccion_datos/modelo_rf_*.pkl
```

### Error: "PostGIS not found"
```bash
# Instalar PostGIS en Ubuntu/Debian
sudo apt install postgresql-14-postgis-3

# O crear extensión manualmente
psql -U postgres -d inmobiliario_db -c "CREATE EXTENSION postgis;"
```

## 📚 Documentación adicional

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **PostGIS**: https://postgis.net/documentation/
- **Scikit-learn**: https://scikit-learn.org/

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Add nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

## 📄 Licencia

MIT License - Proyecto educativo

## 👨‍💻 Autor

Felipe Baeza
- Proyecto: Geoinformática - Análisis Espacial Inmobiliario
- Universidad: [Tu Universidad]
- Fecha: Noviembre 2025

## 🎯 Próximos pasos

- [ ] Agregar autenticación JWT
- [ ] Implementar caché (Redis)
- [ ] Tests unitarios completos
- [ ] Dockerizar aplicación
- [ ] Frontend con React/Vue
- [ ] Análisis SHAP para interpretabilidad
- [ ] API de mapas interactivos
- [ ] Webhooks para notificaciones
- [ ] Búsqueda geoespacial (propiedades cercanas)

---

**¿Necesitas ayuda?** Abre un issue o contacta al autor.
