#!/usr/bin/env python3
"""
Exportador de métricas HDFS -> Prometheus (Fase 4 del proyecto).

Hadoop publica sus métricas internas en JSON (http://namenode:9870/jmx), pero
Prometheus solo entiende su propio formato de texto. Este pequeño servicio hace de
«traductor»: cada vez que Prometheus pide /metrics, consulta el JMX del NameNode y
devuelve las métricas en formato Prometheus.

Solo usa la biblioteca estándar de Python: no hay que instalar nada.

Variables de entorno:
    NAMENODE_URL     (por defecto http://namenode:9870)
    PUERTO_EXPORTER  (por defecto 9101)
    RUTA_FRESCURA    carpeta HDFS cuya última modificación se vigila (por defecto /puerto/raw/ais)

TAREAS PARA LA FASE 4 (buscad «TAREA» en este fichero):
    1. Añadir al menos 3 métricas nuevas de la tabla METRICAS (consultad /jmx en el navegador).
    2. Completar metricas_por_datanode(): una serie por DataNode con su espacio usado y
       su último contacto (etiqueta datanode="...").
    3. Documentar en la memoria qué significa cada métrica y qué umbral de alerta proponéis.
"""
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NAMENODE_URL = os.environ.get("NAMENODE_URL", "http://namenode:9870").rstrip("/")
PUERTO = int(os.environ.get("PUERTO_EXPORTER", "9101"))
RUTA_FRESCURA = os.environ.get("RUTA_FRESCURA", "/puerto/raw/ais")
TIMEOUT = 5

# (bean JMX, atributo, nombre Prometheus, tipo, ayuda)
METRICAS = [
    ("Hadoop:service=NameNode,name=FSNamesystemState", "NumLiveDataNodes",
     "bda_hdfs_datanodes_vivos", "gauge", "DataNodes vivos según el NameNode"),
    ("Hadoop:service=NameNode,name=FSNamesystemState", "NumDeadDataNodes",
     "bda_hdfs_datanodes_muertos", "gauge", "DataNodes declarados muertos"),
    ("Hadoop:service=NameNode,name=FSNamesystemState", "CapacityTotal",
     "bda_hdfs_capacidad_total_bytes", "gauge", "Capacidad total de HDFS en bytes"),
    ("Hadoop:service=NameNode,name=FSNamesystemState", "CapacityUsed",
     "bda_hdfs_capacidad_usada_bytes", "gauge", "Bytes usados por bloques HDFS (incluye réplicas)"),
    ("Hadoop:service=NameNode,name=FSNamesystemState", "CapacityRemaining",
     "bda_hdfs_capacidad_libre_bytes", "gauge", "Bytes libres para HDFS"),
    ("Hadoop:service=NameNode,name=FSNamesystemState", "FilesTotal",
     "bda_hdfs_ficheros_total", "gauge", "Número de ficheros y directorios"),
    ("Hadoop:service=NameNode,name=FSNamesystemState", "BlocksTotal",
     "bda_hdfs_bloques_total", "gauge", "Número de bloques"),
    ("Hadoop:service=NameNode,name=FSNamesystem", "CorruptBlocks",
     "bda_hdfs_bloques_corruptos", "gauge", "Bloques con al menos una réplica corrupta"),
    ("Hadoop:service=NameNode,name=FSNamesystem", "MissingBlocks",
     "bda_hdfs_bloques_perdidos", "gauge", "Bloques sin ninguna réplica disponible (¡pérdida de datos!)"),
    ("Hadoop:service=NameNode,name=FSNamesystem", "UnderReplicatedBlocks",
     "bda_hdfs_bloques_infrarreplicados", "gauge", "Bloques con menos réplicas de las configuradas"),
    # TAREA 1: añadir aquí al menos 3 métricas más. Ideas (comprobad los nombres en /jmx):
    #   FSNamesystem -> PendingReplicationBlocks, PendingDeletionBlocks, ExcessBlocks
    #   FSNamesystemState -> NumStaleDataNodes, VolumeFailuresTotal
    #   JvmMetrics (Hadoop:service=NameNode,name=JvmMetrics) -> MemHeapUsedM, GcTimeMillis
]


