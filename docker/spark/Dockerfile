# Imagen única para spark-master, spark-worker y jupyter.
# Master, workers y driver (Jupyter) DEBEN tener la misma versión de Spark y de Python:
# por eso se construye una sola imagen para los tres.
ARG SPARK_TAG=3.5.8-python3
FROM apache/spark:${SPARK_TAG}

USER root
ENV DEBIAN_FRONTEND=noninteractive TZ=Europe/Madrid

# Utilidades de diagnóstico (ping, curl, procps) y dependencias de Python del proyecto
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl iputils-ping procps tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && ln -sf /usr/bin/python3 /usr/bin/python

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt 2>/dev/null \
 || pip3 install --no-cache-dir -r /tmp/requirements.txt

# Conectores: PostgreSQL (JDBC, fase 5) y Avro (comparativa de formatos, fase 1)
ARG SPARK_VERSION=3.5.8
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.12/${SPARK_VERSION}/spark-avro_2.12-${SPARK_VERSION}.jar /opt/spark/jars/
RUN chmod 644 /opt/spark/jars/*.jar \
 && ln -sf "$(ls /opt/spark/python/lib/py4j-*-src.zip | head -1)" /opt/spark/python/lib/py4j-src.zip

COPY spark-defaults.conf metrics.properties /opt/spark/conf/

# PySpark importable desde Jupyter y desde scripts; /workspace/src con el paquete «puerto»
ENV SPARK_HOME=/opt/spark \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-src.zip:/workspace/src \
    PATH=/opt/spark/bin:/opt/spark/sbin:$PATH \
    HOME=/root

WORKDIR /workspace
