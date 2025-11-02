"""
Script de prueba del sistema de recomendaciones
Prueba diferentes perfiles de usuario
"""
import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


def test_recomendaciones(nombre_caso, preferencias, limit=5):
    """Prueba un caso de recomendación"""
    print(f"\n{'='*80}")
    print(f"🧪 CASO: {nombre_caso}")
    print(f"{'='*80}")
    print(f"\n📋 Preferencias:")
    print(json.dumps(preferencias, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/recomendaciones",
            json=preferencias,
            params={"limit": limit}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ RESPUESTA EXITOSA")
            print(f"   Total analizadas: {data['total_analizadas']}")
            print(f"   Total encontradas: {data['total_encontradas']}")
            
            print(f"\n🏆 TOP {len(data['recomendaciones'])} RECOMENDACIONES:\n")
            
            for i, rec in enumerate(data['recomendaciones'], 1):
                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"#{i} - SCORE: {rec['score_total']:.1f}/100 pts")
                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"🏠 {rec['direccion']}")
                print(f"📍 {rec['comuna']}")
                print(f"💰 ${rec['precio']:,.0f} CLP")
                print(f"📐 {rec['superficie_util']:.0f}m² | {rec['dormitorios']}D/{rec['banos']}B | {rec['estacionamientos']} est.")
                
                print(f"\n📊 Scores Detallados:")
                scores = rec['scores_detallados']
                print(f"   💰 Precio: {scores['precio']:.1f}/20")
                print(f"   📍 Ubicación: {scores['ubicacion']:.1f}/20")
                print(f"   📐 Tamaño: {scores['tamano']:.1f}/15")
                print(f"   🚇 Transporte: {scores['transporte']:.1f}/15")
                print(f"   🏫 Educación: {scores['educacion']:.1f}/10")
                print(f"   🏥 Salud: {scores['salud']:.1f}/10")
                print(f"   🌳 Áreas Verdes: {scores['areas_verdes']:.1f}/10")
                
                print(f"\n💡 Por qué esta propiedad:")
                for razon in rec['explicacion']:
                    print(f"   • {razon}")
                
                print(f"\n📏 Distancias:")
                if rec.get('dist_metro_m'):
                    print(f"   🚇 Metro: {rec['dist_metro_m']:.0f}m")
                if rec.get('dist_educacion_min_m'):
                    print(f"   🏫 Educación: {rec['dist_educacion_min_m']:.0f}m")
                if rec.get('dist_salud_min_m'):
                    print(f"   🏥 Salud: {rec['dist_salud_min_m']:.0f}m")
                if rec.get('dist_areas_verdes_m'):
                    print(f"   🌳 Parques: {rec['dist_areas_verdes_m']:.0f}m")
                print()
            
        else:
            print(f"\n❌ ERROR {response.status_code}")
            print(f"   {response.json().get('detail', 'Error desconocido')}")
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")


def main():
    """Ejecuta todos los casos de prueba"""
    print("\n" + "="*80)
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE RECOMENDACIONES")
    print("="*80)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ========================================================================
    # CASO 1: Familia con niños
    # ========================================================================
    test_recomendaciones(
        "Familia con niños - Prioriza educación y áreas verdes",
        {
            "precio_min": 300000,
            "precio_max": 600000,
            "superficie_min": 50,
            "dormitorios_min": 2,
            "banos_min": 1,
            "comunas_preferidas": ["Providencia", "Ñuñoa", "Las Condes"],
            "prioridad_precio": 7,
            "prioridad_ubicacion": 8,
            "prioridad_transporte": 6,
            "prioridad_educacion": 10,
            "prioridad_salud": 6,
            "prioridad_areas_verdes": 9,
            "prioridad_tamano": 8,
            "requiere_estacionamiento": True
        },
        limit=3
    )
    
    # ========================================================================
    # CASO 2: Profesional soltero
    # ========================================================================
    test_recomendaciones(
        "Profesional soltero - Prioriza transporte y ubicación",
        {
            "precio_min": 250000,
            "precio_max": 500000,
            "superficie_min": 30,
            "dormitorios_min": 1,
            "banos_min": 1,
            "comunas_preferidas": ["Providencia", "Santiago"],
            "prioridad_precio": 9,
            "prioridad_ubicacion": 10,
            "prioridad_transporte": 10,
            "prioridad_educacion": 2,
            "prioridad_salud": 4,
            "prioridad_areas_verdes": 3,
            "prioridad_tamano": 4,
            "requiere_estacionamiento": False
        },
        limit=3
    )
    
    # ========================================================================
    # CASO 3: Pareja joven
    # ========================================================================
    test_recomendaciones(
        "Pareja joven - Equilibrio precio/calidad",
        {
            "precio_min": 300000,
            "precio_max": 700000,
            "superficie_min": 45,
            "dormitorios_min": 2,
            "banos_min": 1,
            "comunas_preferidas": ["Providencia", "Ñuñoa", "Santiago"],
            "prioridad_precio": 8,
            "prioridad_ubicacion": 7,
            "prioridad_transporte": 8,
            "prioridad_educacion": 5,
            "prioridad_salud": 5,
            "prioridad_areas_verdes": 6,
            "prioridad_tamano": 7,
            "requiere_estacionamiento": True
        },
        limit=5
    )
    
    # ========================================================================
    # CASO 4: Inversión - Solo precio bajo
    # ========================================================================
    test_recomendaciones(
        "Inversión - Busca el mejor precio",
        {
            "precio_min": 150000,
            "precio_max": 400000,
            "prioridad_precio": 10,
            "prioridad_ubicacion": 3,
            "prioridad_transporte": 5,
            "prioridad_educacion": 3,
            "prioridad_salud": 3,
            "prioridad_areas_verdes": 3,
            "prioridad_tamano": 4
        },
        limit=5
    )
    
    print("\n" + "="*80)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
