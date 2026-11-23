$ErrorActionPreference = 'Stop'
$deploymentScript = Join-Path $PSScriptRoot '.github\workflows\Deploy-StudyPilot-Qdrant.ps1'

if (-not (Test-Path -LiteralPath $deploymentScript -PathType Leaf)) {
    throw "Deployment script not found: $deploymentScript"
}

& $deploymentScript @args
