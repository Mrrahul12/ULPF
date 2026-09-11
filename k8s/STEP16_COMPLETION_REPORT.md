# ULPF Step 16 — Rolling-Update Resilience Test

## Status

**COMPLETE**

## Objective

Verify that ULPF continues serving requests while Kubernetes performs
a rolling update of the application Deployment.

## Test Environment

- Kubernetes: Docker Desktop Kubernetes
- Namespace: `ulpf`
- Deployment: `ulpf`
- Replicas: 2
- Service Port: 8000
- Local Test Port: 8080
- Rolling Strategy: `RollingUpdate`
- Max Surge: 1
- Max Unavailable: 0
- Readiness Endpoint: `/health`
- Termination Grace Period: 30 seconds

## Test Procedure

1. Verified Kubernetes cluster availability.
2. Verified ULPF Deployment.
3. Verified two healthy replicas.
4. Verified Kubernetes Service endpoints.
5. Established continuous HTTP traffic through the Service.
6. Triggered a Deployment rolling restart.
7. Continued traffic while pods were replaced.
8. Waited for Kubernetes rollout completion.
9. Verified final pod readiness.
10. Verified the ULPF health endpoint after rollout.

## Resilience Architecture

```text
                 Continuous Requests
                         |
                         v
                ULPF Kubernetes Service
                         |
              +----------+----------+
              |                     |
              v                     v
          ULPF Pod 1            ULPF Pod 2
          Ready 1/1             Ready 1/1
              |                     |
              +----------+----------+
                         |
                    Rolling Update
                         |
             +-----------+-----------+
             |                       |
        New Pod Ready          Old Pod Terminating
             |                       |
             +-----------+-----------+
                         |
                  Service Continues
                    Serving Traffic