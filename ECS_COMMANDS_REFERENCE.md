# AWS ECS Quick Reference - Common Commands

## Quick Start

```powershell
# 1. Setup IAM roles and secrets
.\setup-ecs-iam.ps1

# 2. Deploy to ECS
.\deploy-ecs.ps1
```

## Service Management

### View Service Status
```powershell
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].[serviceName,status,runningCount,desiredCount,deployments]' `
    --output table
```

### Scale Service
```powershell
# Scale to 3 tasks
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --desired-count 3 `
    --region us-east-1

# Scale to 0 (stop service)
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --desired-count 0 `
    --region us-east-1
```

### Force New Deployment
```powershell
# After updating Docker image in ECR
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --force-new-deployment `
    --region us-east-1
```

## Container & Task Management

### List Tasks
```powershell
aws ecs list-tasks `
    --cluster acko-production `
    --service-name acko-claims-engine-service `
    --region us-east-1

# With full output
aws ecs list-tasks `
    --cluster acko-production `
    --service-name acko-claims-engine-service `
    --region us-east-1 `
    --query 'taskArns' `
    --output table
```

### View Task Details
```powershell
aws ecs describe-tasks `
    --cluster acko-production `
    --tasks arn:aws:ecs:us-east-1:ACCOUNT_ID:task/acko-production/TASK_ID `
    --region us-east-1 `
    --query 'tasks[0].[taskArn,lastStatus,taskDefinitionArn,containerInstanceArn]' `
    --output table
```

### Execute Command in Running Task (ECS Exec)
```powershell
# List running tasks first
aws ecs list-tasks `
    --cluster acko-production `
    --service-name acko-claims-engine-service `
    --region us-east-1

# Execute shell command
aws ecs execute-command `
    --cluster acko-production `
    --task TASK_ID `
    --container acko-claims-engine `
    --command "python,main.py" `
    --interactive `
    --region us-east-1
```

### Stop Task
```powershell
aws ecs stop-task `
    --cluster acko-production `
    --task arn:aws:ecs:us-east-1:ACCOUNT_ID:task/acko-production/TASK_ID `
    --reason "Manual stop" `
    --region us-east-1
```

## Logging & Monitoring

### View Logs in Real-Time
```powershell
# Stream logs
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1

# Or with grep filter
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1 | findstr "ERROR"
```

### View Logs from Specific Time
```powershell
# Last 1 hour
aws logs filter-log-events `
    --log-group-name /ecs/acko-claims-engine `
    --start-time ([DateTime]::UtcNow.AddHours(-1).Ticks) `
    --region us-east-1 `
    --query 'events[*].[timestamp,message]' `
    --output table
```

### Get Log Events
```powershell
aws logs get-log-events `
    --log-group-name /ecs/acko-claims-engine `
    --log-stream-name ecs/acko-claims-engine/CONTAINER_NAME `
    --region us-east-1 `
    --query 'events[*].[timestamp,message]'
```

## ECR Image Management

### List ECR Images
```powershell
aws ecr describe-images `
    --repository-name acko-claims-engine `
    --region us-east-1 `
    --query 'imageDetails[*].[imageTags,imageSizeInBytes,imagePushedAt]' `
    --output table
```

### Tag and Push New Image
```powershell
# Build
docker build -t acko-claims-engine:v1.0.1 .

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag
docker tag acko-claims-engine:v1.0.1 ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/acko-claims-engine:v1.0.1

# Push
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/acko-claims-engine:v1.0.1

# Update service to use new image
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --force-new-deployment `
    --region us-east-1
```

### Delete ECR Image
```powershell
aws ecr batch-delete-image `
    --repository-name acko-claims-engine `
    --image-ids imageTag=v1.0.0 `
    --region us-east-1
```

## Task Definition Management

### List Task Definitions
```powershell
aws ecs list-task-definitions `
    --family-prefix acko-claims-engine `
    --region us-east-1 `
    --query 'taskDefinitionArns' `
    --output table
```

### View Task Definition
```powershell
aws ecs describe-task-definition `
    --task-definition acko-claims-engine `
    --region us-east-1 `
    --query 'taskDefinition.[family,revision,containerDefinitions,taskRoleArn,executionRoleArn]'
```

### Register New Task Definition
```powershell
aws ecs register-task-definition `
    --cli-input-json file://ecs-task-definition.json `
    --region us-east-1
```

### Deregister Task Definition
```powershell
aws ecs deregister-task-definition `
    --task-definition acko-claims-engine:1 `
    --region us-east-1
```

## Secrets Management

### Create Secret
```powershell
aws secretsmanager create-secret `
    --name acko/database-url `
    --secret-string "postgresql://user:password@endpoint:5432/dbname" `
    --region us-east-1
```

### Update Secret
```powershell
aws secretsmanager update-secret `
    --secret-id acko/database-url `
    --secret-string "postgresql://user:newpassword@endpoint:5432/dbname" `
    --region us-east-1
