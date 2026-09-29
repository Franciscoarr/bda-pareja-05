# Diccionario de datos (datos simulados)

Generados por `datos/generador/generar_datos.py` (semilla 2026). Con la misma escala y semilla, todas las parejas
tienen **exactamente** los mismos datos. Volúmenes aproximados a escala 1: ~250 MB.

> Los datos contienen **defectos intencionados**, como los datos reales: descubrirlos y tratarlos es parte del trabajo
> (fases 3 y 5). Este diccionario describe lo que *debería* contener cada campo.

## maestros/
**muelles.csv** · `id_muelle` (M01…M12), `nombre`, `tipo` (tipo de tráfico que atiende), `calado_max_m`, `longitud_m`,
`lat`, `lon`, `gruas` (identificadores separados por `|`).

**navieras.csv** · `id_naviera` (NAV001…), `nombre`, `pais`, `flota` (nº de buques).

**buques.csv** · `imo` (7 dígitos con dígito de control), `mmsi` (9 dígitos; los 3 primeros = país de bandera), `nombre`,
`tipo`, `descripcion_tipo`, `gt` (arqueo bruto), `eslora_m`, `manga_m`, `calado_m`, `bandera`, `id_naviera`.

## escalas/escalas_AAAA.csv (2024 y 2025)
Una fila por escala (visita de un buque). `id_escala`, `imo`, `buque`, `id_naviera`, `id_muelle`, `tipo_trafico`
(granel_liquido, granel_solido, contenedores, carga_general, ro_ro, fruta_refrigerada, pasajeros, pesca),
`operacion` (carga/descarga/mixta), `mercancia`, `toneladas`, `teu` (contenedores de 20 pies equivalentes),
`eta` (llegada prevista a la bahía), `ata` (atraque real), `atd` (salida real), `origen`, `destino`,
`practicaje` (S/N), `pasajeros`. Fechas en hora local, formato `AAAA-MM-DD hh:mm:ss`.
**Espera en fondeo** = `ata − eta`. **Estancia en muelle** = `atd − ata`.

## ais/ais_AAAA-MM-DD.jsonl (60 días desde el 1-6-2025)
Una línea JSON por posición transmitida por un buque (sistema AIS). `mmsi`, `ts` (UTC, ISO 8601), `lat`, `lon`,
`sog` (velocidad sobre el fondo, nudos), `cog` (rumbo, grados), `estado_nav` (0 navegando, 1 fondeado, 5 amarrado),
`estacion` (antena receptora). Zona de fondeo aproximada: lat 37.03–37.09, lon −7.02 a −6.94.

## sensores/sensores_AAAA-MM-DD.csv (mismos 60 días)
Formato largo: `ts` (hora local con desfase `+02:00`), `id_sensor`, `variable`, `valor`, `unidad`.
- METEO-01: viento_vel (m/s), viento_dir (grados), temperatura (°C), humedad (%), presion (hPa) — cada minuto.
- OLEAJE-01: altura_ola (m) — cada minuto.
- AIRE-01, AIRE-02: so2, no2, pm10 (µg/m³) — cada minuto.
- GRUA-01…06: carga (t), vibracion (mm/s), temp_motor (°C) — cada 5 minutos. Las grúas paran con viento > 14 m/s.

## contenedores/movimientos_2025.csv
`id_movimiento`, `ts`, `contenedor` (ISO 6346: 3 letras + U + 6 dígitos + dígito de control), `codigo_iso`
(22G1 20' seco, 45G1 40' high cube, 45R1 40' refrigerado, 22T6 20' tanque), `tipo`, `lleno` (S/N),
`peso_bruto_kg` (máx. 36 000), `id_escala`, `id_cliente`, `movimiento` (DESCARGA, CARGA, GATE_IN, GATE_OUT),
`bloque_patio`, `clase_imo` (mercancía peligrosa; vacío si no aplica), `temp_consigna_c` (solo refrigerados).

## negocio/ (operador ficticio TML Huelva)
| Fichero | Contenido |
|---|---|
| clientes.csv | `id_cliente`, `razon_social`, `tipo`, `sector`, `familia_principal`, `pais`, `provincia`, `fecha_alta`, `canal_captacion`, `tamano` |
| servicios.csv | Catálogo: `cod_servicio`, `nombre`, `familia`, `unidad`, `tarifa_base_eur`, `coste_unitario_eur` |
| facturas_AAAA.csv | Export del ERP (**`;` y coma decimal**, fechas `dd/mm/aaaa`): `num_factura`, `linea`, `fecha`, `id_cliente`, `cod_servicio`, `cantidad`, `precio_unitario`, `descuento_pct`, `importe` (en la divisa de la factura), `divisa`, `comercial` |
| tipos_cambio.csv | `mes`, `divisa`, `eur_por_unidad` |
| campanas_marketing.csv | `id_campana`, `nombre`, `canal`, `fecha_inicio`, `fecha_fin`, `coste_eur`, `segmento_objetivo`, `leads`, `oportunidades`, `clientes_ganados`, `ingresos_atribuidos_eur` |
| competencia.csv | Estudio de mercado mensual: `mes`, `operador`, `segmento`, `toneladas`, `tarifa_media_eur_t`, `espera_media_h`, `cuota_pct` |
| encuestas_satisfaccion.csv | `fecha`, `id_cliente`, `nps` (0-10), `comentario` (texto libre) |
| redes_sociales.jsonl | `id_post`, `fecha`, `red`, `autor_tipo`, `texto`, `me_gusta`, `compartidos` |
| incidencias.jsonl | `id_incidencia`, `fecha`, `reportado_por`, `texto` (parte de incidencia en texto libre) |

## MANIFIESTO.sha256
Huella SHA-256 de cada fichero generado (formato de `sha256sum`). Sirve para verificar la integridad de extremo a extremo.
