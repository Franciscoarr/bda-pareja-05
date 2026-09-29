#!/bin/bash
# Muestra los bloques de un fichero HDFS y en qué DataNodes está cada réplica (fases 2 y 3).
#   docker compose exec namenode bash /scripts/localizar_bloques.sh /puerto/raw/escalas/escalas_2025.csv
set -euo pipefail
[ $# -ge 1 ] || { echo "Uso: $0 <ruta_hdfs>"; exit 1; }
hdfs fsck "$1" -files -blocks -locations
