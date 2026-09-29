#!/usr/bin/env python3
"""
Generador de datos SIMULADOS del proyecto «Plataforma de datos del Puerto de Huelva».

Todos los datos son ficticios: buques, navieras, clientes, competidores y textos
se generan al azar con una semilla fija, de modo que todas las parejas obtienen
EXACTAMENTE los mismos ficheros si usan la misma escala y semilla.

Solo usa la biblioteca estándar de Python (funciona dentro del contenedor
«jupyter» y también en cualquier Python 3.9+ del PC).

Uso (dentro del contenedor):
    python /workspace/datos/generador/generar_datos.py --escala 1
Opciones:
    --escala  factor de volumen (0.05 = prueba rápida, 1 = clase, 3 = «grande»)
    --semilla semilla aleatoria (por defecto 2026)
    --salida  carpeta de salida (por defecto /datos/raw o ../raw)

Salida (carpeta raw/):
    maestros/   muelles.csv, navieras.csv, buques.csv
    escalas/    escalas_2024.csv, escalas_2025.csv
    ais/        ais_AAAA-MM-DD.jsonl   (un fichero por día)
    sensores/   sensores_AAAA-MM-DD.csv (un fichero por día)
    contenedores/ movimientos_2025.csv
    negocio/    clientes.csv, servicios.csv, facturas_2024.csv, facturas_2025.csv,
                tipos_cambio.csv, campanas_marketing.csv, competencia.csv,
                encuestas_satisfaccion.csv, redes_sociales.jsonl, incidencias.jsonl
    MANIFIESTO.sha256  (huella SHA-256 de cada fichero, formato sha256sum)

Los datos incluyen ERRORES INTENCIONADOS (duplicados, nulos, unidades mezcladas,
fechas en varios formatos, dígitos de control inválidos, líneas JSON rotas...)
que se trabajan en las fases 3 (integridad/calidad) y 5 (BI).
"""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta, date

# ---------------------------------------------------------------------------
# Utilidades de validación (también en src/puerto/*.py)
# ---------------------------------------------------------------------------
_ISO_VAL = {}
_v = 10
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    if _v % 11 == 0:
        _v += 1
    _ISO_VAL[_c] = _v
    _v += 1


def iso6346_digito(codigo10):
    """Dígito de control ISO 6346 para los 10 primeros caracteres (ej. 'MSKU123456')."""
    total = 0
    for i, ch in enumerate(codigo10):
        val = _ISO_VAL[ch] if ch.isalpha() else int(ch)
        total += val * (2 ** i)
    return (total % 11) % 10


def miles(n):
    return f"{n:,}".replace(",", ".")


def imo_digito(seis):
    """Dígito de control IMO para los 6 primeros dígitos."""
    return sum(int(d) * w for d, w in zip(seis, range(7, 1, -1))) % 10


# ---------------------------------------------------------------------------
# Catálogos (ficticios)
# ---------------------------------------------------------------------------
MUELLES = [
    # id, nombre, tipo, calado_max_m, longitud_m, lat, lon, gruas
    ("M01", "Muelle Sur", "contenedores", 14.0, 750, 37.1405, -6.9340, ["GRUA-01", "GRUA-02", "GRUA-03", "GRUA-04"]),
    ("M02", "Muelle Levante", "granel_solido", 13.0, 600, 37.1530, -6.9290, ["GRUA-05"]),
    ("M03", "Muelle de Minerales", "granel_solido", 12.0, 450, 37.1575, -6.9255, ["GRUA-06"]),
    ("M04", "Pantalán Petrolero", "granel_liquido", 16.0, 400, 37.1320, -6.9420, []),
    ("M05", "Muelle de Inflamables", "granel_liquido", 12.5, 350, 37.1360, -6.9395, []),
    ("M06", "Terminal de GNL", "granel_liquido", 13.5, 380, 37.1290, -6.9470, []),
    ("M07", "Muelle Ro-Ro", "ro_ro", 10.0, 300, 37.1620, -6.9230, []),
    ("M08", "Muelle Frigorífico", "fruta_refrigerada", 11.0, 320, 37.1480, -6.9310, ["GRUA-02"]),
    ("M09", "Muelle de Cruceros", "pasajeros", 11.5, 350, 37.2530, -6.9530, []),
    ("M10", "Muelle Pesquero", "pesca", 7.0, 400, 37.2500, -6.9480, []),
    ("M11", "Muelle Multiusos Norte", "carga_general", 10.5, 280, 37.1650, -6.9215, ["GRUA-05"]),
    ("M12", "Muelle Químico", "granel_liquido", 12.0, 300, 37.1400, -6.9370, []),
]
FONDEO = (37.0600, -6.9800)      # zona de fondeo (espera) en la bahía
ENTRADA_MAR = (36.9500, -7.0500)  # punto de aproximación desde alta mar

TIPOS_BUQUE = {
    "contenedores": ("Portacontenedores", (9000, 60000), (140, 300)),
    "granel_solido": ("Granelero", (15000, 45000), (150, 230)),
    "granel_liquido": ("Petrolero/Quimiquero", (8000, 80000), (110, 250)),
    "ro_ro": ("Ro-Ro", (10000, 30000), (140, 200)),
    "fruta_refrigerada": ("Frigorífico", (5000, 15000), (110, 160)),
    "pasajeros": ("Crucero", (40000, 140000), (200, 330)),
    "pesca": ("Pesquero", (200, 1500), (25, 60)),
    "carga_general": ("Carga general", (3000, 12000), (90, 140)),
}
MERCANCIAS = {
    "contenedores": ["Contenedores"],
    "granel_solido": ["Concentrado de cobre", "Fertilizantes", "Cereal", "Pirita", "Clínker"],
    "granel_liquido": ["Crudo", "Gasóleo", "GNL", "Ácido sulfúrico", "Productos químicos", "Biocombustible"],
    "ro_ro": ["Vehículos", "Semirremolques"],
    "fruta_refrigerada": ["Fresa y frutos rojos", "Cítricos", "Fruta tropical"],
    "pasajeros": ["Pasajeros"],
    "pesca": ["Pescado fresco"],
    "carga_general": ["Maquinaria", "Madera", "Bobinas de acero", "Palés"],
}
PESO_TIPO = {  # frecuencia relativa de escalas
    "granel_liquido": 30, "granel_solido": 22, "contenedores": 13, "carga_general": 8,
    "ro_ro": 7, "fruta_refrigerada": 9, "pasajeros": 3, "pesca": 8,
}
PUERTOS = ["Rotterdam", "Algeciras", "Las Palmas", "Tánger Med", "Casablanca", "Lisboa", "Sines",
           "Santos", "Houston", "Amberes", "Génova", "Valencia", "Santa Cruz de Tenerife",
           "Funchal", "Dakar", "Ceuta", "Hamburgo", "Le Havre", "Nueva York", "Abiyán"]
