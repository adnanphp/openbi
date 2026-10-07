FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary ships as a wheel, so build-essential and libpq-dev
# aren't needed. Only libpq5 (the runtime library) is required.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install API-only dependencies first (cached across code changes).
COPY infrastructure/kubernetes/fastapi-app/requirements-api.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-api.txt

# Copy only the packages the API actually imports.
# Not the whole src/ tree — no ETL, no ML, no notebooks.
COPY src/openbi/__init__.py /app/openbi/__init__.py
COPY src/openbi/api/ /app/openbi/api/
COPY src/openbi/config/ /app/openbi/config/
COPY src/openbi/utils/ /app/openbi/utils/

EXPOSE 8000

CMD ["uvicorn", "openbi.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