def _get_json(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def leer_beans():
    """Descarga el JMX completo del NameNode y lo indexa por nombre de bean."""
    datos = _get_json(f"{NAMENODE_URL}/jmx")
    return {b.get("name"): b for b in datos.get("beans", [])}


def linea(nombre, valor, etiquetas=None):
    if etiquetas:
        et = ",".join(f'{k}="{str(v)}"' for k, v in etiquetas.items())
        return f"{nombre}{{{et}}} {valor}"
    return f"{nombre} {valor}"


def metricas_por_datanode(beans):
    """TAREA 2: devolver líneas con una serie por DataNode.

    El bean «Hadoop:service=NameNode,name=NameNodeInfo» tiene el atributo «LiveNodes»,
    que es un TEXTO con JSON dentro:  {"host:puerto": {"usedSpace": ..., "lastContact": ...}, ...}
    Pista: json.loads(beans[...]["LiveNodes"]).items()
    Debe devolver algo como:
        ['# HELP bda_hdfs_datanode_usado_bytes ...', '# TYPE bda_hdfs_datanode_usado_bytes gauge',
         'bda_hdfs_datanode_usado_bytes{datanode="172.18.0.5:9866"} 123456', ...]
    """
    return []


def frescura():
    """Momento (epoch, s) de la última modificación dentro de RUTA_FRESCURA (vía WebHDFS)."""
    url = f"{NAMENODE_URL}/webhdfs/v1{RUTA_FRESCURA}?op=LISTSTATUS&user.name=hadoop"
    datos = _get_json(url)
    estados = datos.get("FileStatuses", {}).get("FileStatus", [])
    if not estados:
        return None, 0
    ultimo = max(e.get("modificationTime", 0) for e in estados) / 1000.0
    return ultimo, len(estados)


def construir_respuesta():
    salida = []
    t0 = time.time()
    try:
        beans = leer_beans()
        arriba = 1
    except (urllib.error.URLError, OSError, ValueError):
        beans, arriba = {}, 0
    latencia = time.time() - t0

    salida += ["# HELP bda_namenode_up 1 si el NameNode responde al exportador",
               "# TYPE bda_namenode_up gauge", linea("bda_namenode_up", arriba),
               "# HELP bda_namenode_respuesta_segundos Tiempo de respuesta del JMX del NameNode",
               "# TYPE bda_namenode_respuesta_segundos gauge",
               linea("bda_namenode_respuesta_segundos", round(latencia, 4))]

    for bean, atributo, nombre, tipo, ayuda in METRICAS:
        valor = beans.get(bean, {}).get(atributo)
        if valor is None:
            continue
        salida += [f"# HELP {nombre} {ayuda}", f"# TYPE {nombre} {tipo}", linea(nombre, valor)]

    if arriba:
        salida += metricas_por_datanode(beans)
        try:
            ultimo, n = frescura()
            if ultimo is not None:
                salida += ["# HELP bda_datos_ultima_modificacion_segundos Epoch de la última escritura en la ruta vigilada",
                           "# TYPE bda_datos_ultima_modificacion_segundos gauge",
                           linea("bda_datos_ultima_modificacion_segundos", round(ultimo, 3), {"ruta": RUTA_FRESCURA}),
                           "# HELP bda_datos_ficheros Ficheros en la ruta vigilada",
                           "# TYPE bda_datos_ficheros gauge",
                           linea("bda_datos_ficheros", n, {"ruta": RUTA_FRESCURA})]
        except (urllib.error.URLError, OSError, ValueError):
            pass  # la ruta aún no existe: no se publica la métrica
    return "\n".join(salida) + "\n"


class Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/metrics"):
            cuerpo = construir_respuesta().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        else:
            cuerpo = b"Exportador HDFS del proyecto BDA. Metricas en /metrics\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass  # sin una línea de log por cada petición de Prometheus


if __name__ == "__main__":
    print(f"Exportador HDFS escuchando en :{PUERTO} (NameNode: {NAMENODE_URL})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador).serve_forever()
