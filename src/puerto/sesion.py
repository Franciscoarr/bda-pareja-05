"""Creación de la SparkSession y utilidades de medida de tiempos."""
import time
from contextlib import contextmanager

from pyspark.sql import SparkSession


def crear_spark(nombre="bda-puerto", local=False, cores_max=None, memoria_executor=None, extra=None):
    """Devuelve una SparkSession.

    local=True  -> todo en el contenedor jupyter (modo local[*]); útil para depurar.
    local=False -> usa el clúster spark://spark-master:7077 (valores de spark-defaults.conf).
    cores_max   -> limita los cores totales de la aplicación (para experimentos de escalado).
    extra       -> diccionario con más opciones de configuración.
    """
    b = SparkSession.builder.appName(nombre)
    if local:
        b = b.master("local[*]")
    if cores_max:
        b = b.config("spark.cores.max", str(cores_max))
    if memoria_executor:
        b = b.config("spark.executor.memory", memoria_executor)
    for k, v in (extra or {}).items():
        b = b.config(k, v)
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def reiniciar_spark(spark, **kwargs):
    """Para la sesión actual y crea otra con nuevas opciones (p. ej. otro cores_max)."""
    spark.stop()
    time.sleep(2)
    return crear_spark(**kwargs)


@contextmanager
def cronometro(etiqueta, resultados=None):
    """Mide el tiempo de un bloque:
        with cronometro("csv", tiempos):
            df.count()
    Si se pasa un diccionario «resultados», guarda allí los segundos."""
    t0 = time.perf_counter()
    yield
    seg = time.perf_counter() - t0
    print(f"[{etiqueta}] {seg:.2f} s")
    if resultados is not None:
        resultados[etiqueta] = round(seg, 3)


def executors_vivos(spark):
    """Número de executors registrados en la aplicación (sin contar el driver)."""
    return spark.sparkContext._jsc.sc().getExecutorMemoryStatus().size() - 1


def sello(pareja):
    """Imprime un sello de evidencia (pareja, fecha y hora, equipo) para las capturas de la memoria.
    Ejecutadlo al principio del cuaderno y dejad visible su salida en las capturas."""
    import datetime
    import os
    import socket
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pc = os.environ.get("PC_ANFITRION", "desconocido")
    print(f"EVIDENCIA · Pareja {pareja} · {ahora} · PC {pc} · contenedor {socket.gethostname()}")
