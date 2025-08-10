#!/bin/bash

BASE_DIR="results_iterative"  # Cambia si tu carpeta base es distinta
BAD_SIZE=65
BAD_TOPOLOGIES=()

echo "🔍 Buscando topologías con CSVs defectuosos (solo cabecera, $BAD_SIZE bytes)..."

# Recorremos cada carpeta tipo topo_XXXX
for topo_dir in "$BASE_DIR"/topo_*; do
    if [ -d "$topo_dir" ]; then
        # Contamos cuántos ficheros pesan exactamente BAD_SIZE bytes
        bad_files=$(find "$topo_dir" -type f -size ${BAD_SIZE}c | wc -l)
        
        if [ "$bad_files" -gt 0 ]; then
            echo "⚠️  Eliminando carpeta con errores: $(basename "$topo_dir")"
            rm -rf "$topo_dir"
            BAD_TOPOLOGIES+=("$(basename "$topo_dir")")
        fi
    fi
done

# Resumen final
echo
echo "===== RESUMEN ====="
if [ ${#BAD_TOPOLOGIES[@]} -eq 0 ]; then
    echo "✅ Todas las topologías tenían CSVs correctos."
else
    echo "🗑 Eliminadas las siguientes topologías con errores:"
    for topo in "${BAD_TOPOLOGIES[@]}"; do
        echo " - $topo"
    done
fi
