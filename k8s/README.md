# Kubernetes deployment

The manifests in this directory target a Kubernetes cluster or AKS.

## Prerequisites


## Apply

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl -n ulpf create secret generic ulpf-secrets `
  --from-literal=ULPF_API_KEY="replace-with-a-real-key" `
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
```

## Verify

```powershell
kubectl -n ulpf rollout status deployment/ulpf
kubectl -n ulpf get pods,service,hpa,pdb
kubectl -n ulpf port-forward service/ulpf 8000:8000
```

Then open `http://localhost:8000/health`.

## Smoke test

With the service port-forward running, execute:

```powershell
.\k8s\smoke-test.ps1 -BaseUrl http://localhost:8000
```

The script verifies rollout readiness, the health endpoint, canonical parsing,
Fortinet parser selection, raw-message preservation, and trace correlation.

For a remote registry, replace `ulpf:step9` with the fully qualified image
name, for example `registry.example.com/ulpf:step10.1`, and set an appropriate
`imagePullSecrets` entry if the registry is private.

## Metrics Server and autoscaling

Docker Desktop Kubernetes requires Metrics Server for HPA CPU and memory
measurements. Install it once per cluster:

```powershell
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-preferred-address-types=InternalIP,Hostname,ExternalIP"}]'
kubectl -n kube-system rollout status deployment/metrics-server
```

Verify metrics and HPA values:

```powershell
kubectl top pods -n ulpf
kubectl -n ulpf get hpa
```

The HPA should show numeric CPU and memory targets instead of `<unknown>`.

## Multi-instance load test

With the Service port-forward running, send concurrent parse requests:

```powershell
python k8s/load_test.py --base-url http://localhost:18000 --requests 100 --workers 10
```

The JSON summary reports successful and failed requests, throughput, latency,
and the number of unique trace IDs observed. The command exits with code 1 if
any request fails.

## Rolling-update resilience test

With the Service port-forward running, test availability during a Deployment
rollout restart:

```powershell
python k8s/rolling_update_test.py --base-url http://localhost:18000 --requests 200 --workers 10
```

The test triggers `kubectl rollout restart`, sends requests concurrently,
waits for rollout completion, and fails if any request fails or the rollout
does not complete successfully. Use `--no-rollout` for a measurement-only run.
