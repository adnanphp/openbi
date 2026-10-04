# OpenBI — Kubernetes Deployment

OpenBI can be deployed to a local Kubernetes cluster (Kind) provisioned
with Terraform.

## Architecture
┌──────────────────────────────────────────────────────────────┐
│ Kind cluster: openbi │
│ │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │
│ │ control-plane │ │ worker │ │ worker2 │ │
│ └────────────────┘ └────────────────┘ └────────────────┘ │
│ │
│ namespace: openbi │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ postgres │ │ fastapi │ │ superset │ │
│ │ 1 replica │ │ 2 replicas │ │ 1 replica │ │
│ │ PVC: 2Gi │ │ │ │ PVC: 1Gi │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ │
└──────────────────────────────────────────────────────────────┘

text

## Prerequisites

- Docker
- Kind (v0.20+)
- kubectl
- Terraform (v1.5+)

## Provisioning the cluster (Terraform)

```bash
cd infrastructure/terraform
terraform init
terraform apply
This creates a Kind cluster named openbi with 1 control-plane and 2
worker nodes. The kubeconfig is stored at ~/.kube/config (you may need
to run kind export kubeconfig --name openbi to merge it).

Deploying OpenBI (kubectl + kustomize)
bash
# Switch to the openbi cluster
kubectl config use-context kind-openbi

# Apply all manifests
kubectl apply -k infrastructure/kubernetes/
Verifying the deployment
bash
# Pods
kubectl get pods -n openbi

# All resources
kubectl get all -n openbi

# PVCs
kubectl get pvc -n openbi

# Port-forward FastAPI
kubectl port-forward -n openbi svc/fastapi 8000:8000 &
curl http://localhost:8000/health
curl http://localhost:8000/kpis/summary

# Port-forward Superset
kubectl port-forward -n openbi svc/superset 8088:8088 &
curl http://localhost:8088/health
What's included
Service	Replicas	Port	Persistent Storage
postgres	1	5432	PVC 2Gi
fastapi	2	8000	—
superset	1	8088	PVC 1Gi
Design decisions
Kind over minikube — Kind runs each cluster node as a Docker
container. It's lighter, faster to start, and better suited for CI/CD.

Terraform for cluster provisioning, kubectl for workloads —
Terraform manages the cluster itself. Workloads are applied with
kubectl/kustomize so they can be updated without Terraform state
conflicts.

Kustomize over Helm — For three services, a Kustomize overlay is
simpler than authoring Helm charts. Helm is available in the cluster
for later use (ingress-nginx, Prometheus, etc.).

Init container for Superset setup — superset db upgrade,
superset fab create-admin, and superset init run in an init
container. They complete once, then the main container runs the web
server. This separates "one-time setup" from "long-running service".

Superset uses its own run-server.sh — This is the exact script
the official Superset image uses. We don't reimplement the startup
command.

Persistent volumes for state — Both Postgres data and Superset
metadata live on PVCs. Pod restarts preserve state.

Two FastAPI replicas — Demonstrates the Service load balancing.
Postgres and Superset run as single replicas because their PVCs use
ReadWriteOnce.

Cleanup
bash
# Delete the OpenBI namespace (keeps the cluster)
kubectl delete -k infrastructure/kubernetes/

# Or destroy the cluster entirely
cd infrastructure/terraform
terraform destroy
Notes on the Kind DNS issue
On Linux with systemd-resolved, Kind nodes may fail to resolve external
DNS (this affects image pulls from Docker Hub and PyPI). Two workarounds
used in this project:

Load images from the host — kind load docker-image <image> --name openbi

Use images built on the host — for FastAPI, we build openbi-fastapi:latest
locally and load it into the cluster instead of pulling at runtime.

Environment variables
The Superset deployment reads the following environment variables:

Variable	Value	Purpose
SUPERSET_SECRET_KEY	(change in prod)	Flask session signing
SUPERSET_BIND_ADDRESS	0.0.0.0	Bind address for gunicorn
SUPERSET_PORT	8088	HTTP port
FLASK_APP	superset.app:create_app()	App factory
SERVER_WORKER_AMOUNT	1	Gunicorn workers
SERVER_THREADS_AMOUNT	20	Threads per worker
SUPERSET_LOAD_EXAMPLES	false	Skip demo data
Troubleshooting
Pods stuck in ImagePullBackOff — Kind's DNS can't reach Docker Hub.
Load the image from the host with kind load docker-image.

Superset crashes with 'tcp' is not a valid port number — the
SUPERSET_BIND_ADDRESS and SUPERSET_PORT env vars must be set
explicitly. Without them, gunicorn reads a tcp:// string from the base
image's environment.

PVC stuck in Pending — the local-path-provisioner must be running.
Verify with kubectl get pods -n local-path-storage.
