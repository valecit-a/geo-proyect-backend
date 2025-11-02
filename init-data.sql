-- ============================================================================
-- Script de Inicialización de Datos - Base de Datos Inmobiliaria
-- ============================================================================
-- Descripción: Carga datos iniciales de comunas, propiedades y grilla espacial
-- Fecha: 2 de Noviembre de 2025
-- Tablas: comunas (32 registros), propiedades (1,623 registros), 
--         grilla_espacial (3,149 registros)
-- ============================================================================

\echo '============================================================================'
\echo '🚀 Iniciando carga de datos...'
\echo '============================================================================'

-- Desactivar triggers y constraints temporalmente para carga rápida
SET session_replication_role = replica;

\echo ''
\echo '📍 Cargando COMUNAS (32 comunas de Santiago)...'

-- Insertar comunas
INSERT INTO comunas (id, nombre) VALUES
(1, 'Cerrillos'),
(2, 'Cerro Navia'),
(3, 'Conchalí'),
(4, 'El Bosque'),
(5, 'Estación Central'),
(6, 'Huechuraba'),
(7, 'Independencia'),
(8, 'La Cisterna'),
(9, 'La Florida'),
(10, 'La Granja'),
(11, 'La Pintana'),
(12, 'La Reina'),
(13, 'Las Condes'),
(14, 'Lo Barnechea'),
(15, 'Lo Espejo'),
(16, 'Lo Prado'),
(17, 'Macul'),
(18, 'Maipú'),
(19, 'Ñuñoa'),
(20, 'Pedro Aguirre Cerda'),
(21, 'Peñalolén'),
(22, 'Providencia'),
(23, 'Pudahuel'),
(24, 'Quilicura'),
(25, 'Quinta Normal'),
(26, 'Recoleta'),
(27, 'Renca'),
(28, 'San Joaquín'),
(29, 'San Miguel'),
(30, 'San Ramón'),
(31, 'Santiago'),
(32, 'Vitacura')
ON CONFLICT (id) DO NOTHING;

\echo '   ✅ Comunas cargadas'

\echo ''
\echo '🏠 Cargando PROPIEDADES desde archivo CSV...'
\echo '   Nota: Este proceso puede tomar varios minutos...'

-- Crear tabla temporal para importar CSV
CREATE TEMP TABLE temp_propiedades (
    row_num INTEGER,
    id INTEGER,
    link TEXT,
    titulo TEXT,
    precio DOUBLE PRECISION,
    direction TEXT,
    superficie_total DOUBLE PRECISION,
    superficie_util DOUBLE PRECISION,
    superficie_terraza DOUBLE PRECISION,
    ambientes INTEGER,
    dormitorios INTEGER,
    banos INTEGER,
    estacionamientos DOUBLE PRECISION,
    cant_max_habitantes INTEGER,
    bodegas DOUBLE PRECISION,
    gastos_comunes DOUBLE PRECISION,
    orientacion TEXT,
    tipo_departamento TEXT,
    cantidad_pisos INTEGER,
    departamentos_piso INTEGER,
    numero_piso_unidad INTEGER,
    codigo INTEGER,
    fecha DATE,
    published_time TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    comuna TEXT,
    published DATE,
    divisa TEXT,
    region TEXT
);

-- Nota: Este COPY requiere que el archivo CSV esté en el container
-- Ver README.md para instrucciones de cómo montar el volumen correctamente

\echo '   → Importando desde CSV...'
-- Descomentar y ajustar la ruta cuando se ejecute en producción:
-- \COPY temp_propiedades FROM '/docker-entrypoint-initdb.d/clean_alquiler_02_11_2023cc.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',', NULL '');

\echo '   → Procesando y cargando propiedades...'

-- Insertar propiedades desde temp a la tabla real
-- (Este bloque se ejecutará solo si el COPY anterior tuvo éxito)
-- INSERT INTO propiedades (
--     comuna_id, direccion, latitud, longitud, titulo,
--     superficie_total, superficie_util, superficie_terraza,
--     dormitorios, banos, estacionamientos,
--     tipo_departamento, numero_piso_unidad, cantidad_pisos,
--     departamentos_piso, gastos_comunes, orientacion,
--     precio, divisa, fuente, codigo, url_original, fecha_publicacion,
--     is_validated, created_at
-- )
-- SELECT ...
-- (Ver script Python cargar_propiedades_csv.py para lógica completa)

\echo '   ⚠️  Carga de propiedades desde CSV requiere script Python'
\echo '   📝 Ejecutar: docker exec geoinformatica-backend python3 /app/cargar_propiedades_csv.py'

\echo ''
\echo '🗺️  Cargando GRILLA ESPACIAL desde GeoJSON...'
\echo '   Nota: 3,149 puntos con 81 características cada uno'

\echo '   ⚠️  Carga de grilla requiere script Python'
\echo '   📝 Ejecutar: docker exec geoinformatica-backend python3 /app/cargar_grilla_densidades.py'

-- Reactivar triggers y constraints
SET session_replication_role = DEFAULT;

\echo ''
\echo '============================================================================'
\echo '📊 Verificando datos cargados...'
\echo '============================================================================'

-- Mostrar resumen
\echo ''
\echo 'Tabla COMUNAS:'
SELECT COUNT(*) as total FROM comunas;

\echo ''
\echo 'Tabla PROPIEDADES:'
SELECT 
    COUNT(*) as total_propiedades,
    COUNT(DISTINCT comuna_id) as comunas_con_datos,
    ROUND(AVG(precio)::numeric, 2) as precio_promedio
FROM propiedades;

\echo ''
\echo 'Tabla GRILLA_ESPACIAL:'
SELECT 
    COUNT(*) as total_puntos,
    COUNT(DISTINCT comuna) as comunas_cubiertas,
    ROUND(AVG(dens_total_600m_km2)::numeric, 2) as densidad_promedio_600m
FROM grilla_espacial;

\echo ''
\echo '============================================================================'
\echo '✅ Script de inicialización completado'
\echo '============================================================================'
\echo ''
\echo 'NOTA: Para carga completa de datos, ejecutar scripts Python:'
\echo '  1. docker exec geoinformatica-backend python3 /app/cargar_propiedades_csv.py'
\echo '  2. docker exec geoinformatica-backend python3 /app/cargar_grilla_densidades.py'
\echo ''
