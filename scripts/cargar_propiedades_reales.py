#!/usr/bin/env python3
"""
Script para cargar las 931 propiedades reales desde el CSV a PostgreSQL
Mapea todas las 62 columnas del dataset a la tabla propiedades
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger
import math

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.models import Propiedad, Comuna
from app.database import get_db, engine
from app.config import settings

# Configurar logging
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


def cargar_dataset(csv_path: str) -> pd.DataFrame:
    """Carga el dataset de propiedades desde CSV"""
    logger.info(f"📂 Cargando dataset desde: {csv_path}")
    
    df = pd.read_csv(csv_path)
    logger.info(f"✅ Dataset cargado: {len(df)} propiedades, {len(df.columns)} columnas")
    
    return df


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y prepara los datos"""
    logger.info("🧹 Limpiando datos...")
    
    df_clean = df.copy()
    
    # Eliminar propiedades con precios anómalos
    df_clean = df_clean[df_clean['precio'] > 1000]  # Mínimo $1M CLP
    df_clean = df_clean[df_clean['precio'] < 5_000_000_000]  # Máximo $5B CLP
    
    # Eliminar propiedades con superficie anómala
    df_clean = df_clean[df_clean['superficie_util'] > 10]  # Mínimo 10m²
    df_clean = df_clean[df_clean['superficie_util'] < 500]  # Máximo 500m²
    
    # Filtrar solo comunas que existen en la BD
    comunas_validas = ['Santiago', 'Providencia', 'Las Condes', 'Las condes', 
                       'Ñuñoa', 'Vitacura', 'La Reina', 'La reina', 
                       'Lo Barnechea', 'Lo barnechea']
    df_clean = df_clean[df_clean['comuna'].isin(comunas_validas)]
    
    # Normalizar nombres de comunas
    df_clean['comuna'] = df_clean['comuna'].replace({
        'Las condes': 'Las Condes',
        'La reina': 'La Reina',
        'Lo barnechea': 'Lo Barnechea'
    })
    
    # Llenar valores NaN en campos numéricos
    campos_numericos = [
        'estacionamientos', 'bodegas', 'gastos_comunes', 'cant_max_habitantes',
        'numero_piso_unidad', 'cantidad_pisos', 'departamentos_piso'
    ]
    for campo in campos_numericos:
        if campo in df_clean.columns:
            df_clean[campo] = df_clean[campo].fillna(0)
    
    logger.info(f"✅ Datos limpios: {len(df_clean)} propiedades válidas")
    logger.info(f"   Comunas: {df_clean['comuna'].value_counts().to_dict()}")
    
    return df_clean


def obtener_comuna_id(session, nombre_comuna: str) -> int:
    """Obtiene el ID de una comuna por nombre"""
    comuna = session.query(Comuna).filter(Comuna.nombre == nombre_comuna).first()
    if not comuna:
        logger.warning(f"⚠️  Comuna no encontrada: {nombre_comuna}")
        return None
    return comuna.id


