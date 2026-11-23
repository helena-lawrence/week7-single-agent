# StudyPilot Qdrant: staging-only ECS Fargate + ECS-managed EBS.
# WARNING: EBS volumes attached to ECS *service* tasks are deleted on task termination.
# This setup is for re-ingestible development data, not durable production Qdrant.
$ErrorActionPreference = 'Stop'
$region = 'eu-west-2'
$cluster = 'Helena-dev'
$service = 'studypilot-qdrant-staging'
$subnet = 'subnet-0c009cab643918e79'
$sgName = 'studypilot-qdrant-staging-sg'
$secretName = 'studypilot/staging/qdrant-api-key'
$logGroup = '/ecs/studypilot-qdrant-staging'

function Invoke-Aws([string[]]$arguments) {
    $output = & aws @arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "AWS command failed: $($output | Out-String)" }
    return ($output -join "`n")
}

$account = (Invoke-Aws -arguments @('sts','get-caller-identity','--query','Account','--output','text')).Trim()
if (-not ($account -match '^\d{12}$')) { throw 'AWS account identity is not valid.' }
Write-Host "AWS account: $account"

$secretArn = (Invoke-Aws -arguments @('secretsmanager','describe-secret','--secret-id',$secretName,'--region',$region,'--query','ARN','--output','text')).Trim()
$vpcId = (Invoke-Aws -arguments @('ec2','describe-subnets','--subnet-ids',$subnet,'--region',$region,'--query','Subnets[0].VpcId','--output','text')).Trim()
$clusterDetails = Invoke-Aws -arguments @('ecs','describe-clusters','--clusters',$cluster,'--region',$region,'--output','json') | ConvertFrom-Json
$namespace = $clusterDetails.clusters[0].serviceConnectDefaults.namespace
if (-not $namespace) { throw 'ECS Service Connect namespace is missing.' }

$existing = Invoke-Aws -arguments @('ecs','describe-services','--cluster',$cluster,'--services',$service,'--region',$region,'--output','json') | ConvertFrom-Json
if (@($existing.services | Where-Object { $_.status -eq 'ACTIVE' }).Count -gt 0) {
    throw "$service already exists. Stopping instead of creating a duplicate."
}

$api = Invoke-Aws -arguments @('ecs','describe-services','--cluster',$cluster,'--services','studypilot-api-staging','--region',$region,'--output','json') | ConvertFrom-Json
$apiSg = $api.services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]
if (-not $apiSg) { throw 'Cannot read the existing FastAPI service security group.' }

$groups = Invoke-Aws -arguments @('ec2','describe-security-groups','--region',$region,'--filters',"Name=group-name,Values=$sgName","Name=vpc-id,Values=$vpcId",'--output','json') | ConvertFrom-Json
$sg = @($groups.SecurityGroups)[0]
if (-not $sg) { throw "Missing $sgName in VPC $vpcId. Create the security group first." }

$publicIngress = @($sg.IpPermissions | Where-Object {
    @($_.IpRanges | Where-Object { $_.CidrIp -eq '0.0.0.0/0' }).Count -gt 0 -or
    @($_.Ipv6Ranges | Where-Object { $_.CidrIpv6 -eq '::/0' }).Count -gt 0
}).Count -gt 0
if ($publicIngress) { throw 'Qdrant SG has public ingress! Remove it before launching.' }

$allowedApi = @($sg.IpPermissions | Where-Object {
    $_.IpProtocol -eq 'tcp' -and $_.FromPort -le 6333 -and $_.ToPort -ge 6333 -and
    @($_.UserIdGroupPairs | Where-Object { $_.GroupId -eq $apiSg }).Count -gt 0
}).Count -gt 0
if (-not $allowedApi) {
    Invoke-Aws -arguments @('ec2','authorize-security-group-ingress','--group-id',$sg.GroupId,'--protocol','tcp','--port','6333','--source-group',$apiSg,'--region',$region) | Out-Null
}

