<#
.SYNOPSIS
Enables ECS Service Connect between the StudyPilot API and UI services.

.DESCRIPTION
Requires AWS CLI credentials and the region, ECS cluster, service names, and
Cloud Map namespace to be supplied explicitly. The Qdrant service must already
be healthy in the same Service Connect namespace. Use -WhatIf to preview changes.

.EXAMPLE
.\Connect-StudyPilot-Services.ps1 -Region eu-west-2 -Cluster study-staging `
    -ApiService studypilot-api -UiService studypilot-ui -Namespace study-staging
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [string]$Region,

    [Parameter(Mandatory = $true)]
    [string]$Cluster,

    [Parameter(Mandatory = $true)]
    [string]$ApiService,

    [Parameter(Mandatory = $true)]
    [string]$UiService,

    [Parameter(Mandatory = $true)]
    [string]$Namespace,

    [string]$SecretId = 'studypilot/staging/agent-api-key',
    [string]$ApiPortName = 'api',
    [string]$ApiDiscoveryName = 'studypilot-api',
    [string]$QdrantService = 'studypilot-qdrant-staging',
    [string]$QdrantSecretId = 'studypilot/staging/qdrant-api-key',
    [string]$QdrantPortName = 'qdrant-http',
    [string]$QdrantDiscoveryName = 'studypilot-qdrant',
    [string]$QdrantCollection = 'ai_study_notes'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-AwsJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & aws @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed (exit $LASTEXITCODE): aws $($Arguments -join ' ')`n$($output -join "`n")"
    }

    try {
        return (($output -join "`n") | ConvertFrom-Json)
    } catch {
        throw "AWS CLI returned invalid JSON for 'aws $($Arguments -join ' ')': $_"
    }
}

function Invoke-Aws {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & aws @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed (exit $LASTEXITCODE): aws $($Arguments -join ' ')`n$($output -join "`n")"
    }
    return $output
}

function Get-CleanTaskDefinition {
    param([Parameter(Mandatory = $true)]$TaskDefinition)

    foreach ($property in @(
        'taskDefinitionArn', 'revision', 'status', 'requiresAttributes',
        'compatibilities', 'registeredAt', 'registeredBy', 'deregisteredAt'
    )) {
        $TaskDefinition.PSObject.Properties.Remove($property) | Out-Null
    }
    return $TaskDefinition
}

function Get-OptionalPropertyValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $json = ConvertTo-Json -InputObject $Value -Depth 80
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw 'AWS CLI was not found. Install AWS CLI v2 and reopen PowerShell.'
}

$null = Invoke-AwsJson @('sts', 'get-caller-identity', '--region', $Region, '--output', 'json')

$namespaceList = Invoke-AwsJson @('servicediscovery', 'list-namespaces', '--region', $Region, '--output', 'json')
$namespaceMatches = @($namespaceList.Namespaces | Where-Object {
    $_.Name -eq $Namespace -or $_.Arn -eq $Namespace -or $_.Id -eq $Namespace
})
if ($namespaceMatches.Count -ne 1) {
    throw "Expected one Cloud Map namespace matching '$Namespace' in region '$Region'; found $($namespaceMatches.Count). Pass its exact name, ARN, or ID."
}
$namespaceInfo = $namespaceMatches[0]
$namespaceIdentifiers = @($namespaceInfo.Arn, $namespaceInfo.Name, $namespaceInfo.Id)

$qdrantResult = Invoke-AwsJson @(
    'ecs', 'describe-services',
    '--cluster', $Cluster,
    '--services', $QdrantService,
    '--region', $Region,
    '--output', 'json'
)
if (@($qdrantResult.failures).Count -gt 0) {
    throw "ECS could not describe Qdrant service '$QdrantService': $($qdrantResult.failures | ConvertTo-Json -Depth 10 -Compress)"
}
$qdrantSvc = $qdrantResult.services | Where-Object { $_.serviceName -eq $QdrantService } | Select-Object -First 1
if (-not $qdrantSvc -or $qdrantSvc.status -ne 'ACTIVE') {
    throw "Qdrant ECS service '$QdrantService' is not active in cluster '$Cluster'. Deploy it and wait for it to stabilize first."
}
if ($qdrantSvc.desiredCount -lt 1 -or $qdrantSvc.runningCount -lt $qdrantSvc.desiredCount) {
    throw "Qdrant service '$QdrantService' is not healthy yet ($($qdrantSvc.runningCount)/$($qdrantSvc.desiredCount) tasks running). Wait for it to stabilize first."
}
$qdrantConnectConfig = Get-OptionalPropertyValue $qdrantSvc 'serviceConnectConfiguration'
if ((Get-OptionalPropertyValue $qdrantConnectConfig 'enabled') -ne $true) {
    throw "Qdrant service '$QdrantService' does not have Service Connect enabled."
}
$qdrantNamespace = Get-OptionalPropertyValue $qdrantConnectConfig 'namespace'
if ($qdrantNamespace -notin $namespaceIdentifiers) {
    throw "Qdrant service '$QdrantService' is connected to namespace '$qdrantNamespace', not '$Namespace'."
}
$qdrantConnectServices = Get-OptionalPropertyValue $qdrantConnectConfig 'services'
$qdrantConnectService = $qdrantConnectServices | Where-Object {
    $_ -and $_.portName -eq $QdrantPortName -and $_.discoveryName -eq $QdrantDiscoveryName
} | Select-Object -First 1
if (-not $qdrantConnectService) {
    throw "Qdrant service '$QdrantService' does not publish '$QdrantDiscoveryName' on port name '$QdrantPortName'."
}