def mapear_propiedad(row: pd.Series, comuna_id: int) -> dict:
    """Mapea una fila del CSV a un diccionario de Propiedad"""
    
    # Convertir distancias de metros a kilómetros para campos legacy
    dist_metro_km = row.get('espacial_dist_transporte_metro_m', 0) / 1000 if pd.notna(row.get('espacial_dist_transporte_metro_m')) else None
    dist_colegio_km = row.get('espacial_dist_educacion_min_m', 0) / 1000 if pd.notna(row.get('espacial_dist_educacion_min_m')) else None
    dist_hospital_km = row.get('espacial_dist_salud_min_m', 0) / 1000 if pd.notna(row.get('espacial_dist_salud_min_m')) else None
    dist_verde_km = row.get('espacial_dist_areas_verdes_m', 0) / 1000 if pd.notna(row.get('espacial_dist_areas_verdes_m')) else None
    dist_comercio_km = row.get('espacial_dist_comercio_m', 0) / 1000 if pd.notna(row.get('espacial_dist_comercio_m')) else None
    dist_turismo_km = row.get('espacial_dist_turismo_m', 0) / 1000 if pd.notna(row.get('espacial_dist_turismo_m')) else None
    
    # Calcular log del precio
    precio_log = np.log(row['precio']) if row['precio'] > 0 else None
    
    # Parsear fecha de publicación
    fecha_pub = None
    if pd.notna(row.get('published_time')):
        try:
            fecha_pub = pd.to_datetime(row['published_time'])
        except:
            pass
    
    # Construir diccionario
    propiedad_data = {
        # Ubicación
        'comuna_id': comuna_id,
        'direccion': str(row.get('direction', ''))[:200],
        'latitud': float(row['latitude']) if pd.notna(row['latitude']) else None,
        'longitud': float(row['longitude']) if pd.notna(row['longitude']) else None,
        
        # Características físicas
        'superficie_total': float(row['superficie_total']),
        'superficie_construida': float(row['superficie_total']) if pd.notna(row['superficie_total']) else None,
        'superficie_util': float(row['superficie_util']),
        'superficie_terraza': float(row['superficie_terraza']) if pd.notna(row['superficie_terraza']) else 0,
        'dormitorios': int(row['dormitorios']),
        'banos': int(row['banos']),
        'estacionamientos': float(row['estacionamientos']) if pd.notna(row['estacionamientos']) else 0,
        'ambientes': int(row['ambientes']) if pd.notna(row['ambientes']) else 0,
        'bodegas': float(row['bodegas']) if pd.notna(row['bodegas']) else 0,
        'cant_max_habitantes': int(row['cant_max_habitantes']) if pd.notna(row['cant_max_habitantes']) else 0,
        
        # Características del edificio
        'tipo_departamento': str(row['tipo_departamento'])[:100] if pd.notna(row['tipo_departamento']) else None,
        'numero_piso_unidad': int(row['numero_piso_unidad']) if pd.notna(row['numero_piso_unidad']) and row['numero_piso_unidad'] > 0 else None,
        'cantidad_pisos': int(row['cantidad_pisos']) if pd.notna(row['cantidad_pisos']) and row['cantidad_pisos'] > 0 else None,
        'departamentos_piso': int(row['departamentos_piso']) if pd.notna(row['departamentos_piso']) and row['departamentos_piso'] > 0 else None,
        'gastos_comunes': float(row['gastos_comunes']) if pd.notna(row['gastos_comunes']) else 0,
        
        # Distancias espaciales - Educación (metros)
        'dist_educacion_basica_m': float(row['espacial_dist_educacion_basica_m']) if pd.notna(row['espacial_dist_educacion_basica_m']) else None,
        'dist_educacion_superior_m': float(row['espacial_dist_educacion_superior_m']) if pd.notna(row['espacial_dist_educacion_superior_m']) else None,
        'dist_educacion_parvularia_m': float(row['espacial_dist_educacion_parvularia_m']) if pd.notna(row['espacial_dist_educacion_parvularia_m']) else None,
        'dist_educacion_min_m': float(row['espacial_dist_educacion_min_m']) if pd.notna(row['espacial_dist_educacion_min_m']) else None,
        
        # Distancias - Salud
        'dist_salud_m': float(row['espacial_dist_salud_m']) if pd.notna(row['espacial_dist_salud_m']) else None,
        'dist_salud_clinicas_m': float(row['espacial_dist_salud_clinicas_m']) if pd.notna(row['espacial_dist_salud_clinicas_m']) else None,
        'dist_salud_min_m': float(row['espacial_dist_salud_min_m']) if pd.notna(row['espacial_dist_salud_min_m']) else None,
        
        # Distancias - Transporte
        'dist_transporte_metro_m': float(row['espacial_dist_transporte_metro_m']) if pd.notna(row['espacial_dist_transporte_metro_m']) else None,
        'dist_transporte_carga_m': float(row['espacial_dist_transporte_carga_m']) if pd.notna(row['espacial_dist_transporte_carga_m']) else None,
        'dist_transporte_min_m': float(row['espacial_dist_transporte_min_m']) if pd.notna(row['espacial_dist_transporte_min_m']) else None,
        
        # Distancias - Seguridad
        'dist_seguridad_pdi_m': float(row['espacial_dist_seguridad_pdi_m']) if pd.notna(row['espacial_dist_seguridad_pdi_m']) else None,
        'dist_seguridad_cuarteles_m': float(row['espacial_dist_seguridad_cuarteles_m']) if pd.notna(row['espacial_dist_seguridad_cuarteles_m']) else None,
        'dist_seguridad_bomberos_m': float(row['espacial_dist_seguridad_bomberos_m']) if pd.notna(row['espacial_dist_seguridad_bomberos_m']) else None,
        'dist_seguridad_min_m': float(row['espacial_dist_seguridad_min_m']) if pd.notna(row['espacial_dist_seguridad_min_m']) else None,
        
        # Distancias - Amenidades
        'dist_areas_verdes_m': float(row['espacial_dist_areas_verdes_m']) if pd.notna(row['espacial_dist_areas_verdes_m']) else None,
        'dist_ocio_m': float(row['espacial_dist_ocio_m']) if pd.notna(row['espacial_dist_ocio_m']) else None,
        'dist_turismo_m': float(row['espacial_dist_turismo_m']) if pd.notna(row['espacial_dist_turismo_m']) else None,
        'dist_comercio_m': float(row['espacial_dist_comercio_m']) if pd.notna(row['espacial_dist_comercio_m']) else None,
        'dist_servicios_publicos_m': float(row['espacial_dist_servicios_publicos_m']) if pd.notna(row['espacial_dist_servicios_publicos_m']) else None,
        'dist_servicios_sernam_m': float(row['espacial_dist_servicios_sernam_m']) if pd.notna(row['espacial_dist_servicios_sernam_m']) else None,
        'dist_puntos_interes_m': float(row['espacial_dist_puntos_interes_m']) if pd.notna(row['espacial_dist_puntos_interes_m']) else None,
        
        # Distancias legacy (km)
        'dist_metro': dist_metro_km,
        'dist_colegio': dist_colegio_km,
        'dist_hospital': dist_hospital_km,
        'dist_area_verde': dist_verde_km,
        'dist_supermercado': dist_comercio_km,
        'dist_mall': dist_turismo_km,
        
        # Precio
        'precio': float(row['precio']),
        'precio_log': precio_log,
        'divisa': str(row.get('divisa', 'CLP')),
        
        # Metadata
        'fuente': 'portalinmobiliario',
        'url_original': str(row.get('link', ''))[:500],
        'titulo': str(row.get('titulo', ''))[:500] if pd.notna(row.get('titulo')) else None,
        'codigo': str(row.get('codigo', ''))[:100] if pd.notna(row.get('codigo')) else None,
        'fecha_publicacion': fecha_pub,
        
        # UTM
        'x_utm': float(row['espacial_x_utm']) if pd.notna(row['espacial_x_utm']) else None,
        'y_utm': float(row['espacial_y_utm']) if pd.notna(row['espacial_y_utm']) else None,
        'zona_utm': str(row['espacial_zona_utm']) if pd.notna(row['espacial_zona_utm']) else None,
        
        'is_validated': True
    }
    
    return propiedad_data


