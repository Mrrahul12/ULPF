# ULPF Deployment

## Local Compose deployment

1. Copy `.env.example` to `.env` and set `ULPF_API_KEY` for protected deployments.
  Set `ULPF_HTTP_PORT` when host port 8000 is already in use.
2. Build and start the application plus Prometheus:

```powershell
docker compose up --build -d
```

3. Check service readiness:

```powershell
Invoke-WebRequest http://localhost:8000/health
```

4. Open the services:

- ULPF API: http://localhost:${ULPF_HTTP_PORT}/docs (default: http://localhost:8000/docs)
- JSON metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090

5. Stop the stack:

```powershell
docker compose down
```

Prometheus data is stored in the named `prometheus_data` volume and survives
container recreation. Remove it explicitly when you want to discard history:

```powershell
docker compose down -v
```

## API example

Without authentication:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/parse `
  -ContentType "application/json" `
  -Body '{"message":"date=2026-09-09 devname=FW01 srcip=10.0.0.5 dstip=192.168.1.20 action=deny"}'
```

With `ULPF_API_KEY` configured, include the `X-API-Key` header.

## Tracing

Tracing is enabled by default. Set `ULPF_OTEL_CONSOLE_EXPORT=true` to print
completed spans during local debugging, or set
`OTEL_EXPORTER_OTLP_ENDPOINT` to send spans to an OpenTelemetry collector.
Every response includes an `X-Trace-ID` header for request correlation.

## Kubernetes deployment

Step 10 adds Kubernetes manifests for a two-replica deployment with rolling
updates, health probes, resource limits, autoscaling, and disruption protection.
See [k8s/README.md](k8s/README.md) for the apply and verification commands.

## CI/CD and image publishing

The workflow at `.github/workflows/ci-cd.yml` runs on pull requests and pushes:

- Installs dependencies and runs the full test suite
- Validates the Compose configuration
- Builds the Docker image
- Publishes `ghcr.io/<owner>/<repository>` on pushes to `main` or `master`

The publish job uses GitHub's built-in `GITHUB_TOKEN`; no registry password is
stored in the repository. For Kubernetes, replace the local image in
`k8s/deployment.yaml` with the published GHCR image and configure an image pull
secret if the package is private.

### Optional automated Kubernetes deployment

The workflow includes a gated `deploy` job. It is disabled by default. To
enable it, create the repository variable `ENABLE_K8S_DEPLOY=true` and these
repository secrets:

- `KUBE_CONFIG_B64`: base64-encoded kubeconfig for the target cluster
- `GHCR_USERNAME`: GitHub username or machine user for image pulls
- `GHCR_TOKEN`: read-only GHCR token
- `ULPF_API_KEY`: application API key, if authentication is required

The deploy job creates or updates the `ulpf` namespace, configures the GHCR
pull secret, deploys the manifests, selects the exact image built for the
commit, and waits for rollout completion.

For local verification, port-forward the Service and run the smoke test:

```powershell
kubectl -n ulpf port-forward service/ulpf 18000:8000
.\k8s\smoke-test.ps1 -BaseUrl http://localhost:18000
```

Run a concurrent multi-replica load test:

```powershell
python k8s/load_test.py --base-url http://localhost:18000 --requests 100 --workers 10
```
