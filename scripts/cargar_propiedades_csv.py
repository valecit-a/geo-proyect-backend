"""
Script para cargar propiedades desde CSV a PostgreSQL Docker
Combina datos del CSV principal con datos geoespaciales de Semana 1
"""
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Set, Tuple, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import hashlib
import numpy as np

# Database URL (desde container a db)
DATABASE_URL = "postgresql://postgres:postgres@db:5432/inmobiliaria_db"

# Crear engine y session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Rutas dentro del container
CSV_PATH = Path("/app/clean_alquiler_02_11_2023cc.csv")
DATOS_GEOESPACIALES = Path("/app/datos_normalizados/datos_normalizados")

# Mapeo de comunas
COMUNAS_SANTIAGO = {
    'cerrillos': 1, 'cerro navia': 2, 'conchalí': 3, 'el bosque': 4,
    'estación central': 5, 'estacion central': 5, 'huechuraba': 6, 'independencia': 7,
    'la cisterna': 8, 'la florida': 9, 'la granja': 10, 'la pintana': 11,
    'la reina': 12, 'las condes': 13, 'lo barnechea': 14, 'lo espejo': 15,
    'lo prado': 16, 'macul': 17, 'maipú': 18, 'maipu': 18, 'ñuñoa': 19, 'nunoa': 19,
    'pedro aguirre cerda': 20, 'peñalolén': 21, 'penalolen': 21, 'providencia': 22,
    'pudahuel': 23, 'quilicura': 24, 'quinta normal': 25, 'recoleta': 26,
    'renca': 27, 'san joaquín': 28, 'san joaquin': 28, 'san miguel': 29,
    'san ramón': 30, 'san ramon': 30, 'santiago': 31, 'vitacura': 32,
}

def generar_hash_propiedad(row: pd.Series) -> str:
    """Genera hash único para identificar duplicados"""
    datos_clave = f"{row.get('latitude', 0):.6f}_{row.get('longitude', 0):.6f}_{row.get('precio', 0):.0f}_{row.get('dormitorios', 0)}_{row.get('banos', 0)}"
    return hashlib.md5(datos_clave.encode()).hexdigest()


def obtener_comuna_id(nombre_comuna: str) -> int:
    """Obtiene ID de comuna"""
    if pd.isna(nombre_comuna):
        return 31  # Santiago por defecto
    
    nombre_limpio = str(nombre_comuna).strip().lower()
    return COMUNAS_SANTIAGO.get(nombre_limpio, 31)


def cargar_datos_geoespaciales() -> Dict:
    """Carga archivos GeoJSON de datos geoespaciales (metro, colegios, hospitales, etc.)"""
    print("\n📍 Cargando datos geoespaciales de Semana 1...")
    
    datos_geo = {}
    archivos_interes = {
        'metro': 'Lineas_de_metro_de_Santiago.geojson',
        'educacion': 'establecimientos_educacion_escolar.geojson',
        'salud': 'puntos_medicos_farmacias_hospitales_filtrados.geojson',
        'areas_verdes': 'areas_verdes_filtradas.geojson',
        'comercio': 'tiendas_filtradas.geojson',
    }
    
    for nombre, archivo in archivos_interes.items():
        filepath = DATOS_GEOESPACIALES / archivo
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    features = data.get('features', [])
                    datos_geo[nombre] = features
                    print(f"   ✅ {nombre}: {len(features)} puntos")
            except Exception as e:
                print(f"   ⚠️  Error cargando {nombre}: {str(e)[:50]}")
        else:
            print(f"   ⚠️  No encontrado: {archivo}")
    
    return datos_geo


