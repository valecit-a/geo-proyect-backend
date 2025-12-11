#!/usr/bin/env python3
"""
Script para cargar propiedades desde archivos GeoJSON
Carga las ~8,000 propiedades de datos_nuevos/DATOS_FILTRADOS/
"""

import os
import sys
import json
import re
from pathlib import Path

# Intentar importar psycopg2
try:
    import psycopg2
except ImportError:
    print("❌ Error: psycopg2 no está instalado")
    print("   Instalar con: pip install psycopg2-binary")
    sys.exit(1)


def extract_number(value):
    """Extrae un número entero de un valor que puede ser string o número"""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r'(\d+)', str(value))
    return int(match.group(1)) if match else 0


def extract_float(value):
    """Extrae un float de un valor que puede ser string o número"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Limpiar string: quitar puntos de miles, cambiar coma por punto
    s = str(value).replace('.', '').replace(',', '.').strip()
    match = re.search(r'([\d.]+)', s)
    return float(match.group(1)) if match else 0.0


def get_db_connection():
    """Obtiene conexión a la base de datos"""
    # Intentar diferentes configuraciones
    configs = [
        # Docker interno (nombre del servicio en docker-compose)
        {'host': 'geoinformatica-db', 'port': 5432, 'database': 'inmobiliaria_db', 'user': 'postgres', 'password': 'geo_pass'},
        {'host': 'db', 'port': 5432, 'database': 'inmobiliaria_db', 'user': 'postgres', 'password': 'geo_pass'},
        # Docker desde host
        {'host': 'localhost', 'port': 5432, 'database': 'inmobiliaria_db', 'user': 'postgres', 'password': 'geo_pass'},
        # Alternativas
        {'host': 'localhost', 'port': 5433, 'database': 'inmobiliaria_db', 'user': 'postgres', 'password': 'geo_pass'},
    ]
    
    for config in configs:
        try:
            conn = psycopg2.connect(**config)
            print(f"✅ Conectado a {config['host']}:{config['port']}/{config['database']}")
            return conn
        except Exception as e:
            continue
    
    print("❌ No se pudo conectar a la base de datos")
    sys.exit(1)


def setup_comunas(cursor, conn):
    """Obtiene el mapeo de comunas existentes en la base de datos"""
    # Primero verificar si las comunas que necesitamos existen
    comunas_necesarias = ['Santiago', 'Ñuñoa', 'La Reina', 'Estación Central']
    
    # Obtener mapa de comunas existentes (buscar por nombre)
    cursor.execute("SELECT id, nombre FROM comunas")
    comunas_map = {}
    for row in cursor.fetchall():
        id_comuna, nombre = row
        comunas_map[nombre] = id_comuna
        # También mapear variantes sin tildes
        nombre_sin_tildes = nombre.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        comunas_map[nombre_sin_tildes] = id_comuna
    
    # Agregar alias comunes
    if 'Ñuñoa' in comunas_map:
        comunas_map['Nunoa'] = comunas_map['Ñuñoa']
    if 'La Reina' in comunas_map:
        comunas_map['LaReina'] = comunas_map['La Reina']
    if 'Estación Central' in comunas_map:
        comunas_map['Estacion Central'] = comunas_map['Estación Central']
        comunas_map['EstacionCentral'] = comunas_map['Estación Central']
    
    # Verificar que tenemos las comunas necesarias
    for comuna in comunas_necesarias:
        if comuna not in comunas_map:
            print(f"⚠️  Advertencia: Comuna '{comuna}' no encontrada en DB, usando ID por defecto")
            # Intentar insertar
            try:
                cursor.execute("INSERT INTO comunas (nombre) VALUES (%s) RETURNING id", (comuna,))
                new_id = cursor.fetchone()[0]
                comunas_map[comuna] = new_id
                conn.commit()
            except Exception as e:
                print(f"   Error insertando comuna: {e}")
                # Usar Santiago como fallback
                comunas_map[comuna] = comunas_map.get('Santiago', 1)
    
    return comunas_map


def find_geojson_dir():
    """Encuentra el directorio de archivos GeoJSON"""
    possible_paths = [
        Path('./datos_nuevos/DATOS_FILTRADOS'),
        Path('../datos_nuevos/DATOS_FILTRADOS'),
        Path('../../datos_nuevos/DATOS_FILTRADOS'),
    ]
    
    for path in possible_paths:
        if path.exists() and list(path.glob('*.geojson')):
            return path
    
    print("❌ No se encontró el directorio de GeoJSON")
    print("   Buscado en:", [str(p) for p in possible_paths])
    sys.exit(1)


def load_geojson_files(geojson_dir, cursor, conn, comunas_map):
    """Carga todos los archivos GeoJSON"""
    archivos = list(geojson_dir.glob('*.geojson'))
    print(f"\n📁 Archivos GeoJSON encontrados: {len(archivos)}")
    
    total_features = 0
    insertados = 0
    errores = 0
    
    for archivo in archivos:
        with open(archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        total_features += len(features)
        
        # Determinar tipo y comuna del nombre del archivo
        nombre_archivo = archivo.name.lower()
        tipo = 'departamento' if 'departamento' in nombre_archivo else 'casa'
        
        if 'santiago' in nombre_archivo:
            comuna_nombre = 'Santiago'
        elif 'nunoa' in nombre_archivo or 'ñuñoa' in nombre_archivo:
            comuna_nombre = 'Ñuñoa'
        elif 'reina' in nombre_archivo:
            comuna_nombre = 'La Reina'
        elif 'estacion' in nombre_archivo or 'central' in nombre_archivo:
            comuna_nombre = 'Estación Central'
        else:
            comuna_nombre = 'Santiago'
        
        comuna_id = comunas_map.get(comuna_nombre, 1)
        archivo_insertados = 0
        
        for feature in features:
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [None, None])
            
            lon, lat = coords[0], coords[1]
            if not lat or not lon:
                errores += 1
                continue
            
            try:
                precio = extract_float(props.get('Precio (UF)', props.get('precio_uf', props.get('precio', 0))))
                superficie = extract_float(props.get('superficie_util', props.get('Superficie útil', props.get('metros_utiles', 50))))
                dormitorios = extract_number(props.get('dormitorios', props.get('Dormitorios', 2))) or 2
                banos = extract_number(props.get('banos', props.get('Baños', 1))) or 1
                estacionamientos = extract_number(props.get('estacionamientos', 0))
                
                # Extraer dirección: preferir direccion_geocoded, luego ubicacion, luego comuna
                direccion = props.get('direccion_geocoded') or props.get('ubicacion') or props.get('direccion') or comuna_nombre
                
                # El tipo se determina del nombre del archivo (Casa o Departamento)
                tipo_propiedad = 'Departamento' if 'departamento' in nombre_archivo else 'Casa'
                
                cursor.execute('''
                    INSERT INTO propiedades (
                        comuna_id, titulo, descripcion, precio, 
                        superficie_util, superficie_total,
                        dormitorios, banos, estacionamientos, bodegas,
                        direccion, latitud, longitud, 
                        geometria, divisa, fuente, tipo_departamento
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s
                    )
                ''', (
                    comuna_id,
                    props.get('titulo', f'{tipo.title()} en {comuna_nombre}'),
                    props.get('descripcion', ''),
                    precio if precio > 0 else None,
                    superficie if superficie > 0 else 50,
                    superficie if superficie > 0 else 50,
                    dormitorios,
                    banos,
                    estacionamientos,
                    extract_number(props.get('bodegas', 0)),
                    direccion,
                    lat,
                    lon,
                    lon, lat,
                    'UF',
                    'GeoJSON',
                    tipo_propiedad
                ))
                insertados += 1
                archivo_insertados += 1
                
            except Exception as e:
                errores += 1
                conn.rollback()
        
        conn.commit()
        print(f"   ✅ {archivo.name}: {archivo_insertados}/{len(features)} insertados")
    
    return total_features, insertados, errores


def main():
    print("=" * 70)
    print("🏠 CARGA DE PROPIEDADES DESDE GEOJSON")
    print("=" * 70)
    
    # Conectar a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Limpiar propiedades existentes
    print("\n🗑️  Limpiando propiedades existentes...")
    cursor.execute("DELETE FROM propiedades")
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM propiedades")
    print(f"   Propiedades después de limpiar: {cursor.fetchone()[0]}")
    
    # Configurar comunas
    print("\n📍 Configurando comunas...")
    comunas_map = setup_comunas(cursor, conn)
    print(f"   Comunas disponibles: {len(comunas_map)}")
    
    # Encontrar directorio de GeoJSON
    geojson_dir = find_geojson_dir()
    print(f"\n📂 Directorio de datos: {geojson_dir}")
    
    # Cargar archivos
    total, insertados, errores = load_geojson_files(geojson_dir, cursor, conn, comunas_map)
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE CARGA")
    print("=" * 70)
    print(f"   Total features en archivos: {total}")
    print(f"   ✅ Propiedades insertadas: {insertados}")
    print(f"   ❌ Errores: {errores}")
    
    # Verificar total en DB
    cursor.execute("SELECT COUNT(*) FROM propiedades")
    total_db = cursor.fetchone()[0]
    print(f"\n🏠 Total en base de datos: {total_db}")
    
    # Distribución por comuna
    cursor.execute('''
        SELECT c.nombre, COUNT(*) 
        FROM propiedades p 
        JOIN comunas c ON p.comuna_id = c.id 
        GROUP BY c.nombre
        ORDER BY COUNT(*) DESC
    ''')
    print("\n📍 Distribución por comuna:")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ CARGA COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