MID_BANDERA = [("224", "España"), ("255", "Portugal (Madeira)"), ("636", "Liberia"), ("538", "Islas Marshall"),
               ("352", "Panamá"), ("215", "Malta"), ("244", "Países Bajos"), ("249", "Malta"),
               ("371", "Panamá"), ("209", "Chipre")]

PAL_A = ["Atlantic", "Iberian", "Blue", "Southern", "Ocean", "Golden", "Nordic", "Aurora", "Delta",
         "Costa", "Silver", "Marisma", "Odiel", "Tinto", "Luz", "Punta", "Cabo", "Estrella", "Doña", "Río"]
PAL_B = ["Spirit", "Trader", "Carrier", "Pioneer", "Wave", "Horizon", "Breeze", "Express", "Star",
         "Voyager", "Mar", "Navigator", "Pride", "Glory", "Venture", "Sol", "Marina", "Bay", "Fortune", "Dawn"]
NAV_A = ["Atlántica", "Odiel", "Tinto", "Iberia", "Blue Wave", "Southern Cross", "Delta", "Nordsee",
         "Mare Nostrum", "Costa de la Luz", "Levante", "Poniente", "Gran Sol", "Cabo Verde", "Alborán",
         "Guadiana", "Estrecho", "Azores", "Canarias", "Bética"]
NAV_B = ["Shipping", "Lines", "Naviera", "Maritime", "Carriers"]
CLI_A = ["Agro", "Frutas", "Química", "Minera", "Logística", "Transitarios", "Energía", "Fertilizantes",
         "Cobre", "Berries", "Aceites", "Maderas", "Graneles", "Conservas", "Automoción", "Cementos"]
CLI_B = ["del Odiel", "Onubense", "del Condado", "Costa Luz", "Andévalo", "Doñana", "Marismas",
         "Tinto", "Aljaraque", "Palos", "Moguer", "Lepe", "Cartaya", "Ayamonte", "Niebla", "Almonte"]
CLI_C = ["S.L.", "S.A.", "Coop.", "S.L.U."]
# cantidad típica por unidad de facturación: (mu, sigma) de una lognormal, o (mín, máx) enteros
CANTIDAD_UNIDAD = {"TEU": (4.5, 0.8), "TEU-día": (6.0, 0.8), "contenedor-día": (3.5, 0.7), "t": (5.8, 1.0),
                   "t-mes": (7.3, 0.8), "m3-mes": (7.3, 0.8), "unidad": (4.8, 0.6), "contenedor": (3.5, 0.7),
                   "expediente": (1, 4), "escala": (1, 1), "hora": (2, 16)}
COMERCIALES = ["C01-Marta", "C02-Javier", "C03-Lucía", "C04-Andrés", "C05-Rocío"]


