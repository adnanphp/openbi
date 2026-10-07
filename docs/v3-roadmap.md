# OpenBI v3.0.0 — Cloud-Readiness Roadmap

Goal: extend OpenBI with the layers that map directly to managed cloud
services, so the same architecture is deployable to AWS or GCP with
minimal application changes.

## Phases

- [x] **Phase 1 — Traefik ingress** (maps to AWS ALB / GCP Load Balancer)
- [x] **Phase 2 — MinIO object storage** (maps to S3 / GCS)
- [x] **Phase 3 — Redis cache** (maps to ElastiCache / Memorystore)
- [x] **Phase 4 — LocalStack** (S3, SQS, Lambda via boto3)
- [x] **Phase 5 — Serverless function** (OpenFaaS; maps to Lambda / Cloud Functions)
- [x] **Phase 6 — Terraform refactor** (full IaC; destroy and rebuild)
- [ ] **Phase 7 — Loki + structured logging** (maps to CloudWatch Logs / Cloud Logging)
- [ ] **Phase 8 — Cloud-mapping document** (the highest-value artifact)

## Non-goals for v3.0.0

- OpenStack (deferred; not in this release)
- Multi-region or HA (out of scope for a local lab)
- Real AWS/GCP deployment (optional, done separately after v3.0.0)

## Success criteria

- Every phase is verifiable in isolation
- The full stack comes up with one command
- The full stack tears down and rebuilds from scratch
- The mapping doc exists and is written in a form suitable for interviews
