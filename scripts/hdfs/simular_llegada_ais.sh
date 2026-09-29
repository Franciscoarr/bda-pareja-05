#!/bin/bash
# -----------------------------------------------------------------------------
# Simula la llegada CONTINUA de datos AIS (un fichero diario cada N segundos) a la
# zona /puerto/landing/ais. Útil en la fase 4 para vigilar la «frescura» de los datos.
#   docker compose exec namenode bash /scripts/simular_llegada_ais.sh [segundos=60]
# Ctrl+C para parar. Si se para, la alerta de datos obsoletos debería dispararse.
# -----------------------------------------------------------------------------
set -uo pipefail
PAUSA="${1:-60}"
hdfs dfs -mkdir -p /puerto/landing/ais
for f in /datos/raw/ais/*.jsonl; do
  nombre=$(basename "$f")
  echo "$(date +%T) >> llega $nombre"
  hdfs dfs -put -f "$f" "/puerto/landing/ais/$nombre"
  sleep "$PAUSA"
done
echo "No quedan más ficheros AIS que simular."
