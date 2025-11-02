"""
Servicio de Recomendaciones de Propiedades
Sistema de scoring multi-criterio basado en preferencias del usuario
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Optional, Tuple
import math

from app.models.models import Propiedad, Comuna
from app.schemas.schemas import PreferenciasUsuario, PropiedadRecomendada, ScoreDetallado


class RecommendationService:
    """Servicio para recomendar propiedades basado en preferencias"""
    
    def __init__(self, db: Session):
        self.db = db
        self.comunas_map = self._cargar_comunas()
    
    def _cargar_comunas(self) -> Dict[int, str]:
        """Carga mapa de IDs a nombres de comunas"""
        comunas = self.db.query(Comuna).all()
        return {comuna.id: comuna.nombre for comuna in comunas}
    
    def recomendar_propiedades(
        self, 
        preferencias: PreferenciasUsuario, 
        limit: int = 10
    ) -> Tuple[List[PropiedadRecomendada], int]:
        """
        Recomienda propiedades basadas en preferencias del usuario
        
        Returns:
            Tuple[List[PropiedadRecomendada], int]: (recomendaciones, total_analizadas)
        """
        # 1. Filtrado (hard constraints)
        propiedades_candidatas = self._filtrar_propiedades(preferencias)
        total_analizadas = len(propiedades_candidatas)
        
        # 2. Scoring de cada propiedad
        propiedades_con_score = []
        for propiedad in propiedades_candidatas:
            score_resultado = self._calcular_score(propiedad, preferencias)
            if score_resultado['score_total'] > 0:  # Solo incluir con score positivo
                propiedades_con_score.append(score_resultado)
        
        # 3. Ordenar por score descendente
        propiedades_con_score.sort(key=lambda x: x['score_total'], reverse=True)
        
        # 4. Tomar top N
        top_propiedades = propiedades_con_score[:limit]
        
        # 5. Convertir a schemas
        recomendaciones = []
        for item in top_propiedades:
            prop = item['propiedad']
            comuna_nombre = self.comunas_map.get(prop.comuna_id, 'Desconocida')
            
            recomendacion = PropiedadRecomendada(
                id=prop.id,
                direccion=prop.direccion,
                comuna=comuna_nombre,
                precio=prop.precio,
                superficie_util=prop.superficie_util,
                dormitorios=prop.dormitorios,
                banos=prop.banos,
                estacionamientos=prop.estacionamientos,
                latitud=prop.latitud,
                longitud=prop.longitud,
                score_total=round(item['score_total'], 2),
                scores_detallados=item['scores_detallados'],
                explicacion=item['explicacion'],
                dist_metro_m=prop.dist_transporte_metro_m,
                dist_educacion_min_m=prop.dist_educacion_min_m,
                dist_salud_min_m=prop.dist_salud_min_m,
                dist_areas_verdes_m=prop.dist_areas_verdes_m
            )
            recomendaciones.append(recomendacion)
        
        return recomendaciones, total_analizadas
    
    def _filtrar_propiedades(self, preferencias: PreferenciasUsuario) -> List[Propiedad]:
        """Filtra propiedades según hard constraints"""
        query = self.db.query(Propiedad)
        
        # Filtro de precio
        if preferencias.precio_min:
            query = query.filter(Propiedad.precio >= preferencias.precio_min)
        if preferencias.precio_max:
            query = query.filter(Propiedad.precio <= preferencias.precio_max)
        
        # Filtro de superficie
        if preferencias.superficie_min:
            query = query.filter(Propiedad.superficie_util >= preferencias.superficie_min)
        if preferencias.superficie_max:
            query = query.filter(Propiedad.superficie_util <= preferencias.superficie_max)
        
        # Filtro de dormitorios
        if preferencias.dormitorios_min:
            query = query.filter(Propiedad.dormitorios >= preferencias.dormitorios_min)
        if preferencias.dormitorios_max:
            query = query.filter(Propiedad.dormitorios <= preferencias.dormitorios_max)
        
        # Filtro de baños
        if preferencias.banos_min:
            query = query.filter(Propiedad.banos >= preferencias.banos_min)
        
        # Filtro de comunas
        if preferencias.comunas_preferidas:
            comuna_ids = [
                comuna_id for comuna_id, nombre in self.comunas_map.items() 
                if nombre in preferencias.comunas_preferidas
            ]
            if comuna_ids:
                query = query.filter(Propiedad.comuna_id.in_(comuna_ids))
        
        # NUEVO: Filtro de tipo de inmueble (Casa / Departamento)
        if preferencias.tipo_inmueble_preferido:
            # Si usuario especifica Casa o Departamento, filtrar por tipo_departamento
            # (nota: tipo_departamento puede contener 'Casa', 'Departamento', 'interior', 'exterior', etc.)
            tipo = preferencias.tipo_inmueble_preferido.lower()
            if tipo in ['casa', 'departamento', 'bungalow']:
                query = query.filter(
                    Propiedad.tipo_departamento.ilike(f'%{preferencias.tipo_inmueble_preferido}%')
                )
        
        # Filtro de estacionamiento
        if preferencias.requiere_estacionamiento:
            query = query.filter(Propiedad.estacionamientos >= 1)
        
        # Filtro de piso
        if preferencias.piso_maximo:
            query = query.filter(
                or_(
                    Propiedad.numero_piso_unidad == None,
                    Propiedad.numero_piso_unidad <= preferencias.piso_maximo
                )
            )
        
        return query.all()
    
    def _calcular_score(
        self, 
        propiedad: Propiedad, 
        preferencias: PreferenciasUsuario
    ) -> Dict:
        """
        Calcula score multi-criterio de una propiedad
        
        Distribución de puntos:
        - Precio: 0-20 pts (ponderado por prioridad)
        - Ubicación: 0-20 pts (ponderado por prioridad)
        - Tamaño: 0-15 pts (ponderado por prioridad)
        - Transporte: 0-15 pts (ponderado por prioridad)
        - Educación: 0-10 pts (ponderado por prioridad)
        - Salud: 0-10 pts (ponderado por prioridad)
        - Áreas Verdes: 0-10 pts (ponderado por prioridad)
        
        Total: 0-100 pts
        """
        scores = {}
        explicaciones = []
        
        # 1. Score de PRECIO (0-20)
        score_precio = self._score_precio(propiedad, preferencias)
        scores['precio'] = score_precio['puntos']
        if score_precio['explicacion']:
            explicaciones.append(score_precio['explicacion'])
        
        # 2. Score de UBICACIÓN (0-20)
        score_ubicacion = self._score_ubicacion(propiedad, preferencias)
        scores['ubicacion'] = score_ubicacion['puntos']
        if score_ubicacion['explicacion']:
            explicaciones.append(score_ubicacion['explicacion'])
        
        # 3. Score de TAMAÑO (0-15)
        score_tamano = self._score_tamano(propiedad, preferencias)
        scores['tamano'] = score_tamano['puntos']
        if score_tamano['explicacion']:
            explicaciones.append(score_tamano['explicacion'])
        
        # 4. Score de TRANSPORTE (0-15)
        score_transporte = self._score_distancia(
            propiedad.dist_transporte_metro_m,
            preferencias.prioridad_transporte,
            15,
            "🚇 Metro muy cercano",
            "🚇 Metro cercano",
            invertir=preferencias.evitar_metro  # NUEVO: invertir si usuario quiere evitar
        )
        scores['transporte'] = score_transporte['puntos']
        if score_transporte['explicacion']:
            explicaciones.append(score_transporte['explicacion'])
        
        # 5. Score de EDUCACIÓN (0-10)
        score_educacion = self._score_distancia(
            propiedad.dist_educacion_min_m,
            preferencias.prioridad_educacion,
            10,
            "🏫 Colegios muy cerca",
            "🏫 Colegios en el barrio",
            invertir=preferencias.evitar_colegios  # NUEVO: invertir si usuario quiere evitar
        )
        scores['educacion'] = score_educacion['puntos']
        if score_educacion['explicacion']:
            explicaciones.append(score_educacion['explicacion'])
        
        # 6. Score de SALUD (0-10)
        score_salud = self._score_distancia(
            propiedad.dist_salud_min_m,
            preferencias.prioridad_salud,
            10,
            "🏥 Centros de salud muy cerca",
            "🏥 Centros de salud cercanos",
            invertir=preferencias.evitar_hospitales  # NUEVO: invertir si usuario quiere evitar
        )
        scores['salud'] = score_salud['puntos']
        if score_salud['explicacion']:
            explicaciones.append(score_salud['explicacion'])
        
        # 7. Score de ÁREAS VERDES (0-10)
        score_areas = self._score_distancia(
            propiedad.dist_areas_verdes_m,
            preferencias.prioridad_areas_verdes,
            10,
            "🌳 Parques muy cerca",
            "🌳 Parques cercanos",
            invertir=preferencias.evitar_areas_verdes  # NUEVO: invertir si usuario quiere evitar
        )
        scores['areas_verdes'] = score_areas['puntos']
        if score_areas['explicacion']:
            explicaciones.append(score_areas['explicacion'])
        
        # Score total
        score_total = sum(scores.values())
        
        # Limitar explicaciones a top 5
        explicaciones_top = explicaciones[:5]
        
        return {
            'propiedad': propiedad,
            'score_total': score_total,
            'scores_detallados': ScoreDetallado(**scores),
            'explicacion': explicaciones_top
        }
    
    def _score_precio(
        self, 
        propiedad: Propiedad, 
        preferencias: PreferenciasUsuario
    ) -> Dict:
        """Score basado en precio (0-20 pts)"""
        if not preferencias.precio_min or not preferencias.precio_max:
            return {'puntos': 10.0, 'explicacion': None}
        
        precio = propiedad.precio
        rango = preferencias.precio_max - preferencias.precio_min
        precio_ideal = preferencias.precio_min + (rango * 0.3)  # 30% del rango
        
        if precio <= precio_ideal:
            # Precio excelente (dentro del 30% inferior del rango)
            puntos_base = 20.0
            explicacion = "💰 Precio excelente dentro de tu presupuesto"
        elif precio <= preferencias.precio_min + (rango * 0.6):
            # Precio bueno (30-60% del rango)
            puntos_base = 16.0
            explicacion = "💰 Precio adecuado a tu presupuesto"
        else:
            # Precio alto (60-100% del rango)
            puntos_base = 12.0
            explicacion = "💰 Precio dentro de tu presupuesto"
        
        # Ponderar por prioridad (0-10)
        factor_prioridad = preferencias.prioridad_precio / 10.0
        puntos_final = puntos_base * factor_prioridad
        
        return {'puntos': round(puntos_final, 2), 'explicacion': explicacion}
    
    def _score_ubicacion(
        self, 
        propiedad: Propiedad, 
        preferencias: PreferenciasUsuario
    ) -> Dict:
        """Score basado en ubicación/comuna (0-20 pts)"""
        comuna_nombre = self.comunas_map.get(propiedad.comuna_id, '')
        
        if preferencias.comunas_preferidas and comuna_nombre in preferencias.comunas_preferidas:
            puntos_base = 20.0
            explicacion = f"📍 Ubicación excelente en {comuna_nombre}"
        else:
            puntos_base = 10.0
            explicacion = None
        
        # Ponderar por prioridad
        factor_prioridad = preferencias.prioridad_ubicacion / 10.0
        puntos_final = puntos_base * factor_prioridad
        
        return {'puntos': round(puntos_final, 2), 'explicacion': explicacion}
    
    def _score_tamano(
        self, 
        propiedad: Propiedad, 
        preferencias: PreferenciasUsuario
    ) -> Dict:
        """Score basado en tamaño (0-15 pts)"""
        puntos = 0.0
        explicacion = None
        
        # Score por superficie
        if propiedad.superficie_util:
            if preferencias.superficie_min:
                if propiedad.superficie_util >= preferencias.superficie_min * 1.2:
                    puntos += 8.0
                    explicacion = f"📐 Excelente tamaño ({propiedad.superficie_util:.0f}m²)"
                elif propiedad.superficie_util >= preferencias.superficie_min:
                    puntos += 6.0
                    explicacion = f"📐 Buen tamaño ({propiedad.superficie_util:.0f}m²)"
                else:
                    puntos += 3.0
            else:
                puntos += 5.0
        
        # Score por dormitorios
        if preferencias.dormitorios_min:
            if propiedad.dormitorios >= preferencias.dormitorios_min + 1:
                puntos += 7.0
            elif propiedad.dormitorios >= preferencias.dormitorios_min:
                puntos += 5.0
            else:
                puntos += 2.0
        else:
            puntos += 3.0
        
        # Ponderar por prioridad
        factor_prioridad = preferencias.prioridad_tamano / 10.0
        puntos_final = puntos * factor_prioridad
        
        return {'puntos': round(puntos_final, 2), 'explicacion': explicacion}
    
    def _score_distancia(
        self,
        distancia_m: Optional[float],
        prioridad: int,
        puntos_max: float,
        texto_excelente: str,
        texto_bueno: str,
        invertir: bool = False  # NUEVO: invierte la lógica (más lejos = mejor)
    ) -> Dict:
        """
        Score genérico basado en distancia
        
        Criterio NORMAL (invertir=False):
        - < 500m: Excelente (100% puntos)
        - 500-1000m: Muy bueno (80% puntos)
        - 1000-2000m: Bueno (60% puntos)
        - 2000-3000m: Aceptable (40% puntos)
        - > 3000m: Lejano (20% puntos)
        
        Criterio INVERTIDO (invertir=True) - para "evitar":
        - > 3000m: Excelente (100% puntos) - ¡Lejos es mejor!
        - 2000-3000m: Muy bueno (80% puntos)
        - 1000-2000m: Bueno (60% puntos)
        - 500-1000m: Regular (40% puntos)
        - < 500m: Malo (20% puntos) - ¡Muy cerca es indeseable!
        """
        if distancia_m is None:
            return {'puntos': puntos_max * 0.5, 'explicacion': None}
        
        # Determinar porcentaje según distancia
        if distancia_m < 500:
            porcentaje = 1.0
            explicacion = f"{texto_excelente} ({distancia_m:.0f}m)"
        elif distancia_m < 1000:
            porcentaje = 0.8
            explicacion = f"{texto_bueno} ({distancia_m:.0f}m)"
        elif distancia_m < 2000:
            porcentaje = 0.6
            explicacion = None
        elif distancia_m < 3000:
            porcentaje = 0.4
            explicacion = None
        else:
            porcentaje = 0.2
            explicacion = None
        
        # INVERTIR lógica si usuario quiere evitar
        if invertir:
            porcentaje = 1.2 - porcentaje  # 1.0→0.2, 0.8→0.4, 0.6→0.6, 0.4→0.8, 0.2→1.0
            if distancia_m > 3000:
                explicacion = f"✅ Bien alejado ({distancia_m:.0f}m)"
            elif distancia_m > 2000:
                explicacion = f"👍 Distancia prudente ({distancia_m:.0f}m)"
            else:
                explicacion = None
        
        # Aplicar porcentaje y prioridad
        factor_prioridad = prioridad / 10.0
        puntos_final = puntos_max * porcentaje * factor_prioridad
        
        return {'puntos': round(puntos_final, 2), 'explicacion': explicacion}
