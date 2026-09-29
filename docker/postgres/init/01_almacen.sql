-- =============================================================================
-- Almacén de datos (data warehouse) de la Fase 5 · modelo en estrella
-- Se ejecuta SOLO la primera vez que arranca PostgreSQL (volumen vacío).
-- Para volver a crearlo:  .\bda.ps1 reset-bi
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS staging;   -- datos limpios cargados desde Spark (tal cual)
CREATE SCHEMA IF NOT EXISTS dw;        -- modelo dimensional para BI

-- ---------------------------------------------------------------- dimensiones
CREATE TABLE IF NOT EXISTS dw.dim_fecha (
    id_fecha      INTEGER PRIMARY KEY,          -- AAAAMMDD
    fecha         DATE NOT NULL,
    anio          SMALLINT NOT NULL,
    trimestre     SMALLINT NOT NULL,
    mes           SMALLINT NOT NULL,
    nombre_mes    VARCHAR(12) NOT NULL,
    dia_semana    SMALLINT NOT NULL,            -- 1 = lunes
    es_fin_semana BOOLEAN NOT NULL,
    campana_fruta BOOLEAN NOT NULL              -- febrero a mayo
);

CREATE TABLE IF NOT EXISTS dw.dim_cliente (
    id_cliente        VARCHAR(10) PRIMARY KEY,
    razon_social      VARCHAR(120),
    tipo              VARCHAR(30),
    sector            VARCHAR(40),
    familia_principal VARCHAR(40),
    pais              VARCHAR(40),
    provincia         VARCHAR(40),
    tamano            VARCHAR(15),
    fecha_alta        DATE,
    canal_captacion   VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS dw.dim_servicio (
    cod_servicio       VARCHAR(5) PRIMARY KEY,
    nombre             VARCHAR(80),
    familia            VARCHAR(40),
    unidad             VARCHAR(20),
    tarifa_base_eur    NUMERIC(12,2),
    coste_unitario_eur NUMERIC(12,2)
);

-- ---------------------------------------------------------------- hechos
CREATE TABLE IF NOT EXISTS dw.fact_facturacion (
    num_factura     VARCHAR(15),
    linea           SMALLINT,
    id_fecha        INTEGER REFERENCES dw.dim_fecha(id_fecha),
    id_cliente      VARCHAR(10) REFERENCES dw.dim_cliente(id_cliente),
    cod_servicio    VARCHAR(5)  REFERENCES dw.dim_servicio(cod_servicio),
    cantidad        NUMERIC(14,2),
    importe_eur     NUMERIC(14,2),   -- convertido a EUR
    coste_eur       NUMERIC(14,2),   -- cantidad x coste unitario
    margen_eur      NUMERIC(14,2),
    comercial       VARCHAR(20),
    PRIMARY KEY (num_factura, linea)
);

-- TAREA (fase 5): completar el modelo con, al menos:
--   dw.fact_escalas        (espera_h, estancia_h, toneladas, teu por fecha/muelle/tipo de tráfico)
--   dw.fact_satisfaccion   (NPS por cliente y fecha)
--   dw.fact_redes          (publicaciones con sentimiento calculado por fecha y red)
--   dw.fact_competencia    (cuota, tarifa y espera por mes, operador y segmento)
--   y las vistas de KPI que use el cuadro de mando (ejemplo abajo).

CREATE OR REPLACE VIEW dw.v_kpi_facturacion_mensual AS
SELECT f.anio, f.mes, s.familia,
       SUM(h.importe_eur) AS facturacion_eur,
       SUM(h.margen_eur)  AS margen_eur,
       COUNT(DISTINCT h.id_cliente) AS clientes_activos
FROM dw.fact_facturacion h
JOIN dw.dim_fecha f    ON f.id_fecha = h.id_fecha
JOIN dw.dim_servicio s ON s.cod_servicio = h.cod_servicio
GROUP BY f.anio, f.mes, s.familia;
