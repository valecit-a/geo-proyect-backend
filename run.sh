#!/bin/bash

# Script para iniciar el servidor de desarrollo

echo "=========================================="
echo "🚀 Iniciando Backend Inmobiliario"
echo "=========================================="

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/bin/activate
fi

# Verificar instalación de dependencias
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI no instalado. Ejecuta: pip install -r requirements.txt"
    exit 1
fi

# Crear directorio de logs
mkdir -p logs

# Iniciar servidor
echo "🌐 Iniciando servidor en http://localhost:8000"
echo "📚 Documentación en http://localhost:8000/docs"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo "=========================================="
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
