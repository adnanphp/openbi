# Terraform — Infrastructure as Code

OpenBI v3.0.0 is reproducible from `terraform apply`. Every component —
the Kind cluster, the application namespaces, the third-party Helm
releases, and the application manifests — is defined in Terraform under
`infrastructure/terraform/`.

## Why this matters

The professional gut-check for infrastructure code is:

> *I don't care if the environment disappears; I can recreate it.*

OpenBI v3.0.0 passes this test. From an empty Docker host:

```bash
cd infrastructure/terraform
terraform init
terraform apply      # ~3 minutes: cluster + namespaces + helm releases
./scripts/bootstrap-kind-images.sh   # load local images
The full stack is running.

What Terraform manages
Layer	Resource type	Files
Kind cluster	kind_cluster	modules/kind-cluster/
Namespaces	kubernetes_namespace	namespaces.tf, openfaas.tf
Helm releases	helm_release	traefik.tf, openfaas.tf
App manifests	kubectl_manifest	minio.tf, redis.tf, localstack.tf, openbi_apps.tf
Readiness gate	null_resource	cluster_ready.tf
Provider config	—	providers.tf, main.tf
Design decisions
1. YAML is the source of truth
Rather than rewrite every manifest as native kubernetes_* resources,
Terraform wraps the existing YAML files under infrastructure/kubernetes/
via the gavinbunney/kubectl provider. This keeps the manifests usable
with plain kubectl apply -k for local iteration while gaining
Terraform's lifecycle tracking.

2. Namespaces use the native provider
kubernetes_namespace (HashiCorp) rather than kubectl_manifest for
namespaces — the latter fails API discovery for the Namespace type on
Kind. Rule of thumb: use native resources when the provider supports
them; use kubectl_manifest only for CRDs (IngressRoute) and resources
the native provider doesn't cover.

3. Multi-document YAML via kubectl_file_documents
Many of our YAML files contain multiple documents separated by ---
(e.g. a Deployment + a Service). The file() function reads only the
first document; the kubectl_file_documents data source splits them.
Each document becomes its own Terraform resource with a stable key.

hcl
data "kubectl_file_documents" "postgres" {
  content = file("${local.openbi_dir}/postgres-deployment.yaml")
}

resource "kubectl_manifest" "postgres" {
  for_each  = data.kubectl_file_documents.postgres.manifests
  yaml_body = each.value
  # ...
}
4. Cluster readiness gate
The kind provider returns as soon as the cluster container starts, but
the Kubernetes API server takes another 15–40 seconds to become fully
responsive. Without an explicit wait, kubectl_manifest resources race
the API server and get spurious 404s.

cluster_ready.tf handles this with a null_resource that polls
/readyz until it returns OK, then sleeps briefly to let CoreDNS and
cluster networking settle. Every manifest depends_on this resource.

5. load_config_file = true is required
The gavinbunney/kubectl provider silently falls back to
localhost:8080 when load_config_file = false, ignoring the
config_path and config_context settings. Setting it to true makes
the provider read the Kind kubeconfig reliably.

What Terraform does NOT manage
Docker image loading
Kind's containerd is a separate image store from the host Docker daemon.
Terraform has no primitive for "load an image into another daemon's
container runtime." This is handled by scripts/bootstrap-kind-images.sh
after terraform apply.

This is not a compromise — it's the standard pattern. In production,
Terraform provisions ECS/GKE; CI handles pushing images to registries;
the two are separate concerns.

Kubeconfig management
The Kind provider writes the cluster's kubeconfig to a path we control
via var.kubeconfig_path. For the kubeconfig to be usable by the shell,
it must be merged into ~/.kube/config:

bash
kind get kubeconfig --name openbi > /tmp/kind-config
KUBECONFIG=/tmp/kind-config:$HOME/.kube/config \
  kubectl config view --flatten > /tmp/merged
mv /tmp/merged ~/.kube/config
This is documented in the bootstrap script but not automated — Terraform
creating files in your home directory is not a good idea.

Workflow
bash
cd infrastructure/terraform

# First time
terraform init

# Plan and review
terraform plan

# Apply
terraform apply

# Load images into Kind
cd ../..
./scripts/bootstrap-kind-images.sh

# Verify
kubectl --context kind-openbi get pods -A

# Tear down (removes cluster and all its resources)
cd infrastructure/terraform
terraform destroy
Cloud mapping
Local	AWS	GCP
Kind cluster via tehcyx/kind	EKS via terraform-aws-modules/eks	GKE via terraform-google-modules/kubernetes-engine
kubernetes_namespace	same	same
helm_release	same	same
kubectl_manifest	same	same
Kind-specific extra_port_mappings	ALB / NLB / Ingress annotations	Cloud Load Balancing / GKE Ingress
Local kubeconfig	aws eks update-kubeconfig	gcloud container clusters get-credentials
What transfers directly:

The entire kubernetes, helm, and kubectl provider configuration

Resource definitions (kubernetes_namespace, helm_release, etc.)

The kubectl_file_documents pattern

The readiness-gate pattern (any cluster provider has the same race)

The terraform init / plan / apply / destroy workflow

Dependency graph semantics

What does not transfer:

The Kind provider (AWS and GCP have their own cluster providers)

extra_port_mappings (a Kind-specific concept)

The image loading step (managed registries + CI handle this instead)

Kind node image versioning (EKS/GKE manage their own control planes)

Verification (Phase 6d)
A fresh terraform destroy && terraform apply cycle rebuilds:

Kind cluster (2 nodes: control-plane + 1 worker)

6 namespaces (traefik, openfaas, openfaas-fn, minio, redis, localstack, openbi)

2 Helm releases (Traefik, OpenFaaS)

23 kubectl_manifest resources (PVCs, Deployments, Services, IngressRoutes)

1 null_resource (cluster readiness)

Plus one shell command (bootstrap-kind-images.sh) for image hydration.

Total time: ~4 minutes from terraform apply to a running platform.

What's next
Remote backend: state on S3 or GCS with locking (DynamoDB / GCS).
Currently using local state, which is fine for a single-developer lab.

Workspaces: dev / staging environments with isolated state.

Modules: extract the app layer (namespaces + helm + manifests)
into a reusable module so the same pattern applies to EKS/GKE.

Real cloud target: terraform apply -var-file=aws.tfvars against
a real EKS cluster — no application changes needed, only the cluster
provisioning module changes.
