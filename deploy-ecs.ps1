# AWS ECS Deployment Script for ACKO Claims Engine
# Prerequisites: AWS CLI configured, Docker installed locally, AWS ECR repository created

param(
    [string]$AwsRegion = "us-east-1",
    [string]$AwsAccountId = "",
    [string]$EcrRepoName = "acko-claims-engine",
    [string]$ImageTag = "latest",
    [string]$EcsClusterName = "acko-production",
    [string]$EcsServiceName = "acko-claims-engine-service",
    [string]$EcsTaskDefinition = "acko-claims-engine"
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -ForegroundColor $Color
}

# 1. Get AWS Account ID if not provided
if (-not $AwsAccountId) {
    Write-Log "Fetching AWS Account ID..." -Color $InfoColor
    $AwsAccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Log "AWS Account ID: $AwsAccountId" -Color $SuccessColor
}

$EcrUri = "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com/$EcrRepoName"

# 2. Build Docker Image
Write-Log "Building Docker image..." -Color $InfoColor
docker build -t "$EcrRepoName`:$ImageTag" .
if ($LASTEXITCODE -ne 0) {
    Write-Log "Docker build failed!" -Color $ErrorColor
    exit 1
}
Write-Log "Docker image built successfully" -Color $SuccessColor

# 3. Login to ECR
Write-Log "Logging in to ECR..." -Color $InfoColor
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com"
if ($LASTEXITCODE -ne 0) {
    Write-Log "ECR login failed!" -Color $ErrorColor
    exit 1
}
Write-Log "ECR login successful" -Color $SuccessColor

# 4. Create ECR repository if it doesn't exist
Write-Log "Checking ECR repository..." -Color $InfoColor
$RepoExists = aws ecr describe-repositories --repository-names $EcrRepoName --region $AwsRegion --query 'repositories[0].repositoryUri' --output text 2>$null
if (-not $RepoExists) {
    Write-Log "Creating ECR repository: $EcrRepoName" -Color $InfoColor
    aws ecr create-repository --repository-name $EcrRepoName --region $AwsRegion
    Write-Log "ECR repository created" -Color $SuccessColor
} else {
    Write-Log "ECR repository already exists: $RepoExists" -Color $SuccessColor
}

# 5. Tag and push image to ECR
Write-Log "Tagging and pushing Docker image to ECR..." -Color $InfoColor
docker tag "$EcrRepoName`:$ImageTag" "$EcrUri`:$ImageTag"
docker push "$EcrUri`:$ImageTag"
if ($LASTEXITCODE -ne 0) {
    Write-Log "Docker push failed!" -Color $ErrorColor
    exit 1
}
Write-Log "Image pushed to ECR: $EcrUri`:$ImageTag" -Color $SuccessColor

# 6. Update ECS task definition with correct AWS account and region
Write-Log "Updating ECS task definition..." -Color $InfoColor
$TaskDefContent = Get-Content "ecs-task-definition.json" | ConvertFrom-Json
$TaskDefContent.containerDefinitions[0].image = "$EcrUri`:$ImageTag"
$TaskDefContent.executionRoleArn = "arn:aws:iam::$AwsAccountId`:role/ecsTaskExecutionRole"
$TaskDefContent.taskRoleArn = "arn:aws:iam::$AwsAccountId`:role/ecsTaskRole"
$TaskDefJson = $TaskDefContent | ConvertTo-Json -Depth 10
$TaskDefJson | Out-File -Encoding UTF8 "ecs-task-definition-updated.json"