$servicesResult = Invoke-AwsJson @(
    'ecs', 'describe-services',
    '--cluster', $Cluster,
    '--services', $ApiService, $UiService,
    '--region', $Region,
    '--output', 'json'
)
if (@($servicesResult.failures).Count -gt 0) {
    throw "ECS could not describe one or more services: $($servicesResult.failures | ConvertTo-Json -Depth 10 -Compress)"
}
$apiSvc = $servicesResult.services | Where-Object { $_.serviceName -eq $ApiService } | Select-Object -First 1
$uiSvc = $servicesResult.services | Where-Object { $_.serviceName -eq $UiService } | Select-Object -First 1
if (-not $apiSvc -or -not $uiSvc) {
    throw "Could not find both ECS services '$ApiService' and '$UiService' in cluster '$Cluster'."
}

$apiTdInfo = Invoke-AwsJson @(
    'ecs', 'describe-task-definition',
    '--task-definition', $apiSvc.taskDefinition,
    '--region', $Region,
    '--output', 'json'
)
$apiTask = $apiTdInfo.taskDefinition
$apiContainer = $apiTask.containerDefinitions | Where-Object { $_.name -eq 'api' } | Select-Object -First 1
if (-not $apiContainer) {
    throw "Container 'api' was not found in task definition '$($apiSvc.taskDefinition)'."
}
$apiPortMappings = @($apiContainer.portMappings | Where-Object { $_.containerPort -eq 8000 })
if ($apiPortMappings.Count -ne 1) {
    throw "Expected exactly one port mapping for container port 8000 in '$($apiSvc.taskDefinition)'; found $($apiPortMappings.Count)."
}
$apiPortMapping = $apiPortMappings[0]
$currentApiPortName = Get-OptionalPropertyValue $apiPortMapping 'name'
if ($currentApiPortName -and $currentApiPortName -ne $ApiPortName) {
    throw "Port 8000 is already named '$currentApiPortName', not '$ApiPortName'. Resolve the task definition manually before continuing."
}
$apiNeedsTaskDefinition = ($currentApiPortName -ne $ApiPortName)

$uiTdInfo = Invoke-AwsJson @(
    'ecs', 'describe-task-definition',
    '--task-definition', $uiSvc.taskDefinition,
    '--region', $Region,
    '--output', 'json'
)
$uiTask = $uiTdInfo.taskDefinition
$uiContainer = $uiTask.containerDefinitions | Where-Object { $_.name -eq 'ui' } | Select-Object -First 1
if (-not $uiContainer) {
    throw "Container 'ui' was not found in task definition '$($uiSvc.taskDefinition)'."
}

$secretResult = Invoke-AwsJson @(
    'secretsmanager', 'describe-secret',
    '--secret-id', $SecretId,
    '--region', $Region,
    '--output', 'json'
)
if (-not $secretResult.ARN) {
    throw "Could not retrieve the ARN for secret '$SecretId'."
}
$secretArn = $secretResult.ARN

$qdrantSecretResult = Invoke-AwsJson @(
    'secretsmanager', 'describe-secret',
    '--secret-id', $QdrantSecretId,
    '--region', $Region,
    '--output', 'json'
)
if (-not $qdrantSecretResult.ARN) {
    throw "Could not retrieve the ARN for Qdrant secret '$QdrantSecretId'."
}
$qdrantSecretArn = $qdrantSecretResult.ARN

