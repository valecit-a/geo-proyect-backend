"""
Script para cargar propiedades desde archivos GeoJSON a la base de datos PostgreSQL
Combina datos de Semana 1 y Semana 4, eliminando duplicados
"""
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import hashlib

# Agregar el directorio raíz al path para importar los modelos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.models import Base, Propiedad, Comuna
from app.database import engine, SessionLocal

# Rutas a los archivos GeoJSON
SEMANA1_PATH = Path(__file__).parent.parent.parent.parent / "autocorrelacion_espacial/semana1_preparacion_datos/datos_procesados/propiedades_kaggle_20251101_154100.geojson"
SEMANA4_PATH = Path(__file__).parent.parent.parent.parent / "autocorrelacion_espacial/semana4_recoleccion_datos/datos_procesados/propiedades_limpias_20251101_162821.geojson"

# Mapeo de comunas
COMUNAS_SANTIAGO = {
    'Cerrillos': 1,
    'Cerro Navia': 2,
    'Conchalí': 3,
    'El Bosque': 4,
    'Estación Central': 5,
    'Huechuraba': 6,
    'Independencia': 7,
    'La Cisterna': 8,
    'La Florida': 9,
    'La Granja': 10,
    'La Pintana': 11,
    'La Reina': 12,
    'Las Condes': 13,
    'Lo Barnechea': 14,
    'Lo Espejo': 15,
    'Lo Prado': 16,
    'Macul': 17,
    'Maipú': 18,
    'Ñuñoa': 19,
    'Pedro Aguirre Cerda': 20,
    'Peñalolén': 21,
    'Providencia': 22,
    'Pudahuel': 23,
    'Quilicura': 24,
    'Quinta Normal': 25,
    'Recoleta': 26,
    'Renca': 27,
    'San Joaquín': 28,
    'San Miguel': 29,
    'San Ramón': 30,
    'Santiago': 31,
    'Vitacura': 32,
}


def generar_hash_propiedad(prop: Dict[str, Any]) -> str:
    """
    Genera un hash único para una propiedad basado en características clave
    Para identificar duplicados incluso si vienen de distintas fuentes
    """
    # Usar características que identifican únicamente una propiedad
    props = prop.get('properties', {})
    
    # Crear string único con datos clave
    datos_clave = f"{props.get('latitud', 0):.6f}_{props.get('longitud', 0):.6f}_{props.get('precio', 0):.0f}_{props.get('dormitorios', 0)}_{props.get('banos', 0)}_{props.get('superficie_util', 0):.1f}"
    
    # Generar hash MD5
    return hashlib.md5(datos_clave.encode()).hexdigest()