# Register/update task definition
Write-Log "Registering ECS task definition..." -Color $InfoColor
$TaskDefArn = aws ecs register-task-definition `
    --cli-input-json file://ecs-task-definition-updated.json `
    --region $AwsRegion `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text
Write-Log "Task definition registered: $TaskDefArn" -Color $SuccessColor

# 7. Create ECS Cluster if it doesn't exist
Write-Log "Checking ECS cluster..." -Color $InfoColor
$ClusterExists = aws ecs describe-clusters --clusters $EcsClusterName --region $AwsRegion --query 'clusters[0].clusterName' --output text 2>$null
if ($ClusterExists -eq "None" -or -not $ClusterExists) {
    Write-Log "Creating ECS cluster: $EcsClusterName" -Color $InfoColor
    aws ecs create-cluster --cluster-name $EcsClusterName --region $AwsRegion
    Write-Log "ECS cluster created" -Color $SuccessColor
} else {
    Write-Log "ECS cluster already exists: $EcsClusterName" -Color $SuccessColor
}

# 8. Create CloudWatch Log Group
Write-Log "Checking CloudWatch Log Group..." -Color $InfoColor
$LogGroupExists = aws logs describe-log-groups --log-group-name-prefix "/ecs/acko-claims-engine" --region $AwsRegion --query 'logGroups[0].logGroupName' --output text 2>$null
if ($LogGroupExists -eq "None" -or -not $LogGroupExists) {
    Write-Log "Creating CloudWatch Log Group..." -Color $InfoColor
    aws logs create-log-group --log-group-name "/ecs/acko-claims-engine" --region $AwsRegion
    aws logs put-retention-policy --log-group-name "/ecs/acko-claims-engine" --retention-in-days 7 --region $AwsRegion
    Write-Log "CloudWatch Log Group created" -Color $SuccessColor
} else {
    Write-Log "CloudWatch Log Group already exists" -Color $SuccessColor
}

# 9. Create or Update ECS Service
Write-Log "Checking ECS service..." -Color $InfoColor
$ServiceExists = aws ecs describe-services --cluster $EcsClusterName --services $EcsServiceName --region $AwsRegion --query 'services[0].serviceName' --output text 2>$null

if ($ServiceExists -eq "None" -or -not $ServiceExists) {
    Write-Log "Creating ECS service: $EcsServiceName" -Color $InfoColor
    
    # You need to replace these with your VPC/subnet IDs
    $SubnetIds = "subnet-12345678,subnet-87654321"  # Replace with your subnet IDs
    $SecurityGroupIds = "sg-12345678"                 # Replace with your security group ID
    
    aws ecs create-service `
        --cluster $EcsClusterName `
        --service-name $EcsServiceName `
        --task-definition $EcsTaskDefinition `
        --desired-count 1 `
        --launch-type FARGATE `
        --network-configuration "awsvpcConfiguration={subnets=[$SubnetIds],securityGroups=[$SecurityGroupIds],assignPublicIp=ENABLED}" `
        --region $AwsRegion
    
    Write-Log "ECS service created" -Color $SuccessColor
} else {
    Write-Log "Updating ECS service: $EcsServiceName" -Color $InfoColor
    aws ecs update-service `
        --cluster $EcsClusterName `
        --service $EcsServiceName `
        --task-definition "$EcsTaskDefinition`:1" `
        --force-new-deployment `
        --region $AwsRegion
    
    Write-Log "ECS service updated" -Color $SuccessColor
}

# 10. Monitor deployment
Write-Log "Waiting for service to stabilize (this may take a few minutes)..." -Color $InfoColor
aws ecs wait services-stable `
    --cluster $EcsClusterName `
    --services $EcsServiceName `
    --region $AwsRegion

if ($LASTEXITCODE -eq 0) {
    Write-Log "Service deployed and stabilized successfully!" -Color $SuccessColor
    
    # Get service details
    Write-Log "Getting service details..." -Color $InfoColor
    aws ecs describe-services `
        --cluster $EcsClusterName `
        --services $EcsServiceName `
        --region $AwsRegion `
        --query 'services[0].[serviceName,status,runningCount,desiredCount]' `
        --output table
} else {
    Write-Log "Service deployment failed or timed out" -Color $ErrorColor
    exit 1
}

Write-Log "Deployment completed successfully!" -Color $SuccessColor
Write-Log "Service URL will be available through your load balancer or ALB" -Color $InfoColor