$qdrantUrl = "http://${QdrantDiscoveryName}:6333"
$existingApiEnvironment = Get-OptionalPropertyValue $apiContainer 'environment'
$existingApiSecrets = Get-OptionalPropertyValue $apiContainer 'secrets'
$apiEnvironment = @($existingApiEnvironment | Where-Object {
    $_ -and $_.name -notin @('RETRIEVAL_MODE', 'QDRANT_URL', 'QDRANT_COLLECTION')
})
$apiEnvironment += @(
    [pscustomobject]@{ name = 'RETRIEVAL_MODE'; value = 'qdrant' },
    [pscustomobject]@{ name = 'QDRANT_URL'; value = $qdrantUrl },
    [pscustomobject]@{ name = 'QDRANT_COLLECTION'; value = $QdrantCollection }
)
$apiSecrets = @($existingApiSecrets | Where-Object { $_ -and $_.name -ne 'QDRANT_API_KEY' })
$apiSecrets += [pscustomobject]@{ name = 'QDRANT_API_KEY'; valueFrom = $qdrantSecretArn }

$currentRetrievalMode = $existingApiEnvironment | Where-Object { $_ -and $_.name -eq 'RETRIEVAL_MODE' } | Select-Object -First 1
$currentQdrantUrl = $existingApiEnvironment | Where-Object { $_ -and $_.name -eq 'QDRANT_URL' } | Select-Object -First 1
$currentQdrantCollection = $existingApiEnvironment | Where-Object { $_ -and $_.name -eq 'QDRANT_COLLECTION' } | Select-Object -First 1
$currentQdrantSecret = $existingApiSecrets | Where-Object { $_ -and $_.name -eq 'QDRANT_API_KEY' } | Select-Object -First 1
$apiNeedsTaskDefinition = $apiNeedsTaskDefinition -or
    -not $currentRetrievalMode -or $currentRetrievalMode.value -ne 'qdrant' -or
    -not $currentQdrantUrl -or $currentQdrantUrl.value -ne $qdrantUrl -or
    -not $currentQdrantCollection -or $currentQdrantCollection.value -ne $QdrantCollection -or
    -not $currentQdrantSecret -or $currentQdrantSecret.valueFrom -ne $qdrantSecretArn
if ($apiNeedsTaskDefinition) {
    if ($currentApiPortName -ne $ApiPortName) {
        $apiPortMapping | Add-Member -NotePropertyName 'name' -NotePropertyValue $ApiPortName -Force
    }
    $apiContainer | Add-Member -NotePropertyName 'environment' -NotePropertyValue $apiEnvironment -Force
    $apiContainer | Add-Member -NotePropertyName 'secrets' -NotePropertyValue $apiSecrets -Force
    $apiTask = Get-CleanTaskDefinition $apiTask
}

$existingUiEnvironment = Get-OptionalPropertyValue $uiContainer 'environment'
$existingUiSecrets = Get-OptionalPropertyValue $uiContainer 'secrets'
$uiEnvironment = @($existingUiEnvironment | Where-Object { $_ -and $_.name -ne 'API_URL' })
$uiEnvironment += [pscustomobject]@{ name = 'API_URL'; value = "http://${ApiDiscoveryName}:8000" }
$uiSecrets = @($existingUiSecrets | Where-Object { $_ -and $_.name -ne 'AGENT_API_KEY' })
$uiSecrets += [pscustomobject]@{ name = 'AGENT_API_KEY'; valueFrom = $secretArn }

$currentApiUrl = $existingUiEnvironment | Where-Object { $_ -and $_.name -eq 'API_URL' } | Select-Object -First 1
$currentApiSecret = $existingUiSecrets | Where-Object { $_ -and $_.name -eq 'AGENT_API_KEY' } | Select-Object -First 1
$uiNeedsTaskDefinition = (
    -not $currentApiUrl -or
    $currentApiUrl.value -ne "http://${ApiDiscoveryName}:8000" -or
    -not $currentApiSecret -or
    $currentApiSecret.valueFrom -ne $secretArn
)
if ($uiNeedsTaskDefinition) {
    $uiContainer | Add-Member -NotePropertyName 'environment' -NotePropertyValue $uiEnvironment -Force
    $uiContainer | Add-Member -NotePropertyName 'secrets' -NotePropertyValue $uiSecrets -Force
    $uiTask = Get-CleanTaskDefinition $uiTask
}

