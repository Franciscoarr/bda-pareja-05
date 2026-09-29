#!/bin/sh
# Arranque de Superset: prepara la base de metadatos y crea el usuario admin (idempotente).
set -e
superset db upgrade
superset fab create-admin --username admin --firstname Admin --lastname BDA \
  --email admin@bda.local --password bda2027 || true
superset init
echo "Superset listo en http://localhost:8088  (admin / bda2027)"
exec superset run -h 0.0.0.0 -p 8088 --with-threads
