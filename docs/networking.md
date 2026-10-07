# Networking — Ingress with Traefik

OpenBI services in the Kind cluster are exposed through **Traefik** as the
ingress controller. This document describes how the routing works, how to
add new services, and how it maps to managed cloud services.

## Architecture
Developer's browser
│
│ HTTP to localhost:8080
▼
Docker host port 8080 ────► Kind node port 80
│
│ hostPort (Traefik pod binds node port 80)
▼
Traefik (in-cluster)
│
│ Host header routing
│
┌──────────────┼──────────────┐
▼ ▼ ▼
api.openbi.local superset.openbi.local traefik.openbi.local
│ │ │
▼ ▼ ▼
fastapi:8000 superset:8088 dashboard@internal

text

## Host port mapping

The Kind cluster is configured (via Terraform) to map:

| Host port | Kind node port | Purpose |
| --------- | -------------- | ------- |
| 8080      | 80             | HTTP ingress |
| 8443      | 443            | HTTPS ingress |

Traefik's Helm install binds `hostPort: 80` and `hostPort: 443` on the
`ingress-ready=true` node, so it receives traffic on those ports.

## DNS

The following entries are added to `/etc/hosts`:
127.0.0.1 traefik.openbi.local
127.0.0.1 api.openbi.local
127.0.0.1 superset.openbi.local

text

Add these to your `/etc/hosts` after setting up the Kind cluster.

## Installing Traefik

Traefik is installed with Helm:

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f infrastructure/kubernetes/traefik-values.yaml
The values file (infrastructure/kubernetes/traefik-values.yaml) configures:

hostPort: 80 for HTTP, hostPort: 443 for HTTPS

nodeSelector: ingress-ready=true — pins Traefik to the Kind control-plane

Toleration for the control-plane taint

Dashboard enabled at traefik.openbi.local

Routing services
Routes are declared as Traefik IngressRoute custom resources, in
infrastructure/kubernetes/ingress-routes.yaml.

Example — route api.openbi.local to the fastapi service:

yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: openbi-api
  namespace: openbi
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`api.openbi.local`)
      kind: Rule
      services:
        - name: fastapi
          port: 8000
Apply with:

bash
kubectl apply -f infrastructure/kubernetes/ingress-routes.yaml
Adding a new service
Deploy the service in the openbi namespace

Add a new IngressRoute resource to ingress-routes.yaml

Add a 127.0.0.1 <name>.openbi.local entry to /etc/hosts

kubectl apply -f infrastructure/kubernetes/ingress-routes.yaml

Test with curl http://<name>.openbi.local:8080/

Verifying
bash
# List active routes
curl -s http://traefik.openbi.local:8080/api/rawdata | jq '.routers'

# Health check each service
curl -s http://api.openbi.local:8080/health
curl -s -o /dev/null -w "%{http_code}\n" http://superset.openbi.local:8080/
Cloud mapping
Local	AWS	GCP
Traefik	Application Load Balancer (ALB)	Cloud Load Balancing
IngressRoute	ALB listener rules	URL map rules
Host header routing	ALB host-based routing	HTTP(S) LB host rules
NodePort + Kind	Target groups + EC2 node ports	Instance groups + backends
/etc/hosts entries	Route 53 hosted zone	Cloud DNS zone
What transfers:

Host-based routing concepts

Path-based routing concepts

TLS termination at the edge

Health checks and backend pools

Multiple services behind one entrypoint

What does not transfer:

The exact CRD (IngressRoute is Traefik-specific)

NodePort mechanics (AWS uses target groups, not NodePorts)

/etc/hosts (production uses real DNS)
