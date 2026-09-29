"""Paquete de apoyo del proyecto «Plataforma de datos del Puerto de Huelva».

Módulos:
    sesion     crear la SparkSession conectada al clúster y medir tiempos
    hdfs_web   consultar HDFS por WebHDFS desde Python (listar, tamaños, réplicas, checksum, fsck)
    validacion dígitos de control ISO 6346 (contenedores) e IMO (buques)
    calidad    motor sencillo de reglas de calidad de datos para DataFrames de Spark (fase 3)
    texto      normalización de texto y sentimiento por léxico (fase 5)
    bi         carga en PostgreSQL por JDBC (fase 5)
    metricas   consultas a la API de Prometheus (fase 4)
"""
__version__ = "2026.1"
