[CmdletBinding()]
param(
    [string] $ProjectRoot = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'

function Get-AzdValue {
    param([Parameter(Mandatory)][string] $Name)

    $value = azd env get-value $Name --cwd $ProjectRoot --no-prompt 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return ($value | Select-Object -Last 1).Trim().Trim('"')
}

$resourceGroup = Get-AzdValue 'AZURE_RESOURCE_GROUP'
if (-not $resourceGroup) {
    throw 'AZURE_RESOURCE_GROUP is not available. Run azd provision first.'
}

$resources = @(
    az resource list --resource-group $resourceGroup --output json |
        ConvertFrom-Json
)

$projectId = Get-AzdValue 'AZURE_AI_PROJECT_ID'
$accountId = if ($projectId) {
    $projectId -replace '/projects/[^/]+$', ''
} else {
    $null
}

$agent = $null
try {
    $agent = azd ai agent show --cwd $ProjectRoot --output json 2>$null |
        ConvertFrom-Json
} catch {
    $agent = $null
}

$deploymentName = Get-AzdValue 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
if (-not $deploymentName) {
    $deployments = Get-AzdValue 'AI_PROJECT_DEPLOYMENTS'
    if ($deployments) {
        try {
            try {
                $deploymentConfig = $deployments | ConvertFrom-Json
            } catch {
                $deploymentsJson = "`"$deployments`"" | ConvertFrom-Json
                $deploymentConfig = $deploymentsJson | ConvertFrom-Json
            }
            $deploymentName = ($deploymentConfig | Select-Object -First 1).name
        } catch {
            $deploymentName = $null
        }
    }
}

$applicationInsights = $resources |
    Where-Object type -eq 'Microsoft.Insights/components' |
    Select-Object -First 1
$logAnalytics = $resources |
    Where-Object type -eq 'Microsoft.OperationalInsights/workspaces' |
    Select-Object -First 1

$accountName = Get-AzdValue 'AZURE_AI_ACCOUNT_NAME'
$projectName = Get-AzdValue 'AZURE_AI_PROJECT_NAME'
$subscriptionId = Get-AzdValue 'AZURE_SUBSCRIPTION_ID'

[pscustomobject]@{
    SubscriptionId = $subscriptionId
    ResourceGroup = $resourceGroup
    Location = Get-AzdValue 'AZURE_LOCATION'
    FoundryAccountName = $accountName
    FoundryAccountId = $accountId
    FoundryProjectName = $projectName
    FoundryProjectId = $projectId
    FoundryProjectEndpoint = Get-AzdValue 'FOUNDRY_PROJECT_ENDPOINT'
    ModelDeploymentName = $deploymentName
    AgentName = $agent.name
    AgentVersion = $agent.version
    AgentStatus = $agent.status
    ResponsesEndpoint = $agent.agent_endpoints.responses
    ApplicationInsightsName = $applicationInsights.name
    ApplicationInsightsId = $applicationInsights.id
    LogAnalyticsName = $logAnalytics.name
    LogAnalyticsId = $logAnalytics.id
    RaiPolicyId = if ($accountId) {
        "$accountId/raiPolicies/Microsoft.DefaultV2"
    } else {
        $null
    }
}