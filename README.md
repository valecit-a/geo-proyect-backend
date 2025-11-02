# Backend Inmobiliario - Sistema de Recomendaciones con ML

## 📁 Estructura del Proyecto

```
geo-proyect-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Aplicación FastAPI principal
│   ├── config.py                  # Configuración y variables de entorno
│   ├── database.py                # Conexión a PostgreSQL/PostGIS
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # Endpoints REST
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py              # Modelos ORM (Propiedad, Comuna)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── schemas.py             # Schemas Pydantic
│   │   └── schemas_ml.py          # Schemas ML (PreferenciasDetalladas)
│   └── services/
│       ├── __init__.py
│       ├── ml_service.py          # Servicio de Machine Learning
│       └── recommendation_ml_service.py  # Sistema de recomendaciones
├── Dockerfile                      # Imagen Docker del backend
├── .dockerignore                   # Archivos excluidos de Docker
├── init-db.sql                     # Script de inicialización de BD
├── requirements.txt                # Dependencias Python
└── cargar_propiedades.py           # Script para cargar datos

```

## 🚀 Tecnologías

- **FastAPI** 0.115.4 - Framework web moderno
- **SQLAlchemy** 2.0.36 - ORM para PostgreSQL
- **GeoAlchemy2** 0.15.2 - Extensión geoespacial
- **Pydantic** 2.9.2 - Validación de datos
- **PostgreSQL 15** + **PostGIS 3.3** - Base de datos geoespacial
- **Uvicorn** 0.32.0 - Servidor ASGI

## 🔧 Configuración

### Variables de Entorno (docker-compose.yml)

```yaml
DATABASE_URL: postgresql://postgres:postgres@db:5432/inmobiliaria_db
DB_HOST: db
DB_PORT: 5432
DB_NAME: inmobiliaria_db
DB_USER: postgres
DB_PASSWORD: postgres
MODEL_PATH: /app/models/model.pkl
ENVIRONMENT: production
BACKEND_CORS_ORIGINS: '["http://localhost:3000","http://localhost","http://frontend:3000"]'
```

## 📡 Endpoints Principales

### Health Check
```bash
GET http://localhost:8000/api/v1/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "✅ Conectada",
  "modelo": "✅ Sistema ML activo",
  "timestamp": "2025-11-02T21:23:39.741078"
}
```

### Recomendaciones ML
```bash
POST http://localhost:8000/api/v1/recomendaciones-ml
Content-Type: application/json

{
  "presupuesto_min": 200000,
  "presupuesto_max": 400000,
  "dormitorios": 2,
  "tipo_inmueble_preferido": "departamento",
  "comuna": "Ñuñoa",
  "prioridad_transporte": 8,
  "prioridad_educacion": 5,
  "prioridad_salud": 7,
  "prioridad_areas_verdes": 6,
  "prioridad_seguridad": 4,
  "prioridad_ambiente": 3,
  "evitar_ruido": true,
  "evitar_contaminacion": false,
  "peso_precio": 0.25,
  "peso_ubicacion": 0.20,
  "peso_caracteristicas": 0.15,
  "peso_transporte": 0.15,
  "peso_educacion": 0.10,
  "peso_salud": 0.15
}
```

## 🗄️ Base de Datos

### Tablas Principales

**propiedades**
- 897 propiedades únicas
- Campos geoespaciales: `geometria` (POINT), `latitud`, `longitud`
- Distancias calculadas: 17 categorías de servicios
- Índices de accesibilidad

**comunas**
- 4 comunas: La Reina, Santiago, Ñuñoa, Estación Central
- Geometrías MULTIPOLYGON

## 🐳 Docker

### Construir Backend
```bash
cd /home/felipe/Documentos/GeoInformatica
sudo docker compose build backend
```

### Levantar Servicios
```bash
sudo docker compose up -d
```

### Ver Logs
```bash
sudo docker logs geoinformatica-backend --tail 50 -f
```

### Reiniciar Backend
```bash
sudo docker compose restart backend
```

## 📊 Sistema de Recomendaciones

El backend implementa un algoritmo de scoring que combina:

1. **Filtros obligatorios:**
   - Presupuesto (min/max)
   - Número de dormitorios
   - Tipo de inmueble
   - Comuna

2. **Scoring multi-criterio:**
   - Precio (normalizado)
   - Ubicación (distancias)
   - Características (habitaciones, baños, m²)
   - Accesibilidad (transporte, educación, salud)
   - Ambiente (áreas verdes, ruido, contaminación)

3. **Normalización de pesos:**
   - Suma de pesos = 1.0 (exacto)
   - Algoritmo garantiza consistencia matemática

## 🔐 Seguridad

- CORS configurado para frontend local
- Variables de entorno para secretos
- Volumen read-only para código en producción
- Healthchecks automáticos

## 📝 Notas de Migración

**Fecha:** 2 de noviembre de 2025

Este backend fue migrado desde `backend-inmobiliario/` a `geo-proyect-backend/` para mantener consistencia con la estructura del proyecto. Todos los archivos y funcionalidades se mantienen intactos.

**Cambios en docker-compose.yml:**
- ✅ `context: ./geo-proyect-backend`
- ✅ `volumes: ./geo-proyect-backend/app:/app/app:ro`
- ✅ `volumes: ./geo-proyect-backend/init-db.sql:...`

## 📚 Documentación Interactiva

Accede a la documentación automática de FastAPI:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

**Versión:** 1.0.0  
**Estado:** ✅ Operativo  
**Puerto:** 8000  
**Contenedor:** geoinformatica-backend
