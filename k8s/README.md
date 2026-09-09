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

For a remote registry, replace `ulpf:step9` with the fully qualified image
name, for example `registry.example.com/ulpf:step10.1`, and set an appropriate
`imagePullSecrets` entry if the registry is private.

## Autoscaling note

The HPA requires the Kubernetes Metrics API (`metrics.k8s.io`). If
`kubectl -n ulpf get hpa` shows `<unknown>` CPU or memory targets, install
Metrics Server for the cluster before relying on autoscaling. The ULPF pods
and Service can run normally without it.
