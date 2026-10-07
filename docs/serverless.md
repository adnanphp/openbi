# Serverless — OpenFaaS

OpenBI includes **OpenFaaS Community Edition** as its local serverless
platform. Functions are deployed as standard HTTP services, invoked
through the same Traefik ingress used by the rest of the platform.

This maps directly to AWS Lambda and GCP Cloud Functions. The concept is
identical: event-driven, stateless, scale-to-zero-capable compute.

## Why OpenFaaS (and not a Lambda emulator)

LocalStack provides an **API emulator** for AWS Lambda. That teaches you
the Lambda *SDK surface* — `create_function`, `invoke`, etc.

OpenFaaS provides the **runtime experience** — you write a function,
deploy it, it scales up on invocation, it scales down when idle. The
mental model is the same, even though the tooling is different.

For learning purposes, OpenFaaS teaches:
- Function deployment lifecycle
- Cold start behavior
- HTTP-based invocation
- Scale-to-zero (with `faas-idler`)
- Function-level observability

LocalStack Lambda teaches:
- The AWS SDK surface for Lambda
- IAM role requirements
- The `runtime` + `handler` contract
- Lambda's specific event format

Both are valuable. OpenFaaS is included because running actual functions
is more instructive than emulating the AWS control plane for them.

## Architecture
faas-cli curl / HTTP client
│ │
│ deploy │ invoke
▼ ▼
OpenFaaS gateway ◄───── Traefik (ingress)
│
├─── function registry
├─── queue-worker (async invocations)
├─── Prometheus (function metrics)
└─── NATS (queue transport)
│
▼
Function Pods (openfaas-fn namespace)
│
▼
Standard Kubernetes Deployments

text

## Installing OpenFaaS

OpenFaaS is installed via Helm (not `arkade install openfaas`, which now
defaults to the Pro edition):

```bash
kubectl create namespace openfaas-fn

helm repo add openfaas https://openfaas.github.io/faas-netes/
helm repo update

helm upgrade --install openfaas openfaas/openfaas \
  --namespace openfaas \
  --create-namespace \
  --set functionNamespace=openfaas-fn \
  --set generateBasicAuth=true \
  --set serviceType=ClusterIP
The openfaas-fn namespace must be created before the Helm install —
the chart expects it to exist.

Exposing the gateway
Traefik routes faas.openbi.local:8080 to the gateway Service:

yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: openfaas-gateway
  namespace: openfaas
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`faas.openbi.local`)
      kind: Rule
      services:
        - name: gateway
          port: 8080
/etc/hosts entry:

text
127.0.0.1  faas.openbi.local
Using the gateway
Install the CLI:

bash
curl -SLsf https://cli.openfaas.com | sudo sh
Login (retrieve the admin password from Kubernetes):

bash
PASSWORD=$(kubectl -n openfaas get secret basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode; echo)
echo -n "$PASSWORD" | faas-cli login --username admin --password-stdin --gateway http://faas.openbi.local:8080
Deploying a function
Deploy a pre-built function from the store:

bash
faas-cli store deploy nodeinfo --gateway http://faas.openbi.local:8080
List functions:

bash
faas-cli list --gateway http://faas.openbi.local:8080
Invoke:

bash
curl -s http://faas.openbi.local:8080/function/nodeinfo
Example response:

text
Hostname: nodeinfo-6c68f7cdd9-9f2k2
Arch: x64
CPUs: 8
Total mem: 7632MB
Platform: linux
Uptime: 93068
The function contract
Every OpenFaaS function is a container that:

Reads the HTTP request body from stdin (for synchronous invocations)

Writes the HTTP response body to stdout

Exits with code 0 on success

The function templates abstract this away. A Python function looks like:

python
def handle(req):
    """handle a request to the function.

    Args:
        req (str): request body
    Returns:
        str: response body
    """
    return "Hello from OpenBI!"
Cloud mapping
Local	AWS	GCP
OpenFaaS gateway	API Gateway + Lambda URL	Cloud Run + API Gateway
Function Pod	Lambda function	Cloud Function
faas-cli deploy	aws lambda create-function	gcloud functions deploy
HTTP invocation via gateway	aws lambda invoke or HTTP endpoint	HTTP trigger
OpenFaaS store	AWS Serverless Application Repository	Cloud Functions samples
Cold start	Cold start (with provisioned concurrency option)	Cold start (with min instances option)
Scale-to-zero	Yes (with faas-idler)	Yes (with --min-instances=0)	Yes (default)
Async invocation	SQS / EventBridge	Pub/Sub	Pub/Sub
Function metrics	CloudWatch / X-Ray	Cloud Monitoring / Trace
What transfers directly:

Function-as-a-container mental model

HTTP invocation contract

Cold start and warm pod behavior

Scale-to-zero and scale-on-demand

Statelessness (state goes to external services)

Async invocation via queue

Per-function environment variables and secrets

Function-level metrics and logs

What does not transfer:

OpenFaaS's specific CLI (faas-cli vs aws lambda)

OpenFaaS's store concept

NATS as the async transport (AWS uses SQS/EventBridge, GCP uses Pub/Sub)

OpenFaaS's basic-auth gateway auth (AWS uses IAM)

Provisioned concurrency semantics

What we did NOT do (and why)
Custom Python function via faas-cli build: Building a custom
function requires either Docker-in-Docker inside the Kind cluster or a
host-run registry pattern. The setup is fragile and the resulting
demonstration doesn't teach new concepts beyond what deploying a
store function already shows.

Lambda emulation via LocalStack: The LocalStack Community image
disables Lambda by default because it requires Docker-in-Docker (which
LocalStack Community doesn't fully support). Enabling Lambda would mean
a fundamentally different LocalStack configuration, adding complexity
without clear benefit for this project.

Both are noted here as future work if a specific use case arises.
