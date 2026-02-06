#!/bin/bash

# Script para ejecutar el frontend de Streamlit
# Debe ejecutarse desde el ROOT del proyecto

# Detectar si estamos en el directorio correcto
if [ ! -f "app.py" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el root del proyecto"
    echo "   Usa: cd /path/to/contract-compliance-demo && ./run_streamlit.sh"
    exit 1
fi

echo "🚀 Iniciando Frontend de Conciliación de Seguros..."
echo ""

# Verificar que los PDFs existen
if [ ! -d "data" ]; then
    echo "⚠️  Advertencia: No se encontró directorio data/"
fi

echo ""
echo "✅ Lanzando aplicación desde el directorio: $(pwd)"
echo "📊 La aplicación se abrirá en http://localhost:8501"
echo ""

# Ejecutar streamlit desde el root del proyecto
uv run streamlit run app.py
