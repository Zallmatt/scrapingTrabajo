#!/bin/bash
# Script para ejecutar solo scrapers automáticos
# Uso: ./scripts/execute_automaticos.sh

set -e  # Salir si hay error

# Obtener el directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR"

# Activar entorno virtual
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "env_scrapping" ]; then
    source env_scrapping/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
else
    echo "⚠️ No se encontró entorno virtual. Continuando sin activar..."
fi

# Array con todos los scrapers automáticos
AUTOMATICOS=(
    "automaticos/scrap_IPC/main.py"
    "automaticos/scrap_EMAE/main.py"
    "automaticos/scrap_SIPA/main.py"
    "automaticos/scrap_RIPTE/main.py"
    "automaticos/scrap_DOLAR/main.py"
    "automaticos/scrap_CBT/main.py"
    "automaticos/scrap_SalarioMVM/main.py"
    "automaticos/scrap_PuestosTrabajoSP/main.py"
    "automaticos/scrap_SalarioSPTotal/main.py"
    "automaticos/scrap_DNRPA/main.py"
    "automaticos/scrap_ANAC/main.py"
    "automaticos/scrap_IERIC/main.py"
    "automaticos/scrap_IndiceSalarios/main.py"
    "automaticos/scrap_IPC_CABA/main.py"
    "automaticos/scrap_IPC_Online/main.py"
    "automaticos/scrap_REM/main.py"
    "automaticos/scrap_IPI/main.py"
    "automaticos/scrap_IPICORR/main.py"
    "automaticos/scrap_Semaforo/main.py"
    "automaticos/scrap_VentasCombustible/main.py"
    "automaticos/scrap_SRT/main.py"
    "automaticos/scrap_Supermercados/main.py"
    "automaticos/scrap_CanastaBasica/run.py"
    "automaticos/scrap_OEDE/main.py"
)

echo "🚀 Ejecutando scrapers automáticos..."
echo "=========================================="
echo "Fecha: $(date)"
echo "Directorio: $PROJECT_DIR"
echo "=========================================="
echo ""

EXITOSOS=0
FALLIDOS=0
NO_ENCONTRADOS=0

for scraper in "${AUTOMATICOS[@]}"; do
    if [ -f "$scraper" ]; then
        echo ""
        echo "▶️ Ejecutando: $scraper"
        echo "----------------------------------------"
        
        if python3 "$scraper"; then
            echo "✅ Completado exitosamente"
            ((EXITOSOS++))
        else
            echo "❌ Error en ejecución"
            ((FALLIDOS++))
            # Continuar con el siguiente
        fi
    else
        echo "⚠️ No encontrado: $scraper"
        ((NO_ENCONTRADOS++))
    fi
done

echo ""
echo "=========================================="
echo "📊 RESUMEN"
echo "=========================================="
echo "✅ Exitosos: $EXITOSOS"
echo "❌ Fallidos: $FALLIDOS"
echo "⚠️ No encontrados: $NO_ENCONTRADOS"
echo "Total procesados: ${#AUTOMATICOS[@]}"
echo "=========================================="

# Salir con código de error si hubo fallos
if [ $FALLIDOS -gt 0 ]; then
    exit 1
fi

exit 0