$apiConnectConfig = Get-OptionalPropertyValue $apiSvc 'serviceConnectConfiguration'
$apiConnectEnabled = (Get-OptionalPropertyValue $apiConnectConfig 'enabled') -eq $true
$existingApiNamespace = Get-OptionalPropertyValue $apiConnectConfig 'namespace'
if ($apiConnectEnabled -and $existingApiNamespace -notin $namespaceIdentifiers) {
    throw "The API service is already connected to namespace '$existingApiNamespace', not '$Namespace'. Resolve the existing configuration before continuing."
}

$existingApiConnectServices = Get-OptionalPropertyValue $apiConnectConfig 'services'
$currentApiConnectService = $existingApiConnectServices | Where-Object { $_ -and $_.portName -eq $ApiPortName } | Select-Object -First 1
$currentApiAliases = Get-OptionalPropertyValue $currentApiConnectService 'clientAliases'
$currentApiAlias = $currentApiAliases | Where-Object {
    $_ -and
    $_.port -eq 8000 -and $_.dnsName -eq $ApiDiscoveryName
} | Select-Object -First 1
$apiNeedsServiceConnect = (
    -not $apiConnectEnabled -or
    -not $currentApiConnectService -or
    (Get-OptionalPropertyValue $currentApiConnectService 'discoveryName') -ne $ApiDiscoveryName -or
    -not $currentApiAlias
)

$apiConnectServices = @(
    $existingApiConnectServices | Where-Object { $_ -and $_.portName -ne $ApiPortName }
)
$apiConnectServices += [pscustomobject]@{
    portName = $ApiPortName
    discoveryName = $ApiDiscoveryName
    clientAliases = @([pscustomobject]@{ port = 8000; dnsName = $ApiDiscoveryName })
}
$serverConfig = @{
    enabled = $true
    namespace = $namespaceInfo.Arn
    services = $apiConnectServices
}
$apiLogConfiguration = Get-OptionalPropertyValue $apiConnectConfig 'logConfiguration'
if ($apiLogConfiguration) {
    $serverConfig.logConfiguration = $apiLogConfiguration
}

$uiConnectConfig = Get-OptionalPropertyValue $uiSvc 'serviceConnectConfiguration'
$uiConnectEnabled = (Get-OptionalPropertyValue $uiConnectConfig 'enabled') -eq $true
$uiExistingNamespace = Get-OptionalPropertyValue $uiConnectConfig 'namespace'
if ($uiConnectEnabled -and $uiExistingNamespace -notin $namespaceIdentifiers) {
    throw "The UI service is already connected to namespace '$uiExistingNamespace', not '$Namespace'. Resolve the existing configuration before continuing."
}
$uiNeedsServiceConnect = (
    -not $uiConnectEnabled -or
    $uiExistingNamespace -notin $namespaceIdentifiers
)
$clientConfig = @{ enabled = $true; namespace = $namespaceInfo.Arn }
$uiLogConfiguration = Get-OptionalPropertyValue $uiConnectConfig 'logConfiguration'
if ($uiLogConfiguration) {
    $clientConfig.logConfiguration = $uiLogConfiguration
}

$apiNeedsUpdate = $apiNeedsTaskDefinition -or $apiNeedsServiceConnect
$uiNeedsUpdate = $uiNeedsTaskDefinition -or $uiNeedsServiceConnect
if (-not $apiNeedsUpdate -and -not $uiNeedsUpdate) {
    Write-Host 'Both ECS services are already configured for StudyPilot Service Connect.'
    return
}

