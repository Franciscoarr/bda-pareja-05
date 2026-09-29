#!/bin/bash
# -----------------------------------------------------------------------------
# EXPERIMENTO CONTROLADO (fase 3): corrompe la réplica local de un bloque en ESTE DataNode
# sobrescribiendo 16 bytes, SIN tocar su fichero .meta (donde están las sumas CRC).
# Se ejecuta DENTRO de un DataNode:
#   docker exec -it bda-puerto-datanode-1 bash /scripts/corromper_bloque.sh blk_1073741830
# Guarda una copia en /tmp/<bloque>.copia para poder comparar después.
# -----------------------------------------------------------------------------
set -euo pipefail
[ $# -ge 1 ] || { echo "Uso: $0 blk_<id>"; exit 1; }
BLK="$1"
F=$(find /tmp/hdfs/data -type f -name "$BLK" | head -1)
if [ -z "$F" ]; then
  echo "Este DataNode ($(hostname)) no guarda ninguna réplica de $BLK. Probad en otro."
  exit 1
fi
cp "$F" "/tmp/$BLK.copia"
echo "Réplica encontrada: $F ($(stat -c %s "$F") bytes)"
echo "SHA-256 antes:   $(sha256sum "$F" | cut -d' ' -f1)"
printf 'CORRUPCION-BDA!!' | dd of="$F" bs=1 seek=1024 conv=notrunc status=none
echo "SHA-256 después: $(sha256sum "$F" | cut -d' ' -f1)"
echo "Hecho. Ahora leed el fichero desde el NameNode (hdfs dfs -cat ... > /dev/null) y observad."
