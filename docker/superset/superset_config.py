# Configuración mínima de Apache Superset para el laboratorio (Fase 5).
import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "cambia-esta-clave")
# Metadatos de Superset (usuarios, gráficos, cuadros de mando) en SQLite dentro del volumen
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"
BABEL_DEFAULT_LOCALE = "es"
LANGUAGES = {"es": {"flag": "es", "name": "Español"}, "en": {"flag": "us", "name": "English"}}
FEATURE_FLAGS = {"DASHBOARD_NATIVE_FILTERS": True, "ENABLE_TEMPLATE_PROCESSING": True}
WTF_CSRF_ENABLED = True
TALISMAN_ENABLED = False     # laboratorio local (http)
ROW_LIMIT = 50000
