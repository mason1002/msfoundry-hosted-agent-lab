[CmdletBinding()]
param(
    [string] $ProjectRoot = (Split-Path $PSScriptRoot -Parent),
    [string] $ConnectionName
)

$ErrorActionPreference = 'Stop'
$context = & (Join-Path $PSScriptRoot 'get-training-context.ps1') `
    -ProjectRoot $ProjectRoot

if (-not $context.FoundryProjectId) {
    throw 'Foundry project was not found. Run azd provision first.'
}
if (-not $context.ApplicationInsightsId) {
    throw 'Application Insights was not found in the training resource group.'
}

if (-not $ConnectionName) {
    $ConnectionName = $context.ApplicationInsightsName
}

$payload = @{
    properties = @{
        authType = 'ProjectManagedIdentity'
        category = 'AppInsights'
        target = $context.ApplicationInsightsId
        metadata = @{
            purpose = 'agent-tracing-monitoring'
        }
    }
} | ConvertTo-Json -Depth 10

$url = "https://management.azure.com$($context.FoundryProjectId)/connections/${ConnectionName}?api-version=2025-06-01"
$payloadPath = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText($payloadPath, $payload, [System.Text.Encoding]::UTF8)
    az rest --method put --url $url --body "@$payloadPath" --headers 'Content-Type=application/json' --output none
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to create the Application Insights project connection.'
    }
} finally {
    Remove-Item $payloadPath -Force -ErrorAction SilentlyContinue
}

az rest --method get --url $url `
    --query '{Name:name,Category:properties.category,AuthType:properties.authType,Target:properties.target}' `
    --output table