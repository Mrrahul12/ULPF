"""Sanity checks for Step 10 deployment artifacts."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_kubernetes_manifests_contain_required_workload_controls():
    deployment = (ROOT / "k8s" / "deployment.yaml").read_text(encoding="utf-8")

    assert "replicas: 2" in deployment
    assert "readinessProbe:" in deployment
    assert "livenessProbe:" in deployment
    assert "readOnlyRootFilesystem: true" in deployment
    assert "secretKeyRef:" in deployment


def test_kubernetes_autoscaling_and_disruption_manifests_exist():
    hpa = (ROOT / "k8s" / "hpa.yaml").read_text(encoding="utf-8")
    pdb = (ROOT / "k8s" / "pdb.yaml").read_text(encoding="utf-8")

    assert "kind: HorizontalPodAutoscaler" in hpa
    assert "minReplicas: 2" in hpa
    assert "maxReplicas: 10" in hpa
    assert "kind: PodDisruptionBudget" in pdb
    assert "minAvailable: 1" in pdb