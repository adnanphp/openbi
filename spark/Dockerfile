FROM docker.io/bitnamilegacy/spark:3.5.1

USER root

# Python packages for our jobs
RUN pip install --no-cache-dir \
    delta-spark==3.1.0 \
    pyarrow==16.1.0 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    psycopg2-binary==2.9.9 \
    python-dotenv==1.0.1

# Add our job code
COPY jobs /opt/openbi/jobs
COPY sql  /opt/openbi/sql
COPY conf /opt/openbi/conf

WORKDIR /opt/openbi

USER 1001
