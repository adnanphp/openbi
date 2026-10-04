from fastapi import FastAPI

app = FastAPI(title="OpenBI API", version="0.1.0")


@app.get("/")
def root():
    return {"service": "OpenBI API", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/kpis/summary")
def kpis_summary():
    return {
        "revenue": 2297200.86,
        "profit": 286397.02,
        "source": "in-memory (K8s deployment demo)",
    }
