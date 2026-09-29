"""Dígitos de control de identificadores marítimos (fase 3: validez de los datos).

ISO 6346 (contenedores): 3 letras de propietario + categoría (U, J o Z) + 6 dígitos + dígito de control.
    Ejemplo válido: CSQU3054383
IMO (buques): 7 dígitos; el último es  (d1*7 + d2*6 + d3*5 + d4*4 + d5*3 + d6*2) mod 10.
    Ejemplo válido: 9074729
"""
import re

_VAL = {}
_v = 10
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    if _v % 11 == 0:          # se saltan 11, 22 y 33
        _v += 1
    _VAL[_c] = _v
    _v += 1

_PATRON_CONT = re.compile(r"^[A-Z]{3}[UJZ][0-9]{7}$")


def digito_iso6346(primeros10):
    total = sum((_VAL[c] if c.isalpha() else int(c)) * (2 ** i) for i, c in enumerate(primeros10))
    return (total % 11) % 10


def contenedor_valido(codigo):
    """True si el código de contenedor tiene formato y dígito de control correctos."""
    if codigo is None:
        return False
    codigo = codigo.strip().upper()
    if not _PATRON_CONT.match(codigo):
        return False
    return digito_iso6346(codigo[:10]) == int(codigo[10])


def imo_valido(imo):
    """True si el número IMO (7 dígitos) tiene el dígito de control correcto."""
    if imo is None:
        return False
    s = str(imo).strip().upper().replace("IMO", "").strip()
    if not re.fullmatch(r"[0-9]{7}", s):
        return False
    return sum(int(d) * w for d, w in zip(s[:6], range(7, 1, -1))) % 10 == int(s[6])


def registrar_udfs(spark):
    """Registra las funciones como UDF de Spark SQL: contenedor_valido(col), imo_valido(col)."""
    from pyspark.sql.types import BooleanType
    spark.udf.register("contenedor_valido", contenedor_valido, BooleanType())
    spark.udf.register("imo_valido", imo_valido, BooleanType())
