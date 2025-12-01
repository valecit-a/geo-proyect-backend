#!/usr/bin/env python3
"""
Script de Carga de Datos desde GeoJSON a PostgreSQL

Este script:
1. Lee los archivos GeoJSON de propiedades en venta
2. Parsea y normaliza los datos
3. Calcula las features necesarias para el modelo
4. Carga los datos en la tabla propiedades de PostgreSQL
5. Predice satisfacción para todas las propiedades usando el modelo LightGBM

Uso:
    python cargar_datos_propiedades.py
    
    # Solo verificar sin cargar:
    python cargar_datos_propiedades.py --dry-run
    
    # Limpiar tabla antes de cargar:
    python cargar_datos_propiedades.py --clean

Requisitos:
    pip install geopandas psycopg2-binary sqlalchemy geoalchemy2 lightgbm
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd
import geopandas as gpd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pickle

# Rutas
BASE_DIR = Path('/home/felipe/Documentos/GeoInformatica')
DATOS_DIR = BASE_DIR / 'datos_nuevos' / 'DATOS_FILTRADOS'
MODELO_PATH = BASE_DIR / 'autocorrelacion_espacial' / 'semana3_modelo_satisfaccion' / 'modelos' / 'modelo_satisfaccion_venta.pkl'
BACKEND_DIR = BASE_DIR / 'geo-proyect-backend'

# Configuración BD (ajustar según docker-compose.yml)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5433'),
    'database': os.getenv('DB_NAME', 'inmobiliario_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'felipeb222')
}

# Valor UF actual (CLP)
VALOR_UF = 38500


def crear_conexion():
    """Crea conexión a la base de datos PostgreSQL"""
    db_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(db_url)
    return engine


def parsear_numero(valor):
    """Extrae número de un string"""
    if pd.isna(valor) or valor is None:
        return None
    
    # Si ya es número, retornarlo
    if isinstance(valor, (int, float)):
        return float(valor)
    
    # Extraer número del string
    match = re.search(r'[\d,\.]+', str(valor).replace(',', '.'))
    if match:
        try:
            # Manejar rangos como "127 - 128 m²"
            num_str = match.group().replace(',', '')
            return float(num_str)
        except ValueError:
            return None
    return None


def parsear_dormitorios_banos(valor):
    """Extrae número de dormitorios/baños del string"""
    if pd.isna(valor) or valor is None:
        return None
    
    match = re.search(r'(\d+)', str(valor))
    if match:
        return int(match.group(1))
    return None


def normalizar_precio(precio, moneda):
    """Normaliza precio a UF"""
    precio_num = parsear_numero(precio)
    if precio_num is None:
        return None
    
    moneda = str(moneda).upper() if pd.notna(moneda) else 'CLF'
    
    if moneda == 'CLP':
        # Convertir pesos a UF
        return precio_num / VALOR_UF
    elif moneda in ['CLF', 'UF']:
        # Ya está en UF
        return precio_num
    else:
        # Asumir UF por defecto
        return precio_num


def cargar_geojson(filepath):
    """Carga y procesa un archivo GeoJSON"""
    print(f"   📂 Cargando {filepath.name}...")
    
    try:
        gdf = gpd.read_file(filepath)
        print(f"      ✓ {len(gdf)} propiedades leídas")
        return gdf
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return None


def procesar_propiedades(gdf, comuna_nombre, tipo_propiedad):
    """Procesa un GeoDataFrame de propiedades"""
    registros = []
    
    for idx, row in gdf.iterrows():
        props = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
        
        # Extraer coordenadas
        geom = props.get('geometry')
        if geom is not None and hasattr(geom, 'x'):
            lon = geom.x
            lat = geom.y
        else:
            lon, lat = None, None
        
        # Parsear campos
        superficie = parsear_numero(props.get('metros_utiles'))
        dormitorios = parsear_dormitorios_banos(props.get('dormitorios'))
        banos = parsear_dormitorios_banos(props.get('banos'))
        precio_uf = normalizar_precio(props.get('precio'), props.get('moneda'))
        
        # Calcular precio por m²
        precio_m2_uf = None
        if precio_uf and superficie and superficie > 0:
            precio_m2_uf = precio_uf / superficie
        
        # Features derivadas
        m2_por_dormitorio = None
        m2_por_habitante = None
        ratio_bano_dorm = None
        total_habitaciones = None
        
        if superficie and dormitorios and dormitorios > 0:
            m2_por_dormitorio = superficie / dormitorios
            m2_por_habitante = superficie / (dormitorios * 2)
        
        if banos and dormitorios and dormitorios > 0:
            ratio_bano_dorm = banos / dormitorios
            total_habitaciones = dormitorios + banos
        
        registro = {
            # Ubicación
            'comuna_nombre': comuna_nombre,
            'direccion': props.get('direccion_geocoded', props.get('ubicacion')),
            'latitud': lat,
            'longitud': lon,
            
            # Características físicas
            'superficie_util': superficie,
            'superficie_total': superficie,  # Asumir igual por ahora
            'dormitorios': dormitorios,
            'banos': banos,
            'estacionamientos': 0,  # No disponible en datos
            'bodegas': 0,
            
            # Tipo
            'tipo_propiedad': tipo_propiedad,
            'tipo_departamento': 'exterior' if tipo_propiedad == 'departamento' else 'Casa',
            
            # Precio
            'precio': precio_uf * VALOR_UF if precio_uf else None,  # En CLP
            'precio_uf': precio_uf,
            'precio_m2_uf': precio_m2_uf,
            'divisa': 'CLP',
            
            # Features derivadas
            'm2_por_dormitorio': m2_por_dormitorio,
            'm2_por_habitante': m2_por_habitante,
            'ratio_bano_dorm': ratio_bano_dorm,
            'total_habitaciones': total_habitaciones,
            
            # Metadata
            'titulo': props.get('titulo'),
            'fuente': 'portal_inmobiliario',
            'fecha_publicacion': props.get('fecha_extraccion'),
            'created_at': datetime.now(),
        }
        
        registros.append(registro)
    
    return registros


def obtener_o_crear_comuna(engine, nombre):
    """Obtiene ID de comuna o la crea si no existe"""
    with engine.connect() as conn:
        # Buscar comuna existente
        result = conn.execute(
            text("SELECT id FROM comunas WHERE nombre = :nombre"),
            {'nombre': nombre}
        ).fetchone()
        
        if result:
            return result[0]
        
        # Crear comuna
        result = conn.execute(
            text("""
                INSERT INTO comunas (nombre, codigo, total_propiedades)
                VALUES (:nombre, :codigo, 0)
                RETURNING id
            """),
            {'nombre': nombre, 'codigo': nombre[:3].upper()}
        )
        conn.commit()
        return result.fetchone()[0]


def cargar_modelo():
    """Carga el modelo de satisfacción"""
    if not MODELO_PATH.exists():
        print(f"   ⚠️ Modelo no encontrado en {MODELO_PATH}")
        return None, None, None
    
    with open(MODELO_PATH, 'rb') as f:
        data = pickle.load(f)
    
    return data.get('modelo'), data.get('scaler'), data.get('features')


def predecir_satisfaccion(df, modelo, scaler, features):
    """Predice satisfacción para un DataFrame de propiedades"""
    if modelo is None:
        return [None] * len(df)
    
    # Preparar features
    X = pd.DataFrame()
    
    for feat in features:
        if feat in df.columns:
            X[feat] = df[feat]
        elif feat.startswith('comuna_'):
            # One-hot encoding de comuna
            comuna_target = feat.replace('comuna_', '')
            X[feat] = (df['comuna_nombre'] == comuna_target).astype(int)
        elif feat == 'es_departamento':
            X[feat] = (df['tipo_propiedad'] == 'departamento').astype(int)
        elif feat == 'es_casa':
            X[feat] = (df['tipo_propiedad'] == 'casa').astype(int)
        else:
            X[feat] = 0  # Valor por defecto
    
    # Rellenar NaN
    X = X.fillna(0)
    
    # Escalar y predecir
    try:
        X_scaled = scaler.transform(X)
        predicciones = modelo.predict(X_scaled)
        # Clampear a rango 0-10
        predicciones = np.clip(predicciones, 0, 10)
        return predicciones
    except Exception as e:
        print(f"   ⚠️ Error en predicción: {e}")
        return [None] * len(df)


def insertar_propiedades(engine, propiedades, comuna_id):
    """Inserta propiedades en la base de datos"""
    inserted = 0
    
    with engine.connect() as conn:
        for prop in propiedades:
            try:
                # Construir WKT para geometría
                geom_wkt = None
                if prop.get('latitud') and prop.get('longitud'):
                    geom_wkt = f"POINT({prop['longitud']} {prop['latitud']})"
                
                conn.execute(
                    text("""
                        INSERT INTO propiedades (
                            comuna_id, direccion, latitud, longitud, geometria,
                            superficie_total, superficie_util, dormitorios, banos,
                            estacionamientos, bodegas, tipo_departamento,
                            precio, divisa, titulo, fuente, fecha_publicacion,
                            satisfaccion_predicha, created_at
                        ) VALUES (
                            :comuna_id, :direccion, :latitud, :longitud,
                            ST_SetSRID(ST_GeomFromText(:geom), 4326),
                            :superficie_total, :superficie_util, :dormitorios, :banos,
                            :estacionamientos, :bodegas, :tipo_departamento,
                            :precio, :divisa, :titulo, :fuente, :fecha_publicacion,
                            :satisfaccion, NOW()
                        )
                    """),
                    {
                        'comuna_id': comuna_id,
                        'direccion': prop.get('direccion'),
                        'latitud': prop.get('latitud'),
                        'longitud': prop.get('longitud'),
                        'geom': geom_wkt,
                        'superficie_total': prop.get('superficie_total'),
                        'superficie_util': prop.get('superficie_util'),
                        'dormitorios': prop.get('dormitorios'),
                        'banos': prop.get('banos'),
                        'estacionamientos': prop.get('estacionamientos'),
                        'bodegas': prop.get('bodegas'),
                        'tipo_departamento': prop.get('tipo_departamento'),
                        'precio': prop.get('precio'),
                        'divisa': prop.get('divisa'),
                        'titulo': prop.get('titulo'),
                        'fuente': prop.get('fuente'),
                        'fecha_publicacion': prop.get('fecha_publicacion'),
                        'satisfaccion': prop.get('satisfaccion_predicha'),
                    }
                )
                inserted += 1
            except Exception as e:
                print(f"      ⚠️ Error insertando: {e}")
        
        conn.commit()
    
    return inserted


def limpiar_tabla(engine):
    """Limpia la tabla de propiedades"""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM propiedades"))
        conn.commit()
    print("   ✓ Tabla propiedades limpiada")


def main():
    parser = argparse.ArgumentParser(description='Cargar datos de propiedades a PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Solo verificar, no cargar')
    parser.add_argument('--clean', action='store_true', help='Limpiar tabla antes de cargar')
    args = parser.parse_args()
    
    print("=" * 80)
    print("🏠 CARGA DE DATOS DE PROPIEDADES EN VENTA")
    print("=" * 80)
    
    # 1. Conectar a BD
    print("\n📡 Conectando a base de datos...")
    try:
        engine = crear_conexion()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✓ Conexión exitosa")
    except Exception as e:
        print(f"   ✗ Error de conexión: {e}")
        sys.exit(1)
    
    # 2. Limpiar si se solicita
    if args.clean and not args.dry_run:
        print("\n🗑️ Limpiando tabla...")
        limpiar_tabla(engine)
    
    # 3. Cargar modelo de satisfacción
    print("\n🧠 Cargando modelo de satisfacción...")
    modelo, scaler, features = cargar_modelo()
    if modelo:
        print(f"   ✓ Modelo cargado: {len(features)} features")
    else:
        print("   ⚠️ Modelo no disponible, se cargará sin predicciones")
    
    # 4. Cargar archivos GeoJSON
    print("\n📂 Procesando archivos GeoJSON...")
    
    # Mapeo de archivos a comunas/tipos
    archivos_config = {
        'casas_estacon_central.geojson': ('Estación Central', 'casa'),
        'casas_la_reina.geojson': ('La Reina', 'casa'),
        'casas_nunoa.geojson': ('Ñuñoa', 'casa'),
        'casas_Santiago.geojson': ('Santiago', 'casa'),
        'departamentos_estacion_central.geojson': ('Estación Central', 'departamento'),
        'departamentos_la_reina.geojson': ('La Reina', 'departamento'),
        'departamentos_nunoa.geojson': ('Ñuñoa', 'departamento'),
        'departamentos_Santiago.geojson': ('Santiago', 'departamento'),
    }
    
    total_cargadas = 0
    resumen = []
    
    for archivo, (comuna_nombre, tipo) in archivos_config.items():
        filepath = DATOS_DIR / archivo
        
        if not filepath.exists():
            print(f"   ⚠️ Archivo no encontrado: {archivo}")
            continue
        
        # Cargar GeoJSON
        gdf = cargar_geojson(filepath)
        if gdf is None or len(gdf) == 0:
            continue
        
        # Procesar propiedades
        propiedades = procesar_propiedades(gdf, comuna_nombre, tipo)
        
        # Crear DataFrame para predicción
        df_props = pd.DataFrame(propiedades)
        
        # Predecir satisfacción
        if modelo:
            predicciones = predecir_satisfaccion(df_props, modelo, scaler, features)
            for i, pred in enumerate(predicciones):
                propiedades[i]['satisfaccion_predicha'] = pred
        
        if args.dry_run:
            print(f"   [DRY-RUN] {archivo}: {len(propiedades)} propiedades")
            resumen.append({
                'archivo': archivo,
                'comuna': comuna_nombre,
                'tipo': tipo,
                'cantidad': len(propiedades)
            })
            continue
        
        # Obtener/crear comuna
        comuna_id = obtener_o_crear_comuna(engine, comuna_nombre)
        
        # Insertar propiedades
        inserted = insertar_propiedades(engine, propiedades, comuna_id)
        total_cargadas += inserted
        
        resumen.append({
            'archivo': archivo,
            'comuna': comuna_nombre,
            'tipo': tipo,
            'cantidad': inserted
        })
        
        print(f"   ✓ {archivo}: {inserted} propiedades cargadas")
    
    # 5. Resumen final
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE CARGA")
    print("=" * 80)
    
    df_resumen = pd.DataFrame(resumen)
    print(df_resumen.to_string(index=False))
    
    print(f"\n📈 Total propiedades: {df_resumen['cantidad'].sum()}")
    
    if not args.dry_run:
        # Actualizar estadísticas de comunas
        print("\n📊 Actualizando estadísticas de comunas...")
        with engine.connect() as conn:
            conn.execute(text("""
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
                    )
            """))
            conn.commit()
        print("   ✓ Estadísticas actualizadas")
    
    print("\n✅ Proceso completado exitosamente!")


if __name__ == '__main__':
    main()
