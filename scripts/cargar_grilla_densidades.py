"""
Script para cargar grilla con densidades y distancias a PostgreSQL
Esta grilla contiene 3,149 puntos de referencia con características espaciales calculadas

Uso:
- Se crea una tabla 'grilla_espacial' con todos los puntos y sus características
- Se puede usar para análisis, visualización de mapas de calor, y predicciones

Autor: Proyecto GeoInformática
Fecha: Noviembre 2025
"""
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

# Database URL (desde container a db)
DATABASE_URL = "postgresql://postgres:postgres@db:5432/inmobiliaria_db"

# Crear engine y session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def crear_tabla_grilla(db):
    """Crea tabla para almacenar grilla espacial si no existe"""
    print("\n📋 Creando tabla grilla_espacial...")
    
    # Verificar si ya existe
    result = db.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'grilla_espacial'
        );
    """)).scalar()
    
    if result:
        print("   ℹ️  Tabla ya existe. Eliminando para recrear...")
        db.execute(text("DROP TABLE IF EXISTS grilla_espacial CASCADE;"))
        db.commit()
    
    # Crear tabla
    db.execute(text("""
        CREATE TABLE grilla_espacial (
            id SERIAL PRIMARY KEY,
            grid_id VARCHAR(50) UNIQUE NOT NULL,
            
            -- Ubicación
            comuna VARCHAR(100),
            x_utm DOUBLE PRECISION NOT NULL,
            y_utm DOUBLE PRECISION NOT NULL,
            latitud DOUBLE PRECISION,
            longitud DOUBLE PRECISION,
            geometria GEOMETRY(Point, 4326),
            zona_utm VARCHAR(10),
            crs_epsg INTEGER,
            
            -- Distancias mínimas a servicios (metros)
            dist_educacion_basica_m DOUBLE PRECISION,
            dist_educacion_superior_m DOUBLE PRECISION,
            dist_educacion_parvularia_m DOUBLE PRECISION,
            dist_educacion_min_m DOUBLE PRECISION,
            
            dist_salud_m DOUBLE PRECISION,
            dist_salud_clinicas_m DOUBLE PRECISION,
            dist_salud_min_m DOUBLE PRECISION,
            
            dist_transporte_metro_m DOUBLE PRECISION,
            dist_transporte_carga_m DOUBLE PRECISION,
            dist_transporte_min_m DOUBLE PRECISION,
            
            dist_seguridad_pdi_m DOUBLE PRECISION,
            dist_seguridad_cuarteles_m DOUBLE PRECISION,
            dist_seguridad_bomberos_m DOUBLE PRECISION,
            dist_seguridad_min_m DOUBLE PRECISION,
            
            dist_areas_verdes_m DOUBLE PRECISION,
            dist_ocio_m DOUBLE PRECISION,
            dist_turismo_m DOUBLE PRECISION,
            dist_comercio_m DOUBLE PRECISION,
            dist_servicios_publicos_m DOUBLE PRECISION,
            dist_servicios_sernam_m DOUBLE PRECISION,
            dist_puntos_interes_m DOUBLE PRECISION,
            
            -- Densidades por radio (servicios/km²)
            -- Radio 300m
            dens_educacion_300m_km2 DOUBLE PRECISION,
            dens_salud_300m_km2 DOUBLE PRECISION,
            dens_comercio_300m_km2 DOUBLE PRECISION,
            dens_seguridad_300m_km2 DOUBLE PRECISION,
            dens_transporte_300m_km2 DOUBLE PRECISION,
            dens_recreacion_300m_km2 DOUBLE PRECISION,
            dens_total_300m_km2 DOUBLE PRECISION,
            
            -- Radio 600m
            dens_educacion_600m_km2 DOUBLE PRECISION,
            dens_salud_600m_km2 DOUBLE PRECISION,
            dens_comercio_600m_km2 DOUBLE PRECISION,
            dens_seguridad_600m_km2 DOUBLE PRECISION,
            dens_transporte_600m_km2 DOUBLE PRECISION,
            dens_recreacion_600m_km2 DOUBLE PRECISION,
            dens_total_600m_km2 DOUBLE PRECISION,
            
            -- Radio 1000m
            dens_educacion_1000m_km2 DOUBLE PRECISION,
            dens_salud_1000m_km2 DOUBLE PRECISION,
            dens_comercio_1000m_km2 DOUBLE PRECISION,
            dens_seguridad_1000m_km2 DOUBLE PRECISION,
            dens_transporte_1000m_km2 DOUBLE PRECISION,
            dens_recreacion_1000m_km2 DOUBLE PRECISION,
            dens_total_1000m_km2 DOUBLE PRECISION,
            
            -- Densidades normalizadas (escala 0-10)
            -- Radio 300m
            dens_norm_educacion_300m DOUBLE PRECISION,
            dens_norm_salud_300m DOUBLE PRECISION,
            dens_norm_comercio_300m DOUBLE PRECISION,
            dens_norm_seguridad_300m DOUBLE PRECISION,
            dens_norm_transporte_300m DOUBLE PRECISION,
            dens_norm_recreacion_300m DOUBLE PRECISION,
            dens_norm_total_300m DOUBLE PRECISION,
            
            -- Radio 600m
            dens_norm_educacion_600m DOUBLE PRECISION,
            dens_norm_salud_600m DOUBLE PRECISION,
            dens_norm_comercio_600m DOUBLE PRECISION,
            dens_norm_seguridad_600m DOUBLE PRECISION,
            dens_norm_transporte_600m DOUBLE PRECISION,
            dens_norm_recreacion_600m DOUBLE PRECISION,
            dens_norm_total_600m DOUBLE PRECISION,
            
            -- Radio 1000m
            dens_norm_educacion_1000m DOUBLE PRECISION,
            dens_norm_salud_1000m DOUBLE PRECISION,
            dens_norm_comercio_1000m DOUBLE PRECISION,
            dens_norm_seguridad_1000m DOUBLE PRECISION,
            dens_norm_transporte_1000m DOUBLE PRECISION,
            dens_norm_recreacion_1000m DOUBLE PRECISION,
            dens_norm_total_1000m DOUBLE PRECISION,
            
            -- Índices de diversidad
            diversidad_servicios_300m INTEGER,
            diversidad_servicios_600m INTEGER,
            diversidad_servicios_1000m INTEGER,
            div_norm_servicios_300m DOUBLE PRECISION,
            div_norm_servicios_600m DOUBLE PRECISION,
            div_norm_servicios_1000m DOUBLE PRECISION,
            
            -- Metadatos
            procesado BOOLEAN DEFAULT false,
            distancias_calculadas BOOLEAN DEFAULT false,
            densidades_calculadas BOOLEAN DEFAULT false,
            fecha_creacion TIMESTAMP,
            fecha_distancias TIMESTAMP,
            fecha_densidades TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """))
    
    # Crear índices
    db.execute(text("""
        CREATE INDEX idx_grilla_grid_id ON grilla_espacial(grid_id);
        CREATE INDEX idx_grilla_comuna ON grilla_espacial(comuna);
        CREATE INDEX idx_grilla_geometria ON grilla_espacial USING GIST(geometria);
        CREATE INDEX idx_grilla_utm ON grilla_espacial(x_utm, y_utm);
    """))
    
    db.commit()
    print("   ✅ Tabla y índices creados")


def utm_to_latlon(x_utm, y_utm, zone=19, hemisphere='S'):
    """
    Convierte coordenadas UTM a lat/lon (aproximación simple)
    Para conversión precisa se debería usar pyproj
    """
    import math
    
    # Constantes
    k0 = 0.9996
    e = 0.081819191
    e1sq = 0.006739497
    
    # Zona UTM
    falseEasting = 500000
    falseNorthing = 10000000 if hemisphere == 'S' else 0
    
    # Remover false easting/northing
    x = x_utm - falseEasting
    y = y_utm - falseNorthing if hemisphere == 'S' else y_utm
    
    # Cálculos (aproximación)
    lon_origin = (zone - 1) * 6 - 180 + 3
    
    M = y / k0
    mu = M / (6378137 * (1 - e*e/4 - 3*e*e*e*e/64))
    
    lat = mu + (3*e1sq/2 - 27*e1sq*e1sq*e1sq/32) * math.sin(2*mu)
    lon = lon_origin + (x / (k0 * 6378137)) * (180/math.pi)
    lat = lat * (180/math.pi)
    
    if hemisphere == 'S':
        lat = -abs(lat)
    
    return lat, lon


def cargar_grilla_desde_geojson(ruta_geojson):
    """Carga grilla desde archivo GeoJSON"""
    print(f"\n📂 Cargando grilla desde: {ruta_geojson}")
    
    with open(ruta_geojson, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data['features']
    print(f"   ✅ {len(features)} puntos cargados")
    
    return features


def insertar_puntos_grilla(db, features):
    """Inserta puntos de grilla en base de datos"""
    print("\n💾 Insertando puntos de grilla...")
    
    insertados = 0
    errores = 0
    
    BATCH_SIZE = 100
    
    for i, feature in enumerate(features):
        if i % 500 == 0:
            print(f"   Procesando {i}/{len(features)}...")
        
        props = feature['properties']
        geom = feature['geometry']
        
        try:
            # Obtener coordenadas
            x_utm = props.get('x_utm')
            y_utm = props.get('y_utm')
            
            # Convertir UTM a lat/lon
            if x_utm and y_utm:
                lat, lon = utm_to_latlon(x_utm, y_utm, zone=19, hemisphere='S')
            else:
                # Si viene en el geometry (GeoJSON está en WGS84)
                coords = geom.get('coordinates', [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                else:
                    lat, lon = None, None
            
            # Preparar fechas
            fecha_creacion = props.get('fecha_creacion')
            fecha_distancias = props.get('fecha_distancias')
            fecha_densidades = props.get('fecha_densidades')
            
            if isinstance(fecha_creacion, str):
                fecha_creacion = datetime.fromisoformat(fecha_creacion.replace('T', ' ').split('.')[0])
            if isinstance(fecha_distancias, str):
                fecha_distancias = datetime.fromisoformat(fecha_distancias.replace('T', ' ').split('.')[0])
            if isinstance(fecha_densidades, str):
                fecha_densidades = datetime.fromisoformat(fecha_densidades.replace('T', ' ').split('.')[0])
            
            # Insertar
            db.execute(text("""
                INSERT INTO grilla_espacial (
                    grid_id, comuna, x_utm, y_utm, latitud, longitud,
                    zona_utm, crs_epsg,
                    
                    dist_educacion_basica_m, dist_educacion_superior_m, dist_educacion_parvularia_m, dist_educacion_min_m,
                    dist_salud_m, dist_salud_clinicas_m, dist_salud_min_m,
                    dist_transporte_metro_m, dist_transporte_carga_m, dist_transporte_min_m,
                    dist_seguridad_pdi_m, dist_seguridad_cuarteles_m, dist_seguridad_bomberos_m, dist_seguridad_min_m,
                    dist_areas_verdes_m, dist_ocio_m, dist_turismo_m, dist_comercio_m,
                    dist_servicios_publicos_m, dist_servicios_sernam_m, dist_puntos_interes_m,
                    
                    dens_educacion_300m_km2, dens_salud_300m_km2, dens_comercio_300m_km2, 
                    dens_seguridad_300m_km2, dens_transporte_300m_km2, dens_recreacion_300m_km2, dens_total_300m_km2,
                    dens_educacion_600m_km2, dens_salud_600m_km2, dens_comercio_600m_km2,
                    dens_seguridad_600m_km2, dens_transporte_600m_km2, dens_recreacion_600m_km2, dens_total_600m_km2,
                    dens_educacion_1000m_km2, dens_salud_1000m_km2, dens_comercio_1000m_km2,
                    dens_seguridad_1000m_km2, dens_transporte_1000m_km2, dens_recreacion_1000m_km2, dens_total_1000m_km2,
                    
                    dens_norm_educacion_300m, dens_norm_salud_300m, dens_norm_comercio_300m,
                    dens_norm_seguridad_300m, dens_norm_transporte_300m, dens_norm_recreacion_300m, dens_norm_total_300m,
                    dens_norm_educacion_600m, dens_norm_salud_600m, dens_norm_comercio_600m,
                    dens_norm_seguridad_600m, dens_norm_transporte_600m, dens_norm_recreacion_600m, dens_norm_total_600m,
                    dens_norm_educacion_1000m, dens_norm_salud_1000m, dens_norm_comercio_1000m,
                    dens_norm_seguridad_1000m, dens_norm_transporte_1000m, dens_norm_recreacion_1000m, dens_norm_total_1000m,
                    
                    diversidad_servicios_300m, diversidad_servicios_600m, diversidad_servicios_1000m,
                    div_norm_servicios_300m, div_norm_servicios_600m, div_norm_servicios_1000m,
                    
                    procesado, distancias_calculadas, densidades_calculadas,
                    fecha_creacion, fecha_distancias, fecha_densidades
                ) VALUES (
                    :grid_id, :comuna, :x_utm, :y_utm, :latitud, :longitud,
                    :zona_utm, :crs_epsg,
                    
                    :dist_educacion_basica_m, :dist_educacion_superior_m, :dist_educacion_parvularia_m, :dist_educacion_min_m,
                    :dist_salud_m, :dist_salud_clinicas_m, :dist_salud_min_m,
                    :dist_transporte_metro_m, :dist_transporte_carga_m, :dist_transporte_min_m,
                    :dist_seguridad_pdi_m, :dist_seguridad_cuarteles_m, :dist_seguridad_bomberos_m, :dist_seguridad_min_m,
                    :dist_areas_verdes_m, :dist_ocio_m, :dist_turismo_m, :dist_comercio_m,
                    :dist_servicios_publicos_m, :dist_servicios_sernam_m, :dist_puntos_interes_m,
                    
                    :dens_educacion_300m_km2, :dens_salud_300m_km2, :dens_comercio_300m_km2,
                    :dens_seguridad_300m_km2, :dens_transporte_300m_km2, :dens_recreacion_300m_km2, :dens_total_300m_km2,
                    :dens_educacion_600m_km2, :dens_salud_600m_km2, :dens_comercio_600m_km2,
                    :dens_seguridad_600m_km2, :dens_transporte_600m_km2, :dens_recreacion_600m_km2, :dens_total_600m_km2,
                    :dens_educacion_1000m_km2, :dens_salud_1000m_km2, :dens_comercio_1000m_km2,
                    :dens_seguridad_1000m_km2, :dens_transporte_1000m_km2, :dens_recreacion_1000m_km2, :dens_total_1000m_km2,
                    
                    :dens_norm_educacion_300m, :dens_norm_salud_300m, :dens_norm_comercio_300m,
                    :dens_norm_seguridad_300m, :dens_norm_transporte_300m, :dens_norm_recreacion_300m, :dens_norm_total_300m,
                    :dens_norm_educacion_600m, :dens_norm_salud_600m, :dens_norm_comercio_600m,
                    :dens_norm_seguridad_600m, :dens_norm_transporte_600m, :dens_norm_recreacion_600m, :dens_norm_total_600m,
                    :dens_norm_educacion_1000m, :dens_norm_salud_1000m, :dens_norm_comercio_1000m,
                    :dens_norm_seguridad_1000m, :dens_norm_transporte_1000m, :dens_norm_recreacion_1000m, :dens_norm_total_1000m,
                    
                    :diversidad_servicios_300m, :diversidad_servicios_600m, :diversidad_servicios_1000m,
                    :div_norm_servicios_300m, :div_norm_servicios_600m, :div_norm_servicios_1000m,
                    
                    :procesado, :distancias_calculadas, :densidades_calculadas,
                    :fecha_creacion, :fecha_distancias, :fecha_densidades
                )
            """), {
                'grid_id': props.get('grid_id'),
                'comuna': props.get('comuna'),
                'x_utm': x_utm,
                'y_utm': y_utm,
                'latitud': lat,
                'longitud': lon,
                'zona_utm': props.get('zona_utm'),
                'crs_epsg': props.get('crs_epsg'),
                
                # Distancias
                'dist_educacion_basica_m': props.get('dist_educacion_basica_m'),
                'dist_educacion_superior_m': props.get('dist_educacion_superior_m'),
                'dist_educacion_parvularia_m': props.get('dist_educacion_parvularia_m'),
                'dist_educacion_min_m': props.get('dist_educacion_min_m'),
                'dist_salud_m': props.get('dist_salud_m'),
                'dist_salud_clinicas_m': props.get('dist_salud_clinicas_m'),
                'dist_salud_min_m': props.get('dist_salud_min_m'),
                'dist_transporte_metro_m': props.get('dist_transporte_metro_m'),
                'dist_transporte_carga_m': props.get('dist_transporte_carga_m'),
                'dist_transporte_min_m': props.get('dist_transporte_min_m'),
                'dist_seguridad_pdi_m': props.get('dist_seguridad_pdi_m'),
                'dist_seguridad_cuarteles_m': props.get('dist_seguridad_cuarteles_m'),
                'dist_seguridad_bomberos_m': props.get('dist_seguridad_bomberos_m'),
                'dist_seguridad_min_m': props.get('dist_seguridad_min_m'),
                'dist_areas_verdes_m': props.get('dist_areas_verdes_m'),
                'dist_ocio_m': props.get('dist_ocio_m'),
                'dist_turismo_m': props.get('dist_turismo_m'),
                'dist_comercio_m': props.get('dist_comercio_m'),
                'dist_servicios_publicos_m': props.get('dist_servicios_publicos_m'),
                'dist_servicios_sernam_m': props.get('dist_servicios_sernam_m'),
                'dist_puntos_interes_m': props.get('dist_puntos_interes_m'),
                
                # Densidades 300m
                'dens_educacion_300m_km2': props.get('dens_educacion_300m_km2'),
                'dens_salud_300m_km2': props.get('dens_salud_300m_km2'),
                'dens_comercio_300m_km2': props.get('dens_comercio_300m_km2'),
                'dens_seguridad_300m_km2': props.get('dens_seguridad_300m_km2'),
                'dens_transporte_300m_km2': props.get('dens_transporte_300m_km2'),
                'dens_recreacion_300m_km2': props.get('dens_recreacion_300m_km2'),
                'dens_total_300m_km2': props.get('dens_total_300m_km2'),
                
                # Densidades 600m
                'dens_educacion_600m_km2': props.get('dens_educacion_600m_km2'),
                'dens_salud_600m_km2': props.get('dens_salud_600m_km2'),
                'dens_comercio_600m_km2': props.get('dens_comercio_600m_km2'),
                'dens_seguridad_600m_km2': props.get('dens_seguridad_600m_km2'),
                'dens_transporte_600m_km2': props.get('dens_transporte_600m_km2'),
                'dens_recreacion_600m_km2': props.get('dens_recreacion_600m_km2'),
                'dens_total_600m_km2': props.get('dens_total_600m_km2'),
                
                # Densidades 1000m
                'dens_educacion_1000m_km2': props.get('dens_educacion_1000m_km2'),
                'dens_salud_1000m_km2': props.get('dens_salud_1000m_km2'),
                'dens_comercio_1000m_km2': props.get('dens_comercio_1000m_km2'),
                'dens_seguridad_1000m_km2': props.get('dens_seguridad_1000m_km2'),
                'dens_transporte_1000m_km2': props.get('dens_transporte_1000m_km2'),
                'dens_recreacion_1000m_km2': props.get('dens_recreacion_1000m_km2'),
                'dens_total_1000m_km2': props.get('dens_total_1000m_km2'),
                
                # Densidades normalizadas 300m
                'dens_norm_educacion_300m': props.get('dens_norm_educacion_300m_km2'),
                'dens_norm_salud_300m': props.get('dens_norm_salud_300m_km2'),
                'dens_norm_comercio_300m': props.get('dens_norm_comercio_300m_km2'),
                'dens_norm_seguridad_300m': props.get('dens_norm_seguridad_300m_km2'),
                'dens_norm_transporte_300m': props.get('dens_norm_transporte_300m_km2'),
                'dens_norm_recreacion_300m': props.get('dens_norm_recreacion_300m_km2'),
                'dens_norm_total_300m': props.get('dens_norm_total_300m_km2'),
                
                # Densidades normalizadas 600m
                'dens_norm_educacion_600m': props.get('dens_norm_educacion_600m_km2'),
                'dens_norm_salud_600m': props.get('dens_norm_salud_600m_km2'),
                'dens_norm_comercio_600m': props.get('dens_norm_comercio_600m_km2'),
                'dens_norm_seguridad_600m': props.get('dens_norm_seguridad_600m_km2'),
                'dens_norm_transporte_600m': props.get('dens_norm_transporte_600m_km2'),
                'dens_norm_recreacion_600m': props.get('dens_norm_recreacion_600m_km2'),
                'dens_norm_total_600m': props.get('dens_norm_total_600m_km2'),
                
                # Densidades normalizadas 1000m
                'dens_norm_educacion_1000m': props.get('dens_norm_educacion_1000m_km2'),
                'dens_norm_salud_1000m': props.get('dens_norm_salud_1000m_km2'),
                'dens_norm_comercio_1000m': props.get('dens_norm_comercio_1000m_km2'),
                'dens_norm_seguridad_1000m': props.get('dens_norm_seguridad_1000m_km2'),
                'dens_norm_transporte_1000m': props.get('dens_norm_transporte_1000m_km2'),
                'dens_norm_recreacion_1000m': props.get('dens_norm_recreacion_1000m_km2'),
                'dens_norm_total_1000m': props.get('dens_norm_total_1000m_km2'),
                
                # Diversidad
                'diversidad_servicios_300m': int(props.get('diversidad_servicios_300m', 0)),
                'diversidad_servicios_600m': int(props.get('diversidad_servicios_600m', 0)),
                'diversidad_servicios_1000m': int(props.get('diversidad_servicios_1000m', 0)),
                'div_norm_servicios_300m': props.get('div_norm_servicios_300m'),
                'div_norm_servicios_600m': props.get('div_norm_servicios_600m'),
                'div_norm_servicios_1000m': props.get('div_norm_servicios_1000m'),
                
                # Metadatos
                'procesado': bool(props.get('procesado', 0)),
                'distancias_calculadas': bool(props.get('distancias_calculadas', 0)),
                'densidades_calculadas': bool(props.get('densidades_calculadas', 0)),
                'fecha_creacion': fecha_creacion,
                'fecha_distancias': fecha_distancias,
                'fecha_densidades': fecha_densidades,
            })
            
            insertados += 1
            
            if insertados % BATCH_SIZE == 0:
                db.commit()
        
        except Exception as e:
            errores += 1
            if errores <= 5:
                print(f"   ⚠️  Error en punto {i}: {str(e)[:100]}")
    
    db.commit()
    
    print(f"\n   ✅ Insertados: {insertados}")
    print(f"   ⚠️  Errores: {errores}")
    
    return insertados, errores


def main():
    print("=" * 70)
    print("🗺️  CARGA DE GRILLA ESPACIAL CON DENSIDADES")
    print("=" * 70)
    
    # Ruta del archivo
    grilla_path = Path("/tmp/grilla_con_densidades.geojson")
    
    if not grilla_path.exists():
        print(f"\n❌ Error: Archivo no encontrado: {grilla_path}")
        return False
    
    # Conectar a DB
    print("\n🔌 Conectando a PostgreSQL...")
    db = SessionLocal()
    
    try:
        db.execute(text("SELECT 1"))
        print("   ✅ Conexión exitosa")
        
        # Crear tabla
        crear_tabla_grilla(db)
        
        # Cargar GeoJSON
        features = cargar_grilla_desde_geojson(grilla_path)
        
        # Insertar puntos
        insertados, errores = insertar_puntos_grilla(db, features)
        
        # Verificar resultado
        total = db.execute(text("SELECT COUNT(*) FROM grilla_espacial")).scalar()
        print(f"\n📊 Total en BD: {total} puntos")
        
        # Estadísticas por comuna
        print("\n📍 Top 10 comunas en grilla:")
        top_comunas = db.execute(text("""
            SELECT comuna, COUNT(*) as total
            FROM grilla_espacial
            WHERE comuna IS NOT NULL
            GROUP BY comuna
            ORDER BY total DESC
            LIMIT 10
        """)).fetchall()
        
        for i, (comuna, total) in enumerate(top_comunas, 1):
            print(f"   {i:2d}. {comuna:25s}: {total:4d} puntos")
        
        # Estadísticas de densidades
        print("\n📈 Estadísticas de densidades (promedio):")
        stats = db.execute(text("""
            SELECT 
                AVG(dens_total_300m_km2) as dens_300m,
                AVG(dens_total_600m_km2) as dens_600m,
                AVG(dens_total_1000m_km2) as dens_1000m,
                AVG(diversidad_servicios_300m) as div_300m,
                AVG(diversidad_servicios_600m) as div_600m,
                AVG(diversidad_servicios_1000m) as div_1000m
            FROM grilla_espacial
        """)).fetchone()
        
        print(f"   Radio 300m:  {stats[0]:.2f} servicios/km² | Diversidad: {stats[3]:.2f}/6")
        print(f"   Radio 600m:  {stats[1]:.2f} servicios/km² | Diversidad: {stats[4]:.2f}/6")
        print(f"   Radio 1000m: {stats[2]:.2f} servicios/km² | Diversidad: {stats[5]:.2f}/6")
        
        print("\n" + "=" * 70)
        print("✅ CARGA DE GRILLA COMPLETADA")
        print("=" * 70)
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    exito = main()
    if not exito:
        import sys
        sys.exit(1)