def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia haversine en metros entre dos puntos"""
    from math import radians, sin, cos, sqrt, atan2
    
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return np.nan
    
    R = 6371000  # Radio de la Tierra en metros
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def calcular_distancias_minimas(df: pd.DataFrame, datos_geo: Dict) -> pd.DataFrame:
    """Calcula distancias mínimas a puntos de interés para cada propiedad"""
    print("\n📏 Calculando distancias a puntos de interés...")
    
    # Inicializar columnas
    df['dist_metro'] = np.nan
    df['dist_colegio'] = np.nan
    df['dist_hospital'] = np.nan
    df['dist_area_verde'] = np.nan
    df['dist_supermercado'] = np.nan
    
    total = len(df)
    
    for idx, row in df.iterrows():
        if idx % 200 == 0:
            print(f"   Procesando {idx}/{total}...")
        
        lat_prop = row['latitude']
        lon_prop = row['longitude']
        
        if pd.isna(lat_prop) or pd.isna(lon_prop):
            continue
        
        # Distancia a metro
        if 'metro' in datos_geo:
            distancias_metro = []
            for feature in datos_geo['metro'][:100]:  # Limitar para velocidad
                geom = feature.get('geometry', {})
                if geom.get('type') == 'Point':
                    coords = geom.get('coordinates', [])
                    if len(coords) >= 2:
                        dist = calcular_distancia(lat_prop, lon_prop, coords[1], coords[0])
                        if not np.isnan(dist):
                            distancias_metro.append(dist)
            
            if distancias_metro:
                df.at[idx, 'dist_metro'] = min(distancias_metro)
        
        # Distancia a colegios
        if 'educacion' in datos_geo:
            distancias_educacion = []
            for feature in datos_geo['educacion'][:200]:
                geom = feature.get('geometry', {})
                if geom.get('type') == 'Point':
                    coords = geom.get('coordinates', [])
                    if len(coords) >= 2:
                        dist = calcular_distancia(lat_prop, lon_prop, coords[1], coords[0])
                        if not np.isnan(dist):
                            distancias_educacion.append(dist)
            
            if distancias_educacion:
                df.at[idx, 'dist_colegio'] = min(distancias_educacion)
        
        # Distancia a salud
        if 'salud' in datos_geo:
            distancias_salud = []
            for feature in datos_geo['salud'][:150]:
                geom = feature.get('geometry', {})
                if geom.get('type') == 'Point':
                    coords = geom.get('coordinates', [])
                    if len(coords) >= 2:
                        dist = calcular_distancia(lat_prop, lon_prop, coords[1], coords[0])
                        if not np.isnan(dist):
                            distancias_salud.append(dist)
            
            if distancias_salud:
                df.at[idx, 'dist_hospital'] = min(distancias_salud)
        
        # Distancia a áreas verdes
        if 'areas_verdes' in datos_geo:
            distancias_verdes = []
            for feature in datos_geo['areas_verdes'][:100]:
                geom = feature.get('geometry', {})
                if geom.get('type') in ['Point', 'Polygon']:
                    coords = geom.get('coordinates', [])
                    if geom.get('type') == 'Point' and len(coords) >= 2:
                        dist = calcular_distancia(lat_prop, lon_prop, coords[1], coords[0])
                        if not np.isnan(dist):
                            distancias_verdes.append(dist)
            
            if distancias_verdes:
                df.at[idx, 'dist_area_verde'] = min(distancias_verdes)
        
        # Distancia a comercio
        if 'comercio' in datos_geo:
            distancias_comercio = []
            for feature in datos_geo['comercio'][:150]:
                geom = feature.get('geometry', {})
                if geom.get('type') == 'Point':
                    coords = geom.get('coordinates', [])
                    if len(coords) >= 2:
                        dist = calcular_distancia(lat_prop, lon_prop, coords[1], coords[0])
                        if not np.isnan(dist):
                            distancias_comercio.append(dist)
            
            if distancias_comercio:
                df.at[idx, 'dist_supermercado'] = min(distancias_comercio)
    
    print(f"   ✅ Distancias calculadas para {total} propiedades")
    return df


def crear_comunas(db):
    """Crea comunas si no existen"""
    print("\n🏘️  Creando comunas...")
    result = db.execute(text("SELECT COUNT(*) FROM comunas")).scalar()
    if result > 0:
        print(f"   ℹ️  Ya existen {result} comunas")
        return
    
    # Crear diccionario invertido: {id: nombre}
    comunas_unicas = {}
    for nombre, comuna_id in COMUNAS_SANTIAGO.items():
        if isinstance(nombre, str) and comuna_id not in comunas_unicas:
            comunas_unicas[comuna_id] = nombre.title()
    
    for comuna_id, nombre in comunas_unicas.items():
        db.execute(text(
            "INSERT INTO comunas (id, nombre) VALUES (:id, :nombre)"
        ), {"id": comuna_id, "nombre": nombre})
    
    db.commit()
    print(f"   ✅ {len(comunas_unicas)} comunas creadas")


def main():
    print("=" * 70)
    print("🚀 CARGA DE PROPIEDADES DESDE CSV + DATOS GEOESPACIALES")
    print("=" * 70)
    
    # 1. Cargar CSV principal
    print(f"\n📂 Cargando CSV: {CSV_PATH.name}")
    if not CSV_PATH.exists():
        print(f"   ❌ Archivo no encontrado: {CSV_PATH}")
        return
    
    df = pd.read_csv(CSV_PATH)
    print(f"   ✅ Cargadas {len(df)} propiedades del CSV")
    
    # 2. Limpiar y preparar datos
    print("\n🧹 Limpiando datos...")
    df = df.drop_duplicates(subset=['latitude', 'longitude', 'precio', 'dormitorios'], keep='first')
    print(f"   ✅ Después de eliminar duplicados: {len(df)} propiedades")
    
    # 3. Cargar datos geoespaciales
    datos_geo = cargar_datos_geoespaciales()
    
    # 4. Calcular distancias
    if datos_geo:
        df = calcular_distancias_minimas(df, datos_geo)
    
    # 5. Conectar a DB
    print("\n🔌 Conectando a PostgreSQL Docker...")
    db = SessionLocal()
    
    try:
        db.execute(text("SELECT 1"))
        print("   ✅ Conexión exitosa")
        
        # 6. Crear comunas
        crear_comunas(db)
        
        # 7. Insertar propiedades (batch por batch para manejar errores)
        print("\n💾 Insertando propiedades...")
        insertadas = 0
        errores = 0
        errores_detalle = []
        
        BATCH_SIZE = 50
        batch_data = []
        
        for idx, row in df.iterrows():
            if idx % 200 == 0:
                print(f"   Procesando {idx}/{len(df)}...")
            
            try:
                comuna_id = obtener_comuna_id(row.get('comuna'))
                
                # Truncar valores largos
                direccion = str(row.get('direction', ''))[:200] if not pd.isna(row.get('direction')) else None
                titulo = str(row.get('titulo', ''))[:500] if not pd.isna(row.get('titulo')) else None
                url_original = str(row.get('link', ''))[:500] if not pd.isna(row.get('link')) else None
                tipo_depto = str(row.get('tipo_departamento', 'Departamento'))[:100]
                orientacion = str(row.get('orientacion', ''))[:50] if not pd.isna(row.get('orientacion')) else None
                
                # Preparar datos
                datos = {
                    "comuna_id": comuna_id,
                    "direccion": direccion,
                    "latitud": row.get('latitude') if not pd.isna(row.get('latitude')) else None,
                    "longitud": row.get('longitude') if not pd.isna(row.get('longitude')) else None,
                    "titulo": titulo,
                    "descripcion": None,
                    "superficie_total": row.get('superficie_total') if not pd.isna(row.get('superficie_total')) else None,
                    "superficie_util": row.get('superficie_util') if not pd.isna(row.get('superficie_util')) else None,
                    "superficie_terraza": row.get('superficie_terraza') if not pd.isna(row.get('superficie_terraza')) else None,
                    "dormitorios": int(row.get('dormitorios', 1)) if not pd.isna(row.get('dormitorios')) else 1,
                    "banos": int(row.get('banos', 1)) if not pd.isna(row.get('banos')) else 1,
                    "estacionamientos": row.get('estacionamientos') if not pd.isna(row.get('estacionamientos')) else None,
                    "tipo_departamento": tipo_depto,
                    "numero_piso_unidad": row.get('numero_piso_unidad') if not pd.isna(row.get('numero_piso_unidad')) else None,
                    "cantidad_pisos": row.get('cantidad_pisos') if not pd.isna(row.get('cantidad_pisos')) else None,
                    "departamentos_piso": row.get('departamentos_piso') if not pd.isna(row.get('departamentos_piso')) else None,
                    "gastos_comunes": row.get('gastos_comunes') if not pd.isna(row.get('gastos_comunes')) else None,
                    "orientacion": orientacion,
                    "dist_metro": row.get('dist_metro') if not pd.isna(row.get('dist_metro')) else None,
                    "dist_supermercado": row.get('dist_supermercado') if not pd.isna(row.get('dist_supermercado')) else None,
                    "dist_area_verde": row.get('dist_area_verde') if not pd.isna(row.get('dist_area_verde')) else None,
                    "dist_colegio": row.get('dist_colegio') if not pd.isna(row.get('dist_colegio')) else None,
                    "dist_hospital": row.get('dist_hospital') if not pd.isna(row.get('dist_hospital')) else None,
                    "precio": row.get('precio') if not pd.isna(row.get('precio')) else None,
                    "divisa": row.get('divisa', 'CLP'),
                    "fuente": "Portal Inmobiliario 2023",
                    "codigo": str(row.get('codigo'))[:100] if not pd.isna(row.get('codigo')) else None,
                    "url_original": url_original,
                    "fecha_publicacion": pd.to_datetime(row.get('fecha')) if not pd.isna(row.get('fecha')) else None,
                    "is_validated": True,
                    "created_at": datetime.now(),
                }
                
                batch_data.append(datos)
                
                # Cuando llegamos al tamaño de batch, insertamos
                if len(batch_data) >= BATCH_SIZE:
                    try:
                        for datos_prop in batch_data:
                            db.execute(text("""
                                INSERT INTO propiedades (
                                    comuna_id, direccion, latitud, longitud, titulo, descripcion,
                                    superficie_total, superficie_util, superficie_terraza,
                                    dormitorios, banos, estacionamientos,
                                    tipo_departamento, numero_piso_unidad, cantidad_pisos,
                                    departamentos_piso, gastos_comunes, orientacion,
                                    dist_metro, dist_supermercado, dist_area_verde, dist_colegio, dist_hospital,
                                    precio, divisa, fuente, codigo, url_original, fecha_publicacion,
                                    is_validated, created_at
                                ) VALUES (
                                    :comuna_id, :direccion, :latitud, :longitud, :titulo, :descripcion,
                                    :superficie_total, :superficie_util, :superficie_terraza,
                                    :dormitorios, :banos, :estacionamientos,
                                    :tipo_departamento, :numero_piso_unidad, :cantidad_pisos,
                                    :departamentos_piso, :gastos_comunes, :orientacion,
                                    :dist_metro, :dist_supermercado, :dist_area_verde, :dist_colegio, :dist_hospital,
                                    :precio, :divisa, :fuente, :codigo, :url_original, :fecha_publicacion,
                                    :is_validated, :created_at
                                )
                            """), datos_prop)
                        db.commit()
                        insertadas += len(batch_data)
                        batch_data = []
                    except Exception as e:
                        db.rollback()
                        # Intentar uno por uno
                        for datos_prop in batch_data:
                            try:
                                db2 = SessionLocal()
                                db2.execute(text("""
                                    INSERT INTO propiedades (
                                        comuna_id, direccion, latitud, longitud, titulo, descripcion,
                                        superficie_total, superficie_util, superficie_terraza,
                                        dormitorios, banos, estacionamientos,
                                        tipo_departamento, numero_piso_unidad, cantidad_pisos,
                                        departamentos_piso, gastos_comunes, orientacion,
                                        dist_metro, dist_supermercado, dist_area_verde, dist_colegio, dist_hospital,
                                        precio, divisa, fuente, codigo, url_original, fecha_publicacion,
                                        is_validated, created_at
                                    ) VALUES (
                                        :comuna_id, :direccion, :latitud, :longitud, :titulo, :descripcion,
                                        :superficie_total, :superficie_util, :superficie_terraza,
                                        :dormitorios, :banos, :estacionamientos,
                                        :tipo_departamento, :numero_piso_unidad, :cantidad_pisos,
                                        :departamentos_piso, :gastos_comunes, :orientacion,
                                        :dist_metro, :dist_supermercado, :dist_area_verde, :dist_colegio, :dist_hospital,
                                        :precio, :divisa, :fuente, :codigo, :url_original, :fecha_publicacion,
                                        :is_validated, :created_at
                                    )
                                """), datos_prop)
                                db2.commit()
                                db2.close()
                                insertadas += 1
                            except Exception as e2:
                                errores += 1
                                if errores <= 5:
                                    print(f"   ⚠️  Error: {str(e2)[:100]}")
                                db2.rollback()
                                db2.close()
                        batch_data = []
            
            except Exception as e:
                errores += 1
                if errores <= 5:
                    print(f"   ⚠️  Error fila {idx}: {str(e)[:100]}")
        
        # Insertar último batch
        if batch_data:
            try:
                for datos_prop in batch_data:
                    db.execute(text("""
                        INSERT INTO propiedades (
                            comuna_id, direccion, latitud, longitud, titulo, descripcion,
                            superficie_total, superficie_util, superficie_terraza,
                            dormitorios, banos, estacionamientos,
                            tipo_departamento, numero_piso_unidad, cantidad_pisos,
                            departamentos_piso, gastos_comunes, orientacion,
                            dist_metro, dist_supermercado, dist_area_verde, dist_colegio, dist_hospital,
                            precio, divisa, fuente, codigo, url_original, fecha_publicacion,
                            is_validated, created_at
                        ) VALUES (
                            :comuna_id, :direccion, :latitud, :longitud, :titulo, :descripcion,
                            :superficie_total, :superficie_util, :superficie_terraza,
                            :dormitorios, :banos, :estacionamientos,
                            :tipo_departamento, :numero_piso_unidad, :cantidad_pisos,
                            :departamentos_piso, :gastos_comunes, :orientacion,
                            :dist_metro, :dist_supermercado, :dist_area_verde, :dist_colegio, :dist_hospital,
                            :precio, :divisa, :fuente, :codigo, :url_original, :fecha_publicacion,
                            :is_validated, :created_at
                        )
                    """), datos_prop)
                db.commit()
                insertadas += len(batch_data)
            except Exception as e:
                db.rollback()
                for datos_prop in batch_data:
                    try:
                        db2 = SessionLocal()
                        db2.execute(text("""
                            INSERT INTO propiedades (
                                comuna_id, direccion, latitud, longitud, titulo, descripcion,
                                superficie_total, superficie_util, superficie_terraza,
                                dormitorios, banos, estacionamientos,
                                tipo_departamento, numero_piso_unidad, cantidad_pisos,
                                departamentos_piso, gastos_comunes, orientacion,
                                dist_metro, dist_supermercado, dist_area_verde, dist_colegio, dist_hospital,
                                precio, divisa, fuente, codigo, url_original, fecha_publicacion,
                                is_validated, created_at
                            ) VALUES (
                                :comuna_id, :direccion, :latitud, :longitud, :titulo, :descripcion,
                                :superficie_total, :superficie_util, :superficie_terraza,
                                :dormitorios, :banos, :estacionamientos,
                                :tipo_departamento, :numero_piso_unidad, :cantidad_pisos,
                                :departamentos_piso, :gastos_comunes, :orientacion,
                                :dist_metro, :dist_supermercado, :dist_area_verde, :dist_colegio, :dist_hospital,
                                :precio, :divisa, :fuente, :codigo, :url_original, :fecha_publicacion,
                                :is_validated, :created_at
                            )
                        """), datos_prop)
                        db2.commit()
                        db2.close()
                        insertadas += 1
                    except:
                        errores += 1
                        db2.rollback()
                        db2.close()
        
        # 8. Verificar
        total = db.execute(text("SELECT COUNT(*) FROM propiedades")).scalar()
        print(f"\n📊 Resultados:")
        print(f"   • Insertadas: {insertadas}")
        print(f"   • Errores: {errores}")
        print(f"   • Total en BD: {total}")
        
        # Estadísticas por comuna
        print("\n📍 Top 10 comunas:")
        top_comunas = db.execute(text("""
            SELECT c.nombre, COUNT(p.id) as total
            FROM comunas c
            JOIN propiedades p ON p.comuna_id = c.id
            GROUP BY c.nombre
            ORDER BY total DESC
            LIMIT 10
        """)).fetchall()
        
        for i, (comuna, total) in enumerate(top_comunas, 1):
            print(f"   {i:2d}. {comuna:25s}: {total:4d}")
        
        print("\n" + "=" * 70)
        print("✅ CARGA COMPLETADA")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
