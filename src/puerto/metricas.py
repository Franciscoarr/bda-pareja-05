"""Consultas a la API HTTP de Prometheus desde Python (fase 4).

    from puerto import metricas as m
    m.valor("bda_hdfs_datanodes_vivos")
    df = m.serie("rate(metrics_worker_coresUsed_Value[1m])", minutos=30)   # pandas DataFrame
    m.alertas()
"""
import time

import requests

PROMETHEUS = "http://prometheus:9090"


def consulta(expr):
    r = requests.get(f"{PROMETHEUS}/api/v1/query", params={"query": expr}, timeout=15)
    r.raise_for_status()
    return r.json()["data"]["result"]


def valor(expr):
    """Valor actual (float) de una expresión que devuelve una sola serie; None si no hay datos."""
    res = consulta(expr)
    return float(res[0]["value"][1]) if res else None


def serie(expr, minutos=30, paso="15s"):
    """Serie temporal de los últimos «minutos» como DataFrame de pandas (una columna por serie)."""
    import pandas as pd
    fin = time.time()
    r = requests.get(f"{PROMETHEUS}/api/v1/query_range",
                     params={"query": expr, "start": fin - minutos * 60, "end": fin, "step": paso}, timeout=30)
    r.raise_for_status()
    columnas = {}
    for s in r.json()["data"]["result"]:
        nombre = ",".join(f"{k}={v}" for k, v in s["metric"].items() if k != "__name__") or expr
        columnas[nombre] = pd.Series({pd.to_datetime(t, unit="s"): float(v) for t, v in s["values"]})
    return pd.DataFrame(columnas)


def alertas():
    r = requests.get(f"{PROMETHEUS}/api/v1/alerts", timeout=15)
    r.raise_for_status()
    return [{"alerta": a["labels"].get("alertname"), "estado": a["state"], "desde": a.get("activeAt"),
             "severidad": a["labels"].get("severidad")} for a in r.json()["data"]["alerts"]]


def objetivos():
    r = requests.get(f"{PROMETHEUS}/api/v1/targets", timeout=15)
    r.raise_for_status()
    return [{"job": t["labels"].get("job"), "instancia": t["labels"].get("instance"), "salud": t["health"],
             "ultimo_error": t.get("lastError", "")} for t in r.json()["data"]["activeTargets"]]
