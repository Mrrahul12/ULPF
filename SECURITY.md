# ULPF Security Guide

## API Authentication

ULPF supports optional API-key authentication through the `ULPF_API_KEY`
environment variable.

The API key must never be hard-coded in source code, Dockerfiles, Kubernetes
manifests, or committed configuration files.

Clients send the key using:

    X-API-Key: <api-key>

Invalid or missing credentials return HTTP 401 without exposing the configured
secret.

## API Key Rotation

### Docker / environment-based deployment

1. Generate a new strong API key outside the repository.
2. Update the `ULPF_API_KEY` environment variable.
3. Restart the application.
4. Verify authenticated requests with the new key.
5. Revoke the old key.

### Kubernetes

Create or replace the Kubernetes Secret without committing the Secret
manifest:

    kubectl -n ulpf create secret generic ulpf-secrets \
      --from-literal=ULPF_API_KEY="$ULPF_API_KEY" \
      --dry-run=client -o yaml | kubectl apply -f -

Restart the deployment:

    kubectl -n ulpf rollout restart deployment/ulpf

Verify the rollout:

    kubectl -n ulpf rollout status deployment/ulpf

Never commit the generated Secret YAML or the actual API key.

## NetworkPolicy

ULPF includes `k8s/networkpolicy.yaml`.

The policy restricts ingress to the ULPF pods while allowing TCP traffic to
the application port 8000.

The policy has been verified against the local Kubernetes service using an
in-cluster health check.

## TLS / Ingress

`k8s/ingress-tls.yaml` provides a template for remote Kubernetes clusters
using an NGINX Ingress controller.

The template:

- redirects HTTP traffic to HTTPS;
- routes HTTPS traffic to the `ulpf` Service;
- references the Kubernetes Secret `ulpf-tls`;
- does not contain a certificate or private key.

The example hostname `ulpf.example.com` must be replaced with the real
deployment hostname.

The local Docker Desktop cluster currently has no Ingress controller, so this
manifest should not be applied locally until an appropriate controller is
installed.

Create the TLS Secret separately on the remote cluster:

    kubectl -n ulpf create secret tls ulpf-tls \
      --cert=path/to/tls.crt \
      --key=path/to/tls.key

Never commit `tls.crt`, `tls.key`, or generated TLS Secret YAML containing
private key material.

## Request Protection

ULPF limits incoming request bodies and validates log messages before
processing.

Oversized requests are rejected safely, and empty or whitespace-only messages
are rejected.

## Vulnerability Scanning

CI performs:

- Python dependency vulnerability scanning using `pip-audit`;
- Docker image vulnerability scanning using Trivy.

HIGH and CRITICAL container vulnerabilities cause the CI security scan to
fail when applicable unfixed vulnerabilities are detected.

## Logging

ULPF request logging records request metadata such as:

- HTTP method;
- request path;
- response status;
- request ID;
- trace ID;
- request duration.

API keys and raw authentication headers must not be written to application
logs.