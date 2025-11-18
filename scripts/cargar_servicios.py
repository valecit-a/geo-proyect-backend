#!/usr/bin/env python3
"""
Script para cargar puntos de interés (servicios) desde archivos GeoJSON normalizados
a la base de datos PostgreSQL/PostGIS.

Este script lee los archivos GeoJSON de servicios normalizados y los inserta
en la tabla puntos_interes, diferenciando los tipos según las propiedades de cada feature.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Configuración de conexión a la base de datos
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'inmobiliaria_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'host': os.getenv('POSTGRES_HOST', 'geoinformatica-db'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

# Ruta base a los archivos GeoJSON normalizados
# Primero intentamos la ruta del contenedor Docker, luego la ruta local
if os.path.exists('/app/datos_normalizados/datos_normalizados'):
    BASE_PATH = Path('/app/datos_normalizados/datos_normalizados')
elif os.path.exists('/app/datos_normalizados'):
    BASE_PATH = Path('/app/datos_normalizados')
else:
    BASE_PATH = Path(__file__).parent.parent.parent / 'autocorrelacion_espacial' / 'semana1_preparacion_datos' / 'datos_normalizados' / 'datos_normalizados'

# Mapeo de archivos GeoJSON a tipos de servicio
# Formato: 'nombre_archivo.geojson': 'tipo_servicio'
ARCHIVO_A_TIPO = {
    # Educación
    'establecimientos_educacion_escolar.geojson': 'colegio',
    'establecimientos_educacion_superior.geojson': 'colegio',  # Universidad también como colegio
    'establecimientos_parvularia_filtrados.geojson': 'colegio',  # Parvularia como colegio
    
    # Transporte
    'Lineas_de_metro_de_Santiago.geojson': 'metro',
    
    # Salud (se diferenciará por properties)
    'puntos_medicos_farmacias_hospitales_filtrados.geojson': 'salud',  # Especial: contiene múltiples tipos
    'redes_de_clinicas_filtradas.geojson': 'centro_medico',
    
    # Áreas verdes y recreación
    'areas_verdes_filtradas.geojson': 'parque',
    'ocio_filtrado.geojson': 'parque',  # Ocio como parque
    
    # Comercio
    'tiendas_filtradas.geojson': 'supermercado',
    'servicios_filtrados.geojson': 'supermercado',  # Servicios como supermercado
    
    # Seguridad
    'cuarteles_filtrados.geojson': 'comisaria',
    'cuerpos_de_bomberos_filtrados.geojson': 'bombero',
    'unidades_operativas_pdi_filtradas.geojson': 'comisaria',  # PDI como comisaría
}


def transformar_coordenadas_utm_a_latlon(x_utm: float, y_utm: float) -> Tuple[float, float]:
    """
    Convierte coordenadas UTM (EPSG:32719 - WGS84 / UTM zone 19S) a lat/lon (EPSG:4326).
    
    Args:
        x_utm: Coordenada X en UTM
        y_utm: Coordenada Y en UTM
    
    Returns:
        Tupla (latitud, longitud)
    """
    try:
        from pyproj import Transformer
        # Transformer de UTM 19S a WGS84
        transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(x_utm, y_utm)
        return lat, lon
    except ImportError:
        print("ADVERTENCIA: pyproj no disponible, usando aproximación simple")
        # Aproximación muy básica (NO USAR EN PRODUCCIÓN)
        # Solo para fallback si pyproj no está disponible
        lon = (x_utm - 500000) / 111320.0 - 70.0
        lat = (y_utm - 10000000) / 110540.0
        return lat, lon


def determinar_tipo_salud(properties: Dict) -> str:
    """
    Determina el tipo específico de servicio de salud basado en las propiedades.
    
    Args:
        properties: Diccionario de propiedades del feature GeoJSON
    
    Returns:
        Tipo de servicio: 'farmacia', 'centro_medico', o 'centro_medico' (por defecto)
    """
    amenity = properties.get('amenity', '').lower()
    healthcare = properties.get('healthcare', '').lower()
    name = properties.get('name', '').lower()
    
    # Identificar farmacias
    if amenity == 'pharmacy' or healthcare == 'pharmacy':
        return 'farmacia'
    if 'farmacia' in name or 'pharmacy' in name:
        return 'farmacia'
    
    # Identificar hospitales
    if amenity == 'hospital' or healthcare == 'hospital':
        return 'centro_medico'
    if 'hospital' in name or 'clínica' in name or 'clinic' in name:
        return 'centro_medico'
    
    # Identificar clínicas y centros médicos
    if amenity in ['clinic', 'doctors'] or healthcare in ['clinic', 'doctor']:
        return 'centro_medico'
    if 'cesfam' in name or 'centro médico' in name or 'integramédica' in name:
        return 'centro_medico'
    
    # Por defecto, centro médico
    return 'centro_medico'


def extraer_informacion_poi(feature: Dict, tipo_archivo: str) -> Optional[Dict]:
    """
    Extrae información relevante de un feature GeoJSON para crear un punto de interés.
    
    Args:
        feature: Feature GeoJSON
        tipo_archivo: Tipo de servicio del archivo
    
    Returns:
        Diccionario con información del POI o None si no se puede procesar
    """
    try:
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        # Extraer coordenadas
        coordinates = geometry.get('coordinates', [])
        if not coordinates or len(coordinates) < 2:
            return None
        
        x_utm, y_utm = coordinates[0], coordinates[1]
        
        # Convertir a lat/lon
        latitud, longitud = transformar_coordenadas_utm_a_latlon(x_utm, y_utm)
        
        # Determinar tipo específico
        if tipo_archivo == 'salud':
            tipo = determinar_tipo_salud(properties)
        else:
            tipo = tipo_archivo
        
        # Extraer nombre
        nombre = properties.get('name') or properties.get('nombre') or 'Sin nombre'
        
        # Extraer dirección
        direccion_partes = []
        if properties.get('addr_street'):
            direccion_partes.append(properties['addr_street'])
        if properties.get('addr_housenumber'):
            direccion_partes.append(properties['addr_housenumber'])
        if properties.get('addr_city'):
            direccion_partes.append(properties['addr_city'])
        
        direccion = ', '.join(direccion_partes) if direccion_partes else None
        
        # Extraer otros campos
        telefono = properties.get('phone')
        horario = properties.get('opening_hours')
        descripcion = properties.get('healthcare_speciality') or properties.get('amenity')
        
        return {
            'tipo': tipo,
            'nombre': nombre,
            'direccion': direccion,
            'latitud': latitud,
            'longitud': longitud,
            'descripcion': descripcion,
            'telefono': telefono,
            'horario': horario
        }
    
    except Exception as e:
        print(f"Error procesando feature: {e}")
        return None


def cargar_archivo_geojson(archivo_path: Path, tipo_servicio: str, conn) -> int:
    """
    Carga un archivo GeoJSON en la base de datos.
    
    Args:
        archivo_path: Ruta al archivo GeoJSON
        tipo_servicio: Tipo de servicio del archivo
        conn: Conexión a la base de datos
    
    Returns:
        Número de registros insertados
    """
    print(f"\nProcesando: {archivo_path.name}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        print(f"  - Features encontrados: {len(features)}")
        
        # Procesar features
        pois = []
        for feature in features:
            poi = extraer_informacion_poi(feature, tipo_servicio)
            if poi:
                pois.append(poi)
        
        print(f"  - POIs válidos: {len(pois)}")
        
        if not pois:
            return 0
        
        # Preparar datos para inserción
        values = [
            (
                poi['tipo'],
                poi['nombre'],
                poi['direccion'],
                poi['latitud'],
                poi['longitud'],
                poi['descripcion'],
                poi['telefono'],
                poi['horario']
            )
            for poi in pois
        ]
        
        # Insertar en la base de datos
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO puntos_interes 
                (tipo, nombre, direccion, latitud, longitud, geometria, descripcion, telefono, horario)
            VALUES %s
        """
        
        # Usar template con ST_SetSRID para geometría
        template = """(
            %s, %s, %s, %s, %s, 
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s, %s
        )"""
        
        # Preparar valores con longitud para geometría
        values_with_geom = [
            (
                v[0], v[1], v[2], v[3], v[4],  # tipo, nombre, direccion, latitud, longitud
                v[4], v[3],  # longitud, latitud para ST_MakePoint (x, y)
                v[5], v[6], v[7]  # descripcion, telefono, horario
            )
            for v in values
        ]
        
        execute_values(cursor, insert_query, values_with_geom, template=template)
        conn.commit()
        cursor.close()
        
        print(f"  ✓ Insertados: {len(pois)} registros")
        return len(pois)
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        conn.rollback()
        return 0


