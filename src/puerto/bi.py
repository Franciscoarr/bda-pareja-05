"""Carga del almacén de datos en PostgreSQL (fase 5).

    from puerto import bi
    bi.ejecutar_sql("TRUNCATE dw.fact_facturacion, dw.dim_cliente, dw.dim_servicio, dw.dim_fecha CASCADE")
    bi.cargar(dim_fecha_df, "dw.dim_fecha")          # modo append: respeta el esquema creado en SQL
    bi.leer(spark, "dw.v_kpi_facturacion_mensual").show()

Orden de carga: primero dimensiones, después hechos (por las claves foráneas).
"""
from datetime import date, timedelta

JDBC_URL = "jdbc:postgresql://postgres:5432/puerto_dw"
PROPIEDADES = {"user": "bda", "password": "bda2027", "driver": "org.postgresql.Driver"}
PG = dict(host="postgres", port=5432, dbname="puerto_dw", user="bda", password="bda2027")


def ejecutar_sql(sql):
    """Ejecuta SQL directamente en PostgreSQL (DDL, TRUNCATE, vistas...)."""
    import psycopg2
    with psycopg2.connect(**PG) as con:
        with con.cursor() as cur:
            cur.execute(sql)
            try:
                return cur.fetchall()
            except psycopg2.ProgrammingError:
                return None


def cargar(df, tabla, modo="append", lote=5000):
    """Escribe un DataFrame de Spark en una tabla de PostgreSQL por JDBC.
    OJO: modo «overwrite» BORRA y recrea la tabla (se pierden claves y vistas). Usad TRUNCATE + append."""
    (df.write.mode(modo).option("batchsize", lote)
       .jdbc(JDBC_URL, tabla, properties=PROPIEDADES))


def leer(spark, tabla_o_consulta):
    """Lee una tabla o una consulta: leer(spark, "(SELECT ...) AS t")."""
    return spark.read.jdbc(JDBC_URL, tabla_o_consulta, properties=PROPIEDADES)


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def dim_fecha(spark, inicio=date(2024, 1, 1), fin=date(2025, 12, 31)):
    """Genera la dimensión fecha completa como DataFrame de Spark."""
    filas = []
    d = inicio
    while d <= fin:
        filas.append((int(d.strftime("%Y%m%d")), d, d.year, (d.month - 1) // 3 + 1, d.month, MESES[d.month - 1],
                      d.isoweekday(), d.isoweekday() >= 6, 2 <= d.month <= 5))
        d += timedelta(days=1)
    return spark.createDataFrame(filas, "id_fecha int, fecha date, anio short, trimestre short, mes short, "
                                        "nombre_mes string, dia_semana short, es_fin_semana boolean, campana_fruta boolean")
