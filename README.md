# Plataforma de datos del Puerto de Huelva · Big Data Aplicado (05075)

Proyecto integrador del módulo **Big Data Aplicado** · Curso de Especialización en Inteligencia Artificial y Big Data ·
IES La Marisma (Huelva) · curso 2026/2027.

Trabajáis **por parejas** durante todo el curso sobre una plataforma de datos para el puerto: buques que llegan y
esperan, posiciones AIS, sensores de grúas y calidad del aire, movimientos de contenedores y, al final, los datos de
negocio de un operador de terminal. Cada fase cierra un Resultado de Aprendizaje (RA).

> **Todos los datos son simulados.** Buques, navieras, clientes, competidores y textos son ficticios y se generan
> con `datos/generador/generar_datos.py`. Cualquier parecido con empresas reales es casual.

## Fases

| Fase | RA | Qué construís | Cuaderno | Memoria |
|---|---|---|---|---|
| 1 | RA1 | Diseño del lago de datos, ingesta, formatos, procesamiento y presentación | `notebooks/F1_ingesta_formatos.ipynb` | `entregas/F1/` |
| 2 | RA2 | HDFS y Spark distribuidos: escalado, tolerancia a fallos, crecimiento | `notebooks/F2_computacion_distribuida.ipynb` | `entregas/F2/` |
| 3 | RA3 | Calidad e integridad: reglas, cuarentena, checksums, corrupción controlada | `notebooks/F3_integridad_calidad.ipynb` | `entregas/F3/` |
| 4 | RA4 | Monitorización: Prometheus, Grafana, alertas, fiabilidad y estabilidad | `notebooks/F4_monitorizacion.ipynb` | `entregas/F4/` |
| 5 | RA5 | Inteligencia de negocio: limpieza, texto, modelo en estrella, Superset | `notebooks/F5_bi.ipynb` | `entregas/F5/` |

## Requisitos del PC

- Windows 10/11 de 64 bits con **16 GB de RAM** (8 GB funciona con escala de datos 0.3 y sin perfiles extra), 25 GB libres.
- **Docker Desktop** con WSL 2, **Git** y **Visual Studio Code**. Pasos detallados en [`docs/INSTALACION.md`](docs/INSTALACION.md).

## Puesta en marcha (primera vez)

```powershell
git clone https://github.com/<organizacion>/<vuestro-repo>.git
cd <vuestro-repo>
.\bda.ps1 iniciar          # la primera vez construye la imagen de Spark (5-10 min)
.\bda.ps1 datos            # genera ~250 MB de datos simulados (≈ 30 s)
.\bda.ps1 ingesta          # los copia a HDFS
```
Abrid http://localhost:8888 → `notebooks/00_comprobar_entorno.ipynb` y ejecutad todas las celdas.

## Órdenes de `bda.ps1`

| Orden | Para qué |
|---|---|
| `.\bda.ps1 iniciar [monitor\|bi\|todo]` | Arranca el núcleo (+ monitorización o BI) |
| `.\bda.ps1 parar` | Para todo sin borrar nada |
| `.\bda.ps1 estado` | Qué está en marcha y direcciones web |
| `.\bda.ps1 datos [escala]` | Genera los datos (escala 1 por defecto; 0.3 en PCs justos) |
| `.\bda.ps1 ingesta` | Copia `datos/raw` a HDFS `/puerto/raw` |
| `.\bda.ps1 verificar` | Compara SHA-256 de HDFS con el manifiesto |
| `.\bda.ps1 hdfs dfs -ls /puerto` | Cualquier comando `hdfs` |
| `.\bda.ps1 escalar datanode 4` | Añade nodos |
| `.\bda.ps1 consola namenode` | Consola dentro de un contenedor |
| `.\bda.ps1 logs <servicio>` | Ver errores de un servicio |
| `.\bda.ps1 reset` | Borra contenedores (y HDFS). Luego: `iniciar` + `ingesta` |

## Servicios

| Servicio | Dirección | Usuario |
|---|---|---|
| HDFS NameNode | http://localhost:9870 | — |
| Spark master | http://localhost:8080 | — |
| JupyterLab | http://localhost:8888 | — |
| Spark (aplicación activa) | http://localhost:4040 | — |
| Prometheus *(monitor)* | http://localhost:9090 | — |
| Grafana *(monitor)* | http://localhost:3000 | admin / bda2027 |
| Superset *(bi)* | http://localhost:8088 | admin / bda2027 |
| PostgreSQL *(bi)* | localhost:5432, BD `puerto_dw` | bda / bda2027 |

Los puertos solo escuchan en `127.0.0.1`: nadie del aula puede entrar en vuestros servicios. Las contraseñas son de
laboratorio; en producción se cambiarían y se guardarían fuera del repositorio.

## Estructura

```
bda.ps1 / bda.sh          atajos (Windows / Linux-Mac)
docker-compose.yml        definición del clúster
docker/                   configuración de Hadoop, Spark, Prometheus, Grafana, Superset, PostgreSQL y el exportador
datos/generador/          generador de datos simulados         datos/raw/  (no se sube a GitHub)
datos/lexico/             léxico de sentimiento (fase 5)       datos/muestra/  ejemplos pequeños para mirar
notebooks/                cuadernos de cada fase
src/puerto/               paquete Python de apoyo (sesión Spark, WebHDFS, calidad, texto, BI, métricas)
scripts/                  scripts de HDFS y de pruebas de caos
entregas/F1..F5/          memorias y evidencias de cada fase
docs/                     instalación, arquitectura, guía de Superset y diccionario de datos
```

## Normas de trabajo y entregas

1. **Commits pequeños y frecuentes de los dos miembros.** El historial de Git es evidencia de autoría.
   Mensajes claros: `F2: experimento de caída de DataNode`.
2. Nada de datos generados ni contraseñas reales en el repositorio (`.gitignore` ya excluye `datos/raw/`).
3. **Entrega de cada fase:** (a) crear el tag `F1-entrega` (`F2-entrega`...) en GitHub y (b) subir a Moodle el ZIP que
   GitHub genera para ese tag y el enlace. La fecha de entrega es la de Moodle.
   ```powershell
   git tag F1-entrega
   git push origin F1-entrega
   ```
4. **Evidencias obligatorias:** cada apartado de la memoria lleva capturas de pantalla propias (con el reloj visible y el
   sello `sello(PAREJA)` de la primera celda del cuaderno), además de comandos y salidas. Sin evidencias no se puntúa.
5. **Defensa a criterio del profesor:** el profesor puede pedir a cualquier pareja o miembro que explique su trabajo
   (en clase o en una cita). Lo que no se sepa explicar no cuenta (cláusula de autoría de la programación).
6. El uso de herramientas de IA debe **declararse** en la memoria (apartado 5). Lo que no se sepa defender no cuenta.