def cargar_geojson(filepath: Path) -> List[Dict[str, Any]]:
    """Carga un archivo GeoJSON y retorna la lista de features"""
    print(f"\n📂 Cargando: {filepath.name}")
    
    if not filepath.exists():
        print(f"   ❌ Archivo no encontrado: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"   ✅ Cargadas {len(features)} propiedades")
    return features


def combinar_y_deduplicar(features_semana1: List[Dict], features_semana4: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Combina propiedades de ambas semanas y elimina duplicados
    Prioriza datos de Semana 4 (más limpios) sobre Semana 1
    """
    print("\n🔄 Combinando y eliminando duplicados...")
    
    propiedades_unicas = {}
    hashes_vistos: Set[str] = set()
    stats = {
        'semana1_originales': len(features_semana1),
        'semana4_originales': len(features_semana4),
        'duplicados': 0,
        'unicas': 0,
        'priorizadas_semana4': 0,
    }
    
    # Primero procesar Semana 4 (prioridad)
    for feature in features_semana4:
        hash_prop = generar_hash_propiedad(feature)
        if hash_prop not in hashes_vistos:
            propiedades_unicas[hash_prop] = {
                'feature': feature,
                'fuente': 'Semana 4 (limpia)'
            }
            hashes_vistos.add(hash_prop)
            stats['priorizadas_semana4'] += 1
    
    # Luego procesar Semana 1 (solo agregar las que no existen)
    for feature in features_semana1:
        hash_prop = generar_hash_propiedad(feature)
        if hash_prop not in hashes_vistos:
            propiedades_unicas[hash_prop] = {
                'feature': feature,
                'fuente': 'Semana 1 (Kaggle)'
            }
            hashes_vistos.add(hash_prop)
        else:
            stats['duplicados'] += 1
    
    stats['unicas'] = len(propiedades_unicas)
    
    print(f"\n📊 Estadísticas de deduplicación:")
    print(f"   • Semana 1 originales: {stats['semana1_originales']}")
    print(f"   • Semana 4 originales: {stats['semana4_originales']}")
    print(f"   • Total sin filtrar: {stats['semana1_originales'] + stats['semana4_originales']}")
    print(f"   • Duplicados encontrados: {stats['duplicados']}")
    print(f"   • 🎯 Propiedades únicas: {stats['unicas']}")
    print(f"   • Priorizadas de Semana 4: {stats['priorizadas_semana4']}")
    
    return list(propiedades_unicas.values()), stats


def crear_comunas(db):
    """Crea las comunas en la base de datos si no existen"""
    print("\n🏘️  Creando comunas...")
    
    comunas_existentes = db.query(Comuna).count()
    if comunas_existentes > 0:
        print(f"   ℹ️  Ya existen {comunas_existentes} comunas en la BD")
        return
    
    for nombre, comuna_id in COMUNAS_SANTIAGO.items():
        comuna = Comuna(
            id=comuna_id,
            nombre=nombre,
            region='Metropolitana de Santiago',
            provincia='Santiago'
        )
        db.add(comuna)
    
    db.commit()
    print(f"   ✅ Creadas {len(COMUNAS_SANTIAGO)} comunas")


def obtener_comuna_id(nombre_comuna: str) -> int:
    """Obtiene el ID de una comuna por su nombre"""
    # Limpiar nombre
    nombre_limpio = nombre_comuna.strip()
    
    # Buscar coincidencia exacta
    if nombre_limpio in COMUNAS_SANTIAGO:
        return COMUNAS_SANTIAGO[nombre_limpio]
    
    # Buscar coincidencia case-insensitive
    for nombre, id_comuna in COMUNAS_SANTIAGO.items():
        if nombre.lower() == nombre_limpio.lower():
            return id_comuna
    
    # Por defecto, Santiago
    print(f"   ⚠️  Comuna '{nombre_comuna}' no encontrada, usando Santiago")
    return COMUNAS_SANTIAGO['Santiago']


def insertar_propiedades(db, propiedades_con_fuente: List[Dict], stats: Dict):
    """Inserta las propiedades en la base de datos"""
    print("\n💾 Insertando propiedades en la base de datos...")
    
    insertadas = 0
    errores = 0
    comunas_sin_mapear = set()
    
    for i, item in enumerate(propiedades_con_fuente, 1):
        feature = item['feature']
        fuente = item['fuente']
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        try:
            # Obtener coordenadas
            coords = geometry.get('coordinates', [0, 0])
            longitud = coords[0] if len(coords) > 0 else None
            latitud = coords[1] if len(coords) > 1 else None
            
            # Obtener comuna_id
            nombre_comuna = props.get('comuna', 'Santiago')
            comuna_id = obtener_comuna_id(nombre_comuna)
            
            if nombre_comuna not in COMUNAS_SANTIAGO:
                comunas_sin_mapear.add(nombre_comuna)
            
            # Crear objeto Propiedad
            propiedad = Propiedad(
                comuna_id=comuna_id,
                direccion=props.get('direccion'),
                latitud=latitud,
                longitud=longitud,
                
                # Superficies
                superficie_total=props.get('superficie_total'),
                superficie_construida=props.get('superficie_construida'),
                superficie_util=props.get('superficie_util'),
                superficie_terraza=props.get('superficie_terraza'),
                
                # Características básicas
                dormitorios=props.get('dormitorios', 1),
                banos=props.get('banos', 1),
                estacionamientos=props.get('estacionamientos'),
                
                # Tipo de propiedad
                tipo_departamento=props.get('tipo_inmueble', 'Departamento'),
                
                # Edificio
                numero_piso_unidad=props.get('numero_piso_unidad'),
                cantidad_pisos=props.get('cantidad_pisos'),
                departamentos_piso=props.get('departamentos_piso'),
                gastos_comunes=props.get('gastos_comunes'),
                orientacion=props.get('orientacion'),
                
                # Distancias (educación)
                dist_educacion_basica_m=props.get('dist_educacion_basica_m'),
                dist_educacion_superior_m=props.get('dist_educacion_superior_m'),
                dist_educacion_parvularia_m=props.get('dist_educacion_parvularia_m'),
                dist_educacion_min_m=props.get('dist_educacion_min_m'),
                
                # Distancias (salud)
                dist_salud_m=props.get('dist_salud_m'),
                dist_salud_clinicas_m=props.get('dist_salud_clinicas_m'),
                dist_salud_min_m=props.get('dist_salud_min_m'),
                
                # Distancias (transporte)
                dist_transporte_metro_m=props.get('dist_transporte_metro_m'),
                dist_transporte_carga_m=props.get('dist_transporte_carga_m'),
                dist_transporte_min_m=props.get('dist_transporte_min_m'),
                
                # Distancias (seguridad)
                dist_seguridad_pdi_m=props.get('dist_seguridad_pdi_m'),
                dist_seguridad_cuarteles_m=props.get('dist_seguridad_cuarteles_m'),
                dist_seguridad_bomberos_m=props.get('dist_seguridad_bomberos_m'),
                dist_seguridad_min_m=props.get('dist_seguridad_min_m'),
                
                # Distancias (áreas verdes y servicios)
                dist_areas_verdes_m=props.get('dist_areas_verdes_m'),
                dist_comercio_m=props.get('dist_comercio_m'),
                dist_servicios_publicos_m=props.get('dist_servicios_publicos_m'),
                
                # Distancias simplificadas (compatibilidad)
                dist_metro=props.get('dist_transporte_metro_m'),
                dist_supermercado=props.get('dist_comercio_m'),
                dist_area_verde=props.get('dist_areas_verdes_m'),
                dist_colegio=props.get('dist_educacion_min_m'),
                dist_hospital=props.get('dist_salud_min_m'),
                
                # Precio
                precio=props.get('precio'),
                divisa=props.get('divisa', 'CLP'),
                
                # Metadata
                fuente=fuente,
                titulo=props.get('titulo'),
                descripcion=props.get('descripcion'),
                codigo=props.get('codigo'),
                url_original=props.get('url_original'),
                
                # Flags
                is_validated=True,
                created_at=datetime.now(),
            )
            
            db.add(propiedad)
            insertadas += 1
            
            # Commit cada 100 propiedades para evitar memory issues
            if insertadas % 100 == 0:
                db.commit()
                print(f"   ✅ Insertadas {insertadas}/{len(propiedades_con_fuente)} propiedades...")
        
        except Exception as e:
            errores += 1
            if errores <= 5:  # Solo mostrar primeros 5 errores
                print(f"   ⚠️  Error en propiedad {i}: {str(e)[:100]}")
    
    # Commit final
    db.commit()
    
    print(f"\n✅ Proceso completado:")
    print(f"   • Insertadas exitosamente: {insertadas}")
    print(f"   • Errores: {errores}")
    
    if comunas_sin_mapear:
        print(f"\n⚠️  Comunas sin mapeo (se asignaron a Santiago):")
        for comuna in sorted(comunas_sin_mapear):
            print(f"   • {comuna}")
    
    return insertadas, errores


def main():
    """Función principal"""
    print("=" * 70)
    print("🚀 CARGA DE PROPIEDADES A BASE DE DATOS DOCKER")
    print("=" * 70)
    
    # 1. Cargar archivos GeoJSON
    features_semana1 = cargar_geojson(SEMANA1_PATH)
    features_semana4 = cargar_geojson(SEMANA4_PATH)
    
    if not features_semana1 and not features_semana4:
        print("\n❌ No se encontraron archivos GeoJSON")
        return
    
    # 2. Combinar y eliminar duplicados
    propiedades_unicas, stats = combinar_y_deduplicar(features_semana1, features_semana4)
    
    # 3. Conectar a la base de datos
    print("\n🔌 Conectando a la base de datos...")
    db = SessionLocal()
    
    try:
        # Verificar conexión
        db.execute(text("SELECT 1"))
        print("   ✅ Conexión exitosa")
        
        # 4. Crear comunas
        crear_comunas(db)
        
        # 5. Insertar propiedades
        insertadas, errores = insertar_propiedades(db, propiedades_unicas, stats)
        
        # 6. Verificar resultados
        print("\n📊 Verificando resultados en la base de datos...")
        total_bd = db.query(Propiedad).count()
        print(f"   • Total propiedades en BD: {total_bd}")
        
        # Estadísticas por comuna
        print("\n📍 Propiedades por comuna (Top 10):")
        from sqlalchemy import func
        top_comunas = db.query(
            Comuna.nombre,
            func.count(Propiedad.id).label('total')
        ).join(Propiedad).group_by(Comuna.nombre).order_by(func.count(Propiedad.id).desc()).limit(10).all()
        
        for i, (comuna, total) in enumerate(top_comunas, 1):
            print(f"   {i:2d}. {comuna:25s}: {total:4d} propiedades")
        
        print("\n" + "=" * 70)
        print("✅ CARGA COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
