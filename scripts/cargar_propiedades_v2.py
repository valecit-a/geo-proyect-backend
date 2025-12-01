#!/usr/bin/env python3
"""
Script mejorado para cargar propiedades desde GeoJSON a PostgreSQL
con mejor manejo de errores y diagnóstico.
"""
import sys
import json
import re
import warnings
from pathlib import Path
import psycopg2
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

# Suprimir warnings de sklearn
warnings.filterwarnings('ignore')

# Rutas
BASE_DIR = Path('/home/felipe/Documentos/GeoInformatica')
DATOS_DIR = BASE_DIR / 'datos_nuevos' / 'DATOS_FILTRADOS'
MODELO_PATH = BASE_DIR / 'geo-proyect-backend' / 'modelos' / 'modelo_satisfaccion_venta.pkl'

# Configuración BD
DB_CONFIG = {
    'host': 'localhost',
    'port': '5433',
    'database': 'inmobiliario_db',
    'user': 'postgres',
    'password': 'felipeb222'
}

# Valor UF
VALOR_UF = 38500

def cargar_modelo():
    """Carga el modelo de satisfacción"""
    try:
        with open(MODELO_PATH, 'rb') as f:
            data = pickle.load(f)
        return data['modelo'], data['scaler'], data['features']
    except Exception as e:
        print(f"Error cargando modelo: {e}")
        return None, None, None

def parsear_numero(texto):
    """Extrae número de un texto"""
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)
    try:
        # Limpiar texto
        texto = str(texto).replace(',', '.').strip()
        # Buscar número
        match = re.search(r'[\d\.]+', texto)
        if match:
            return float(match.group())
    except:
        pass
    return None

def parsear_precio(precio_str, moneda):
    """Parsea el precio del string"""
    precio = parsear_numero(precio_str)
    if precio is None:
        return None
    
    moneda_str = str(moneda).upper() if moneda else 'CLP'
    # CLF = UF
    if moneda_str in ('CLF', 'UF'):
        return precio
    # CLP = pesos chilenos
    elif moneda_str == 'CLP' or precio > 100000:
        return precio / VALOR_UF
    return precio

def predecir_satisfaccion(modelo, scaler, features, superficie, dormitorios, banos, precio_uf, comuna, tipo):
    """Predice satisfacción para una propiedad"""
    if modelo is None:
        return 5.5  # Valor por defecto
    if any(x is None for x in [superficie, dormitorios, banos, precio_uf]):
        return 5.5
    
    try:
        sup = max(1, superficie)
        dorms = max(1, dormitorios)
        
        feature_dict = {
            'superficie_util': superficie,
            'dormitorios': dormitorios,
            'banos': banos,
            'precio_uf': precio_uf,
            'precio_m2_uf': precio_uf / sup,
            'm2_por_dormitorio': superficie / dorms,
            'm2_por_habitante': superficie / (dorms * 2),
            'ratio_bano_dorm': banos / dorms,
            'total_habitaciones': dormitorios + banos,
            'es_departamento': 1 if tipo.lower() == 'departamento' else 0,
            'es_casa': 1 if tipo.lower() == 'casa' else 0,
            'comuna_Estación Central': 1 if comuna == 'Estación Central' else 0,
            'comuna_La Reina': 1 if comuna == 'La Reina' else 0,
            'comuna_Ñuñoa': 1 if comuna == 'Ñuñoa' else 0,
            'comuna_Santiago': 1 if comuna == 'Santiago' else 0,
        }
        
        X = pd.DataFrame([{f: feature_dict.get(f, 0) for f in features}])
        X = X.fillna(0)
        X_scaled = scaler.transform(X)
        pred = modelo.predict(X_scaled)[0]
        return float(np.clip(pred, 0, 10))
    except Exception as e:
        return 5.5

def cargar_geojson(filepath, comuna, tipo):
    """Carga un archivo GeoJSON y retorna las propiedades"""
    propiedades = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [None, None])
        
        # Extraer datos
        prop = {
            'direccion': props.get('direccion_geocoded', props.get('ubicacion', '')),
            'latitud': coords[1] if len(coords) > 1 else None,
            'longitud': coords[0] if len(coords) > 0 else None,
            'superficie_util': parsear_numero(props.get('metros_utiles')),
            'dormitorios': parsear_numero(props.get('dormitorios')),
            'banos': parsear_numero(props.get('banos')),
            'precio': props.get('precio'),
            'moneda': props.get('moneda', 'CLP'),
            'titulo': props.get('titulo', ''),
            'comuna': comuna,
            'tipo': tipo
        }
        
        # Convertir dormitorios y baños a int
        if prop['dormitorios'] is not None:
            prop['dormitorios'] = int(prop['dormitorios'])
        if prop['banos'] is not None:
            prop['banos'] = int(prop['banos'])
        
        propiedades.append(prop)
    
    return propiedades

