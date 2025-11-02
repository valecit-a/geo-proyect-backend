#!/bin/bash

# Script de prueba: Sistema de Recomendaciones ML con Preferencias Detalladas
# Demuestra cómo un usuario puede dar información MUY ESPECÍFICA

echo "==========================================================================="
echo "🧪 TEST: Sistema de Recomendaciones ML - Preferencias Detalladas"
echo "==========================================================================="
echo ""

echo "📋 ESCENARIO: Usuario con preferencias MUY específicas"
echo "   - Presupuesto: \$250.000 - \$350.000"
echo "   - 2-3 dormitorios, 2 baños mínimo"
echo "   - Comunas: Providencia o Ñuñoa"
echo ""
echo "   ✅ QUIERE (importancia positiva):"
echo "      • Metro muy cerca (+9): máximo 600m"
echo "      • Parques cerca (+10): máximo 500m"
echo "      • Consultorios cerca (+10): máximo 1000m"
echo ""
echo "   ❌ NO QUIERE (importancia negativa):"
echo "      • Colegios cerca (-8): prefiere a más de 500m (evitar ruido)"
echo ""
echo "==========================================================================="
echo ""

sleep 2

echo "🚀 Ejecutando consulta al endpoint ML..."
echo ""

curl -X POST "http://localhost:8000/api/v1/recomendaciones-ml?limit=5" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3001" \
  -d '{
    "precio_min": 250000,
    "precio_max": 350000,
    "dormitorios_min": 2,
    "dormitorios_max": 3,
    "banos_min": 2,
    "comunas_preferidas": ["Providencia", "Ñuñoa"],
    
    "transporte": {
      "importancia_metro": 9,
      "distancia_maxima_metro_m": 600,
      "importancia_buses": 3,
      "distancia_maxima_buses_m": 300
    },
    
    "educacion": {
      "importancia_colegios": -8,
      "distancia_maxima_colegios_m": 500,
      "importancia_universidades": 0
    },
    
    "salud": {
      "importancia_consultorios": 10,
      "distancia_maxima_consultorios_m": 1000,
      "importancia_hospitales": 5,
      "distancia_maxima_hospitales_m": 2000
    },
    
    "areas_verdes": {
      "importancia_parques": 10,
      "distancia_maxima_parques_m": 500,
      "importancia_plazas": 5,
      "distancia_maxima_plazas_m": 300
    },
    
    "peso_precio": 0.25,
    "peso_ubicacion": 0.15,
    "peso_tamano": 0.10,
    "peso_transporte": 0.20,
    "peso_educacion": 0.10,
    "peso_salud": 0.10,
    "peso_servicios": 0.05,
    "peso_areas_verdes": 0.05
  }' | python3 -m json.tool

echo ""
echo "==========================================================================="
echo "✅ Test completado!"
echo ""
echo "📊 CARACTERÍSTICAS DEL SISTEMA ML:"
echo ""
echo "1️⃣  Preferencias DETALLADAS por categoría (-10 a +10)"
echo "2️⃣  Valores NEGATIVOS para EVITAR características"
echo "3️⃣  Valores POSITIVOS para BUSCAR características"
echo "4️⃣  Scoring EXPLICADO con puntos fuertes/débiles"
echo "5️⃣  Confianza del modelo (0-1)"
echo "6️⃣  Sugerencias inteligentes para mejorar búsqueda"
echo ""
echo "🎯 EJEMPLO PRÁCTICO:"
echo "   Usuario NO quiere colegios cerca (ruido) → importancia_colegios: -8"
echo "   Sistema INVIERTE el scoring: más lejos = mejor puntaje"
echo "   Resultado: propiedades SIN colegios cerca tienen score alto"
echo ""
echo "==========================================================================="
