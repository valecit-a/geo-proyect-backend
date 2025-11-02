#!/bin/bash

echo "=========================================="
echo "📦 Instalación Backend Inmobiliario"
echo "=========================================="
echo ""

# 1. Crear entorno virtual
echo "1️⃣  Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# 2. Actualizar pip
echo "2️⃣  Actualizando pip..."
pip install --upgrade pip -q

# 3. Instalar dependencias
echo "3️⃣  Instalando dependencias..."
pip install -r requirements.txt -q

echo ""
echo "✅ Dependencias instaladas"
echo ""

# 4. Verificar PostgreSQL
echo "4️⃣  Verificando PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL no detectado. Instálalo con:"
    echo "   sudo apt install postgresql postgresql-contrib postgis"
else
    echo "✅ PostgreSQL instalado"
fi

echo ""

# 5. Crear base de datos
echo "5️⃣  ¿Deseas crear la base de datos ahora? (s/n)"
read -r response
if [[ "$response" =~ ^([sS][iI]|[sS])$ ]]; then
    echo "Creando base de datos 'inmobiliario_db'..."
    psql -U postgres -c "CREATE DATABASE inmobiliario_db;" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Base de datos creada"
    else
        echo "⚠️  La base de datos ya existe o hubo un error"
    fi
fi

echo ""

# 6. Inicializar base de datos
echo "6️⃣  ¿Deseas inicializar las tablas? (s/n)"
read -r response
if [[ "$response" =~ ^([sS][iI]|[sS])$ ]]; then
    python scripts/init_db.py
fi

echo ""

# 7. Test del modelo
echo "7️⃣  ¿Deseas probar el modelo ML? (s/n)"
read -r response
if [[ "$response" =~ ^([sS][iI]|[sS])$ ]]; then
    python scripts/test_model.py
fi

echo ""
echo "=========================================="
echo "✅ INSTALACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Para iniciar el servidor:"
echo "  ./run.sh"
echo ""
echo "O manualmente:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Documentación: http://localhost:8000/docs"
echo "=========================================="
