"""
Servicio de Recomendaciones con Machine Learning
Sistema avanzado de scoring con preferencias detalladas y modelo LightGBM de satisfacción
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Optional, Tuple
import math
from datetime import datetime
from loguru import logger

from app.models.models import Propiedad, Comuna, PuntoInteres
from app.schemas.schemas_ml import (
    PreferenciasDetalladas,
    PropiedadRecomendadaML,
    ScoreML,
    RecomendacionesResponseML,
    FeedbackPropiedad,
    HistorialBusqueda
)
from app.utils.currency import uf_to_clp, clp_to_uf, VALOR_UF_CLP

# Importar servicio de satisfacción
try:
    from app.services.satisfaccion_service import get_satisfaccion_service
    SATISFACCION_DISPONIBLE = True
except ImportError:
    SATISFACCION_DISPONIBLE = False
    logger.warning("⚠️ SatisfaccionService no disponible")


class RecommendationMLService:
    """Servicio avanzado de recomendaciones con Machine Learning y modelo LightGBM de satisfacción"""
    
    def __init__(self, db: Session):
        self.db = db
        self.comunas_map = self._cargar_comunas()
        self.modelo_version = "v3.0_LightGBM_Satisfaccion"
        
        # Inicializar servicio de satisfacción
        self.satisfaccion_service = None
        if SATISFACCION_DISPONIBLE:
            try:
                self.satisfaccion_service = get_satisfaccion_service()
                logger.info("✅ Modelo LightGBM de satisfacción integrado (R²=0.86)")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar modelo de satisfacción: {e}")
    
    def _normalizar_precio_a_clp(self, precio: float, divisa: str) -> float:
        """Normaliza cualquier precio a CLP
        
        Args:
            precio: Valor del precio
            divisa: 'pesos', 'CLP', 'UF', 'undefined', etc.
            
        Returns:
            Precio en CLP
        """
        if not precio:
            return 0.0
            
        divisa_lower = (divisa or 'pesos').lower()
        
        # Si ya está en pesos/CLP, retornar tal cual
        if divisa_lower in ['pesos', 'clp', 'peso']:
            return precio
        
        # Si es UF o undefined con valores pequeños (< 10000), asumir UF
        if divisa_lower in ['uf', 'undefined', 'none'] and precio < 10000:
            return uf_to_clp(precio)
        
        # Para valores grandes, asumir que ya están en CLP
        return precio
    
    def _cargar_comunas(self) -> Dict[int, str]:
        """Carga mapa de IDs a nombres de comunas"""
        comunas = self.db.query(Comuna).all()
        return {comuna.id: comuna.nombre for comuna in comunas}
    
    def _calcular_distancia_haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula la distancia en metros entre dos puntos usando la fórmula de Haversine"""
        R = 6371000  # Radio de la Tierra en metros
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _calcular_distancia_minima_poi(self, lat: float, lon: float, tipo_poi: str) -> Optional[float]:
        """
        Calcula la distancia mínima de un punto a los POIs de un tipo específico
        
        Args:
            lat: Latitud de la propiedad
            lon: Longitud de la propiedad
            tipo_poi: Tipo de POI ('metro', 'colegio', 'universidad', 'centro_medico', etc.)
            
        Returns:
            Distancia mínima en metros, o None si no hay POIs del tipo
        """
        try:
            # Para metro, buscar tanto por tipo como por nombre (estaciones de metro)
            if tipo_poi == 'metro':
                result = self.db.execute(text("""
                    SELECT MIN(
                        ST_Distance(
                            geometria::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                        )
                    ) as distancia_min
                    FROM puntos_interes
                    WHERE (tipo = 'metro' OR LOWER(nombre) LIKE 'metro %' OR LOWER(nombre) LIKE 'estación metro%')
                    AND geometria IS NOT NULL
                """), {'lat': lat, 'lon': lon}).fetchone()
            else:
                # Buscar POIs cercanos del tipo especificado usando PostGIS
                result = self.db.execute(text("""
                    SELECT MIN(
                        ST_Distance(
                            geometria::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                        )
                    ) as distancia_min
                    FROM puntos_interes
                    WHERE tipo = :tipo
                    AND geometria IS NOT NULL
                """), {'lat': lat, 'lon': lon, 'tipo': tipo_poi}).fetchone()
            
            if result and result[0] is not None:
                return float(result[0])
            return None
        except Exception as e:
            logger.debug(f"Error calculando distancia a {tipo_poi}: {e}")
            return None
    
    def _enriquecer_propiedad_con_distancias(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict[str, Optional[float]]:
        """
        Calcula las distancias de una propiedad a los POIs relevantes según las preferencias
        
        Args:
            prop: Propiedad a enriquecer
            pref: Preferencias del usuario
            
        Returns:
            Dict con distancias calculadas
        """
        distancias = {}
        
        if not prop.latitud or not prop.longitud:
            return distancias
        
        # Calcular distancia al metro si se pide transporte
        if pref.transporte and pref.transporte.importancia_metro != 0:
            distancias['metro'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'metro'
            )
        
        # Calcular distancia a colegios si se pide educación
        if pref.educacion and pref.educacion.importancia_colegios != 0:
            distancias['colegio'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'colegio'
            )
        
        # Calcular distancia a universidades si se pide
        if pref.educacion and pref.educacion.importancia_universidades != 0:
            distancias['universidad'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'universidad'
            )
        
        # Calcular distancia a centros médicos si se pide salud
        if pref.salud and pref.salud.importancia_hospitales != 0:
            distancias['centro_medico'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'centro_medico'
            )
        
        # Calcular distancia a farmacias si se pide
        if pref.salud and pref.salud.importancia_farmacias != 0:
            distancias['farmacia'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'farmacia'
            )
        
        # Calcular distancia a supermercados si se pide servicios
        if pref.servicios and pref.servicios.importancia_supermercados != 0:
            distancias['supermercado'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'supermercado'
            )
        
        # Calcular distancia a parques si se pide áreas verdes
        if pref.areas_verdes and pref.areas_verdes.importancia_parques != 0:
            distancias['parque'] = self._calcular_distancia_minima_poi(
                prop.latitud, prop.longitud, 'parque'
            )
        
        return distancias
    
    def recomendar_propiedades(
        self,
        preferencias: PreferenciasDetalladas,
        limit: int = 10
    ) -> RecomendacionesResponseML:
        """
        Recomienda propiedades usando sistema avanzado con ML
        
        Args:
            preferencias: Preferencias detalladas del usuario
            limit: Número máximo de recomendaciones
            
        Returns:
            RecomendacionesResponseML con recomendaciones y metadata
        """
        # 1. Filtrado (hard constraints)
        propiedades_candidatas = self._filtrar_propiedades(preferencias)
        total_analizadas = len(propiedades_candidatas)
        
        # Determinar si necesitamos calcular distancias (si hay preferencias de POI)
        necesita_distancias = (
            preferencias.transporte is not None or
            preferencias.educacion is not None or
            preferencias.salud is not None or
            preferencias.servicios is not None or
            preferencias.areas_verdes is not None
        )
        
        # 2. Scoring básico rápido (sin satisfacción ML)
        propiedades_con_score = []
        for propiedad in propiedades_candidatas:
            try:
                # Calcular distancias a POIs si es necesario
                distancias_calculadas = None
                if necesita_distancias:
                    distancias_calculadas = self._enriquecer_propiedad_con_distancias(propiedad, preferencias)
                
                resultado_ml = self._calcular_score_ml(propiedad, preferencias, distancias_calculadas)
                if resultado_ml['score_total'] > 0:  # Solo incluir con score positivo
                    propiedades_con_score.append(resultado_ml)
            except Exception as e:
                logger.debug(f"Error scoring propiedad {propiedad.id}: {e}")
                continue
        
        # 3. Ordenar por score descendente
        propiedades_con_score.sort(key=lambda x: x['score_total'], reverse=True)
        
        # 4. Tomar top N*2 (margen para re-ranking con satisfacción)
        candidatas_top = propiedades_con_score[:limit * 2]
        
        # 5. Calcular satisfacción ML solo para las top candidatas
        for resultado in candidatas_top:
            if self.satisfaccion_service:
                try:
                    satisfaccion_data = self._calcular_satisfaccion_ml(resultado['propiedad'])
                    if satisfaccion_data:
                        resultado['satisfaccion_score'] = satisfaccion_data['satisfaccion']
                        resultado['satisfaccion_nivel'] = satisfaccion_data['nivel']
                        
                        # Agregar contribución de satisfacción al score (30% del total)
                        score_sat_normalizado = (satisfaccion_data['satisfaccion'] / 10) * 100
                        peso_satisfaccion = 0.30
                        resultado['score_total'] += score_sat_normalizado * peso_satisfaccion
                        
                        # Agregar categoría de satisfacción
                        resultado['scores_categorias'].append(ScoreML(
                            categoria="Satisfacción ML",
                            score=score_sat_normalizado,
                            peso=peso_satisfaccion,
                            contribucion=score_sat_normalizado * peso_satisfaccion,
                            explicacion=f"LightGBM: {satisfaccion_data['satisfaccion']:.1f}/10 ({satisfaccion_data['nivel']})",
                            factores_positivos=[f"Predicción ML: {satisfaccion_data['nivel']}"],
                            factores_negativos=[]
                        ))
                        
                        # Agregar a puntos fuertes/débiles
                        if satisfaccion_data['satisfaccion'] >= 7:
                            resultado['puntos_fuertes'].insert(0, f"Satisfacción ML alta: {satisfaccion_data['satisfaccion']:.1f}/10")
                        elif satisfaccion_data['satisfaccion'] < 4:
                            resultado['puntos_debiles'].insert(0, f"Satisfacción ML baja: {satisfaccion_data['satisfaccion']:.1f}/10")
                except Exception as e:
                    logger.debug(f"Error satisfacción para {resultado['propiedad'].id}: {e}")
        
        # 6. Re-ordenar con satisfacción incluida
        candidatas_top.sort(key=lambda x: x['score_total'], reverse=True)
        
        # 7. Tomar top N final
        top_propiedades = candidatas_top[:limit]
        
        # 8. Convertir a schemas
        recomendaciones = []
        for resultado in top_propiedades:
            prop = resultado['propiedad']
            comuna_nombre = self.comunas_map.get(prop.comuna_id, 'Desconocida')
            
            # Normalizar precio a CLP
            precio_clp = self._normalizar_precio_a_clp(prop.precio, prop.divisa)
            
            recomendacion = PropiedadRecomendadaML(
                id=prop.id,
                direccion=prop.direccion or f"Propiedad {prop.id}",
                comuna=comuna_nombre,
                tipo_propiedad=prop.tipo_departamento or 'Casa',
                precio=precio_clp,
                divisa='CLP',
                superficie_util=prop.superficie_util or 0.0,
                dormitorios=prop.dormitorios or 0,
                banos=prop.banos or 0,
                estacionamientos=prop.estacionamientos or 0,
                latitud=prop.latitud or 0.0,
                longitud=prop.longitud or 0.0,
                # Características adicionales del edificio
                gastos_comunes=prop.gastos_comunes,
                orientacion=prop.orientacion,
                numero_piso=prop.numero_piso_unidad,
                cantidad_pisos=prop.cantidad_pisos,
                bodegas=int(prop.bodegas) if prop.bodegas else 0,
                # Scoring
                score_total=min(100.0, max(0.0, round(resultado['score_total'], 2))),
                score_confianza=min(1.0, max(0.0, round(resultado['confianza'], 3))),
                scores_por_categoria=resultado['scores_categorias'],
                satisfaccion_score=round(resultado.get('satisfaccion_score', 0), 2) if resultado.get('satisfaccion_score') else None,
                satisfaccion_nivel=resultado.get('satisfaccion_nivel'),
                resumen_explicacion=resultado['resumen'],
                puntos_fuertes=resultado['puntos_fuertes'],
                puntos_debiles=resultado['puntos_debiles'],
                distancias=resultado['distancias']
            )
            recomendaciones.append(recomendacion)
        
        # 6. Generar sugerencias
        sugerencias = self._generar_sugerencias(
            total_analizadas, 
            len(recomendaciones),
            preferencias
        )
        
        return RecomendacionesResponseML(
            total_encontradas=len(recomendaciones),
            total_analizadas=total_analizadas,
            recomendaciones=recomendaciones,
            preferencias_aplicadas=preferencias.dict(exclude_none=True),
            modelo_version=self.modelo_version,
            sugerencias=sugerencias
        )
    
    def _filtrar_propiedades(self, pref: PreferenciasDetalladas) -> List[Propiedad]:
        """Aplica hard constraints (filtros obligatorios)"""
        query = self.db.query(Propiedad)
        
        # Filtro básico: solo propiedades con coordenadas válidas
        query = query.filter(
            Propiedad.latitud.isnot(None),
            Propiedad.longitud.isnot(None)
        )
        
        # Filtros de precio
        if pref.precio_min:
            query = query.filter(Propiedad.precio >= pref.precio_min)
        if pref.precio_max:
            query = query.filter(Propiedad.precio <= pref.precio_max)
        
        # Filtros de superficie
        if pref.superficie_min:
            query = query.filter(Propiedad.superficie_util >= pref.superficie_min)
        if pref.superficie_max:
            query = query.filter(Propiedad.superficie_util <= pref.superficie_max)
        
        # Filtros de dormitorios
        if pref.dormitorios_min:
            query = query.filter(Propiedad.dormitorios >= pref.dormitorios_min)
        if pref.dormitorios_max:
            query = query.filter(Propiedad.dormitorios <= pref.dormitorios_max)
        
        # Filtros de baños
        if pref.banos_min:
            query = query.filter(Propiedad.banos >= pref.banos_min)
        
        # Filtros de estacionamientos
        if pref.estacionamientos_min:
            query = query.filter(Propiedad.estacionamientos >= pref.estacionamientos_min)
        
        # Filtros de comunas
        if pref.comunas_preferidas:
            comunas_ids = [cid for cid, nombre in self.comunas_map.items() 
                          if nombre in pref.comunas_preferidas]
            if comunas_ids:
                query = query.filter(Propiedad.comuna_id.in_(comunas_ids))
        
        # Excluir comunas no deseadas
        if pref.comunas_evitar:
            comunas_excluir_ids = [cid for cid, nombre in self.comunas_map.items() 
                                   if nombre in pref.comunas_evitar]
            if comunas_excluir_ids:
                query = query.filter(~Propiedad.comuna_id.in_(comunas_excluir_ids))
        
        # Filtro de tipo de inmueble (Casa/Departamento)
        if pref.tipo_inmueble_preferido:
            tipo_lower = pref.tipo_inmueble_preferido.lower()
            if tipo_lower == 'casa':
                # Filtrar solo casas
                query = query.filter(
                    Propiedad.tipo_departamento.ilike('%casa%')
                )
            elif tipo_lower in ['departamento', 'depto']:
                # Filtrar solo departamentos (todo lo que NO sea casa)
                query = query.filter(
                    ~Propiedad.tipo_departamento.ilike('%casa%')
                )
        
        # Obtener propiedades base
        propiedades_base = query.all()
        
        # ===== FILTROS ESPACIALES BASADOS EN PREFERENCIAS DE POI =====
        # Solo aplicar filtros espaciales si la importancia es alta (>= 7)
        propiedades_filtradas = propiedades_base
        
        # Filtro por cercanía al metro (si importancia >= 7)
        if pref.transporte and pref.transporte.importancia_metro >= 7:
            dist_max = pref.transporte.distancia_maxima_metro_m
            propiedades_filtradas = self._filtrar_por_cercania_poi(
                propiedades_filtradas, 'metro', dist_max
            )
            logger.info(f"🚇 Filtro metro (dist_max={dist_max}m): {len(propiedades_filtradas)} propiedades")
        
        # Filtro por cercanía a colegios (si importancia >= 7)
        if pref.educacion and pref.educacion.importancia_colegios >= 7:
            dist_max = pref.educacion.distancia_maxima_colegios_m
            propiedades_filtradas = self._filtrar_por_cercania_poi(
                propiedades_filtradas, 'colegio', dist_max
            )
            logger.info(f"🏫 Filtro colegios (dist_max={dist_max}m): {len(propiedades_filtradas)} propiedades")
        
        # Filtro por cercanía a centros médicos (si importancia >= 7)
        if pref.salud and pref.salud.importancia_hospitales >= 7:
            dist_max = pref.salud.distancia_maxima_hospitales_m
            propiedades_filtradas = self._filtrar_por_cercania_poi(
                propiedades_filtradas, 'centro_medico', dist_max
            )
            logger.info(f"🏥 Filtro centros médicos (dist_max={dist_max}m): {len(propiedades_filtradas)} propiedades")
        
        # Filtro por cercanía a supermercados (si importancia >= 7)
        if pref.servicios and pref.servicios.importancia_supermercados >= 7:
            dist_max = pref.servicios.distancia_maxima_supermercados_m
            propiedades_filtradas = self._filtrar_por_cercania_poi(
                propiedades_filtradas, 'supermercado', dist_max
            )
            logger.info(f"🛒 Filtro supermercados (dist_max={dist_max}m): {len(propiedades_filtradas)} propiedades")
        
        return propiedades_filtradas
    
    def _filtrar_por_cercania_poi(
        self, 
        propiedades: List[Propiedad], 
        tipo_poi: str, 
        dist_max_m: float
    ) -> List[Propiedad]:
        """
        Filtra propiedades que estén cerca de POIs de un tipo específico
        
        Args:
            propiedades: Lista de propiedades a filtrar
            tipo_poi: Tipo de POI ('metro', 'colegio', 'centro_medico', etc.)
            dist_max_m: Distancia máxima en metros
            
        Returns:
            Lista de propiedades filtradas
        """
        if not propiedades or dist_max_m >= 9999999:
            return propiedades
        
        # Obtener IDs de propiedades que cumplen el criterio usando PostGIS
        prop_ids = [p.id for p in propiedades]
        
        try:
            # Para metro, buscar también por nombre
            if tipo_poi == 'metro':
                result = self.db.execute(text("""
                    SELECT DISTINCT p.id
                    FROM propiedades p
                    WHERE p.id = ANY(:prop_ids)
                    AND p.geometria IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM puntos_interes poi
                        WHERE (poi.tipo = 'metro' OR LOWER(poi.nombre) LIKE 'metro %' OR LOWER(poi.nombre) LIKE 'estación metro%')
                        AND poi.geometria IS NOT NULL
                        AND ST_DWithin(
                            p.geometria::geography,
                            poi.geometria::geography,
                            :dist_max
                        )
                    )
                """), {
                    'prop_ids': prop_ids,
                    'dist_max': dist_max_m
                }).fetchall()
            else:
                result = self.db.execute(text("""
                    SELECT DISTINCT p.id
                    FROM propiedades p
                    WHERE p.id = ANY(:prop_ids)
                    AND p.geometria IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM puntos_interes poi
                        WHERE poi.tipo = :tipo_poi
                        AND poi.geometria IS NOT NULL
                        AND ST_DWithin(
                            p.geometria::geography,
                            poi.geometria::geography,
                            :dist_max
                        )
                    )
                """), {
                    'prop_ids': prop_ids,
                    'tipo_poi': tipo_poi,
                    'dist_max': dist_max_m
                }).fetchall()
            
            ids_filtrados = {row[0] for row in result}
            return [p for p in propiedades if p.id in ids_filtrados]
            
        except Exception as e:
            logger.warning(f"Error en filtro espacial para {tipo_poi}: {e}")
            return propiedades
    
    def _calcular_score_ml(
        self, 
        prop: Propiedad, 
        pref: PreferenciasDetalladas,
        distancias_calculadas: Optional[Dict[str, Optional[float]]] = None
    ) -> Dict:
        """
        Calcula score completo con ML y explicaciones detalladas
        
        Args:
            prop: Propiedad a evaluar
            pref: Preferencias del usuario
            distancias_calculadas: Distancias precalculadas a POIs (opcional)
        
        Returns:
            Dict con score_total, confianza, scores_categorias, resumen, etc.
        """
        scores_categorias = []
        puntos_fuertes = []
        puntos_debiles = []
        distancias = {}
        
        # Usar distancias calculadas si están disponibles
        dist_calc = distancias_calculadas or {}
        
        # Actualizar campos de distancia en la propiedad temporalmente
        if dist_calc.get('metro') is not None:
            prop.dist_transporte_metro_m = dist_calc['metro']
        if dist_calc.get('colegio') is not None:
            prop.dist_educacion_min_m = dist_calc['colegio']
        if dist_calc.get('centro_medico') is not None:
            prop.dist_salud_min_m = dist_calc['centro_medico']
        if dist_calc.get('farmacia') is not None:
            prop.dist_salud_m = dist_calc['farmacia']
        if dist_calc.get('supermercado') is not None:
            prop.dist_comercio_m = dist_calc['supermercado']
        if dist_calc.get('parque') is not None:
            prop.dist_areas_verdes_m = dist_calc['parque']
        
        # ===== 1. SCORE DE PRECIO =====
        score_precio_data = self._score_precio(prop, pref)
        scores_categorias.append(ScoreML(
            categoria="Precio",
            score=score_precio_data['score'],
            peso=pref.peso_precio,
            contribucion=score_precio_data['score'] * pref.peso_precio,
            explicacion=score_precio_data['explicacion'],
            factores_positivos=score_precio_data['positivos'],
            factores_negativos=score_precio_data['negativos']
        ))
        if score_precio_data['score'] >= 70:
            puntos_fuertes.append(f"Precio: {score_precio_data['explicacion']}")
        elif score_precio_data['score'] < 40:
            puntos_debiles.append(f"Precio: {score_precio_data['explicacion']}")
        
        # ===== 2. SCORE DE UBICACIÓN =====
        score_ubicacion_data = self._score_ubicacion(prop, pref)
        scores_categorias.append(ScoreML(
            categoria="Ubicación",
            score=score_ubicacion_data['score'],
            peso=pref.peso_ubicacion,
            contribucion=score_ubicacion_data['score'] * pref.peso_ubicacion,
            explicacion=score_ubicacion_data['explicacion'],
            factores_positivos=score_ubicacion_data['positivos'],
            factores_negativos=score_ubicacion_data['negativos']
        ))
        if score_ubicacion_data['score'] >= 70:
            puntos_fuertes.append(f"Ubicación: {score_ubicacion_data['explicacion']}")
        
        # ===== 3. SCORE DE TAMAÑO =====
        score_tamano_data = self._score_tamano(prop, pref)
        scores_categorias.append(ScoreML(
            categoria="Tamaño",
            score=score_tamano_data['score'],
            peso=pref.peso_tamano,
            contribucion=score_tamano_data['score'] * pref.peso_tamano,
            explicacion=score_tamano_data['explicacion'],
            factores_positivos=score_tamano_data['positivos'],
            factores_negativos=score_tamano_data['negativos']
        ))
        
        # ===== 4. SCORE DE TRANSPORTE =====
        if pref.transporte:
            score_transporte_data = self._score_transporte(prop, pref)
            scores_categorias.append(ScoreML(
                categoria="Transporte",
                score=score_transporte_data['score'],
                peso=pref.peso_transporte,
                contribucion=score_transporte_data['score'] * pref.peso_transporte,
                explicacion=score_transporte_data['explicacion'],
                factores_positivos=score_transporte_data['positivos'],
                factores_negativos=score_transporte_data['negativos']
            ))
            if prop.dist_transporte_metro_m:
                distancias['metro_m'] = round(prop.dist_transporte_metro_m, 1)
                if score_transporte_data['score'] >= 70:
                    puntos_fuertes.append(f"Metro a {int(prop.dist_transporte_metro_m)}m")
                elif score_transporte_data['score'] < 40:
                    puntos_debiles.append(f"Metro lejos ({int(prop.dist_transporte_metro_m)}m)")
        
        # ===== 5. SCORE DE EDUCACIÓN =====
        if pref.educacion:
            score_educacion_data = self._score_educacion(prop, pref)
            scores_categorias.append(ScoreML(
                categoria="Educación",
                score=score_educacion_data['score'],
                peso=pref.peso_educacion,
                contribucion=score_educacion_data['score'] * pref.peso_educacion,
                explicacion=score_educacion_data['explicacion'],
                factores_positivos=score_educacion_data['positivos'],
                factores_negativos=score_educacion_data['negativos']
            ))
            if prop.dist_educacion_min_m:
                distancias['colegio_m'] = round(prop.dist_educacion_min_m, 1)
                # Si el usuario EVITA colegios y están lejos, es POSITIVO
                if pref.educacion.importancia_colegios < 0:
                    if prop.dist_educacion_min_m > 500:
                        puntos_fuertes.append(f"Sin colegios cerca ({int(prop.dist_educacion_min_m)}m) - como preferiste")
                else:
                    if score_educacion_data['score'] >= 70:
                        puntos_fuertes.append(f"Colegio a {int(prop.dist_educacion_min_m)}m")
        
        # ===== 6. SCORE DE SALUD =====
        if pref.salud:
            score_salud_data = self._score_salud(prop, pref)
            scores_categorias.append(ScoreML(
                categoria="Salud",
                score=score_salud_data['score'],
                peso=pref.peso_salud,
                contribucion=score_salud_data['score'] * pref.peso_salud,
                explicacion=score_salud_data['explicacion'],
                factores_positivos=score_salud_data['positivos'],
                factores_negativos=score_salud_data['negativos']
            ))
            if prop.dist_salud_min_m:
                distancias['salud_m'] = round(prop.dist_salud_min_m, 1)
                if score_salud_data['score'] >= 70:
                    puntos_fuertes.append(f"Centro de salud a {int(prop.dist_salud_min_m)}m")
        
        # ===== 7. SCORE DE ÁREAS VERDES =====
        if pref.areas_verdes:
            score_verdes_data = self._score_areas_verdes(prop, pref)
            scores_categorias.append(ScoreML(
                categoria="Áreas Verdes",
                score=score_verdes_data['score'],
                peso=pref.peso_areas_verdes,
                contribucion=score_verdes_data['score'] * pref.peso_areas_verdes,
                explicacion=score_verdes_data['explicacion'],
                factores_positivos=score_verdes_data['positivos'],
                factores_negativos=score_verdes_data['negativos']
            ))
            if prop.dist_areas_verdes_m:
                distancias['parque_m'] = round(prop.dist_areas_verdes_m, 1)
                if score_verdes_data['score'] >= 70:
                    puntos_fuertes.append(f"Parque a {int(prop.dist_areas_verdes_m)}m")
        
        # ===== 8. SCORE DE EDIFICIO (NUEVO) =====
        if pref.edificio:
            score_edificio_data = self._score_edificio(prop, pref)
            scores_categorias.append(ScoreML(
                categoria="Edificio",
                score=score_edificio_data['score'],
                peso=pref.peso_edificio,
                contribucion=score_edificio_data['score'] * pref.peso_edificio,
                explicacion=score_edificio_data['explicacion'],
                factores_positivos=score_edificio_data['positivos'],
                factores_negativos=score_edificio_data['negativos']
            ))
            
            # Agregar puntos fuertes/débiles
            for punto in score_edificio_data['positivos'][:2]:  # Top 2
                puntos_fuertes.append(punto)
            for punto in score_edificio_data['negativos'][:2]:  # Top 2
                puntos_debiles.append(punto)
        
        # NOTA: Satisfacción ML se calcula en recomendar_propiedades() solo para top candidatas
        # Esto optimiza el rendimiento evitando calcular ML para todas las propiedades
        
        # ===== CALCULAR SCORE TOTAL (sin satisfacción, se agrega después) =====
        score_total = sum(sc.contribucion for sc in scores_categorias)
        
        # Calcular confianza (basado en disponibilidad de datos)
        campos_disponibles = 0
        campos_totales = 8  # Sin satisfacción ML en esta etapa
        if prop.precio: campos_disponibles += 1
        if prop.dist_transporte_metro_m: campos_disponibles += 1
        if prop.dist_educacion_min_m: campos_disponibles += 1
        if prop.dist_salud_min_m: campos_disponibles += 1
        if prop.dist_areas_verdes_m: campos_disponibles += 1
        if prop.gastos_comunes or prop.numero_piso_unidad or prop.orientacion: campos_disponibles += 1
        campos_disponibles += 2  # ubicación y tamaño siempre disponibles
        confianza = campos_disponibles / campos_totales
        
        # Limitar puntos fuertes y débiles a top 5
        puntos_fuertes = puntos_fuertes[:5]
        if not puntos_debiles:
            puntos_debiles = ["Sin debilidades significativas"]
        else:
            puntos_debiles = puntos_debiles[:5]
        
        # Generar resumen
        resumen = self._generar_resumen(score_total, puntos_fuertes, prop, pref)
        
        return {
            'propiedad': prop,
            'score_total': score_total,
            'satisfaccion_score': 0.0,  # Se calcula después en recomendar_propiedades()
            'satisfaccion_nivel': "N/A",  # Se calcula después en recomendar_propiedades()
            'confianza': confianza,
            'scores_categorias': scores_categorias,
            'resumen': resumen,
            'puntos_fuertes': puntos_fuertes,
            'puntos_debiles': puntos_debiles,
            'distancias': distancias
        }
    
    def _score_precio(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de precio (0-100)"""
        if not prop.precio or not pref.precio_max:
            return {'score': 50, 'explicacion': 'Sin datos', 'positivos': [], 'negativos': []}
        
        # Score basado en qué tan cerca del mínimo está
        rango = pref.precio_max - (pref.precio_min or 0)
        if rango == 0:
            score = 50
        else:
            # Mientras más cerca del mínimo, mejor score
            posicion = (prop.precio - (pref.precio_min or 0)) / rango
            score = max(0, 100 - (posicion * 100))
        
        precio_m2 = prop.precio / prop.superficie_util if prop.superficie_util else 0
        
        # Constante para conversión UF a CLP
        VALOR_UF_CLP = 37500
        precio_clp = int(prop.precio * VALOR_UF_CLP)
        precio_formateado = f"{int(prop.precio):,} UF (${precio_clp:,} CLP)"
        
        positivos = []
        negativos = []
        
        if score >= 80:
            explicacion = f"Excelente precio ({precio_formateado})"
            positivos.append(f"Precio muy competitivo: {precio_formateado}")
        elif score >= 60:
            explicacion = f"Buen precio ({precio_formateado})"
            positivos.append(f"Precio razonable: {precio_formateado}")
        elif score >= 40:
            explicacion = f"Precio moderado ({precio_formateado})"
        else:
            explicacion = f"Precio alto ({precio_formateado})"
            negativos.append(f"Precio alto para presupuesto: {precio_formateado}")
        
        if precio_m2 > 0:
            precio_m2_clp = int(precio_m2 * VALOR_UF_CLP)
            positivos.append(f"Precio/m²: {int(precio_m2):,} UF (${precio_m2_clp:,} CLP)")
        
        return {
            'score': score,
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _score_ubicacion(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de ubicación/comuna"""
        comuna_nombre = self.comunas_map.get(prop.comuna_id, '')
        
        if pref.comunas_preferidas and comuna_nombre in pref.comunas_preferidas:
            score = 100
            explicacion = f"Comuna preferida: {comuna_nombre}"
            positivos = [f"Ubicado en {comuna_nombre} (tu comuna preferida)"]
            negativos = []
        elif pref.comunas_evitar and comuna_nombre in pref.comunas_evitar:
            score = 0
            explicacion = f"Comuna evitada: {comuna_nombre}"
            positivos = []
            negativos = [f"En {comuna_nombre} (querías evitar)"]
        else:
            score = 50
            explicacion = f"Comuna: {comuna_nombre}"
            positivos = [f"Ubicado en {comuna_nombre}"]
            negativos = []
        
        return {
            'score': score,
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _score_tamano(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de tamaño"""
        score = 50  # Neutral por defecto
        positivos = []
        negativos = []
        
        if prop.superficie_util:
            explicacion = f"{prop.superficie_util}m²"
            
            # Score basado en rango deseado
            if pref.superficie_min and prop.superficie_util >= pref.superficie_min:
                score += 25
                positivos.append(f"Superficie: {prop.superficie_util}m²")
            
            if pref.superficie_max and prop.superficie_util <= pref.superficie_max:
                score += 25
        else:
            explicacion = "Sin datos de superficie"
        
        # Dormitorios
        if prop.dormitorios:
            if pref.dormitorios_min and prop.dormitorios >= pref.dormitorios_min:
                score += 10
            if pref.dormitorios_max and prop.dormitorios <= pref.dormitorios_max:
                score += 10
        
        # Baños
        if prop.banos and pref.banos_min and prop.banos >= pref.banos_min:
            score += 10
        
        # Estacionamientos
        if pref.estacionamientos_min and prop.estacionamientos >= pref.estacionamientos_min:
            score += 10
            positivos.append(f"{prop.estacionamientos} estacionamiento(s)")
        elif pref.estacionamientos_min and prop.estacionamientos < pref.estacionamientos_min:
            negativos.append(f"Solo {prop.estacionamientos} estacionamiento(s)")
        
        return {
            'score': min(100, score),
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _score_transporte(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de transporte (considera preferencias positivas Y negativas)"""
        if not pref.transporte:
            return {'score': 50, 'explicacion': 'Sin preferencias', 'positivos': [], 'negativos': []}
        
        importancia = pref.transporte.importancia_metro
        dist_actual = prop.dist_transporte_metro_m
        dist_max = pref.transporte.distancia_maxima_metro_m
        
        if not dist_actual:
            return {'score': 50, 'explicacion': 'Sin datos de metro', 'positivos': [], 'negativos': []}
        
        positivos = []
        negativos = []
        
        # Si importancia es POSITIVA: más cerca = mejor
        if importancia > 0:
            if dist_actual <= dist_max:
                score = 100 - (dist_actual / dist_max * 50)  # 50-100
                explicacion = f"Metro cercano ({int(dist_actual)}m)"
                positivos.append(f"Metro a {int(dist_actual)}m - excelente acceso")
            else:
                score = 50 - ((dist_actual - dist_max) / dist_max * 50)
                score = max(0, score)
                explicacion = f"Metro un poco lejos ({int(dist_actual)}m)"
                negativos.append(f"Metro a {int(dist_actual)}m - más lejos de lo deseado")
        
        # Si importancia es NEGATIVA: más lejos = mejor (usuario quiere EVITAR metro)
        elif importancia < 0:
            if dist_actual >= dist_max:
                score = 100  # Perfecto, está lejos como quiere
                explicacion = f"Lejos del metro ({int(dist_actual)}m) - como preferiste"
                positivos.append(f"Sin metro cerca ({int(dist_actual)}m) - tranquilidad")
            else:
                score = (dist_actual / dist_max) * 100  # Mientras más cerca, peor score
                explicacion = f"Metro cercano ({int(dist_actual)}m) - no deseado"
                negativos.append(f"Metro a {int(dist_actual)}m - preferías sin metro cerca")
        
        # Importancia neutra
        else:
            score = 50
            explicacion = f"Metro a {int(dist_actual)}m"
        
        # Ajustar score según magnitud de importancia (-10 a +10)
        factor_importancia = abs(importancia) / 10.0
        score = 50 + (score - 50) * factor_importancia
        
        return {
            'score': max(0, min(100, score)),
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _score_educacion(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de educación (puede ser positivo o negativo según preferencias)"""
        if not pref.educacion:
            return {'score': 50, 'explicacion': 'Sin preferencias', 'positivos': [], 'negativos': []}
        
        importancia = pref.educacion.importancia_colegios
        dist_actual = prop.dist_educacion_min_m
        dist_max = pref.educacion.distancia_maxima_colegios_m
        
        if not dist_actual:
            return {'score': 50, 'explicacion': 'Sin datos de colegios', 'positivos': [], 'negativos': []}
        
        positivos = []
        negativos = []
        
        # Si importancia es POSITIVA: más cerca = mejor
        if importancia > 0:
            if dist_actual <= dist_max:
                score = 100 - (dist_actual / dist_max * 50)
                explicacion = f"Colegio cercano ({int(dist_actual)}m)"
                positivos.append(f"Colegio a {int(dist_actual)}m")
            else:
                score = 50 - ((dist_actual - dist_max) / dist_max * 50)
                score = max(0, score)
                explicacion = f"Colegio lejos ({int(dist_actual)}m)"
                negativos.append(f"Colegio lejos ({int(dist_actual)}m)")
        
        # Si importancia es NEGATIVA: más lejos = mejor (evita ruido de colegios)
        elif importancia < 0:
            if dist_actual >= dist_max:
                score = 100
                explicacion = f"Sin colegios cerca ({int(dist_actual)}m) - como preferiste"
                positivos.append(f"Sin colegios en {int(dist_actual)}m - zona tranquila")
            else:
                score = (dist_actual / dist_max) * 100
                explicacion = f"Colegio cerca ({int(dist_actual)}m) - no deseado"
                negativos.append(f"Colegio cerca ({int(dist_actual)}m) - riesgo de ruido")
        else:
            score = 50
            explicacion = f"Colegio a {int(dist_actual)}m"
        
        # Ajustar según magnitud
        factor_importancia = abs(importancia) / 10.0
        score = 50 + (score - 50) * factor_importancia
        
        return {
            'score': max(0, min(100, score)),
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _score_salud(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de salud"""
        if not pref.salud:
            return {'score': 50, 'explicacion': 'Sin preferencias', 'positivos': [], 'negativos': []}
        
        importancia = pref.salud.importancia_consultorios
        dist_actual = prop.dist_salud_min_m
        dist_max = pref.salud.distancia_maxima_consultorios_m
        
        if not dist_actual:
            return {'score': 50, 'explicacion': 'Sin datos de salud', 'positivos': [], 'negativos': []}
        
        positivos = []
        negativos = []
        
        if importancia > 0:
            if dist_actual <= dist_max:
                score = 100 - (dist_actual / dist_max * 50)
                explicacion = f"Salud cercana ({int(dist_actual)}m)"
                positivos.append(f"Consultorio a {int(dist_actual)}m")
            else:
                score = 50 - ((dist_actual - dist_max) / dist_max * 50)
                score = max(0, score)
                explicacion = f"Salud lejos ({int(dist_actual)}m)"
                negativos.append(f"Salud lejos ({int(dist_actual)}m)")
        elif importancia < 0:
            if dist_actual >= dist_max:
                score = 100
                explicacion = f"Lejos de centros de salud ({int(dist_actual)}m)"
                positivos.append(f"Sin centros de salud cerca")
            else:
                score = (dist_actual / dist_max) * 100
                explicacion = f"Centro de salud cerca ({int(dist_actual)}m)"
                negativos.append(f"Centro de salud muy cerca")
        else:
            score = 50
            explicacion = f"Salud a {int(dist_actual)}m"
        
        factor_importancia = abs(importancia) / 10.0
        score = 50 + (score - 50) * factor_importancia
        
        return {
            'score': max(0, min(100, score)),
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _score_areas_verdes(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de áreas verdes"""
        if not pref.areas_verdes:
            return {'score': 50, 'explicacion': 'Sin preferencias', 'positivos': [], 'negativos': []}
        
        importancia = pref.areas_verdes.importancia_parques
        dist_actual = prop.dist_areas_verdes_m
        dist_max = pref.areas_verdes.distancia_maxima_parques_m
        
        if not dist_actual:
            return {'score': 50, 'explicacion': 'Sin datos de parques', 'positivos': [], 'negativos': []}
        
        positivos = []
        negativos = []
        
        if importancia > 0:
            if dist_actual <= dist_max:
                score = 100 - (dist_actual / dist_max * 50)
                explicacion = f"Parque cercano ({int(dist_actual)}m)"
                positivos.append(f"Parque a {int(dist_actual)}m")
            else:
                score = 50 - ((dist_actual - dist_max) / dist_max * 50)
                score = max(0, score)
                explicacion = f"Parque lejos ({int(dist_actual)}m)"
                negativos.append(f"Parque lejos ({int(dist_actual)}m)")
        elif importancia < 0:
            if dist_actual >= dist_max:
                score = 100
                explicacion = f"Lejos de parques ({int(dist_actual)}m)"
                positivos.append(f"Sin parques cerca")
            else:
                score = (dist_actual / dist_max) * 100
                explicacion = f"Parque cerca ({int(dist_actual)}m)"
        else:
            score = 50
            explicacion = f"Parque a {int(dist_actual)}m"
        
        factor_importancia = abs(importancia) / 10.0
        score = 50 + (score - 50) * factor_importancia
        
        return {
            'score': max(0, min(100, score)),
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _generar_resumen(
        self, 
        score: float, 
        puntos_fuertes: List[str],
        prop: Propiedad,
        pref: PreferenciasDetalladas
    ) -> str:
        """Genera resumen explicativo de la recomendación"""
        if score >= 80:
            nivel = "Excelente opción"
        elif score >= 60:
            nivel = "Buena opción"
        elif score >= 40:
            nivel = "Opción aceptable"
        else:
            nivel = "Opción con limitaciones"
        
        # Resaltar factores clave según preferencias
        factores_clave = []
        if pref.transporte and pref.transporte.importancia_metro > 7:
            factores_clave.append("transporte")
        if pref.educacion and abs(pref.educacion.importancia_colegios) > 7:
            if pref.educacion.importancia_colegios < 0:
                factores_clave.append("sin colegios cerca")
            else:
                factores_clave.append("con colegios")
        if pref.areas_verdes and pref.areas_verdes.importancia_parques > 7:
            factores_clave.append("áreas verdes")
        
        if factores_clave:
            resumen = f"{nivel} con {', '.join(factores_clave)}"
        else:
            resumen = nivel
        
        return resumen
    
    def _score_edificio(self, prop: Propiedad, pref: PreferenciasDetalladas) -> Dict:
        """Score de características del edificio (0-100)"""
        score = 50  # Neutral por defecto
        positivos = []
        negativos = []
        explicaciones = []
        
        pref_edif = pref.edificio
        
        # ===== 1. GASTOS COMUNES =====
        if prop.gastos_comunes and pref_edif.gastos_comunes_max:
            if prop.gastos_comunes <= pref_edif.gastos_comunes_max:
                bonus = 25 * (1 - prop.gastos_comunes / pref_edif.gastos_comunes_max)
                score += bonus
                positivos.append(f"Gastos comunes ${int(prop.gastos_comunes):,} (dentro de presupuesto)")
                explicaciones.append(f"Gastos comunes ${int(prop.gastos_comunes):,}")
            else:
                exceso = (prop.gastos_comunes - pref_edif.gastos_comunes_max) / pref_edif.gastos_comunes_max
                penalizacion = min(30, exceso * 50)
                score -= penalizacion
                negativos.append(f"Gastos comunes ${int(prop.gastos_comunes):,} (excede ${int(pref_edif.gastos_comunes_max):,})")
                explicaciones.append(f"Gastos exceden presupuesto en ${int(prop.gastos_comunes - pref_edif.gastos_comunes_max):,}")
        
        # ===== 2. PISO Y ALTURA =====
        if prop.numero_piso_unidad:
            # Aplicar filtros de rango
            if pref_edif.piso_minimo and prop.numero_piso_unidad < pref_edif.piso_minimo:
                score -= 20
                negativos.append(f"Piso {prop.numero_piso_unidad} (buscas piso {pref_edif.piso_minimo}+)")
            elif pref_edif.piso_maximo and prop.numero_piso_unidad > pref_edif.piso_maximo:
                score -= 20
                negativos.append(f"Piso {prop.numero_piso_unidad} (buscas hasta piso {pref_edif.piso_maximo})")
            else:
                # Scoring basado en preferencia alto/bajo
                if pref_edif.importancia_piso_alto > 0:
                    # Usuario prefiere pisos altos
                    score_piso = (prop.numero_piso_unidad / 20) * 25  # Max 25 puntos
                    score += score_piso * (pref_edif.importancia_piso_alto / 10)
                    if prop.numero_piso_unidad >= 10:
                        positivos.append(f"Piso {prop.numero_piso_unidad} (alto, como prefieres)")
                elif pref_edif.importancia_piso_alto < 0:
                    # Usuario prefiere pisos bajos
                    score_piso = max(0, 25 - (prop.numero_piso_unidad / 20) * 25)
                    score += score_piso * (abs(pref_edif.importancia_piso_alto) / 10)
                    if prop.numero_piso_unidad <= 3:
                        positivos.append(f"Piso {prop.numero_piso_unidad} (bajo, como prefieres)")
                
                explicaciones.append(f"Piso {prop.numero_piso_unidad}")
        
        # ===== 3. ORIENTACIÓN =====
        if prop.orientacion and pref_edif.orientaciones_preferidas:
            orientacion_match = any(
                pref_orient.lower() in prop.orientacion.lower() 
                for pref_orient in pref_edif.orientaciones_preferidas
            )
            
            if orientacion_match:
                score += 20 * (pref_edif.importancia_orientacion / 10)
                positivos.append(f"Orientación {prop.orientacion.title()} (preferida)")
                explicaciones.append(f"Orientación ideal: {prop.orientacion}")
            else:
                if pref_edif.importancia_orientacion > 5:
                    score -= 10
                    negativos.append(f"Orientación {prop.orientacion.title()} (prefieres {', '.join(pref_edif.orientaciones_preferidas)})")
        
        # ===== 4. TERRAZA =====
        if pref_edif.necesita_terraza:
            if prop.superficie_terraza and prop.superficie_terraza >= (pref_edif.terraza_minima_m2 or 0):
                score += 25
                positivos.append(f"Terraza {int(prop.superficie_terraza)}m² (indispensable)")
                explicaciones.append(f"Terraza de {int(prop.superficie_terraza)}m²")
            elif not prop.superficie_terraza or prop.superficie_terraza < (pref_edif.terraza_minima_m2 or 0):
                score -= 30  # Penalización FUERTE si es indispensable
                negativos.append(f"Sin terraza (indispensable para ti)")
        elif pref_edif.importancia_terraza > 0:
            if prop.superficie_terraza:
                bonus = min(15, (prop.superficie_terraza / 20) * 15)
                score += bonus * (pref_edif.importancia_terraza / 10)
                positivos.append(f"Terraza {int(prop.superficie_terraza)}m²")
        
        # ===== 5. TIPO DE DEPARTAMENTO =====
        if prop.tipo_departamento and pref_edif.tipo_preferido:
            if prop.tipo_departamento.lower() == pref_edif.tipo_preferido.lower():
                score += 10 * (pref_edif.importancia_tipo / 10)
                positivos.append(f"Departamento {prop.tipo_departamento} (como prefieres)")
        
        # ===== 6. PRIVACIDAD/DENSIDAD =====
        if prop.departamentos_piso and pref_edif.departamentos_por_piso_max:
            if prop.departamentos_piso <= pref_edif.departamentos_por_piso_max:
                score += 10
                if prop.departamentos_piso <= 2:
                    positivos.append(f"Solo {prop.departamentos_piso} deptos/piso (privado)")
            else:
                score -= 10
                negativos.append(f"{prop.departamentos_piso} deptos/piso (buscas max {pref_edif.departamentos_por_piso_max})")
        
        # Limitar score entre 0 y 100
        score = max(0, min(100, score))
        
        # Generar explicación
        if score >= 80:
            explicacion = "Excelentes características del edificio"
        elif score >= 60:
            explicacion = "Buenas características del edificio"
        elif score >= 40:
            explicacion = "Características aceptables del edificio"
        else:
            explicacion = "Características limitadas del edificio"
        
        if explicaciones:
            explicacion += f": {', '.join(explicaciones[:3])}"
        
        return {
            'score': score,
            'explicacion': explicacion,
            'positivos': positivos,
            'negativos': negativos
        }
    
    def _calcular_satisfaccion_ml(self, prop: Propiedad) -> Optional[Dict]:
        """
        Calcula la satisfacción predicha usando el modelo LightGBM (R²=0.86)
        
        Args:
            prop: Propiedad a evaluar
            
        Returns:
            Dict con satisfaccion (0-10), nivel, emoji, descripcion
            None si no se puede calcular
        """
        if not self.satisfaccion_service:
            return None
        
        # Obtener nombre de comuna
        comuna_nombre = self.comunas_map.get(prop.comuna_id, 'Santiago')
        
        # Determinar tipo de propiedad
        tipo_propiedad = 'departamento'
        if prop.tipo_departamento:
            tipo_lower = prop.tipo_departamento.lower()
            if 'casa' in tipo_lower:
                tipo_propiedad = 'casa'
        
        # Calcular precio en UF
        precio_clp = self._normalizar_precio_a_clp(prop.precio, prop.divisa)
        precio_uf = clp_to_uf(precio_clp) if precio_clp > 0 else 0
        
        # Preparar distancias disponibles
        distancias = {}
        if prop.dist_transporte_min_m:
            distancias['dist_transporte_min_m'] = prop.dist_transporte_min_m
        if prop.dist_transporte_metro_m:
            distancias['dist_transporte_metro_m'] = prop.dist_transporte_metro_m
        if prop.dist_educacion_min_m:
            distancias['dist_educacion_min_m'] = prop.dist_educacion_min_m
        if prop.dist_salud_min_m:
            distancias['dist_salud_min_m'] = prop.dist_salud_min_m
        if prop.dist_areas_verdes_m:
            distancias['dist_areas_verdes_m'] = prop.dist_areas_verdes_m
        if prop.dist_comercio_m:
            distancias['dist_comercio_m'] = prop.dist_comercio_m
        
        try:
            # Llamar al servicio de satisfacción
            resultado = self.satisfaccion_service.predecir_satisfaccion(
                superficie_util=prop.superficie_util or 50,
                dormitorios=prop.dormitorios or 1,
                banos=prop.banos or 1,
                precio_uf=precio_uf if precio_uf > 0 else 3000,
                comuna=comuna_nombre,
                tipo_propiedad=tipo_propiedad,
                latitud=prop.latitud,
                longitud=prop.longitud,
                distancias=distancias if distancias else None
            )
            
            return resultado
            
        except Exception as e:
            logger.debug(f"Error prediciendo satisfacción para prop {prop.id}: {e}")
            return None
    
    def _generar_sugerencias(
        self,
        total_analizadas: int,
        total_encontradas: int,
        pref: PreferenciasDetalladas
    ) -> List[str]:
        """Genera sugerencias para mejorar búsqueda"""
        sugerencias = []
        
        if total_encontradas == 0:
            sugerencias.append("No se encontraron propiedades con esos criterios. Intenta ampliar tu presupuesto o reducir requisitos.")
        elif total_encontradas < 5:
            sugerencias.append("Pocas opciones encontradas. Considera ampliar tu rango de precio o flexibilizar algunas preferencias.")
        
        if pref.precio_max and pref.precio_min:
            rango = pref.precio_max - pref.precio_min
            if rango < 50000:
                sugerencias.append("Tu rango de precio es muy estrecho. Ampliarlo en $20.000-30.000 podría darte más opciones.")
        
        if pref.comunas_preferidas and len(pref.comunas_preferidas) == 1:
            sugerencias.append("Estás buscando solo en 1 comuna. Agregar comunas vecinas podría darte más opciones.")
        
        return sugerencias if sugerencias else None
