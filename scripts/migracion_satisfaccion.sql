-- ============================================================================
-- MIGRACIÓN: Agregar campos de satisfacción a la base de datos
-- ============================================================================
-- Proyecto: GeoInformática
-- Fecha: Enero 2025
-- Descripción: Agrega los campos necesarios para el modelo de satisfacción
-- ============================================================================

-- 1. Agregar columnas de satisfacción a tabla propiedades
ALTER TABLE propiedades 
ADD COLUMN IF NOT EXISTS satisfaccion FLOAT,
ADD COLUMN IF NOT EXISTS satisfaccion_predicha FLOAT,
ADD COLUMN IF NOT EXISTS tipo_propiedad VARCHAR(20) DEFAULT 'departamento',
ADD COLUMN IF NOT EXISTS precio_uf FLOAT;

-- 2. Crear índices para búsquedas eficientes
CREATE INDEX IF NOT EXISTS idx_propiedades_satisfaccion 
ON propiedades(satisfaccion_predicha);

CREATE INDEX IF NOT EXISTS idx_propiedades_tipo 
ON propiedades(tipo_propiedad);

CREATE INDEX IF NOT EXISTS idx_propiedades_precio_uf 
ON propiedades(precio_uf);

-- 3. Actualizar precio_uf desde precio existente (asumiendo precio en CLP)
-- NOTA: Ajustar VALOR_UF según corresponda
UPDATE propiedades 
SET precio_uf = precio / 38500.0
WHERE precio IS NOT NULL AND precio_uf IS NULL;

-- 4. Actualizar tipo_propiedad basado en tipo_departamento existente
UPDATE propiedades 
SET tipo_propiedad = CASE 
    WHEN tipo_departamento IS NOT NULL AND tipo_departamento != 'Casa' THEN 'departamento'
    ELSE 'casa'
END
WHERE tipo_propiedad IS NULL OR tipo_propiedad = '';

-- 5. Verificar comunas existentes y crear las faltantes
INSERT INTO comunas (nombre, codigo, total_propiedades)
SELECT 'La Reina', 'LRE', 0
WHERE NOT EXISTS (SELECT 1 FROM comunas WHERE nombre = 'La Reina');

INSERT INTO comunas (nombre, codigo, total_propiedades)
SELECT 'Ñuñoa', 'NUN', 0
WHERE NOT EXISTS (SELECT 1 FROM comunas WHERE nombre = 'Ñuñoa');

INSERT INTO comunas (nombre, codigo, total_propiedades)
SELECT 'Santiago', 'STG', 0
WHERE NOT EXISTS (SELECT 1 FROM comunas WHERE nombre = 'Santiago');

INSERT INTO comunas (nombre, codigo, total_propiedades)
SELECT 'Estación Central', 'EST', 0
WHERE NOT EXISTS (SELECT 1 FROM comunas WHERE nombre = 'Estación Central');

-- 6. Crear vista para consulta rápida de propiedades con satisfacción
CREATE OR REPLACE VIEW v_propiedades_satisfaccion AS
SELECT 
    p.id,
    p.direccion,
    c.nombre as comuna,
    p.tipo_propiedad,
    p.superficie_util,
    p.dormitorios,
    p.banos,
    p.precio_uf,
    p.satisfaccion_predicha,
    p.latitud,
    p.longitud,
    p.created_at,
    -- Clasificación de satisfacción
    CASE 
        WHEN p.satisfaccion_predicha >= 8 THEN 'Excelente'
        WHEN p.satisfaccion_predicha >= 6 THEN 'Bueno'
        WHEN p.satisfaccion_predicha >= 4 THEN 'Regular'
        ELSE 'Bajo'
    END as nivel_satisfaccion
FROM propiedades p
JOIN comunas c ON p.comuna_id = c.id;

-- 7. Actualizar estadísticas de comunas
UPDATE comunas c SET
    total_propiedades = (
        SELECT COUNT(*) FROM propiedades p WHERE p.comuna_id = c.id
    ),
    precio_promedio = (
        SELECT AVG(precio) FROM propiedades p WHERE p.comuna_id = c.id
    ),
    precio_m2_promedio = (
        SELECT AVG(precio / NULLIF(superficie_util, 0)) 
        FROM propiedades p WHERE p.comuna_id = c.id
    );

-- 8. Mostrar resumen
SELECT 
    'Migración completada' as status,
    (SELECT COUNT(*) FROM propiedades) as total_propiedades,
    (SELECT COUNT(*) FROM propiedades WHERE satisfaccion_predicha IS NOT NULL) as con_satisfaccion,
    (SELECT COUNT(*) FROM comunas) as total_comunas;
