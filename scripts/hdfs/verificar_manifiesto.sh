#!/bin/bash
# -----------------------------------------------------------------------------
# Integridad EXTREMO A EXTREMO (fase 3): comprueba que lo que hay en HDFS es
# exactamente lo que se generó, comparando SHA-256 con el manifiesto original.
#   docker compose exec namenode bash /scripts/verificar_manifiesto.sh [ruta_hdfs=/puerto/raw] [carpeta_local=/datos/raw]
# -----------------------------------------------------------------------------
set -uo pipefail
RUTA="${1:-/puerto/raw}"
LOCAL="${2:-/datos/raw}"
TMP=/tmp/verificacion_$$
mkdir -p "$TMP"
echo ">> Descargando $RUTA de HDFS a $TMP (la lectura ya verifica los CRC de HDFS)..."
hdfs dfs -get "$RUTA" "$TMP/" || { echo "ERROR al leer de HDFS"; exit 2; }
cd "$TMP/$(basename "$RUTA")"
echo ">> Comparando SHA-256 con $LOCAL/MANIFIESTO.sha256"
if sha256sum -c --quiet $LOCAL/MANIFIESTO.sha256; then
  echo "RESULTADO: todos los ficheros coinciden ($(wc -l < $LOCAL/MANIFIESTO.sha256) ficheros)"
  estado=0
else
  echo "RESULTADO: HAY DIFERENCIAS (ver líneas FAILED arriba)"
  estado=1
fi
rm -rf "$TMP"
exit $estado