def main():
    print("=" * 80)
    print("🏠 CARGA MEJORADA DE PROPIEDADES - v2")
    print("=" * 80)
    
    # Conectar a BD
    print("\n📡 Conectando a base de datos...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("   ✓ Conexión exitosa")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        sys.exit(1)
    
    # Obtener comunas existentes
    cur.execute("SELECT id, nombre FROM comunas")
    comunas = {row[1]: row[0] for row in cur.fetchall()}
    print(f"   Comunas disponibles: {list(comunas.keys())}")
    
    # Cargar modelo
    print("\n🧠 Cargando modelo de satisfacción...")
    modelo, scaler, features = cargar_modelo()
    if modelo:
        print(f"   ✓ Modelo cargado: {len(features)} features")
    else:
        print("   ⚠️ Modelo no disponible, usando valor por defecto")
    
    # Archivos a procesar
    archivos = {
        'casas_estacon_central.geojson': ('Estación Central', 'casa'),
        'casas_la_reina.geojson': ('La Reina', 'casa'),
        'casas_nunoa.geojson': ('Ñuñoa', 'casa'),
        'casas_Santiago.geojson': ('Santiago', 'casa'),
        'departamentos_estacion_central.geojson': ('Estación Central', 'departamento'),
        'departamentos_la_reina.geojson': ('La Reina', 'departamento'),
        'departamentos_nunoa.geojson': ('Ñuñoa', 'departamento'),
        'departamentos_Santiago.geojson': ('Santiago', 'departamento'),
    }
    
    # Procesar cada archivo
    print("\n📂 Procesando archivos GeoJSON...")
    total_insertadas = 0
    total_errores = 0
    resumen = []
    direcciones_vistas = set()
    
    for archivo, (comuna, tipo) in archivos.items():
        filepath = DATOS_DIR / archivo
        if not filepath.exists():
            print(f"   ⚠️ No existe: {archivo}")
            continue
        
        print(f"   📂 Procesando {archivo}...")
        propiedades = cargar_geojson(filepath, comuna, tipo)
        print(f"      Leídas: {len(propiedades)}")
        
        # Obtener comuna_id
        comuna_id = comunas.get(comuna)
        if not comuna_id:
            print(f"      ⚠️ Comuna {comuna} no encontrada")
            resumen.append({'archivo': archivo, 'comuna': comuna, 'tipo': tipo, 'insertadas': 0, 'errores': len(propiedades)})
            continue
        
        # Insertar propiedades
        insertadas = 0
        errores = 0
        duplicados = 0
        
        for prop in propiedades:
            try:
                # Crear clave única para evitar duplicados
                clave = f"{prop['latitud']:.6f}_{prop['longitud']:.6f}" if prop['latitud'] and prop['longitud'] else None
                if clave and clave in direcciones_vistas:
                    duplicados += 1
                    continue
                if clave:
                    direcciones_vistas.add(clave)
                
                # Validar coordenadas
                if prop['latitud'] is None or prop['longitud'] is None:
                    errores += 1
                    continue
                
                # Parsear precio a UF
                precio_uf = parsear_precio(prop['precio'], prop['moneda'])
                
                # Valores por defecto si faltan datos
                superficie = prop['superficie_util'] if prop['superficie_util'] and prop['superficie_util'] > 0 else 50.0
                dormitorios = prop['dormitorios'] if prop['dormitorios'] and prop['dormitorios'] > 0 else 2
                banos = prop['banos'] if prop['banos'] and prop['banos'] > 0 else 1
                precio_uf = precio_uf if precio_uf and precio_uf > 0 else 3000.0
                
                # Predecir satisfacción
                satisfaccion = predecir_satisfaccion(
                    modelo, scaler, features,
                    superficie, dormitorios, banos,
                    precio_uf, comuna, tipo
                )
                
                # Insertar
                cur.execute("""
                    INSERT INTO propiedades (
                        comuna_id, direccion, latitud, longitud, geometria,
                        superficie_total, superficie_util, dormitorios, banos,
                        precio, tipo_propiedad, satisfaccion_predicha,
                        fuente, created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, NOW()
                    )
                """, (
                    comuna_id,
                    (prop['direccion'] or '')[:300],
                    prop['latitud'],
                    prop['longitud'],
                    prop['longitud'],
                    prop['latitud'],
                    superficie,
                    superficie,
                    dormitorios,
                    banos,
                    precio_uf,
                    tipo,
                    satisfaccion,
                    'geojson_v2'
                ))
                insertadas += 1
                
            except Exception as e:
                errores += 1
                conn.rollback()
                continue
        
        conn.commit()
        print(f"      ✓ Insertadas: {insertadas}, Duplicados: {duplicados}, Errores: {errores}")
        total_insertadas += insertadas
        total_errores += errores
        resumen.append({
            'archivo': archivo, 
            'comuna': comuna, 
            'tipo': tipo, 
            'insertadas': insertadas,
            'duplicados': duplicados,
            'errores': errores
        })
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE CARGA")
    print("=" * 80)
    for r in resumen:
        print(f"   {r['archivo']:45} {r['insertadas']:>5} ok, {r.get('duplicados', 0):>4} dup, {r.get('errores', 0):>4} err")
    
    print(f"\n📈 Total propiedades insertadas: {total_insertadas}")
    print(f"📈 Total errores: {total_errores}")
    
    # Verificar total
    cur.execute("SELECT COUNT(*) FROM propiedades")
    total = cur.fetchone()[0]
    print(f"📊 Total propiedades en BD: {total}")
    
    # Estadísticas de satisfacción
    cur.execute("""
        SELECT 
            AVG(satisfaccion_predicha), 
            MIN(satisfaccion_predicha), 
            MAX(satisfaccion_predicha),
            COUNT(satisfaccion_predicha)
        FROM propiedades 
        WHERE satisfaccion_predicha IS NOT NULL
    """)
    stats = cur.fetchone()
    if stats[0]:
        print(f"📈 Satisfacción: avg={stats[0]:.2f}, min={stats[1]:.2f}, max={stats[2]:.2f}")
    
    # Por comuna
    print("\n📊 Por comuna:")
    cur.execute("""
        SELECT c.nombre, COUNT(*) 
        FROM propiedades p 
        JOIN comunas c ON p.comuna_id = c.id 
        GROUP BY c.nombre 
        ORDER BY COUNT(*) DESC
    """)
    for row in cur.fetchall():
        print(f"   {row[0]:20} {row[1]:>6}")
    
    conn.close()
    print("\n✅ Proceso completado!")

if __name__ == '__main__':
    main()
