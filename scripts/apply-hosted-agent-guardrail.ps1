[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ProjectEndpoint,

    [Parameter(Mandatory)]
    [string] $AgentName,

    [Parameter(Mandatory)]
    [string] $SourceVersion,

    [Parameter(Mandatory)]
    [string] $RaiPolicyId
)

$ErrorActionPreference = 'Stop'
$apiVersion = 'v1'
$baseUri = $ProjectEndpoint.TrimEnd('/')
$token = az account get-access-token `
    --resource https://ai.azure.com `
    --query accessToken `
    --output tsv

if (-not $token) {
    throw 'Unable to acquire a Microsoft Foundry access token.'
}

$client = [System.Net.Http.HttpClient]::new()
$client.DefaultRequestHeaders.Authorization = `
    [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)

try {
    $versionUri = "$baseUri/agents/$AgentName/versions/$SourceVersion`?api-version=$apiVersion"
    $sourceJson = $client.GetStringAsync($versionUri).GetAwaiter().GetResult()
    $source = $sourceJson | ConvertFrom-Json

    $raiConfig = [pscustomobject]@{
        rai_policy_name = $RaiPolicyId
    }
    $source.definition | Add-Member `
        -NotePropertyName rai_config `
        -NotePropertyValue $raiConfig `
        -Force

    $metadata = [ordered]@{
        description = $source.description
        metadata = $source.metadata
        definition = $source.definition
    } | ConvertTo-Json -Depth 50 -Compress

    $downloadUri = "$baseUri/agents/$AgentName/code:download?api-version=$apiVersion&agent_version=$SourceVersion"
    $downloadResponse = $client.GetAsync($downloadUri).GetAwaiter().GetResult()
    $null = $downloadResponse.EnsureSuccessStatusCode()
    $codeBytes = $downloadResponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $codeHash = [Convert]::ToHexString($sha256.ComputeHash($codeBytes)).ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }

    $multipart = [System.Net.Http.MultipartFormDataContent]::new()
    try {
        $metadataContent = [System.Net.Http.StringContent]::new(
            $metadata,
            [System.Text.Encoding]::UTF8,
            'application/json'
        )
        $multipart.Add($metadataContent, 'metadata', 'metadata.json')

        $codeContent = [System.Net.Http.ByteArrayContent]::new($codeBytes)
        $codeContent.Headers.ContentType = `
            [System.Net.Http.Headers.MediaTypeHeaderValue]::new('application/zip')
        $multipart.Add($codeContent, 'code', "$AgentName.zip")

        $request = [System.Net.Http.HttpRequestMessage]::new(
            [System.Net.Http.HttpMethod]::Post,
            "$baseUri/agents/$AgentName/versions?api-version=$apiVersion"
        )
        try {
            $request.Headers.Add('x-ms-code-zip-sha256', $codeHash)
            $request.Content = $multipart
            $response = $client.SendAsync($request).GetAwaiter().GetResult()
            $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            if (-not $response.IsSuccessStatusCode) {
                throw "Guardrail version creation failed ($([int]$response.StatusCode)): $responseBody"
            }

            $created = $responseBody | ConvertFrom-Json
            [pscustomobject]@{
                Agent = $created.name
                Version = $created.version
                Status = $created.status
                RaiPolicy = $created.definition.rai_config.rai_policy_name
                SourceCodeSha256 = $codeHash
            }
        }
        finally {
            $request.Dispose()
        }
    }
    finally {
        $multipart.Dispose()
    }
}
finally {
    $client.Dispose()
    Remove-Variable token -ErrorAction SilentlyContinue
}