def cargar_propiedades_a_bd(df: pd.DataFrame):
    """Carga todas las propiedades a la base de datos"""
    logger.info("💾 Iniciando carga a base de datos...")
    
    # Crear sesión
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Limpiar tabla existente (opcional)
        logger.warning("⚠️  ¿Desea limpiar la tabla propiedades existente? (se perderán datos)")
        respuesta = input("Escriba 'SI' para confirmar: ")
        if respuesta == 'SI':
            logger.info("🗑️  Eliminando propiedades existentes...")
            session.query(Propiedad).delete()
            session.commit()
            logger.info("✅ Tabla limpiada")
        
        # Cargar propiedades
        total = len(df)
        exitosos = 0
        errores = 0
        
        logger.info(f"📤 Cargando {total} propiedades...")
        
        for idx, row in df.iterrows():
            try:
                # Obtener comuna_id
                comuna_id = obtener_comuna_id(session, row['comuna'])
                if not comuna_id:
                    logger.warning(f"⚠️  Propiedad {idx + 1}: Comuna '{row['comuna']}' no encontrada, saltando...")
                    errores += 1
                    continue
                
                # Mapear propiedad
                propiedad_data = mapear_propiedad(row, comuna_id)
                
                # Crear objeto Propiedad
                propiedad = Propiedad(**propiedad_data)
                
                # Agregar a sesión
                session.add(propiedad)
                exitosos += 1
                
                # Commit cada 50 propiedades
                if exitosos % 50 == 0:
                    session.commit()
                    logger.info(f"   Progreso: {exitosos}/{total} propiedades cargadas")
                
            except Exception as e:
                logger.error(f"❌ Error en propiedad {idx + 1}: {str(e)}")
                errores += 1
                session.rollback()
        
        # Commit final
        session.commit()
        
        logger.info("=" * 70)
        logger.info("📊 RESUMEN DE CARGA:")
        logger.info("=" * 70)
        logger.info(f"✅ Exitosas: {exitosos}")
        logger.info(f"❌ Errores: {errores}")
        logger.info(f"📈 Total procesadas: {total}")
        logger.info(f"🎯 Tasa de éxito: {(exitosos/total)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        session.rollback()
        raise
    
    finally:
        session.close()


def verificar_carga():
    """Verifica que las propiedades se cargaron correctamente"""
    logger.info("\n🔍 Verificando carga...")
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        total = session.query(Propiedad).count()
        logger.info(f"✅ Total propiedades en BD: {total}")
        
        # Propiedades por comuna
        logger.info("\n📍 Propiedades por comuna:")
        comunas = session.query(Comuna).all()
        for comuna in comunas:
            count = session.query(Propiedad).filter(Propiedad.comuna_id == comuna.id).count()
            logger.info(f"   {comuna.nombre}: {count} propiedades")
        
        # Estadísticas
        from sqlalchemy import func
        stats = session.query(
            func.min(Propiedad.precio).label('min_precio'),
            func.max(Propiedad.precio).label('max_precio'),
            func.avg(Propiedad.precio).label('avg_precio'),
            func.min(Propiedad.superficie_util).label('min_superficie'),
            func.max(Propiedad.superficie_util).label('max_superficie'),
            func.avg(Propiedad.superficie_util).label('avg_superficie')
        ).first()
        
        logger.info("\n💰 Estadísticas de precio:")
        logger.info(f"   Min: ${stats.min_precio:,.0f} CLP")
        logger.info(f"   Max: ${stats.max_precio:,.0f} CLP")
        logger.info(f"   Promedio: ${stats.avg_precio:,.0f} CLP")
        
        logger.info("\n🏠 Estadísticas de superficie:")
        logger.info(f"   Min: {stats.min_superficie:.1f} m²")
        logger.info(f"   Max: {stats.max_superficie:.1f} m²")
        logger.info(f"   Promedio: {stats.avg_superficie:.1f} m²")
        
        # Muestra de 3 propiedades
        logger.info("\n🔎 Muestra de 3 propiedades:")
        propiedades = session.query(Propiedad).limit(3).all()
        for prop in propiedades:
            logger.info(f"\n   ID: {prop.id}")
            logger.info(f"   Título: {prop.titulo}")
            logger.info(f"   Comuna: {prop.comuna.nombre}")
            logger.info(f"   Precio: ${prop.precio:,.0f}")
            logger.info(f"   Superficie: {prop.superficie_util}m²")
            logger.info(f"   {prop.dormitorios}D/{prop.banos}B")
            logger.info(f"   Dist metro: {prop.dist_metro:.2f} km" if prop.dist_metro else "   Sin info metro")
        
    finally:
        session.close()


def main():
    """Función principal"""
    logger.info("=" * 70)
    logger.info("🚀 CARGA DE PROPIEDADES REALES A BASE DE DATOS")
    logger.info("=" * 70)
    
    # Ruta al CSV
    csv_path = Path(__file__).parent.parent.parent / "datos_procesados" / "propiedades_kaggle_20251101_154100.csv"
    
    if not csv_path.exists():
        logger.error(f"❌ Archivo no encontrado: {csv_path}")
        return
    
    try:
        # 1. Cargar dataset
        df = cargar_dataset(str(csv_path))
        
        # 2. Limpiar datos
        df_clean = limpiar_datos(df)
        
        # 3. Cargar a BD
        cargar_propiedades_a_bd(df_clean)
        
        # 4. Verificar
        verificar_carga()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ PROCESO COMPLETADO EXITOSAMENTE")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Error fatal en el proceso: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
