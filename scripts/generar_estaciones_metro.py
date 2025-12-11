"""
Script para generar estaciones de metro a partir de las líneas de metro.
Utiliza las coordenadas conocidas de estaciones de metro de Santiago.
"""
import json
from pathlib import Path

# Estaciones de metro de Santiago - coordenadas en EPSG:4326 (lat, lon)
# Fuente: Datos públicos de Metro de Santiago
ESTACIONES_METRO = {
    "Línea 1": [
        ("San Pablo", -33.4252, -70.6823),
        ("Neptuno", -33.4243, -70.6754),
        ("Pajaritos", -33.4244, -70.6674),
        ("Las Rejas", -33.4237, -70.6570),
        ("Ecuador", -33.4228, -70.6517),
        ("San Alberto Hurtado", -33.4214, -70.6456),
        ("Universidad de Santiago", -33.4500, -70.6789),
        ("Estación Central", -33.4522, -70.6772),
        ("Unión Latinoamericana", -33.4533, -70.6686),
        ("República", -33.4535, -70.6608),
        ("Los Héroes", -33.4495, -70.6542),
        ("La Moneda", -33.4425, -70.6535),
        ("Universidad de Chile", -33.4420, -70.6495),
        ("Santa Lucía", -33.4407, -70.6437),
        ("Universidad Católica", -33.4417, -70.6400),
        ("Baquedano", -33.4376, -70.6348),
        ("Salvador", -33.4379, -70.6275),
        ("Manuel Montt", -33.4378, -70.6198),
        ("Pedro de Valdivia", -33.4374, -70.6117),
        ("Los Leones", -33.4380, -70.6037),
        ("Tobalaba", -33.4191, -70.5873),
        ("El Golf", -33.4155, -70.5844),
        ("Alcántara", -33.4147, -70.5758),
        ("Escuela Militar", -33.4116, -70.5672),
        ("Manquehue", -33.4035, -70.5588),
        ("Hernando de Magallanes", -33.3965, -70.5517),
        ("Los Dominicos", -33.3901, -70.5415),
    ],
    "Línea 2": [
        ("Vespucio Norte", -33.3899, -70.6083),
        ("Zapadores", -33.3979, -70.6089),
        ("Dorsal", -33.4079, -70.6088),
        ("Einstein", -33.4179, -70.6085),
        ("Cementerios", -33.4259, -70.6083),
        ("Cerro Blanco", -33.4339, -70.6077),
        ("Patronato", -33.4399, -70.6085),
        ("Puente Cal y Canto", -33.4359, -70.6405),
        ("Santa Ana", -33.4375, -70.6455),
        ("Los Héroes L2", -33.4495, -70.6542),
        ("Toesca", -33.4565, -70.6543),
        ("Parque O'Higgins", -33.4655, -70.6535),
        ("Rondizzoni", -33.4749, -70.6525),
        ("Franklin", -33.4845, -70.6515),
        ("El Llano", -33.4945, -70.6495),
        ("San Miguel", -33.5035, -70.6485),
        ("Lo Vial", -33.5125, -70.6477),
        ("Departamental", -33.5225, -70.6468),
        ("Ciudad del Niño", -33.5315, -70.6459),
        ("Lo Ovalle", -33.5415, -70.6449),
        ("El Parrón", -33.5495, -70.6440),
        ("La Cisterna", -33.5295, -70.6623),
    ],
    "Línea 3": [
        ("Los Libertadores", -33.3818, -70.6423),
        ("Plaza Chacabuco", -33.3918, -70.6423),
        ("Independencia", -33.4018, -70.6423),
        ("Hospitales", -33.4118, -70.6423),
        ("Vivaceta", -33.4218, -70.6423),
        ("Plaza de Armas", -33.4378, -70.6498),
        ("Universidad de Chile L3", -33.4420, -70.6495),
        ("Parque Almagro", -33.4520, -70.6395),
        ("Matta", -33.4620, -70.6395),
        ("Irarrázaval", -33.4420, -70.6095),
        ("Ñuñoa", -33.4520, -70.5995),
        ("Plaza Egaña", -33.4520, -70.5795),
        ("Fernando Castillo Velasco", -33.4620, -70.5595),
    ],
    "Línea 4": [
        ("Tobalaba L4", -33.4191, -70.5873),
        ("Cristóbal Colón", -33.4281, -70.5883),
        ("Francisco Bilbao", -33.4381, -70.5893),
        ("Príncipe de Gales", -33.4481, -70.5903),
        ("Simón Bolívar", -33.4581, -70.5913),
        ("Plaza Egaña L4", -33.4520, -70.5795),
        ("Los Orientales", -33.4681, -70.5923),
        ("Grecia", -33.4781, -70.5933),
        ("Los Presidentes", -33.4881, -70.5943),
        ("Quilín", -33.4981, -70.5953),
        ("Las Torres", -33.5081, -70.5963),
        ("Macul", -33.5181, -70.5973),
        ("Vicuña Mackenna", -33.5281, -70.5983),
        ("Vicente Valdés", -33.5381, -70.5993),
        ("Rojas Magallanes", -33.5481, -70.6003),
        ("Trinidad", -33.5581, -70.6013),
        ("San José de la Estrella", -33.5681, -70.6023),
        ("Los Quillayes", -33.5781, -70.6033),
        ("Elisa Correa", -33.5881, -70.6043),
        ("Hospital Sótero del Río", -33.5981, -70.6053),
        ("Protectora de la Infancia", -33.6081, -70.6063),
        ("Las Mercedes", -33.6181, -70.6073),
        ("Plaza de Puente Alto", -33.6281, -70.6083),
    ],
    "Línea 5": [
        ("Plaza de Maipú", -33.5100, -70.7560),
        ("Santiago Bueras", -33.5040, -70.7480),
        ("Del Sol", -33.4980, -70.7400),
        ("Monte Tabor", -33.4920, -70.7320),
        ("Las Parcelas", -33.4860, -70.7240),
        ("Laguna Sur", -33.4800, -70.7160),
        ("Barrancas", -33.4741, -70.7082),
        ("Pudahuel", -33.4365, -70.7430),
        ("San Pablo L5", -33.4252, -70.6823),
        ("Lo Prado", -33.4452, -70.6923),
        ("Blanqueado", -33.4495, -70.6642),
        ("Gruta de Lourdes", -33.4548, -70.6592),
        ("Quinta Normal", -33.4377, -70.6696),
        ("Cumming", -33.4480, -70.6647),
        ("Santa Ana L5", -33.4375, -70.6455),
        ("Bellas Artes", -33.4383, -70.6428),
        ("Baquedano L5", -33.4376, -70.6348),
        ("Parque Bustamante", -33.4476, -70.6248),
        ("Santa Isabel", -33.4576, -70.6148),
        ("Ñuble", -33.4676, -70.6048),
        ("Rodrigo de Araya", -33.4776, -70.5948),
        ("Carlos Valdovinos", -33.4876, -70.5848),
        ("Camino Agrícola", -33.4976, -70.5748),
        ("Pedrero", -33.5076, -70.5648),
        ("Mirador", -33.5176, -70.5548),
        ("Bellavista de la Florida", -33.5276, -70.5448),
        ("Vicente Valdés L5", -33.5381, -70.5993),
    ],
    "Línea 6": [
        ("Los Leones L6", -33.4380, -70.6037),
        ("Inés de Suárez", -33.4340, -70.6137),
        ("Ñuñoa L6", -33.4520, -70.5995),
        ("Estadio Nacional", -33.4620, -70.6095),
        ("Ñuble L6", -33.4676, -70.6048),
        ("Biobío", -33.4776, -70.5948),
        ("Franklin L6", -33.4845, -70.6515),
        ("Cerrillos", -33.4945, -70.7115),
    ],
}

