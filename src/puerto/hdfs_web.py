"""Consultas a HDFS desde Python mediante la API REST WebHDFS del NameNode.

En el contenedor jupyter no está el comando «hdfs»; para operaciones de METADATOS
(listar, tamaños, réplicas, sumas de verificación, fsck) usamos HTTP. Para leer y
escribir DATOS usad siempre Spark (spark.read / df.write).

Ejemplos:
    from puerto import hdfs_web as h
    h.ls("/puerto/raw")
    h.resumen("/puerto/raw/ais")            # tamaño lógico y espacio real (con réplicas)
    h.checksum("/puerto/raw/escalas/escalas_2025.csv")
    h.replicacion("/puerto/raw/escalas/escalas_2025.csv", 2)
    print(h.fsck("/puerto/raw/escalas"))
    h.datanodes()
"""
import json

import requests

NAMENODE = "http://namenode:9870"
USUARIO = "hadoop"
_T = 30


def _url(ruta, op, **params):
    extra = "".join(f"&{k}={v}" for k, v in params.items())
    return f"{NAMENODE}/webhdfs/v1{ruta}?op={op}&user.name={USUARIO}{extra}"


def _get(ruta, op, **params):
    r = requests.get(_url(ruta, op, **params), timeout=_T)
    if r.status_code != 200:
        raise RuntimeError(f"WebHDFS {op} {ruta}: HTTP {r.status_code} {r.text[:300]}")
    return r.json()


def listar(ruta="/"):
    """Lista el contenido de una carpeta: lista de diccionarios."""
    estados = _get(ruta, "LISTSTATUS")["FileStatuses"]["FileStatus"]
    return [{"nombre": e["pathSuffix"], "tipo": e["type"], "bytes": e["length"],
             "replicas": e.get("replication", 0), "bloque_mb": round(e.get("blockSize", 0) / 2**20),
             "modificado_ms": e["modificationTime"]} for e in estados]


def ls(ruta="/"):
    """Muestra el contenido de una carpeta como tabla."""
    filas = listar(ruta)
    print(f"{'tipo':9} {'réplicas':>8} {'bloque':>7} {'tamaño':>12}  nombre")
    for f in filas:
        print(f"{f['tipo']:9} {f['replicas']:>8} {str(f['bloque_mb'])+' MB':>7} {_humano(f['bytes']):>12}  {f['nombre']}")
    return None


def estado(ruta):
    return _get(ruta, "GETFILESTATUS")["FileStatus"]


def resumen(ruta):
    """Tamaño lógico (length) y espacio consumido en disco (spaceConsumed = length x réplicas)."""
    c = _get(ruta, "GETCONTENTSUMMARY")["ContentSummary"]
    return {"ficheros": c["fileCount"], "carpetas": c["directoryCount"], "bytes": c["length"],
            "bytes_en_disco": c["spaceConsumed"], "tamano": _humano(c["length"]),
            "en_disco": _humano(c["spaceConsumed"])}


def checksum(ruta):
    """Suma de verificación HDFS del fichero (por defecto MD5-of-MD5-of-CRC32C)."""
    return _get(ruta, "GETFILECHECKSUM")["FileChecksum"]


def replicacion(ruta, n):
    """Cambia el factor de replicación de un FICHERO (no de carpetas)."""
    r = requests.put(_url(ruta, "SETREPLICATION", replication=n), timeout=_T)
    r.raise_for_status()
    return r.json().get("boolean")


def borrar(ruta, recursivo=False):
    r = requests.delete(_url(ruta, "DELETE", recursive=str(recursivo).lower()), timeout=_T)
    r.raise_for_status()
    return r.json().get("boolean")


def fsck(ruta="/", bloques=True, ubicaciones=True):
    """Informe de salud del sistema de ficheros (equivale a «hdfs fsck ruta -files -blocks -locations»)."""
    url = f"{NAMENODE}/fsck?ugi={USUARIO}&path={ruta}"
    if bloques:
        url += "&files=1&blocks=1"
    if ubicaciones:
        url += "&locations=1"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.text


def jmx(bean=None):
    """Métricas internas del NameNode (JSON). bean p.ej. 'Hadoop:service=NameNode,name=FSNamesystem'."""
    url = f"{NAMENODE}/jmx" + (f"?qry={bean}" if bean else "")
    return requests.get(url, timeout=_T).json()["beans"]


def datanodes():
    """Lista de DataNodes vivos con su uso de disco y último contacto (segundos)."""
    info = jmx("Hadoop:service=NameNode,name=NameNodeInfo")[0]
    vivos = json.loads(info["LiveNodes"])
    muertos = json.loads(info.get("DeadNodes", "{}"))
    filas = []
    for nombre, d in vivos.items():
        filas.append({"datanode": nombre, "estado": "vivo", "usado": _humano(d.get("usedSpace", 0)),
                      "bloques": d.get("numBlocks"), "ultimo_contacto_s": d.get("lastContact")})
    for nombre, d in muertos.items():
        filas.append({"datanode": nombre, "estado": "MUERTO", "usado": "-", "bloques": None,
                      "ultimo_contacto_s": d.get("lastContact")})
    return filas


def _humano(n):
    n = float(n or 0)
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"
