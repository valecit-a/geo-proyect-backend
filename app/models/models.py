"""
Modelos de base de datos (ORM)
Tablas: propiedades, comunas
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.database import Base


class Comuna(Base):
    """Tabla de comunas de Santiago"""
    __tablename__ = "comunas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    codigo = Column(String(10), unique=True)
    geometria = Column(Geometry('POLYGON', srid=4326))
    
    # Estadísticas
    precio_promedio = Column(Float)
    precio_m2_promedio = Column(Float)
    total_propiedades = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    propiedades = relationship("Propiedad", back_populates="comuna")


class Propiedad(Base):
    """Tabla de propiedades inmobiliarias"""
    __tablename__ = "propiedades"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Ubicación
    comuna_id = Column(Integer, ForeignKey("comunas.id"), nullable=False)
    direccion = Column(String(200))
    latitud = Column(Float)
    longitud = Column(Float)
    geometria = Column(Geometry('POINT', srid=4326))
    
    # Características físicas
    superficie_total = Column(Float, nullable=False)  # m²
    superficie_construida = Column(Float)
    superficie_util = Column(Float)  # Superficie útil real
    superficie_terraza = Column(Float)
    dormitorios = Column(Integer, nullable=False)
    banos = Column(Integer, nullable=False)
    estacionamientos = Column(Float)
    ambientes = Column(Integer)
    bodegas = Column(Float)
    cant_max_habitantes = Column(Integer)
    
    # Características del edificio/departamento
    # Por defecto, si no se entrega `tipo_departamento`, asumimos 'Casa'
    # - `default` aplica en el lado de SQLAlchemy al crear el objeto
    # - `server_default` aplica en el lado del servidor (Postgres) para inserts directos
    tipo_departamento = Column(
        String(100),
        nullable=True,
        default='Casa',
        server_default=text("'Casa'")
    )  # 'interior', 'exterior', etc.
    numero_piso_unidad = Column(Integer)
    cantidad_pisos = Column(Integer)  # Pisos del edificio
    departamentos_piso = Column(Integer)
    gastos_comunes = Column(Float)
    orientacion = Column(String(50))
    
    # Características espaciales - Educación (distancias en metros)
    dist_educacion_basica_m = Column(Float)
    dist_educacion_superior_m = Column(Float)
    dist_educacion_parvularia_m = Column(Float)
    dist_educacion_min_m = Column(Float)  # Distancia mínima a cualquier educación
    
    # Características espaciales - Salud (metros)
    dist_salud_m = Column(Float)
    dist_salud_clinicas_m = Column(Float)
    dist_salud_min_m = Column(Float)
    
    # Características espaciales - Transporte (metros)
    dist_transporte_metro_m = Column(Float)
    dist_transporte_carga_m = Column(Float)
    dist_transporte_min_m = Column(Float)
    
    # Características espaciales - Seguridad (metros)
    dist_seguridad_pdi_m = Column(Float)
    dist_seguridad_cuarteles_m = Column(Float)
    dist_seguridad_bomberos_m = Column(Float)
    dist_seguridad_min_m = Column(Float)
    
    # Características espaciales - Amenidades (metros)
    dist_areas_verdes_m = Column(Float)
    dist_ocio_m = Column(Float)
    dist_turismo_m = Column(Float)
    dist_comercio_m = Column(Float)
    dist_servicios_publicos_m = Column(Float)
    dist_servicios_sernam_m = Column(Float)
    dist_puntos_interes_m = Column(Float)
    
    # Columnas legacy (para compatibilidad con modelo ML actual)
    dist_metro = Column(Float)  # dist_transporte_metro_m / 1000
    dist_supermercado = Column(Float)  # dist_comercio_m / 1000
    dist_area_verde = Column(Float)  # dist_areas_verdes_m / 1000
    dist_colegio = Column(Float)  # dist_educacion_min_m / 1000
    dist_hospital = Column(Float)  # dist_salud_min_m / 1000
    dist_mall = Column(Float)  # dist_turismo_m / 1000
    
    # Precio
    precio = Column(Float)  # Precio real (si existe)
    precio_log = Column(Float)  # log(precio) real
    precio_predicho = Column(Float)  # Predicción
    precio_predicho_log = Column(Float)  # log(predicción)
    divisa = Column(String(10), default='CLP')
    
    # Metadata
    fuente = Column(String(50))  # 'portalinmobiliario', 'yapo', 'manual', etc.
    url_original = Column(String(500))
    titulo = Column(String(500))
    descripcion = Column(Text)
    codigo = Column(String(100))  # Código del anuncio
    fecha_publicacion = Column(DateTime(timezone=True))
    
    # UTM coordinates
    x_utm = Column(Float)
    y_utm = Column(Float)
    zona_utm = Column(String(10))
    
    is_outlier = Column(Boolean, default=False)
    is_validated = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    comuna = relationship("Comuna", back_populates="propiedades")
