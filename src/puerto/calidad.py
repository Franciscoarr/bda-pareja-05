"""Motor sencillo de reglas de CALIDAD DE DATOS para DataFrames de Spark (fase 3).

Idea: cada regla es una condición que una fila CORRECTA debe cumplir. El motor añade
a cada fila la lista de reglas que incumple (columna «_errores»), genera un informe
por regla y separa las filas válidas de las que van a CUARENTENA.

Ejemplo:
    from puerto import calidad as q
    reglas = [
        q.completitud("id_muelle", critica=True),
        q.rango("toneladas", 0, 400000, critica=True),
        q.unicidad(["id_escala"]),
        q.consistencia("atd_posterior_ata", F.col("atd") >= F.col("ata"), critica=True),
    ]
    marcado = q.evaluar(df, reglas)
    q.informe(marcado, reglas).show(truncate=False)
    validos, cuarentena = q.separar(marcado, reglas)

Dimensiones de calidad usadas: completitud, validez, exactitud, consistencia, unicidad, actualidad.
"""
from dataclasses import dataclass

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F


@dataclass
class Regla:
    nombre: str
    dimension: str
    condicion: Column          # True = la fila CUMPLE la regla
    critica: bool = False      # si se incumple, la fila va a cuarentena
    descripcion: str = ""


# ------------------------------------------------------------------ constructores de reglas
def completitud(col, critica=False):
    c = F.col(col)
    return Regla(f"completo_{col}", "completitud",
                 c.isNotNull() & (F.trim(c.cast("string")) != ""), critica, f"{col} no puede estar vacío")


def rango(col, minimo=None, maximo=None, critica=False):
    c = F.col(col)
    cond = F.lit(True)
    if minimo is not None:
        cond = cond & (c >= minimo)
    if maximo is not None:
        cond = cond & (c <= maximo)
    return Regla(f"rango_{col}", "validez", cond, critica, f"{col} entre {minimo} y {maximo}")


def en_conjunto(col, valores, critica=False):
    return Regla(f"dominio_{col}", "validez", F.col(col).isin(list(valores)), critica,
                 f"{col} debe ser uno de {sorted(valores)}")


def patron(col, regex, critica=False):
    return Regla(f"formato_{col}", "validez", F.col(col).rlike(regex), critica, f"{col} cumple {regex}")


def unicidad(cols, critica=False):
    """Marca como error la 2.ª, 3.ª... aparición de la misma clave (la primera se conserva)."""
    w = Window.partitionBy(*[F.col(c) for c in cols]).orderBy(F.monotonically_increasing_id())
    return Regla("unico_" + "_".join(cols), "unicidad", F.row_number().over(w) == 1, critica,
                 f"clave única {cols}")


def consistencia(nombre, condicion, critica=False, descripcion=""):
    return Regla(nombre, "consistencia", condicion, critica, descripcion)


def personalizada(nombre, dimension, condicion, critica=False, descripcion=""):
    return Regla(nombre, dimension, condicion, critica, descripcion)


# ------------------------------------------------------------------ evaluación
def evaluar(df: DataFrame, reglas) -> DataFrame:
    """Añade la columna _errores (array con los nombres de las reglas incumplidas)."""
    marcas = [F.when(~F.coalesce(r.condicion, F.lit(False)), F.lit(r.nombre)) for r in reglas]
    return df.withColumn("_errores", F.filter(F.array(*marcas), lambda x: x.isNotNull()))


def informe(marcado: DataFrame, reglas) -> DataFrame:
    """Una fila por regla: filas que la incumplen y porcentaje."""
    total = marcado.count()
    aggs = [F.sum(F.when(F.array_contains("_errores", r.nombre), 1).otherwise(0)).alias(r.nombre) for r in reglas]
    cuentas = marcado.agg(*aggs).collect()[0].asDict()
    spark = marcado.sparkSession
    filas = [(r.nombre, r.dimension, r.critica, int(cuentas[r.nombre] or 0),
              round(100.0 * (cuentas[r.nombre] or 0) / total, 3) if total else 0.0, r.descripcion) for r in reglas]
    return spark.createDataFrame(filas, "regla string, dimension string, critica boolean, filas_ko long, "
                                        "pct_ko double, descripcion string").orderBy(F.desc("filas_ko"))


def separar(marcado: DataFrame, reglas):
    """Devuelve (validos, cuarentena). Van a cuarentena las filas que incumplen alguna regla CRÍTICA."""
    criticas = [r.nombre for r in reglas if r.critica]
    if not criticas:
        return marcado.drop("_errores"), marcado.limit(0)
    falla = F.lit(False)
    for n in criticas:
        falla = falla | F.array_contains("_errores", n)
    cuarentena = marcado.filter(falla).withColumn("_motivo", F.array_join("_errores", ","))
    validos = marcado.filter(~falla).drop("_errores")
    return validos, cuarentena.drop("_errores")


def puntuacion(informe_df: DataFrame) -> float:
    """Índice de calidad 0-100: 100 menos la media de % de error de las reglas."""
    media = informe_df.agg(F.avg("pct_ko")).collect()[0][0] or 0.0
    return round(100.0 - media, 2)


# ------------------------------------------------------------------ perfilado
def perfil(df: DataFrame, max_columnas=40) -> DataFrame:
    """Perfil rápido: nulos, % nulos y valores distintos (aprox.) por columna."""
    cols = df.columns[:max_columnas]
    total = df.count()
    exprs = []
    for c in cols:
        exprs.append(F.sum(F.when(F.col(c).isNull() | (F.trim(F.col(c).cast("string")) == ""), 1).otherwise(0)).alias(f"n__{c}"))
        exprs.append(F.approx_count_distinct(F.col(c)).alias(f"d__{c}"))
    r = df.agg(*exprs).collect()[0].asDict()
    filas = [(c, dict(df.dtypes)[c], int(r[f"n__{c}"]), round(100.0 * r[f"n__{c}"] / total, 2) if total else 0.0,
              int(r[f"d__{c}"])) for c in cols]
    return df.sparkSession.createDataFrame(filas, "columna string, tipo string, nulos long, pct_nulos double, distintos_aprox long")