$groupList = Invoke-Aws -arguments @('logs','describe-log-groups','--log-group-name-prefix',$logGroup,'--region',$region,'--output','json') | ConvertFrom-Json
if (@($groupList.logGroups | Where-Object { $_.logGroupName -eq $logGroup }).Count -eq 0) {
    Invoke-Aws -arguments @('logs','create-log-group','--log-group-name',$logGroup,'--region',$region) | Out-Null
}
Invoke-Aws -arguments @('logs','put-retention-policy','--log-group-name',$logGroup,'--retention-in-days','7','--region',$region) | Out-Null

$task = @{
  family = 'studypilot-qdrant-staging'
  networkMode = 'awsvpc'
  requiresCompatibilities = @('FARGATE')
  cpu = '1024'
  memory = '2048'
  executionRoleArn = "arn:aws:iam::${account}:role/studypilot-ecs-execution-role"
  volumes = @(@{ name='qdrant-data'; configuredAtLaunch=$true })
  containerDefinitions = @(@{
    name = 'qdrant'
    image = 'qdrant/qdrant:v1.20.2'
    essential = $true
    secrets = @(@{ name='QDRANT__SERVICE__API_KEY'; valueFrom=$secretArn })
    portMappings = @(@{ name='qdrant-http'; containerPort=6333; protocol='tcp'; appProtocol='http' })
    mountPoints = @(@{ sourceVolume='qdrant-data'; containerPath='/qdrant/storage'; readOnly=$false })
    logConfiguration = @{ logDriver='awslogs'; options=@{
      'awslogs-group' = $logGroup; 'awslogs-region'=$region; 'awslogs-stream-prefix'='qdrant'
    }}
  })
}
$taskPath = Join-Path $env:TEMP 'studypilot-qdrant-secure-task.json'
$task | ConvertTo-Json -Depth 30 | Set-Content -Path $taskPath -Encoding ascii
$registered = Invoke-Aws -arguments @('ecs','register-task-definition','--cli-input-json',"file://$taskPath",'--region',$region,'--output','json') | ConvertFrom-Json
$taskArn = $registered.taskDefinition.taskDefinitionArn
Write-Host "Registered Qdrant task: $taskArn"

$serviceConfig = @{
  cluster=$cluster
  serviceName=$service
  taskDefinition=$taskArn
  launchType='FARGATE'
  desiredCount=1
  networkConfiguration=@{awsvpcConfiguration=@{
    subnets=@($subnet); securityGroups=@($sg.GroupId); assignPublicIp='ENABLED'
  }}
  serviceConnectConfiguration=@{
    enabled=$true
    namespace=$namespace
    services=@(@{
      portName='qdrant-http'
      discoveryName='studypilot-qdrant'
      clientAliases=@(@{dnsName='studypilot-qdrant';port=6333})
    })
  }
  volumeConfigurations=@(@{
    name='qdrant-data'
    managedEBSVolume=@{
      roleArn="arn:aws:iam::${account}:role/studypilot-ecs-ebs-role"
      volumeType='gp3'
      sizeInGiB=20
      encrypted=$true
      filesystemType='ext4'
      iops=3000
      throughput=125
    }
  })
}
$servicePath = Join-Path $env:TEMP 'studypilot-qdrant-create-service.json'
$serviceConfig | ConvertTo-Json -Depth 30 | Set-Content -Path $servicePath -Encoding ascii
Write-Host "Launching $service in cluster $cluster with a 20-GiB encrypted EBS volume and restricted inbound access."
Invoke-Aws -arguments @('ecs','create-service','--cli-input-json',"file://$servicePath",'--region',$region,'--query','service.[serviceName,status,desiredCount]','--output','table','--no-cli-pager') | Write-Host
Write-Host "Qdrant endpoint for authorized ECS clients: http://studypilot-qdrant:6333"
Write-Host 'WARNING: This is staging-only storage. ECS will delete this task EBS volume when the task terminates. Make snapshots/backups before relying on the data.'
