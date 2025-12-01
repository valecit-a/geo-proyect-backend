#!/usr/bin/env python3
"""
Script simplificado para cargar propiedades desde GeoJSON a PostgreSQL
y calcular satisfacción predicha.
"""
import sys
import json
from pathlib import Path
import psycopg2
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

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

def parsear_precio(precio_str, moneda):
    """Parsea el precio del string"""
    if precio_str is None:
        return None
    
    try:
        # Limpiar el string
        precio_str = str(precio_str).replace('.', '').replace(',', '.').strip()
        # Extraer número
        import re
        match = re.search(r'[\d\.]+', precio_str)
        if match:
            precio = float(match.group())
            # CLF = UF, no convertir
            # CLP = pesos chilenos, convertir a UF
            moneda_str = str(moneda).upper() if moneda else 'CLP'
            if moneda_str == 'CLF' or moneda_str == 'UF':
                return precio  # Ya está en UF
            elif moneda_str == 'CLP' or precio > 100000:
                return precio / VALOR_UF  # Convertir de CLP a UF
            return precio
    except:
        pass
    return None

def predecir_satisfaccion(modelo, scaler, features, superficie, dormitorios, banos, precio_uf, comuna, tipo):
    """Predice satisfacción para una propiedad"""
    if modelo is None or superficie is None or dormitorios is None or banos is None or precio_uf is None:
        return None
    
    try:
        # Calcular features derivadas
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
        
        # Crear vector con todas las features (rellenar con 0 las que faltan)
        X = pd.DataFrame([{f: feature_dict.get(f, 0) for f in features}])
        X = X.fillna(0)
        
        # Escalar y predecir
        X_scaled = scaler.transform(X)
        pred = modelo.predict(X_scaled)[0]
        
        # Clampear a 0-10
        return float(np.clip(pred, 0, 10))
    except Exception as e:
        return None

def cargar_geojson(filepath, comuna, tipo):
    """Carga un archivo GeoJSON y retorna las propiedades"""
    propiedades = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [None, None])
        
        # Extraer datos básicos - campos reales del GeoJSON
        prop = {
            'direccion': props.get('direccion_geocoded', props.get('ubicacion', '')),
            'latitud': coords[1] if len(coords) > 1 else None,
            'longitud': coords[0] if len(coords) > 0 else None,
            'superficie_util': props.get('metros_utiles', props.get('superficie_util')),
            'dormitorios': props.get('dormitorios'),
            'banos': props.get('banos'),
            'precio': props.get('precio'),
            'moneda': props.get('moneda', 'CLP'),
            'titulo': props.get('titulo', ''),
            'comuna': comuna,
            'tipo': tipo
        }
        
        # Limpiar dormitorios (formato: "3 dormitorios")
        if prop['dormitorios']:
            try:
                import re
                match = re.search(r'(\d+)', str(prop['dormitorios']))
                prop['dormitorios'] = int(match.group(1)) if match else None
            except:
                prop['dormitorios'] = None
        
        # Limpiar baños (formato: "2 baños")
        if prop['banos']:
            try:
                import re
                match = re.search(r'(\d+)', str(prop['banos']))
                prop['banos'] = int(match.group(1)) if match else None
            except:
                prop['banos'] = None
        
        # Limpiar superficie (formato: "85 m² útiles")
        if prop['superficie_util']:
            try:
                import re
                sup_str = str(prop['superficie_util']).replace('m²', '').replace('útiles', '').replace(',', '.').strip()
                # Manejar rangos como "127 - 128"
                if '-' in sup_str:
                    sup_str = sup_str.split('-')[0]
                match = re.search(r'[\d\.]+', sup_str)
                prop['superficie_util'] = float(match.group()) if match else None
            except:
                prop['superficie_util'] = None
        
        propiedades.append(prop)
    
    return propiedades

def main():
    print("=" * 80)
    print("🏠 CARGA SIMPLIFICADA DE PROPIEDADES")
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
        print("   ⚠️ Modelo no disponible")
    
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
    resumen = []
    
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
            print(f"      ⚠️ Comuna {comuna} no encontrada, saltando...")
            resumen.append({'archivo': archivo, 'comuna': comuna, 'tipo': tipo, 'insertadas': 0})
            continue
        
        # Insertar propiedades
        insertadas = 0
        errores = 0
        for i, prop in enumerate(propiedades):
            try:
                # Parsear precio a UF
                precio_uf = parsear_precio(prop['precio'], prop['moneda'])
                
                # Validar datos mínimos
                if prop['latitud'] is None or prop['longitud'] is None:
                    errores += 1
                    continue
                if prop['superficie_util'] is None or prop['superficie_util'] <= 0:
                    errores += 1
                    continue
                if prop['dormitorios'] is None or prop['dormitorios'] <= 0:
                    errores += 1
                    continue
                if prop['banos'] is None or prop['banos'] <= 0:
                    errores += 1
                    continue
                if precio_uf is None or precio_uf <= 0:
                    errores += 1
                    continue
                
                # Predecir satisfacción
                satisfaccion = predecir_satisfaccion(
                    modelo, scaler, features,
                    prop['superficie_util'],
                    prop['dormitorios'],
                    prop['banos'],
                    precio_uf,
                    comuna,
                    tipo
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
                    prop['direccion'][:300] if prop['direccion'] else None,
                    prop['latitud'],
                    prop['longitud'],
                    prop['longitud'],
                    prop['latitud'],
                    prop['superficie_util'],  # superficie_total
                    prop['superficie_util'],  # superficie_util
                    prop['dormitorios'],
                    prop['banos'],
                    precio_uf,
                    tipo,
                    satisfaccion,
                    'geojson_carga'
                ))
                insertadas += 1
            except Exception as e:
                errores += 1
                if errores <= 3:  # Solo mostrar primeros 3 errores
                    print(f"      Error en prop {i}: {e}")
                conn.rollback()
        
        conn.commit()
        print(f"      ✓ Insertadas: {insertadas}")
        total_insertadas += insertadas
        resumen.append({'archivo': archivo, 'comuna': comuna, 'tipo': tipo, 'insertadas': insertadas})
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE CARGA")
    print("=" * 80)
    for r in resumen:
        print(f"   {r['archivo']:45} {r['comuna']:20} {r['tipo']:12} {r['insertadas']:>5}")
    print(f"\n📈 Total propiedades insertadas: {total_insertadas}")
    
    # Verificar total
    cur.execute("SELECT COUNT(*) FROM propiedades")
    total = cur.fetchone()[0]
    print(f"📊 Total propiedades en BD: {total}")
    
    # Estadísticas de satisfacción
    cur.execute("SELECT AVG(satisfaccion_predicha), MIN(satisfaccion_predicha), MAX(satisfaccion_predicha) FROM propiedades WHERE satisfaccion_predicha IS NOT NULL")
    stats = cur.fetchone()
    if stats[0]:
        print(f"📈 Satisfacción: avg={stats[0]:.2f}, min={stats[1]:.2f}, max={stats[2]:.2f}")
    
    conn.close()
    print("\n✅ Proceso completado!")

if __name__ == '__main__':
    main()
