---

title: "How I Built a Two-Tier Data Platform in 9 Phases (Spark, Kafka, dbt, Kubernetes)"
published: false
description: "A complete data platform — batch + streaming, single-node + distributed, local + Kubernetes. What I built, what broke, and what I learned."
tags: dataengineering, spark, kafka, kubernetes
cover_image: https://raw.githubusercontent.com/adnanphp/openbi/main/docs/images/social-preview.png
--------------------------------------------------------------------------------------------------

> **TL;DR** — I built [OpenBI](https://github.com/adnanphp/openbi), an end-to-end data platform that runs at two scales: a single-node Postgres warehouse on 10K rows, and a distributed Spark + Delta Lake pipeline on 1M+ rows. It also has a streaming tier (Kafka + Structured Streaming) and a Kubernetes deployment (Kind + Terraform). 100+ tests, 2 green CI workflows. This post covers the architecture, the specific bugs I hit, and what I'd do differently.

---

## Why I built this

Most data engineering portfolio projects pick a scale: either a small Postgres demo or a full Spark pipeline. I wanted **both** — running side-by-side, serving the same dashboards, with **zero code changes** when switching between them.

That constraint turned out to be interesting because it forced me to think about:

* What changes when you go from 10K to 1M rows
* Where the BI layer *should* be decoupled from compute
* What the "serving layer" actually is

---

## The architecture

The platform has three tiers.

### Tier 1 — v1: Postgres + pandas (10K rows)

The original version. Python ETL loads a CSV into a staging table, transforms it into a star schema (5 dimensions + 1 fact), and computes 5 KPI views. A scikit-learn layer does RFM + KMeans segmentation and ETS forecasting. Results are served via Superset and FastAPI.

```text
CSV → staging → star schema → KPI views → Superset / FastAPI
                                      ├── RFM + KMeans
                                      └── ETS forecasting
```

**Revenue processed:** $2,297,200.86 (verified against source data).

![Executive dashboard](https://raw.githubusercontent.com/adnanphp/openbi/main/docs/images/executive_dashboard.png)

### Tier 2 — v2: Spark + Delta Lake (1M rows)

Same domain, but distributed. A synthetic 1M-row Parquet dataset is ingested by PySpark into a Delta Bronze table, transformed into a Delta Silver star schema (partitioned by year), and aggregated into Delta Gold tables. Those are published to Postgres via JDBC.

```text
Parquet → Delta Bronze → Delta Silver → Delta Gold → Postgres warehouse_big
                                      ├── Spark MLlib (RFM + KMeans)
                                      └── Spark MLlib forecasting
```

**Revenue processed:** $287,833,061.24 (100× the v1 scale).

### Tier 3 — Streaming: Kafka + Structured Streaming

Real-time orders flow through Kafka, get consumed by a Spark Structured Streaming job, and land in Delta Bronze. A second streaming job publishes micro-batches to a Postgres table.

```text
producer.py → Kafka → Structured Streaming → Delta Bronze → Postgres
                              │
                              ▼
                    Superset real-time dashboard
```

**Events processed during the demo run:** 12,000+.

![Streaming dashboard](https://raw.githubusercontent.com/adnanphp/openbi/main/docs/images/streaming_dashboard.png)

### Serving layer

The BI layer is decoupled from compute:

* **Superset** dashboards read from `warehouse` (v1) or `warehouse_big` (v2). Same column names, same charts.
* **FastAPI** exposes `/kpis`, `/customers`, `/forecasts` — same endpoints regardless of which schema backs them.

**Zero BI code changes** when switching between v1 and v2. That's the whole point.

---

## The stack

| Layer          | Tools                                                    |
| -------------- | -------------------------------------------------------- |
| Ingestion      | pandas, PySpark, Kafka                                   |
| Storage        | PostgreSQL, Delta Lake (Parquet)                         |
| Compute        | Apache Spark (batch + streaming), Spark SQL, Spark MLlib |
| Orchestration  | Apache Airflow, Make                                     |
| Transformation | dbt                                                      |
| BI             | Apache Superset                                          |
| API            | FastAPI                                                  |
| Monitoring     | Prometheus, Grafana, statsd-exporter                     |
| Testing        | pytest (100+ tests)                                      |
| CI             | GitHub Actions (2 workflows)                             |
| Deployment     | Docker Compose, Kubernetes (Kind), Terraform, Kustomize  |

All 100% open source. Total cost to run: **$0**.

---

## The parts that were hard

### 1. Kind's DNS doesn't behave like Docker Compose's

Kind runs each cluster node as a Docker container. On Linux with `systemd-resolved`, the resolver inside a Kind container can't reach the host's DNS. Image pulls fail with:

```text
dial tcp: lookup registry-1.docker.io on 172.19.0.1:53:
server misbehaving
```

The fix is to pre-load images into the cluster from the host:

```bash
docker pull postgres:16-alpine
kind load docker-image postgres:16-alpine --name openbi
```

For images you build yourself (like the FastAPI service), you build on the host and load them the same way:

```bash
docker build -t openbi-fastapi:latest fastapi-app/
kind load docker-image openbi-fastapi:latest --name openbi
```

Then the manifest uses `imagePullPolicy: IfNotPresent`, which tells Kubernetes to use the loaded image instead of pulling.

**Why this matters:** cloud emulators are not the cloud. Kind is close, but its networking is different enough to break things that work in a real cluster.

---

### 2. Terraform doesn't expand `~` in path variables

I set:

```hcl
variable "kubeconfig_path" {
  default = "~/.kube/config"
}
```

Terraform interpreted `~` as a literal directory name. It created:

```text
infrastructure/terraform/~/.kube/config
```

inside my project — and worse, I committed it to git.

That kubeconfig contains client certificates. Anyone with access to the public repo could have connected to my cluster.

The fix:

* Removed the file from git history (`git rm --cached`, then rewrote the commit)
* Added `infrastructure/terraform/~/` and `**/kubeconfig` to `.gitignore`
* Changed the variable default to an absolute path:

```text
/home/adnan/.kube/config
```

**The lesson:** never trust `~` in any IaC tool. Always use absolute paths. And audit `git status` carefully — I would have missed this if I hadn't grepped the commit output.

---

### 3. Kubernetes probes need longer initial delays than you think

Superset takes 30–60 seconds to warm up on first start. My original readiness probe had `initialDelaySeconds: 5`.

Kubernetes killed the pod before it finished initializing, restarted it, killed it again — a crash loop that looked like Superset was broken.

The actual fix was:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 10
  timeoutSeconds: 5
```

Superset's first start now succeeds. Subsequent starts are faster because the metadata DB is warm.

![Kubernetes pods](https://raw.githubusercontent.com/adnanphp/openbi/main/docs/images/k8s_pods.png)

---

### 4. Superset's CLI has a bug

`superset run` in Superset 3.1.3 fails with:

```text
Error: 'tcp' is not a valid port number.
```

The fix is to call the image's own `run-server.sh` directly, which wraps Gunicorn:

```yaml
command:
  - /usr/bin/run-server.sh

env:
  - name: SUPERSET_BIND_ADDRESS
    value: "0.0.0.0"
  - name: SUPERSET_PORT
    value: "8088"
  - name: FLASK_APP
    value: "superset.app:create_app()"
```

The `superset run` wrapper is what breaks — the underlying Gunicorn server is fine. This is documented in several Superset GitHub issues.

---

### 5. Kustomize doesn't always detect file changes

`kubectl apply -k .` sometimes uses a cached version of the manifest, even after you edit the file.

If the deployed resource doesn't match what's on disk, force a clean apply:

```bash
kubectl delete -k .
kubectl apply -k .
```

Or, for a single resource:

```bash
kubectl delete deployment superset -n openbi
kubectl apply -k .
```

Why this happens: Kustomize hashes each resource. If two applies happen close together, the second can use the first's cached state.

---

## What I'd do differently

### Set up CI on day one

I hit the same class of bug — missing dependency — three times in different layers.

Each time, the fix was one line in a `requirements.txt` or a Dockerfile. But I only caught them because I ran CI after pushing.

If I'd set up GitHub Actions in Phase 1, I would have caught all three in the first hour instead of the third day.

**Always set up CI before writing production code.**

---

### Add a backup target earlier

I lost a Postgres volume mid-project because I ran:

```bash
docker compose down -v
```

instead of:

```bash
docker compose down
```

The `-v` option wipes volumes. Rebuilding from scratch took about 15 minutes.

The fix is trivial:

```makefile
backup:
	@mkdir -p backups
	docker compose exec -T postgres pg_dump -U openbi openbi > \
		backups/openbi_$$(date +%Y%m%d_%H%M%S).sql
```

Run:

```bash
make backup
```

before any risky operation.

---

### Write the tests as I went, not after

I wrote tests in batches after each phase.

If I'd written them incrementally, I would have caught bugs earlier — and I wouldn't have had to reverse-engineer test cases from working code.

---

## What's next

The platform is functional: **100+ tests passing, 2 green CI workflows.**

The next steps I'd consider:

* **Ingress controller** — expose services on real hostnames
* **Helm chart** — package OpenBI for one-command installation
* **Real cloud deployment** — GKE free tier
* **Companion ML paper** — I already published one on a related experiment

---

## Links

* **Repo:** [github.com/adnanphp/openbi](https://github.com/adnanphp/openbi)
* **Kubernetes docs:** [docs/kubernetes.md](https://github.com/adnanphp/openbi/blob/main/docs/kubernetes.md)
* **v2.0.0 release:** [GitHub Release](https://github.com/adnanphp/openbi/releases/tag/v2.0.0)



If you're building something similar — or hitting any of the same bugs — I'd love to hear about it in the comments.

---