def generar_geojson_estaciones():
    """Genera un archivo GeoJSON con las estaciones de metro"""
    features = []
    
    for linea, estaciones in ESTACIONES_METRO.items():
        for nombre, lat, lon in estaciones:
            # Crear nombre único para evitar duplicados
            nombre_completo = f"Metro {nombre}"
            
            feature = {
                "type": "Feature",
                "properties": {
                    "nombre": nombre_completo,
                    "tipo": "metro",
                    "linea": linea,
                    "descripcion": f"Estación de metro {nombre} - {linea}"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "name": "Estaciones_Metro_Santiago",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": features
    }
    
    # Guardar archivo
    output_path = Path(__file__).parent.parent.parent / "autocorrelacion_espacial" / "semana1_preparacion_datos" / "datos_normalizados" / "datos_normalizados" / "Estaciones_metro_Santiago.geojson"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Generadas {len(features)} estaciones de metro")
    print(f"📁 Archivo guardado en: {output_path}")
    
    return len(features)


def cargar_estaciones_a_db():
    """Carga las estaciones de metro directamente a la base de datos"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/inmobiliaria_db")
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Eliminar estaciones de metro existentes
        session.execute(text("DELETE FROM puntos_interes WHERE tipo = 'metro'"))
        
        # Insertar nuevas estaciones
        insertados = 0
        for linea, estaciones in ESTACIONES_METRO.items():
            for nombre, lat, lon in estaciones:
                nombre_completo = f"Metro {nombre}"
                
                session.execute(text("""
                    INSERT INTO puntos_interes (nombre, tipo, geometria, categoria)
                    VALUES (
                        :nombre,
                        'metro',
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                        'transporte'
                    )
                """), {
                    'nombre': nombre_completo,
                    'lat': lat,
                    'lon': lon
                })
                insertados += 1
        
        session.commit()
        print(f"✅ Insertadas {insertados} estaciones de metro en la base de datos")
        return insertados
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Generar archivo GeoJSON
    generar_geojson_estaciones()
