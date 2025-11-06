# Carga de Datos - Backend GeoInformática

## 📊 Resumen de Carga

**Fecha:** 6 de noviembre de 2025  
**Archivo origen:** `clean_alquiler_02_11_2023cc.csv`  
**Registros totales:** 1,944 propiedades  
**Registros cargados:** 1,867 propiedades (96%)  
**Comunas:** 50 comunas de Santiago

## 🗂️ Archivos Generados

### 1. `generar_carga_propiedades.py`
Script Python que lee el CSV de propiedades y genera un archivo SQL con INSERT statements.

**Características:**
- Convierte propiedades a formato SQL
- Crea geometrías PostGIS (POINT) desde lat/lon
- Maneja valores NULL correctamente
- Escapa caracteres especiales
- Procesa en lotes de 100 registros
- Actualiza estadísticas de comunas

**Uso:**
```bash
cd geo-proyect-backend
python3 generar_carga_propiedades.py
```

### 2. `init-data-propiedades.sql`
Archivo SQL generado automáticamente con:
- INSERTs de 50 comunas
- INSERTs de 1,944 propiedades
- UPDATE de estadísticas

## 📋 Estructura de Datos Cargados

### Comunas (50 total)
Top 5 comunas con más propiedades:
1. **Santiago**: 606 propiedades (precio promedio: $405,167)
2. **Estación Central**: 271 propiedades (precio promedio: $345,436)
3. **Las Condes**: 141 propiedades (precio promedio: $765,450)
4. **San Miguel**: 136 propiedades (precio promedio: $385,876)
5. **La Cisterna**: 117 propiedades (precio promedio: $352,916)

### Propiedades (1,867 cargadas)
Campos principales:
- **Ubicación**: comuna_id, dirección, lat/lon, geometría PostGIS
- **Características**: superficie, dormitorios, baños, estacionamientos
- **Edificio**: tipo, piso, orientación, gastos comunes
- **Precio**: precio, divisa
- **Metadata**: fuente, URL, título, código, fecha publicación

## 🚀 Cómo Cargar en el Backend

### Método 1: Ejecutar directamente (Recomendado)
```bash
sudo docker exec -i geoinformatica-db psql -U postgres -d inmobiliaria_db < init-data-propiedades.sql
```

### Método 2: Copiar al contenedor
```bash
# 1. Copiar archivo
docker cp init-data-propiedades.sql geoinformatica-db:/tmp/

# 2. Ejecutar dentro del contenedor
docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -f /tmp/init-data-propiedades.sql
```

## 🔍 Verificación

### Ver total de propiedades
```sql
SELECT COUNT(*) as total FROM propiedades;
```

### Ver comunas con propiedades
```sql
SELECT 
    nombre, 
    total_propiedades, 
    ROUND(precio_promedio::numeric, 0) as precio_prom,
    ROUND(precio_m2_promedio::numeric, 0) as precio_m2
FROM comunas 
WHERE total_propiedades > 0 
ORDER BY total_propiedades DESC;
```

### Ver muestra de propiedades
```sql
SELECT 
    id,
    c.nombre as comuna,
    dormitorios,
    banos,
    superficie_total,
    precio,
    ST_AsText(geometria) as ubicacion
FROM propiedades p
JOIN comunas c ON p.comuna_id = c.id
LIMIT 10;
```

## ⚠️ Notas Importantes

### Errores durante la carga
- **77 registros fallaron** (4% del total)
- **Causa principal**: Nombres de comunas no coincidentes (ej: variaciones en mayúsculas/minúsculas, con tildes, etc.)
- **Solución**: Los registros con error se omitieron automáticamente

### Datos de Semana 3
Este script carga **únicamente las propiedades base**. Para cargar datos procesados de la Semana 3 (autocorrelación espacial, LISA, submercados), necesitarías:

1. Agregar columnas adicionales al modelo `Propiedad`:
   - `moran_local` (Float): Índice de Moran local
   - `cluster_type` (String): Tipo de cluster LISA (HH, LL, HL, LH)
   - `submercado_id` (Integer): ID del submercado asignado
   - `similaridad_precio` (Float): Score de similitud

2. Procesar los GeoJSON de semana2 para extraer índices:
   - `grilla_con_indices.geojson`
   - `grilla_evaluacion_santiago.geojson`

3. Relacionar propiedades con celdas de grilla por ubicación

## 📁 Archivos Relacionados

- `/autocorrelacion_espacial/semana2_caracteristicas_espaciales/features/`
  - `grilla_con_densidades.geojson` (10.7 MB)
  - `grilla_con_distancias.geojson` (4.3 MB)
  - `grilla_con_indices.geojson` (11.9 MB)
  - `grilla_evaluacion_santiago.geojson` (1.1 MB)

## 🔄 Próximos Pasos

Para completar la integración con Semana 3:

1. **Extender el modelo de datos**
   ```python
   # app/models/models.py
   class Propiedad(Base):
       # ... campos existentes ...
       
       # Análisis espacial (Semana 3)
       moran_local = Column(Float)
       cluster_lisa = Column(String(10))  # 'HH', 'LL', 'HL', 'LH', 'NS'
       submercado_id = Column(Integer)
       score_localizacion = Column(Float)
   ```

2. **Crear script de carga de análisis espacial**
   - Leer GeoJSON de grilla
   - Hacer join espacial con propiedades
   - Actualizar campos de análisis

3. **Exponer en API**
   ```python
   # Endpoint para filtrar por cluster
   @router.get("/propiedades/cluster/{cluster_type}")
   
   # Endpoint para obtener submercados
   @router.get("/submercados")
   ```

## ✅ Estado Actual

- [x] Modelo de datos base (propiedades + comunas)
- [x] Script generador de SQL
- [x] Carga de 1,867 propiedades
- [x] Estadísticas por comuna
- [x] Geometrías PostGIS
- [ ] Integración con análisis Semana 3
- [ ] Campos de autocorrelación espacial
- [ ] API de clusters y submercados
