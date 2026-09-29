#!/bin/bash
# -----------------------------------------------------------------------------
# Ingesta por lotes de los datos simulados en HDFS (se ejecuta DENTRO del NameNode).
#   .\bda.ps1 ingesta              (desde Windows)
#   docker compose exec namenode bash /scripts/ingesta.sh [origen] [destino]
# Crea la estructura de zonas del lago de datos y copia /datos/raw -> /puerto/raw.
# Con otro destino (p. ej. /prueba/raw) las zonas y el control se crean bajo /prueba.
# Es IDEMPOTENTE: se puede repetir sin duplicar datos (put -f sobrescribe).
# -----------------------------------------------------------------------------
set -euo pipefail
ORIGEN="${1:-/datos/raw}"
DESTINO="${2:-/puerto/raw}"

if [ ! -f "$ORIGEN/MANIFIESTO.sha256" ]; then
  echo "ERROR: no hay datos en $ORIGEN. Generadlos antes con:  .\\bda.ps1 datos" >&2
  exit 1
fi

BASE=$(dirname "$DESTINO")
inicio=$(date +%s)
echo ">> Creando zonas del lago de datos en $BASE"
hdfs dfs -mkdir -p "$DESTINO" "$BASE/bronze" "$BASE/silver" "$BASE/gold" "$BASE/cuarentena" "$BASE/control"

for d in maestros escalas negocio contenedores sensores ais; do
  n=$(ls -1 "$ORIGEN/$d" | wc -l)
  echo ">> Ingestando $d ($n ficheros)"
  hdfs dfs -mkdir -p "$DESTINO/$d"
  hdfs dfs -put -f "$ORIGEN/$d"/* "$DESTINO/$d/"
done
hdfs dfs -put -f "$ORIGEN/MANIFIESTO.sha256" "$BASE/control/MANIFIESTO.sha256"

fin=$(date +%s)
registro="{\"fecha\":\"$(date -Iseconds)\",\"origen\":\"$ORIGEN\",\"destino\":\"$DESTINO\",\"segundos\":$((fin-inicio))}"
echo "$registro" | hdfs dfs -appendToFile - "$BASE/control/ingestas.jsonl"
echo ">> Ingesta terminada en $((fin-inicio)) s. Resumen:"
hdfs dfs -du -s -h "$DESTINO"/*
