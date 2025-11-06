#!/bin/bash
# Script de verificación de carga de datos

echo "============================================================================"
echo " VERIFICACIÓN DE DATOS - BACKEND GEOINFORMÁTICA"
echo "============================================================================"
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar que el contenedor esté corriendo
echo -e "${BLUE}1. Verificando contenedor de base de datos...${NC}"
if sudo docker ps | grep -q geoinformatica-db; then
    echo -e "${GREEN}✓ Contenedor geoinformatica-db está corriendo${NC}"
else
    echo "✗ Error: Contenedor no está corriendo"
    exit 1
fi
echo ""

# Total de propiedades
echo -e "${BLUE}2. Total de propiedades cargadas:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "SELECT COUNT(*) as total_propiedades FROM propiedades;"
echo ""

# Total de comunas
echo -e "${BLUE}3. Total de comunas:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "SELECT COUNT(*) as total_comunas FROM comunas WHERE total_propiedades > 0;"
echo ""

# Top 10 comunas
echo -e "${BLUE}4. Top 10 comunas con más propiedades:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "
SELECT 
    nombre, 
    total_propiedades, 
    ROUND(precio_promedio::numeric, 0) as precio_prom
FROM comunas 
WHERE total_propiedades > 0 
ORDER BY total_propiedades DESC 
LIMIT 10;
"
echo ""

# Rango de precios
echo -e "${BLUE}5. Rango de precios:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "
SELECT 
    ROUND(MIN(precio)::numeric, 0) as precio_min,
    ROUND(AVG(precio)::numeric, 0) as precio_promedio,
    ROUND(MAX(precio)::numeric, 0) as precio_max
FROM propiedades 
WHERE precio IS NOT NULL;
"
echo ""

# Distribución por dormitorios
echo -e "${BLUE}6. Distribución por dormitorios:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "
SELECT 
    dormitorios,
    COUNT(*) as cantidad,
    ROUND(AVG(precio)::numeric, 0) as precio_promedio
FROM propiedades 
WHERE precio IS NOT NULL
GROUP BY dormitorios 
ORDER BY dormitorios;
"
echo ""

# Verificar geometrías
echo -e "${BLUE}7. Verificando geometrías PostGIS:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "
SELECT 
    COUNT(*) as con_geometria,
    (SELECT COUNT(*) FROM propiedades) - COUNT(*) as sin_geometria
FROM propiedades 
WHERE geometria IS NOT NULL;
"
echo ""

# Muestra de 3 propiedades
echo -e "${BLUE}8. Muestra de propiedades:${NC}"
sudo docker exec geoinformatica-db psql -U postgres -d inmobiliaria_db -c "
SELECT 
    p.id,
    c.nombre as comuna,
    p.dormitorios as dorms,
    p.banos,
    ROUND(p.superficie_total::numeric, 0) as m2,
    ROUND(p.precio::numeric, 0) as precio,
    SUBSTRING(p.titulo, 1, 40) as titulo
FROM propiedades p
JOIN comunas c ON p.comuna_id = c.id
WHERE p.precio IS NOT NULL
ORDER BY RANDOM()
LIMIT 5;
"
echo ""

echo "============================================================================"
echo -e "${GREEN} ✓ VERIFICACIÓN COMPLETA${NC}"
echo "============================================================================"
echo ""
echo "Para consultas personalizadas, usa:"
echo "  sudo docker exec -it geoinformatica-db psql -U postgres -d inmobiliaria_db"
echo ""
