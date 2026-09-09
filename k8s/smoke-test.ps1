[CmdletBinding()]
param(
    [string]$Namespace = "ulpf",
    [string]$BaseUrl = "http://localhost:18000",
    [string]$ApiKey = "",
    [int]$ExpectedReplicas = 2
)

$ErrorActionPreference = "Stop"

Write-Host "Checking deployment rollout..."
kubectl -n $Namespace rollout status deployment/ulpf --timeout=120s

$deployment = kubectl -n $Namespace get deployment ulpf -o json | ConvertFrom-Json
if ($deployment.status.readyReplicas -ne $ExpectedReplicas) {
    throw "Expected $ExpectedReplicas ready replicas, found $($deployment.status.readyReplicas)."
}

$headers = @{}
if ($ApiKey) {
    $headers["X-API-Key"] = $ApiKey
}

Write-Host "Checking service health at $BaseUrl/health..."
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Headers $headers
if ($health.status -ne "ok") {
    throw "Health check returned an unexpected status: $($health.status)"
}

$rawMessage = 'date=2026-09-09 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 action=deny'
$body = @{ message = $rawMessage } | ConvertTo-Json

Write-Host "Checking canonical parsing..."
$response = Invoke-WebRequest -Method Post -Uri "$BaseUrl/parse" -Headers $headers -ContentType "application/json" -Body $body
$eventResponse = $response.Content | ConvertFrom-Json
if ($eventResponse.accepted -ne $true) {
    throw "The parse endpoint rejected the smoke-test log."
}
if ($eventResponse.event.raw.message -ne $rawMessage) {
    throw "The canonical event did not preserve the original raw message."
}
if ($eventResponse.event.provenance.parser -ne "fortinet") {
    throw "Expected the Fortinet parser, found $($eventResponse.event.provenance.parser)."
}

Write-Host "Kubernetes smoke test passed. Trace ID: $($response.Headers['X-Trace-ID'])"
