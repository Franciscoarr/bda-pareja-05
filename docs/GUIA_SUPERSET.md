# Guía rápida de Apache Superset (fase 5)

Arranque: `.\bda.ps1 iniciar bi` · http://localhost:8088 · usuario **admin**, contraseña **bda2027**
(la primera vez tarda 1-2 min en preparar su base de datos interna: `.\bda.ps1 logs superset`).

## 1. Conectar el almacén de datos
*Settings* (engranaje, arriba a la derecha) → **Database Connections** → **+ Database** → **PostgreSQL** →
«Connect this database with a SQLAlchemy URI string instead» →
```
postgresql+psycopg2://bda:bda2027@postgres:5432/puerto_dw
```
Nombre visible: `Almacén TML`. **Test connection** → **Connect**.
Ojo: el servidor es `postgres` (nombre del contenedor), no `localhost`.

## 2. Datasets
**Datasets** → **+ Dataset** → base `Almacén TML`, esquema `dw`, tabla o vista (p. ej. `v_kpi_facturacion_mensual`).
Consejo: cread **vistas SQL** con los KPI ya calculados y usad cada vista como dataset. Para consultas puntuales:
**SQL** → **SQL Lab** (y desde el resultado, *Save dataset*).

En cada dataset, *Edit dataset* → *Columns*: marcad las columnas de fecha como **temporales** (*Is temporal*) y
definid **métricas** reutilizables (*Metrics*), p. ej. `SUM(facturacion_eur)`.

## 3. Gráficos recomendados
| Pregunta | Tipo de gráfico en Superset |
|---|---|
| Facturación, margen, clientes activos, NPS | *Big Number with Trendline* |
| Evolución mensual por línea de negocio | *Line Chart* (dimensión: familia) |
| Reparto por servicio o cliente | *Bar Chart* ordenado / *Treemap* |
| Clientes en riesgo de fuga | *Table* con formato condicional |
| Cuota frente a la competencia | *Line Chart* o *Bar Chart* agrupado |
| Termómetro de opinión | *Line Chart* del % de publicaciones negativas |
| Espera en fondeo vs. ventas | *Mixed Chart* (dos ejes) |

## 4. Cuadro de mando
**Dashboards** → **+ Dashboard** → arrastrad los gráficos → **Filters** (panel izquierdo) → añadid filtros nativos por
año, trimestre y línea de negocio y aplicadlos a todos los gráficos → **Save**.
Buenas prácticas: lo más importante arriba a la izquierda, máximo 6-8 gráficos, títulos que respondan a una pregunta
(«¿Estamos perdiendo clientes de contenedores?»), colores coherentes y unidades visibles.

## 5. Exportar para la entrega
Dashboard → **⋯** → **Download** → **Export to ZIP** (incluye gráficos y datasets) y **Download as image** para la memoria.
Guardad ambos en `entregas/F5/`.

## 6. Problemas frecuentes
| Síntoma | Solución |
|---|---|
| `Could not load database driver` | Revisad que la URI empiece por `postgresql+psycopg2://` |
| `connection refused` | El servidor es `postgres`, no `localhost`; comprobad que el perfil `bi` está en marcha |
| Un gráfico no muestra fechas | Marcad la columna como temporal en el dataset |
| Cambié la vista en PostgreSQL y Superset no lo ve | Dataset → *Edit* → *Sync columns from source* |
