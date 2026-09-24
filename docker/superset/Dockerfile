FROM apache/superset:3.1.3

USER root

# Postgres driver
RUN pip install --no-cache-dir psycopg2-binary==2.9.9

# Our config
COPY superset_config.py /app/pythonpath/superset_config.py

USER superset
