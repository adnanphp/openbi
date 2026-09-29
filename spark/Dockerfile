FROM docker.io/bitnamilegacy/spark:3.5.1

USER root

# Python deps
RUN pip install --no-cache-dir \
    delta-spark==3.1.0 \
    pyarrow==16.1.0 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    psycopg2-binary==2.9.9 \
    python-dotenv==1.0.1 \
    pytest==8.0.0

# Pre-download Delta Lake + PostgreSQL JDBC JARs
RUN python3 - << 'PY'
import urllib.request, os
base = "https://repo1.maven.org/maven2"
jars = [
    ("io/delta/delta-spark_2.12/3.1.0/delta-spark_2.12-3.1.0.jar", "delta-spark_2.12-3.1.0.jar"),
    ("io/delta/delta-storage/3.1.0/delta-storage-3.1.0.jar", "delta-storage-3.1.0.jar"),
    ("org/antlr/antlr4-runtime/4.9.3/antlr4-runtime-4.9.3.jar", "antlr4-runtime-4.9.3.jar"),
    ("org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar", "postgresql-42.7.3.jar"),
]
target = "/opt/bitnami/spark/jars"
for url_path, name in jars:
    out = os.path.join(target, name)
    print(f"  downloading {name}")
    urllib.request.urlretrieve(f"{base}/{url_path}", out)
    print(f"  ✓ {name} ({os.path.getsize(out):,} bytes)")
PY

COPY jobs /opt/openbi/jobs
COPY sql  /opt/openbi/sql
COPY conf /opt/openbi/conf
COPY tests /opt/openbi/tests

WORKDIR /opt/openbi

USER 1001