$tempFiles = @()
try {
    $apiTaskDefinitionFile = $null
    if ($apiNeedsTaskDefinition) {
        $apiTaskDefinitionFile = Join-Path $env:TEMP ("studypilot-api-task-{0}.json" -f [guid]::NewGuid())
        Write-JsonFile -Value $apiTask -Path $apiTaskDefinitionFile
        $tempFiles += $apiTaskDefinitionFile
    }
    $uiTaskDefinitionFile = $null
    if ($uiNeedsTaskDefinition) {
        $uiTaskDefinitionFile = Join-Path $env:TEMP ("studypilot-ui-task-{0}.json" -f [guid]::NewGuid())
        Write-JsonFile -Value $uiTask -Path $uiTaskDefinitionFile
        $tempFiles += $uiTaskDefinitionFile
    }
    $serverConfigFile = $null
    if ($apiNeedsServiceConnect) {
        $serverConfigFile = Join-Path $env:TEMP ("studypilot-api-connect-{0}.json" -f [guid]::NewGuid())
        Write-JsonFile -Value $serverConfig -Path $serverConfigFile
        $tempFiles += $serverConfigFile
    }
    $clientConfigFile = $null
    if ($uiNeedsServiceConnect) {
        $clientConfigFile = Join-Path $env:TEMP ("studypilot-ui-connect-{0}.json" -f [guid]::NewGuid())
        Write-JsonFile -Value $clientConfig -Path $clientConfigFile
        $tempFiles += $clientConfigFile
    }

    Write-Host "Region: $Region"
    Write-Host "Cluster: $Cluster"
    Write-Host "API service: $ApiService"
    Write-Host "UI service: $UiService"
    Write-Host "Service Connect namespace: $($namespaceInfo.Name) ($($namespaceInfo.Arn))"
    Write-Host "API secret: $SecretId"
    Write-Host "Qdrant service: $QdrantService ($qdrantUrl)"
    Write-Host "Qdrant secret: $QdrantSecretId"
    if (-not $PSCmdlet.ShouldProcess(
        "ECS cluster '$Cluster' in '$Region'",
        'Register task definitions and update StudyPilot API/UI services for Service Connect'
    )) {
        return
    }

    $apiTaskDefinitionArn = $apiSvc.taskDefinition
    if ($apiNeedsTaskDefinition) {
        $apiRegistration = Invoke-AwsJson @(
            'ecs', 'register-task-definition',
            '--cli-input-json', "file://$apiTaskDefinitionFile",
            '--region', $Region,
            '--output', 'json'
        )
        $apiTaskDefinitionArn = $apiRegistration.taskDefinition.taskDefinitionArn
        Write-Host "Registered API task definition: $apiTaskDefinitionArn"
    }

    $uiTaskDefinitionArn = $uiSvc.taskDefinition
    if ($uiNeedsTaskDefinition) {
        $uiRegistration = Invoke-AwsJson @(
            'ecs', 'register-task-definition',
            '--cli-input-json', "file://$uiTaskDefinitionFile",
            '--region', $Region,
            '--output', 'json'
        )
        $uiTaskDefinitionArn = $uiRegistration.taskDefinition.taskDefinitionArn
        Write-Host "Registered UI task definition: $uiTaskDefinitionArn"
    }

    if ($apiNeedsUpdate) {
        $apiUpdateArguments = @(
            'ecs', 'update-service',
            '--cluster', $Cluster,
            '--service', $ApiService,
            '--task-definition', $apiTaskDefinitionArn,
            '--region', $Region,
            '--output', 'json'
        )
        if ($apiNeedsServiceConnect) {
            $apiUpdateArguments += @('--service-connect-configuration', "file://$serverConfigFile")
        }
        $apiUpdate = Invoke-AwsJson $apiUpdateArguments
        Write-Host "API update requested: $($apiUpdate.service.taskDefinition)"
        Write-Host 'Verifying API deployment reaches steady state...'
        Invoke-Aws @('ecs', 'wait', 'services-stable', '--cluster', $Cluster, '--services', $ApiService, '--region', $Region) | Out-Null
    }

    if ($uiNeedsUpdate) {
        $uiUpdateArguments = @(
            'ecs', 'update-service',
            '--cluster', $Cluster,
            '--service', $UiService,
            '--task-definition', $uiTaskDefinitionArn,
            '--region', $Region,
            '--output', 'json'
        )
        if ($uiNeedsServiceConnect) {
            $uiUpdateArguments += @('--service-connect-configuration', "file://$clientConfigFile")
        }
        $uiUpdate = Invoke-AwsJson $uiUpdateArguments
        Write-Host "UI update requested: $($uiUpdate.service.taskDefinition)"
        Write-Host 'Verifying UI deployment reaches steady state...'
        Invoke-Aws @('ecs', 'wait', 'services-stable', '--cluster', $Cluster, '--services', $UiService, '--region', $Region) | Out-Null
    }

    Write-Host "SUCCESS: Streamlit now targets http://${ApiDiscoveryName}:8000." -ForegroundColor Green
    $final = Invoke-AwsJson @(
        'ecs', 'describe-services',
        '--cluster', $Cluster,
        '--services', $ApiService, $UiService,
        '--region', $Region,
        '--output', 'json'
    )
    $final.services |
        Select-Object serviceName, runningCount, desiredCount, @{ Name = 'ServiceConnectEnabled'; Expression = { $_.serviceConnectConfiguration.enabled } } |
        Format-Table -AutoSize
} finally {
    foreach ($tempFile in $tempFiles) {
        if (Test-Path -LiteralPath $tempFile) {
            [System.IO.File]::Delete($tempFile)
        }
    }
}
