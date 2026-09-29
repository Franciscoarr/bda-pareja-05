"""Tratamiento de texto no estructurado (fase 5): normalización y sentimiento por léxico.

En Spark se recomienda NO usar funciones Python fila a fila (UDF) si se puede evitar:
    df_norm = df.withColumn("texto_norm", normalizar_col("texto"))
    tokens  = df_norm.select("id_post", F.explode(F.split("texto_norm", r"\\s+")).alias("palabra"))
    lexico  = spark.read.csv("/datos/lexico/sentimiento_es.csv", header=True, inferSchema=True)
    sent    = tokens.join(lexico, "palabra").groupBy("id_post").agg(F.sum("polaridad").alias("sentimiento"))
"""
import csv
import os
import re
import unicodedata

CON_TILDE = "áéíóúüñàèìòùâêîôû"
SIN_TILDE = "aeiouunaeiouaeiou"

STOPWORDS = set("""a al algo ante con contra de del desde el en entre es esta este esto hacia hasta la las le les lo los
mas me mi muy nos o para pero por que se si sin sobre su sus tambien te tu un una uno unos unas y ya hoy
otra otro vez nuestro nuestra estamos esta estan ha han hay fue ser son como cuando donde""".split())


def normalizar(texto):
    """Minúsculas, sin tildes, sin hashtags/menciones/URL/puntuación, espacios simples (Python puro)."""
    if texto is None:
        return ""
    t = texto.lower()
    t = re.sub(r"https?://\S+|[#@]\w+", " ", t)
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9ñ ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normalizar_col(col):
    """Lo mismo que normalizar() pero con funciones nativas de Spark (sin UDF)."""
    from pyspark.sql import functions as F
    c = F.lower(F.col(col) if isinstance(col, str) else col)
    c = F.regexp_replace(c, r"https?://\S+|[#@]\w+", " ")
    c = F.translate(c, CON_TILDE, SIN_TILDE)
    c = F.regexp_replace(c, r"[^a-z0-9 ]", " ")
    return F.trim(F.regexp_replace(c, r"\s+", " "))


def tokens(texto, quitar_stopwords=True):
    ts = normalizar(texto).split()
    return [t for t in ts if not (quitar_stopwords and t in STOPWORDS)]


def cargar_lexico(ruta=None):
    ruta = ruta or ("/datos/lexico/sentimiento_es.csv" if os.path.exists("/datos") else
                    os.path.join(os.path.dirname(__file__), "..", "..", "datos", "lexico", "sentimiento_es.csv"))
    with open(ruta, encoding="utf-8") as f:
        return {fila["palabra"]: int(fila["polaridad"]) for fila in csv.DictReader(f)}


def sentimiento(texto, lexico):
    """Suma de polaridades de las palabras del texto (>0 positivo, <0 negativo, 0 neutro)."""
    return sum(lexico.get(t, 0) for t in tokens(texto, quitar_stopwords=False))