def main():
    """Función principal."""
    print("=" * 80)
    print("CARGA DE PUNTOS DE INTERÉS (SERVICIOS)")
    print("=" * 80)
    
    # Verificar que existe el directorio de datos
    if not BASE_PATH.exists():
        print(f"\n✗ ERROR: No se encuentra el directorio de datos normalizados:")
        print(f"  {BASE_PATH}")
        sys.exit(1)
    
    print(f"\nDirectorio de datos: {BASE_PATH}")
    
    # Conectar a la base de datos
    print("\nConectando a la base de datos...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Conexión establecida")
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        sys.exit(1)
    
    # Limpiar tabla de puntos de interés (opcional)
    print("\nLimpiando tabla puntos_interes...")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM puntos_interes")
        conn.commit()
        cursor.close()
        print("✓ Tabla limpiada")
    except Exception as e:
        print(f"⚠ Advertencia al limpiar tabla: {e}")
        conn.rollback()
    
    # Procesar cada archivo
    total_insertados = 0
    archivos_procesados = 0
    archivos_con_error = 0
    
    print("\n" + "=" * 80)
    print("PROCESANDO ARCHIVOS GEOJSON")
    print("=" * 80)
    
    for archivo_nombre, tipo_servicio in ARCHIVO_A_TIPO.items():
        archivo_path = BASE_PATH / archivo_nombre
        
        if not archivo_path.exists():
            print(f"\n⚠ Archivo no encontrado: {archivo_nombre}")
            archivos_con_error += 1
            continue
        
        try:
            insertados = cargar_archivo_geojson(archivo_path, tipo_servicio, conn)
            total_insertados += insertados
            archivos_procesados += 1
        except Exception as e:
            print(f"\n✗ Error procesando {archivo_nombre}: {e}")
            archivos_con_error += 1
    
    # Cerrar conexión
    conn.close()
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Archivos procesados:     {archivos_procesados}")
    print(f"Archivos con error:      {archivos_con_error}")
    print(f"Total POIs insertados:   {total_insertados}")
    print("=" * 80)
    
    if total_insertados > 0:
        print("\n✓ Carga completada exitosamente")
        sys.exit(0)
    else:
        print("\n⚠ No se insertaron registros")
        sys.exit(1)


if __name__ == '__main__':
    main()
