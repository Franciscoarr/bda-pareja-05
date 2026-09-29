#!/usr/bin/env bash
# Equivalente de bda.ps1 para Linux / macOS / WSL.  Uso: ./bda.sh <orden> [args]
set -uo pipefail
cd "$(dirname "$0")"
IMAGEN="bda-puerto/spark:3.5.8"
PERFILES=(--profile monitor --profile bi)
orden="${1:-ayuda}"; shift || true

urls() {
  cat <<'U'
  HDFS NameNode ...... http://localhost:9870
  Spark master ....... http://localhost:8080
  JupyterLab ......... http://localhost:8888
  Spark (aplicación) . http://localhost:4040
  Prometheus ......... http://localhost:9090   (perfil monitor)
  Grafana ............ http://localhost:3000   admin / bda2027
  Superset ........... http://localhost:8088   admin / bda2027 (perfil bi)
  PostgreSQL ......... localhost:5432 bda / bda2027, BD puerto_dw
U
}
construir_si_falta() { docker image inspect "$IMAGEN" >/dev/null 2>&1 || docker compose build spark-master; }

case "$orden" in
  construir) docker compose build spark-master ;;
  iniciar)
    construir_si_falta
    case "${1:-}" in
      "") docker compose up -d ;;
      monitor|bi) docker compose --profile "$1" up -d ;;
      todo) docker compose "${PERFILES[@]}" up -d ;;
      *) echo "Perfil desconocido: $1"; exit 1 ;;
    esac
    urls ;;
  parar) docker compose "${PERFILES[@]}" stop ;;
  estado) docker compose "${PERFILES[@]}" ps; urls ;;
  datos) docker compose exec jupyter python /datos/generador/generar_datos.py --escala "${1:-1}" ;;
  ingesta) docker compose exec namenode bash /scripts/ingesta.sh ;;
  verificar) docker compose exec namenode bash /scripts/verificar_manifiesto.sh ;;
  hdfs) docker compose exec namenode hdfs "$@" ;;
  escalar) docker compose up -d --no-recreate --scale "$1=$2" "$1" ;;
  consola) docker compose "${PERFILES[@]}" exec "${1:-namenode}" bash ;;
  logs) docker compose "${PERFILES[@]}" logs --tail 80 "${1:-namenode}" ;;
  reset) read -rp "Se borrará HDFS. ¿Seguro? (s/n) " ok; [ "$ok" = s ] && docker compose "${PERFILES[@]}" down --remove-orphans ;;
  reset-bi) read -rp "Se borrarán también los volúmenes. ¿Seguro? (s/n) " ok; [ "$ok" = s ] && docker compose "${PERFILES[@]}" down -v --remove-orphans ;;
  urls) urls ;;
  *) sed -n '3,20p' bda.ps1 ;;
esac