```

### Get Secret Value
```powershell
aws secretsmanager get-secret-value `
    --secret-id acko/database-url `
    --region us-east-1 `
    --query SecretString `
    --output text
```

### List Secrets
```powershell
aws secretsmanager list-secrets `
    --filters Key=name,Values=acko `
    --region us-east-1 `
    --query 'SecretList[*].[Name,LastChangedDate]' `
    --output table
```

## Cluster Management

### Create Cluster
```powershell
aws ecs create-cluster `
    --cluster-name acko-production `
    --region us-east-1
```

### List Clusters
```powershell
aws ecs list-clusters `
    --region us-east-1 `
    --query 'clusterArns' `
    --output table
```

### View Cluster Details
```powershell
aws ecs describe-clusters `
    --clusters acko-production `
    --region us-east-1 `
    --query 'clusters[0].[clusterName,status,registeredContainerInstancesCount,runningCount,pendingCount]' `
    --output table
```

### Delete Cluster
```powershell
# First scale down all services
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --desired-count 0 `
    --region us-east-1

# Wait for tasks to stop, then delete
aws ecs delete-cluster `
    --cluster acko-production `
    --region us-east-1
```

## Service Management

### List Services
```powershell
aws ecs list-services `
    --cluster acko-production `
    --region us-east-1 `
    --query 'serviceArns' `
    --output table
```

### Delete Service
```powershell
# Scale to 0 first
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --desired-count 0 `
    --region us-east-1

# Wait, then delete
aws ecs delete-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --force `
    --region us-east-1
```

## CloudWatch Logs

### Create Log Group
```powershell
aws logs create-log-group `
    --log-group-name /ecs/acko-claims-engine `
    --region us-east-1
```

### Set Log Retention
```powershell
aws logs put-retention-policy `
    --log-group-name /ecs/acko-claims-engine `
    --retention-in-days 30 `
    --region us-east-1
```

### List Log Groups
```powershell
aws logs describe-log-groups `
    --log-group-name-prefix /ecs `
    --region us-east-1 `
    --query 'logGroups[*].[logGroupName,retentionInDays,storedBytes]' `
    --output table
```

## Troubleshooting

### Check Service Events
```powershell
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].events[0:10]' `
    --output table
```

### View Failed Task Logs
```powershell
# List tasks with last status
aws ecs list-tasks `
    --cluster acko-production `
    --region us-east-1 `
    --query 'taskArns' | ForEach-Object {
    aws ecs describe-tasks `
        --cluster acko-production `
        --tasks $_ `
        --region us-east-1 `
        --query 'tasks[0].[taskArn,lastStatus]'
}
```

### View Task Exit Codes
```powershell
aws ecs describe-tasks `
    --cluster acko-production `
    --tasks TASK_ARN `
    --region us-east-1 `
    --query 'tasks[0].containers[0].[exitCode,reason]'
```

### Check Container Health
```powershell
aws ecs describe-task-definition `
    --task-definition acko-claims-engine `
    --region us-east-1 `
    --query 'taskDefinition.containerDefinitions[0].healthCheck'
```

## Auto-Scaling

### Create Auto-Scaling Target
```powershell
aws application-autoscaling register-scalable-target `
    --service-namespace ecs `
    --resource-id service/acko-production/acko-claims-engine-service `
    --scalable-dimension ecs:service:DesiredCount `
    --min-capacity 1 `
    --max-capacity 10 `
    --region us-east-1
```

### Create Scaling Policy (Target Tracking)
```powershell
aws application-autoscaling put-scaling-policy `
    --policy-name acko-cpu-scaling `
    --service-namespace ecs `
    --resource-id service/acko-production/acko-claims-engine-service `
    --scalable-dimension ecs:service:DesiredCount `
    --policy-type TargetTrackingScaling `
    --target-tracking-scaling-policy-configuration "TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization}" `
    --region us-east-1
```

## Useful Aliases (PowerShell)

```powershell
# Add to your PowerShell profile
function Get-EcsServiceStatus {
    param([string]$ServiceName = "acko-claims-engine-service")
    aws ecs describe-services `
        --cluster acko-production `
        --services $ServiceName `
        --region us-east-1 `
        --query 'services[0].[serviceName,status,runningCount,desiredCount]' `
        --output table
}

function Watch-EcsLogs {
    param([int]$Lines = 100)
    aws logs tail /ecs/acko-claims-engine --follow --max-items $Lines --region us-east-1
}

function Get-EcsTasks {
    aws ecs list-tasks `
        --cluster acko-production `
        --service-name acko-claims-engine-service `
        --region us-east-1 `
        --query 'taskArns' `
        --output table
}
```

---

**More Info:**
- AWS ECS CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/ecs/
- AWS Fargate Documentation: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/launch_types.html