class Gen:
    def __init__(self, escala, semilla, salida):
        self.escala = escala
        self.r = random.Random(semilla)
        self.salida = salida
        self.inicio_ais = date(2025, 6, 1)
        self.dias_ais = max(3, int(round(60 * escala)))
        self.buques = []
        self.navieras = []
        self.escalas = []
        self.clientes = []
        self.servicios = []

    # ---------------------------------------------------------- utilidades
    def ruta(self, *partes):
        p = os.path.join(self.salida, *partes)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    # ---------------------------------------------------------- maestros
    def maestros(self):
        r = self.r
        with open(self.ruta("maestros", "muelles.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id_muelle", "nombre", "tipo", "calado_max_m", "longitud_m", "lat", "lon", "gruas"])
            for m in MUELLES:
                w.writerow([m[0], m[1], m[2], m[3], m[4], m[5], m[6], "|".join(m[7])])

        usados = set()
        for i in range(40):
            while True:
                n = f"{r.choice(NAV_A)} {r.choice(NAV_B)}"
                if n not in usados:
                    usados.add(n)
                    break
            pais = r.choice(["España", "Portugal", "Países Bajos", "Grecia", "Dinamarca", "Italia", "Marruecos", "Noruega"])
            self.navieras.append({"id_naviera": f"NAV{i+1:03d}", "nombre": n, "pais": pais,
                                  "flota": r.randint(3, 120)})
        with open(self.ruta("maestros", "navieras.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(self.navieras[0].keys()))
            w.writeheader()
            w.writerows(self.navieras)

        tipos = list(PESO_TIPO.keys())
        pesos = [PESO_TIPO[t] for t in tipos]
        usados = set()
        for i in range(320):
            t = r.choices(tipos, weights=pesos)[0]
            desc, (gt0, gt1), (e0, e1) = TIPOS_BUQUE[t]
            while True:
                nombre = f"{r.choice(PAL_A)} {r.choice(PAL_B)}"
                if r.random() < 0.3:
                    nombre += " " + r.choice(["I", "II", "III", "IV", "V"])
                if nombre not in usados:
                    usados.add(nombre)
                    break
            seis = f"{r.randint(900000, 999999)}"
            imo = seis + str(imo_digito(seis))
            mid, bandera = r.choice(MID_BANDERA)
            mmsi = mid + f"{r.randint(0, 999999):06d}"
            gt = r.randint(gt0, gt1)
            eslora = round(r.uniform(e0, e1), 1)
            self.buques.append({
                "imo": imo, "mmsi": mmsi, "nombre": nombre, "tipo": t, "descripcion_tipo": desc,
                "gt": gt, "eslora_m": eslora, "manga_m": round(eslora * r.uniform(0.13, 0.17), 1),
                "calado_m": round(min(15.5, 4 + eslora / 25 + r.uniform(-1, 1)), 1),
                "bandera": bandera, "id_naviera": r.choice(self.navieras)["id_naviera"],
            })
        with open(self.ruta("maestros", "buques.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(self.buques[0].keys()))
            w.writeheader()
            for b in self.buques:
                fila = dict(b)
                if r.random() < 0.02:          # IMO con dígito de control erróneo
                    fila["imo"] = b["imo"][:6] + str((int(b["imo"][6]) + 3) % 10)
                w.writerow(fila)
        self.log(f"maestros: {len(MUELLES)} muelles, {len(self.navieras)} navieras, {len(self.buques)} buques")

    # ---------------------------------------------------------- escalas
    def _espera_horas(self, tipo, dt):
        """Horas de espera en fondeo. Historia: congestión de contenedores en 2025-T3."""
        r = self.r
        base = {"contenedores": 5, "granel_liquido": 7, "granel_solido": 9, "ro_ro": 2,
                "fruta_refrigerada": 3, "pasajeros": 0.3, "pesca": 0.2, "carga_general": 6}[tipo]
        if tipo == "contenedores" and dt.year == 2025 and dt.month in (7, 8, 9, 10):
            base *= 2.8           # avería GRUA-04 + congestión
        if tipo == "fruta_refrigerada" and dt.month in (2, 3, 4, 5):
            base *= 1.4           # campaña de frutos rojos
        if dt.year == 2025 and dt.month == 9 and 8 <= dt.day <= 12:
            base += 30            # huelga de estiba (ficticia)
        return max(0.0, r.expovariate(1 / base) if base > 0 else 0.0)

    def escalas_gen(self):
        r = self.r
        n = max(200, int(6500 * self.escala))
        t0 = datetime(2024, 1, 1)
        span = (datetime(2025, 12, 31, 23, 0) - t0).total_seconds()
        muelles_por_tipo = {}
        for m in MUELLES:
            muelles_por_tipo.setdefault(m[2], []).append(m[0])
        buques_por_tipo = {}
        for b in self.buques:
            buques_por_tipo.setdefault(b["tipo"], []).append(b)
        tipos = list(PESO_TIPO.keys())
        pesos = [PESO_TIPO[t] for t in tipos]
        filas = []
        for i in range(n):
            t = r.choices(tipos, weights=pesos)[0]
            # estacionalidad: fruta en feb-may; cruceros en primavera/otoño
            eta = t0 + timedelta(seconds=r.random() * span)
            if t == "fruta_refrigerada" and r.random() < 0.65:
                eta = datetime(r.choice([2024, 2025]), r.randint(2, 5), r.randint(1, 28), r.randint(0, 23))
            b = r.choice(buques_por_tipo.get(t) or self.buques)
            muelle = r.choice(muelles_por_tipo[t])
            espera = self._espera_horas(t, eta)
            ata = eta + timedelta(hours=espera)
            estancia = {"contenedores": 22, "granel_liquido": 30, "granel_solido": 48, "ro_ro": 12,
                        "fruta_refrigerada": 26, "pasajeros": 9, "pesca": 6, "carga_general": 30}[t]
            atd = ata + timedelta(hours=max(2, r.gauss(estancia, estancia * 0.3)))
            if t == "contenedores":
                teu = int(max(50, r.gauss(900, 350)))
                ton = round(teu * r.uniform(9, 14), 1)
            elif t == "pasajeros":
                teu, ton = 0, 0.0
            elif t == "pesca":
                teu, ton = 0, round(r.uniform(5, 80), 1)
            else:
                teu = 0
                ton = round(b["gt"] * r.uniform(0.6, 1.3), 1)
            filas.append({
                "id_escala": f"ESC-{eta.year}-{i+1:06d}",
                "imo": b["imo"], "buque": b["nombre"], "id_naviera": b["id_naviera"],
                "id_muelle": muelle, "tipo_trafico": t,
                "operacion": r.choice(["descarga", "carga", "mixta"]),
                "mercancia": r.choice(MERCANCIAS[t]), "toneladas": ton, "teu": teu,
                "eta": eta, "ata": ata, "atd": atd,
                "origen": r.choice(PUERTOS), "destino": r.choice(PUERTOS),
                "practicaje": "S" if b["eslora_m"] > 80 else r.choice(["S", "N"]),
                "pasajeros": int(r.uniform(900, 4200)) if t == "pasajeros" else 0,
            })
        filas.sort(key=lambda x: x["eta"])
        self.escalas = filas

        cols = ["id_escala", "imo", "buque", "id_naviera", "id_muelle", "tipo_trafico", "operacion",
                "mercancia", "toneladas", "teu", "eta", "ata", "atd", "origen", "destino",
                "practicaje", "pasajeros"]
        por_anio = {2024: [], 2025: []}
        for e in filas:
            por_anio[e["eta"].year].append(e)
        sucias = 0
        for anio, lista in por_anio.items():
            with open(self.ruta("escalas", f"escalas_{anio}.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(cols)
                for e in lista:
                    fila = dict(e)
                    fmt = "%Y-%m-%d %H:%M:%S"
                    fila["eta"], fila["ata"], fila["atd"] = (e["eta"].strftime(fmt), e["ata"].strftime(fmt),
                                                            e["atd"].strftime(fmt))
                    x = r.random()
                    if x < 0.03:                        # fecha en formato español
                        fila["ata"] = e["ata"].strftime("%d/%m/%Y %H:%M")
                        sucias += 1
                    elif x < 0.04:                      # muelle nulo
                        fila["id_muelle"] = ""
                        sucias += 1
                    elif x < 0.045:                     # salida anterior a la llegada
                        fila["atd"] = (e["ata"] - timedelta(hours=r.randint(1, 10))).strftime(fmt)
                        sucias += 1
                    elif x < 0.055 and e["toneladas"] > 0:  # toneladas registradas en kg
                        fila["toneladas"] = round(e["toneladas"] * 1000, 0)
                        sucias += 1
                    elif x < 0.075:                     # nombre de buque con mayúsculas/espacios
                        fila["buque"] = "  " + e["buque"].upper() + " "
                        sucias += 1
                    elif x < 0.077:
                        fila["toneladas"] = -abs(e["toneladas"])
                        sucias += 1
                    w.writerow([fila[c] for c in cols])
                    if r.random() < 0.015:              # duplicado exacto
                        w.writerow([fila[c] for c in cols])
                        sucias += 1
        self.log(f"escalas: {len(filas)} (+{sucias} filas con defectos intencionados)")

    # ---------------------------------------------------------- AIS
    def ais(self):
        r = self.r
        mmsi_por_imo = {b["imo"]: b["mmsi"] for b in self.buques}
        coord_muelle = {m[0]: (m[5], m[6]) for m in MUELLES}
        total = 0
        d0 = datetime.combine(self.inicio_ais, datetime.min.time())
        d1 = d0 + timedelta(days=self.dias_ais)
        activas = [e for e in self.escalas if e["atd"] > d0 - timedelta(hours=6) and e["eta"] < d1]

        def interp(p, q, f):
            return p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f

        def rumbo(p, q):
            ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
            return round((ang + 360) % 360, 1)

        # pre-calcular trayectorias por escala: tramos (inicio, fin, desde, hasta, estado)
        trayectos = []
        for e in activas:
            mmsi = mmsi_por_imo.get(e["imo"])
            muelle = e["id_muelle"] or "M01"
            dest = coord_muelle[muelle]
            fondeo = (FONDEO[0] + r.uniform(-0.01, 0.01), FONDEO[1] + r.uniform(-0.015, 0.015))
            llegada_bahia = e["eta"] - timedelta(hours=2)
            tramos = [
                (llegada_bahia, e["eta"], ENTRADA_MAR, fondeo, 0),
                (e["eta"], e["ata"] - timedelta(minutes=45), fondeo, fondeo, 1),
                (e["ata"] - timedelta(minutes=45), e["ata"], fondeo, dest, 0),
                (e["ata"], e["atd"], dest, dest, 5),
                (e["atd"], e["atd"] + timedelta(hours=2), dest, ENTRADA_MAR, 0),
            ]
            trayectos.append((mmsi, tramos))

        for dia in range(self.dias_ais):
            ini = d0 + timedelta(days=dia)
            fin = ini + timedelta(days=1)
            nombre = f"ais_{ini.date().isoformat()}.jsonl"
            n_dia = 0
            with open(self.ruta("ais", nombre), "w", encoding="utf-8") as f:
                for mmsi, tramos in trayectos:
                    for (a, b, p, q, estado) in tramos:
                        if b <= ini or a >= fin or b <= a:
                            continue
                        paso = 20 if estado == 0 else 180   # navegando: cada 20 s; parado: 3 min
                        t = max(a, ini)
                        dur = (b - a).total_seconds()
                        while t < min(b, fin):
                            fr = (t - a).total_seconds() / dur
                            lat, lon = interp(p, q, fr)
                            lat += r.gauss(0, 0.00015)
                            lon += r.gauss(0, 0.00015)
                            if estado == 0:
                                sog = round(max(0.5, r.gauss(9.5, 1.5)), 1)
                                cog = rumbo(p, q)
                            else:
                                sog = round(abs(r.gauss(0.1, 0.1)), 1)
                                cog = round(r.uniform(0, 359.9), 1)
                            reg = {"mmsi": mmsi, "ts": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "lat": round(lat, 5), "lon": round(lon, 5), "sog": sog, "cog": cog,
                                   "estado_nav": estado, "estacion": r.choice(["AIS-HUE-1", "AIS-HUE-2"])}
                            x = r.random()
                            if x < 0.003:
                                reg["lat"], reg["lon"] = 91.0, 181.0       # posición no disponible
                            elif x < 0.004:
                                reg["lat"], reg["lon"] = 0.0, 0.0          # «Null Island»
                            linea = json.dumps(reg, separators=(",", ":"))
                            if r.random() < 0.001:
                                linea = linea[: r.randint(10, len(linea) - 5)]  # línea truncada
                            f.write(linea + "\n")
                            n_dia += 1
                            if r.random() < 0.005:                         # duplicado de estación
                                f.write(linea + "\n")
                                n_dia += 1
                            t += timedelta(seconds=paso + r.randint(0, 10))
                # tráfico de paso (sin escala): barcos que cruzan por fuera de la bahía
                for k in range(r.randint(8, 15)):
                    mmsi = f"{r.choice(MID_BANDERA)[0]}{r.randint(0, 999999):06d}"
                    p = (36.90 + r.uniform(-0.05, 0.05), -7.30)
                    q = (36.85 + r.uniform(-0.05, 0.05), -6.60)
                    a = ini + timedelta(seconds=r.randint(0, 80000))
                    for s in range(0, 3 * 3600, 30):
                        fr = s / (3 * 3600)
                        lat, lon = interp(p, q, fr)
                        tt = a + timedelta(seconds=s)
                        if tt >= fin:
                            break
                        f.write(json.dumps({"mmsi": mmsi, "ts": tt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                            "lat": round(lat, 5), "lon": round(lon, 5),
                                            "sog": round(r.gauss(13, 1), 1), "cog": rumbo(p, q),
                                            "estado_nav": 0, "estacion": "AIS-HUE-1"},
                                           separators=(",", ":")) + "\n")
                        n_dia += 1
            total += n_dia
        self.log(f"ais: {self.dias_ais} días, {miles(total)} posiciones")

    # ---------------------------------------------------------- sensores
    def sensores(self):
        r = self.r
        total = 0
        d0 = datetime.combine(self.inicio_ais, datetime.min.time())
        viento_base = 5.0
        for dia in range(self.dias_ais):
            ini = d0 + timedelta(days=dia)
            nombre = f"sensores_{ini.date().isoformat()}.csv"
            temp_en_f = (dia == min(12, self.dias_ais - 1))        # un día el sensor mide en ºF
            aire2_atascado = dia in (20, 21)                      # sensor «congelado»
            meteo_caido = (dia == min(30, self.dias_ais - 1))
            with open(self.ruta("sensores", nombre), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ts", "id_sensor", "variable", "valor", "unidad"])
                for minuto in range(24 * 60):
                    t = ini + timedelta(minutes=minuto)
                    ts = t.strftime("%Y-%m-%dT%H:%M:00+02:00")
                    h = t.hour + t.minute / 60
                    viento_base = max(0.5, viento_base + r.gauss(0, 0.15) + (6 - viento_base) * 0.01)
                    racha = viento_base + (8 if (dia % 17 == 5 and 12 <= t.hour <= 18) else 0)
                    temp = 22 + 7 * math.sin((h - 9) / 24 * 2 * math.pi) + r.gauss(0, 0.3)
                    filas = []
                    if not (meteo_caido and 6 <= t.hour < 12):
                        filas += [
                            ("METEO-01", "viento_vel", round(racha + r.gauss(0, 0.4), 2), "m/s"),
                            ("METEO-01", "viento_dir", round((250 + r.gauss(0, 25)) % 360, 0), "grados"),
                            ("METEO-01", "temperatura", round(temp * 9 / 5 + 32, 2) if temp_en_f else round(temp, 2),
                             "F" if temp_en_f else "C"),
                            ("METEO-01", "humedad", round(min(100, max(20, 65 - (temp - 22) * 2 + r.gauss(0, 3))), 1), "%"),
                            ("METEO-01", "presion", round(1016 + r.gauss(0, 1.2), 1), "hPa"),
                        ]
                    filas.append(("OLEAJE-01", "altura_ola", round(max(0.1, 0.4 + racha * 0.06 + r.gauss(0, 0.05)), 2), "m"))
                    for s, off in (("AIRE-01", 0), ("AIRE-02", 3)):
                        pico = 25 if (7 <= t.hour <= 9 or 18 <= t.hour <= 20) else 0
                        so2 = 8 + off + pico * 0.3 + r.gauss(0, 1.5)
                        no2 = 20 + off + pico + r.gauss(0, 3)
                        pm10 = 18 + off + racha * 0.8 + r.gauss(0, 2)
                        if s == "AIRE-02" and aire2_atascado:
                            so2, no2, pm10 = 11.0, 23.0, 21.0
                        filas += [(s, "so2", round(max(0, so2), 1), "ug/m3"), (s, "no2", round(max(0, no2), 1), "ug/m3"),
                                  (s, "pm10", round(max(0, pm10), 1), "ug/m3")]
                    if minuto % 5 == 0:
                        for g in range(1, 7):
                            gid = f"GRUA-{g:02d}"
                            trabajando = 7 <= t.hour < 23 and racha < 14 and r.random() < 0.8
                            carga = round(r.uniform(8, 38), 1) if trabajando else 0.0
                            vib = 2.0 + (carga / 20) + r.gauss(0, 0.3)
                            if gid == "GRUA-04":            # degradación progresiva (mantenimiento predictivo)
                                vib += dia * 0.08
                            tmot = 45 + carga * 0.6 + r.gauss(0, 1.5) + (dia * 0.15 if gid == "GRUA-04" else 0)
                            filas += [(gid, "carga", carga, "t"), (gid, "vibracion", round(max(0, vib), 2), "mm/s"),
                                      (gid, "temp_motor", round(tmot, 1), "C")]
                    for (sid, var, val, uni) in filas:
                        if r.random() < 0.0008:
                            val = -999                       # valor centinela de error
                        w.writerow([ts, sid, var, val, uni])
                        total += 1
                        if r.random() < 0.002:
                            w.writerow([ts, sid, var, val, uni])  # lectura duplicada
                            total += 1
        self.log(f"sensores: {self.dias_ais} días, {miles(total)} lecturas")

    # ---------------------------------------------------------- contenedores
    def contenedores(self):
        r = self.r
        prefijos = ["MSK", "CMA", "HLC", "OOL", "EVR", "MED", "ONE", "YML", "ZIM", "HUE", "ODL", "TNT"]
        tipos = [("22G1", "20 DV", 2200, 30480), ("45G1", "40 HC", 3900, 32500), ("45R1", "40 Reefer", 4800, 34000),
                 ("22T6", "20 Tanque", 3700, 36000)]
        esc_cont = [e for e in self.escalas if e["tipo_trafico"] == "contenedores" and e["eta"].year == 2025]
        limite = int(400000 * self.escala)
        total = 0
        cols = ["id_movimiento", "ts", "contenedor", "codigo_iso", "tipo", "lleno", "peso_bruto_kg",
                "id_escala", "id_cliente", "movimiento", "bloque_patio", "clase_imo", "temp_consigna_c"]
        ids_cli = [c["id_cliente"] for c in self.clientes] or ["CLI0001"]
        with open(self.ruta("contenedores", "movimientos_2025.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for e in esc_cont:
                if total >= limite:
                    break
                n = min(int(e["teu"] * 0.55), 900)
                for k in range(n):
                    pref = r.choice(prefijos)
                    num = f"{r.randint(0, 999999):06d}"
                    base = pref + "U" + num
                    dig = iso6346_digito(base)
                    if r.random() < 0.01:
                        dig = (dig + r.randint(1, 9)) % 10            # dígito de control erróneo
                    cont = base + str(dig)
                    cod, desc, tara, maxbruto = r.choices(tipos, weights=[40, 40, 12, 8])[0]
                    lleno = r.random() < 0.8
                    peso = tara + (r.uniform(4000, maxbruto - tara) if lleno else 0)
                    if r.random() < 0.004:
                        peso = r.uniform(40000, 60000)                 # sobrepeso imposible
                    reefer = cod == "45R1"
                    temp = round(r.choice([-18, -1, 1, 2, 4, 12]) + r.gauss(0, 0.2), 1) if reefer else ""
                    if reefer and r.random() < 0.05:
                        temp = ""                                      # reefer sin consigna
                    cli = r.choice(ids_cli)
                    t = e["ata"] + timedelta(minutes=r.randint(0, int((e["atd"] - e["ata"]).total_seconds() // 60)))
                    movs = ["DESCARGA", "GATE_OUT"] if e["operacion"] != "carga" else ["GATE_IN", "CARGA"]
                    for mv in movs:
                        total += 1
                        fila = [f"MOV{total:08d}", t.strftime("%Y-%m-%d %H:%M:%S"), cont, cod, desc,
                                "S" if lleno else "N", round(peso), e["id_escala"], cli, mv,
                                f"B{r.randint(1, 24):02d}-{r.randint(1, 40):02d}",
                                r.choice(["", "", "", "", "", "", "", "", "3", "8", "9"]), temp]
                        w.writerow(fila)
                        if r.random() < 0.004:
                            w.writerow(fila)
                            total += 1
                        t += timedelta(hours=r.uniform(4, 96))
        self.log(f"contenedores: {miles(total)} movimientos")

    # ---------------------------------------------------------- negocio (BI)
    def negocio(self):
        r = self.r
        sectores = [("agroalimentario", ["fruta_refrigerada", "contenedores", "carga_general"]),
                    ("químico", ["granel_liquido", "contenedores"]),
                    ("minero", ["granel_solido"]),
                    ("energía", ["granel_liquido"]),
                    ("automoción", ["ro_ro"]),
                    ("distribución", ["contenedores", "carga_general"]),
                    ("construcción", ["granel_solido", "carga_general"])]
        # --- servicios (catálogo) ---
        self.servicios = [
            ("S01", "Estiba/desestiba contenedor", "contenedores", "TEU", 95.0, 61.0),
            ("S02", "Almacenaje contenedor en patio", "contenedores", "TEU-día", 6.5, 2.1),
            ("S03", "Conexión reefer", "fruta_refrigerada", "contenedor-día", 38.0, 19.0),
            ("S04", "Manipulación fruta refrigerada", "fruta_refrigerada", "t", 14.0, 7.5),
            ("S05", "Carga/descarga granel sólido", "granel_solido", "t", 3.2, 2.2),
            ("S06", "Almacenaje granel sólido", "granel_solido", "t-mes", 1.1, 0.4),
            ("S07", "Trasiego granel líquido", "granel_liquido", "t", 1.6, 0.9),
            ("S08", "Almacenaje en tanque", "granel_liquido", "m3-mes", 2.4, 1.0),
            ("S09", "Operación ro-ro", "ro_ro", "unidad", 42.0, 25.0),
            ("S10", "Carga general", "carga_general", "t", 8.5, 5.6),
            ("S11", "Pesaje VGM", "contenedores", "contenedor", 25.0, 9.0),
            ("S12", "Inspección fitosanitaria (gestión)", "fruta_refrigerada", "expediente", 120.0, 70.0),
            ("S13", "Consigna y agencia", "general", "escala", 650.0, 380.0),
            ("S14", "Alquiler de grúa móvil", "general", "hora", 210.0, 150.0),
            ("S15", "Gestión aduanera", "general", "expediente", 85.0, 40.0),
        ]
        with open(self.ruta("negocio", "servicios.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["cod_servicio", "nombre", "familia", "unidad", "tarifa_base_eur", "coste_unitario_eur"])
            w.writerows(self.servicios)
        serv_por_fam = {}
        for s in self.servicios:
            serv_por_fam.setdefault(s[2], []).append(s)

        # --- clientes ---
        usados = set()
        n_cli = 400
        for i in range(n_cli):
            sec, fams = r.choice(sectores)
            while True:
                nombre = f"{r.choice(CLI_A)} {r.choice(CLI_B)} {r.choice(CLI_C)}"
                if nombre not in usados:
                    usados.add(nombre)
                    break
            pais = r.choices(["España", "Portugal", "Marruecos", "Países Bajos", "Reino Unido", "Francia"],
                             weights=[70, 8, 6, 6, 5, 5])[0]
            prov = r.choice(["Huelva", "Sevilla", "Badajoz", "Cádiz", "Córdoba", "Madrid"]) if pais == "España" else ""
            alta = date(2018, 1, 1) + timedelta(days=r.randint(0, 2900))
            self.clientes.append({
                "id_cliente": f"CLI{i+1:04d}", "razon_social": nombre, "tipo": r.choice(["cargador", "transitario", "naviera", "agente"]),
                "sector": sec, "familia_principal": r.choice(fams), "pais": pais, "provincia": prov,
                "fecha_alta": alta.isoformat(), "canal_captacion": r.choice(["feria", "comercial", "web", "recomendación", "LinkedIn"]),
                "tamano": r.choices(["grande", "mediana", "pequeña"], weights=[15, 35, 50])[0],
            })
        # Pareto: peso de facturación por cliente
        pesos_cli = []
        for c in self.clientes:
            p = r.paretovariate(1.25) * {"grande": 6, "mediana": 2, "pequeña": 1}[c["tamano"]]
            pesos_cli.append(p)
        with open(self.ruta("negocio", "clientes.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(self.clientes[0].keys()))
            w.writeheader()
            for c in self.clientes:
                fila = dict(c)
                if r.random() < 0.03:
                    fila["razon_social"] = c["razon_social"].upper()
                if r.random() < 0.02:
                    fila["provincia"] = ""
                w.writerow(fila)
                if r.random() < 0.01:          # cliente duplicado con otro formato de nombre
                    fila2 = dict(c)
                    fila2["razon_social"] = c["razon_social"].replace(" S.L.", " SL").replace(" S.A.", " SA")
                    w.writerow(fila2)

        # clientes de contenedores que «se van» en 2025-T4 por las esperas
        cont_cli = [c for c in self.clientes if c["familia_principal"] == "contenedores"]
        fugados = set(c["id_cliente"] for c in r.sample(cont_cli, max(1, len(cont_cli) // 4)))

        # --- tipos de cambio USD->EUR (mensual) ---
        tc = {}
        with open(self.ruta("negocio", "tipos_cambio.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["mes", "divisa", "eur_por_unidad"])
            v = 0.92
            for anio in (2024, 2025):
                for mes in range(1, 13):
                    v = round(v + r.gauss(0, 0.012), 4)
                    tc[(anio, mes)] = v
                    w.writerow([f"{anio}-{mes:02d}", "USD", v])

        # --- facturas (export de ERP: ; como separador, coma decimal, fecha dd/mm/aaaa) ---
        n_lineas_anio = int(30000 * self.escala) if self.escala < 1 else int(30000 * self.escala)
        n_lineas_anio = max(1500, n_lineas_anio)
        ids = [c["id_cliente"] for c in self.clientes]
        cli_idx = {c["id_cliente"]: c for c in self.clientes}
        for anio in (2024, 2025):
            with open(self.ruta("negocio", f"facturas_{anio}.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["num_factura", "linea", "fecha", "id_cliente", "cod_servicio", "cantidad",
                            "precio_unitario", "descuento_pct", "importe", "divisa", "comercial"])
                nf = 0
                i = 0
                while i < n_lineas_anio:
                    cid = r.choices(ids, weights=pesos_cli)[0]
                    c = cli_idx[cid]
                    mes = r.randint(1, 12)
                    if c["familia_principal"] == "fruta_refrigerada" and r.random() < 0.6:
                        mes = r.randint(2, 5)
                    if anio == 2025 and cid in fugados and mes >= 10:
                        continue                              # ya no factura: fuga
                    dia = r.randint(1, 28)
                    nf += 1
                    num = f"F{anio}-{nf:06d}"
                    fam = c["familia_principal"]
                    propios = serv_por_fam.get(fam, []) or serv_por_fam["general"]
                    for ln in range(1, r.randint(1, 4) + 1):
                        s = r.choice(serv_por_fam["general"]) if r.random() < 0.25 else r.choice(propios)
                        cod, _, _, unidad, tarifa, _ = s
                        crecim = 1.0
                        if anio == 2025 and fam == "fruta_refrigerada":
                            crecim = 1.25
                        mu, sd = CANTIDAD_UNIDAD[unidad]
                        if unidad in ("expediente", "escala", "hora"):
                            cant = float(r.randint(int(mu), int(sd)))
                        else:
                            cant = round(max(1, r.lognormvariate(mu, sd)) * crecim, 2)
                        precio = round(tarifa * (1.03 if anio == 2025 else 1.0) * r.uniform(0.95, 1.05), 2)
                        desc = r.choice([0, 0, 0, 5, 10, 15]) if c["tamano"] == "grande" else r.choice([0, 0, 0, 5])
                        imp = round(cant * precio * (1 - desc / 100), 2)
                        divisa = "EUR"
                        if c["pais"] in ("Reino Unido", "Marruecos") and r.random() < 0.5:
                            divisa = "USD"
                            imp = round(imp / tc[(anio, mes)], 2)
                            precio = round(precio / tc[(anio, mes)], 2)
                        fecha = f"{dia:02d}/{mes:02d}/{anio}"

                        def es(x):
                            return f"{x:.2f}".replace(".", ",")
                        fila = [num, ln, fecha, cid, cod, es(cant), es(precio), desc, es(imp), divisa,
                                r.choice(COMERCIALES)]
                        x = r.random()
                        if x < 0.01:
                            fila[3] = cid.lower()                       # id en minúsculas
                        elif x < 0.015:
                            fila[8] = ""                                # importe vacío
                        elif x < 0.02:
                            fila[2] = f"{anio}-{mes:02d}-{dia:02d}"     # fecha ISO mezclada
                        w.writerow(fila)
                        i += 1
                        if r.random() < 0.004:
                            w.writerow(fila)                            # línea duplicada
        # --- campañas de marketing ---
        campanas = []
        canales = [("Feria Fruit Attraction", "feria", 38000, "agroalimentario", 4.5),
                   ("Feria Breakbulk Europe", "feria", 42000, "minero", 2.2),
                   ("LinkedIn Ads logística", "LinkedIn", 12000, "distribución", 0.4),
                   ("Emailing cargadores", "email", 3000, "químico", 1.2),
                   ("Revista sectorial portuaria", "prensa", 9000, "energía", 0.6),
                   ("Visitas comerciales Portugal", "comercial", 15000, "automoción", 1.8),
                   ("Jornada puertas abiertas", "evento", 7000, "construcción", 0.9)]
        k = 0
        for anio in (2024, 2025):
            for (nombre, canal, coste, seg, roi) in canales:
                for rep in range(2 if canal in ("LinkedIn", "email") else 1):
                    k += 1
                    ini = date(anio, r.randint(1, 11), r.randint(1, 20))
                    leads = int(max(3, r.gauss(coste / 400 * (1 + roi / 3), 8)))
                    opp = int(leads * r.uniform(0.15, 0.4))
                    gan = int(max(0, round(opp * min(0.9, 0.12 * roi + r.uniform(-0.05, 0.05)))))
                    ingresos = round(coste * roi * r.uniform(0.8, 1.2), 2)
                    campanas.append([f"CMP{k:03d}", f"{nombre} {anio}", canal, ini.isoformat(),
                                     (ini + timedelta(days=r.randint(3, 60))).isoformat(), round(coste * r.uniform(0.9, 1.1), 2),
                                     seg, leads, opp, gan, ingresos])
        with open(self.ruta("negocio", "campanas_marketing.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id_campana", "nombre", "canal", "fecha_inicio", "fecha_fin", "coste_eur", "segmento_objetivo",
                        "leads", "oportunidades", "clientes_ganados", "ingresos_atribuidos_eur"])
            w.writerows(campanas)

        # --- competencia (mensual, puertos ficticios) ---
        segs = {"granel_liquido": 950000, "granel_solido": 620000, "contenedores": 180000,
                "fruta_refrigerada": 60000, "ro_ro": 90000}
        with open(self.ruta("negocio", "competencia.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["mes", "operador", "segmento", "toneladas", "tarifa_media_eur_t", "espera_media_h", "cuota_pct"])
            for anio in (2024, 2025):
                for mes in range(1, 13):
                    for seg, mercado in segs.items():
                        cuotas = {"TML Huelva (nosotros)": 0.34, "Terminal Guadiana": 0.24,
                                  "Puerto Bahía Sur": 0.26, "Terminal Atlántico Norte": 0.16}
                        esperas = {"TML Huelva (nosotros)": 6.0, "Terminal Guadiana": 7.5,
                                   "Puerto Bahía Sur": 6.5, "Terminal Atlántico Norte": 9.0}
                        if seg == "contenedores" and anio == 2025 and mes >= 7:
                            desplaz = min(0.10, 0.025 * (mes - 6))
                            cuotas["TML Huelva (nosotros)"] -= desplaz
                            cuotas["Terminal Guadiana"] += desplaz
                            esperas["TML Huelva (nosotros)"] = 14.0 + r.uniform(-1, 2)
                        if seg == "fruta_refrigerada" and anio == 2025:
                            cuotas["TML Huelva (nosotros)"] += 0.05
                            cuotas["Puerto Bahía Sur"] -= 0.05
                        estac = 1.6 if (seg == "fruta_refrigerada" and 2 <= mes <= 5) else 1.0
                        for op, cu in cuotas.items():
                            cu = max(0.02, cu + r.gauss(0, 0.01))
                            ton = round(mercado * estac * cu * r.uniform(0.95, 1.05))
                            tarifa = round({"granel_liquido": 1.7, "granel_solido": 3.4, "contenedores": 9.8,
                                            "fruta_refrigerada": 15.0, "ro_ro": 7.5}[seg] * r.uniform(0.9, 1.1), 2)
                            w.writerow([f"{anio}-{mes:02d}", op, seg, ton, tarifa,
                                        round(esperas[op] + r.gauss(0, 0.8), 1), round(cu * 100, 1)])

        # --- textos: redes sociales, encuestas, incidencias ---
        pos = ["rapidez en la descarga", "excelente coordinación con la terminal", "gran trabajo del equipo de estiba",
               "la campaña de fresa ha ido genial", "operativa impecable", "muy buena atención comercial",
               "cadena de frío perfecta", "puntualidad en el atraque"]
        neg = ["esperas interminables en fondeo", "retrasos en la descarga de contenedores", "la grúa vuelve a estar parada",
               "servicio lento y caro", "colas de camiones en la puerta", "mala comunicación con la terminal",
               "otra vez sin fecha de atraque", "perdimos la conexión del reefer"]
        neu = ["hoy atraca un nuevo portacontenedores", "reunión sobre la ampliación del muelle sur",
               "publicadas las tarifas del próximo año", "visita institucional a la terminal",
               "nuevo servicio semanal con Canarias", "jornada técnica sobre digitalización portuaria"]
        comps = ["Terminal Guadiana", "Puerto Bahía Sur", "Terminal Atlántico Norte"]
        n_posts = max(400, int(5000 * self.escala))
        with open(self.ruta("negocio", "redes_sociales.jsonl"), "w", encoding="utf-8") as f:
            for i in range(n_posts):
                anio = r.choice([2024, 2025])
                mes = r.randint(1, 12)
                dia = r.randint(1, 28)
                p_neg = 0.25
                if anio == 2025 and mes in (8, 9, 10):
                    p_neg = 0.6
                x = r.random()
                if x < p_neg:
                    txt, pol = r.choice(neg), -1
                elif x < p_neg + 0.35:
                    txt, pol = r.choice(pos), 1
                else:
                    txt, pol = r.choice(neu), 0
                extra = ""
                if pol == -1 and r.random() < 0.3:
                    extra = f" Nos estamos planteando {r.choice(comps)}."
                elif pol == 1 and r.random() < 0.2:
                    extra = " ¡Mejor que en " + r.choice(comps) + "!"
                texto = f"{txt[0].upper()}{txt[1:]} en TML Huelva.{extra} #PuertoHuelva #logistica"
                if r.random() < 0.1:
                    texto = texto.upper()
                post = {"id_post": f"P{i+1:06d}", "fecha": f"{anio}-{mes:02d}-{dia:02d}T{r.randint(7,22):02d}:{r.randint(0,59):02d}:00",
                        "red": r.choice(["LinkedIn", "X", "Instagram"]),
                        "autor_tipo": r.choice(["cliente", "prensa", "ciudadano", "empleado", "transportista"]),
                        "texto": texto, "me_gusta": int(r.expovariate(1 / 25)), "compartidos": int(r.expovariate(1 / 4))}
                if r.random() < 0.05:
                    del post["red"]
                f.write(json.dumps(post, ensure_ascii=False) + "\n")

        with open(self.ruta("negocio", "encuestas_satisfaccion.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fecha", "id_cliente", "nps", "comentario"])
            for c in self.clientes:
                for anio in (2024, 2025):
                    for trimestre in (1, 2, 3, 4):
                        if r.random() < 0.35:
                            continue
                        base = 8.2
                        if c["familia_principal"] == "contenedores" and anio == 2025 and trimestre >= 3:
                            base = 5.3
                        if c["familia_principal"] == "fruta_refrigerada" and anio == 2025:
                            base = 8.9
                        nps = int(min(10, max(0, round(r.gauss(base, 1.5)))))
                        com = r.choice(pos) if nps >= 8 else (r.choice(neg) if nps <= 5 else r.choice(neu + [""]))
                        mes = (trimestre - 1) * 3 + r.randint(1, 3)
                        w.writerow([f"{anio}-{mes:02d}-{r.randint(1,28):02d}", c["id_cliente"], nps, com])

        plantillas_inc = [
            "Parada de la {g} durante {h} horas por {causa}. Afecta a la escala {e}.",
            "Retraso en el atraque de {e} por {causa}; el buque queda en fondeo {h} h.",
            "Fuga menor detectada en {m} durante el trasiego; activado protocolo, sin daños.",
            "Contenedor reefer con alarma de temperatura en el patio {b}; se reconecta en {h} h.",
            "Colas de camiones en la puerta principal por caída del sistema de citas ({h} h).",
            "Inspección fitosanitaria retrasa la salida de fruta de la escala {e}.",
            "Rotura de eslinga en {m}; sin heridos, operación reanudada tras {h} h.",
        ]
        causas = ["viento fuerte", "avería eléctrica", "falta de personal", "vibraciones anómalas",
                  "mantenimiento correctivo", "niebla", "huelga de estiba", "fallo del sistema informático"]
        with open(self.ruta("negocio", "incidencias.jsonl"), "w", encoding="utf-8") as f:
            n_inc = max(150, int(1500 * self.escala))
            for i in range(n_inc):
                e = r.choice(self.escalas)
                g = r.choice(["GRUA-01", "GRUA-02", "GRUA-03", "GRUA-04", "GRUA-04", "GRUA-05", "GRUA-06"])
                causa = r.choice(causas)
                if g == "GRUA-04" and r.random() < 0.6:
                    causa = "vibraciones anómalas"
                txt = r.choice(plantillas_inc).format(g=g, h=r.randint(1, 18), causa=causa, e=e["id_escala"],
                                                      m=r.choice([m[1] for m in MUELLES]), b=f"B{r.randint(1,24):02d}")
                f.write(json.dumps({"id_incidencia": f"INC{i+1:05d}",
                                    "fecha": (e["ata"] + timedelta(hours=r.randint(0, 20))).strftime("%Y-%m-%d %H:%M"),
                                    "reportado_por": r.choice(["jefe de turno", "capitanía", "seguridad", "mantenimiento"]),
                                    "texto": txt}, ensure_ascii=False) + "\n")
        self.log(f"negocio: {len(self.clientes)} clientes, {len(self.servicios)} servicios, facturas 2024-2025, "
                 f"{len(campanas)} campañas, {n_posts} publicaciones, incidencias y encuestas")

    # ---------------------------------------------------------- manifiesto
    def manifiesto(self):
        lineas = []
        for raiz, _, ficheros in os.walk(self.salida):
            for nom in sorted(ficheros):
                if nom == "MANIFIESTO.sha256":
                    continue
                p = os.path.join(raiz, nom)
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for bloque in iter(lambda: f.read(1 << 20), b""):
                        h.update(bloque)
                rel = os.path.relpath(p, self.salida).replace(os.sep, "/")
                lineas.append(f"{h.hexdigest()}  {rel}")
        lineas.sort(key=lambda x: x.split("  ", 1)[1])
        with open(os.path.join(self.salida, "MANIFIESTO.sha256"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lineas) + "\n")
        self.log(f"manifiesto: {len(lineas)} ficheros con SHA-256")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--escala", type=float, default=1.0)
    ap.add_argument("--semilla", type=int, default=2026)
    defecto = "/datos/raw" if os.path.isdir("/datos") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw")
    ap.add_argument("--salida", default=defecto)
    a = ap.parse_args()
    salida = os.path.abspath(a.salida)
    if os.path.isdir(salida) and os.listdir(salida):
        print(f"AVISO: {salida} no está vacía; los ficheros se sobrescriben.", file=sys.stderr)
    os.makedirs(salida, exist_ok=True)
    g = Gen(a.escala, a.semilla, salida)
    t = time.time()
    g.log(f"Generando datos simulados en {salida} (escala={a.escala}, semilla={a.semilla})")
    g.maestros()
    g.escalas_gen()
    g.negocio()          # antes que contenedores: necesita la lista de clientes
    g.contenedores()
    g.ais()
    g.sensores()
    g.manifiesto()
    tam = sum(os.path.getsize(os.path.join(rz, f)) for rz, _, fs in os.walk(salida) for f in fs)
    g.log(f"Terminado en {time.time()-t:.0f} s. Tamaño total: {tam/1e6:.0f} MB")


if __name__ == "__main__":
    main()
