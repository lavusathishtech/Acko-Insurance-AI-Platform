# AWS ECS Deployment Guide for ACKO Claims Engine

This guide walks you through deploying your FastAPI application to AWS ECS (Elastic Container Service) with Fargate.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   AWS ECS Cluster                    │
│  ┌───────────────────────────────────────────────┐  │
│  │  ECS Service (Load Balanced)                  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │ ECS Task 1                              │  │  │
│  │  │ ┌──────────────────────────────────────┐│  │  │
│  │  │ │ Docker Container (FastAPI + Uvicorn)││  │  │
│  │  │ │ Port: 8000                          ││  │  │
│  │  │ └──────────────────────────────────────┘│  │  │
│  │  │                                          │  │  │
│  │  │ ✓ Auto-scaling enabled                  │  │  │
│  │  │ ✓ Health checks configured              │  │  │
│  │  │ ✓ CloudWatch logs enabled               │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
│                        ↓                              │
│                  [ALB / Load Balancer]               │
└─────────────────────────────────────────────────────┘
              ↓                   ↓
        [S3 Bucket]        [RDS PostgreSQL]
```

## Prerequisites

1. **AWS Account** with appropriate permissions (EC2, ECS, ECR, IAM, RDS)
2. **AWS CLI** installed and configured (`aws --version`)
3. **Docker** installed locally (`docker --version`)
4. **PowerShell** (for Windows) or bash (for Linux/Mac)
5. **VPC and Subnets** created in AWS (for Fargate tasks)
6. **Security Groups** configured to allow inbound port 8000

## Step-by-Step Deployment

### Step 1: Prerequisites Setup

Verify AWS CLI is configured:
```powershell
aws sts get-caller-identity
```

You should see your AWS account information.

### Step 2: Set Up IAM Roles and Secrets

Run the IAM setup script:
```powershell
.\setup-ecs-iam.ps1
```

This script will:
- Create `ecsTaskExecutionRole` (for ECS to pull images and access logs)
- Create `ecsTaskRole` (for your application to access AWS services)
- Create AWS Secrets Manager entries for:
  - AWS credentials
  - Database URL (PostgreSQL RDS)

**You'll be prompted to enter:**
- AWS Access Key ID
- AWS Secret Access Key  
- Database connection string (e.g., `postgresql://user:password@rds-endpoint:5432/dbname`)

### Step 3: Configure VPC and Security Groups

Before deployment, you need to know:

**1. Subnet IDs** (for VPC networking):
```powershell
aws ec2 describe-subnets --region us-east-1 --query 'Subnets[*].[SubnetId,AvailabilityZone,CidrBlock]' --output table
```

**2. Security Group IDs** (for inbound rules):
```powershell
aws ec2 describe-security-groups --region us-east-1 --query 'SecurityGroups[*].[GroupId,GroupName,IpPermissions]' --output table
```

Make sure your security group has:
- **Inbound Rule:** TCP port 8000 (from ALB or 0.0.0.0/0)
- **Outbound Rule:** All traffic (default)

**3. Update the deployment script:**

Edit `deploy-ecs.ps1` and update these lines with your actual values:
```powershell
$SubnetIds = "subnet-12345678,subnet-87654321"  # Your subnet IDs
$SecurityGroupIds = "sg-12345678"                 # Your security group ID
```

### Step 4: Deploy to ECS

Run the deployment script:
```powershell
.\deploy-ecs.ps1 -AwsRegion us-east-1 -AwsAccountId YOUR_ACCOUNT_ID
```

**Parameters:**
- `-AwsRegion` (optional, default: us-east-1)
- `-AwsAccountId` (optional, auto-fetched if not provided)
- `-EcrRepoName` (optional, default: acko-claims-engine)
- `-ImageTag` (optional, default: latest)
- `-EcsClusterName` (optional, default: acko-production)
- `-EcsServiceName` (optional, default: acko-claims-engine-service)

**What the script does:**
1. ✓ Builds Docker image
2. ✓ Logs in to ECR
3. ✓ Creates ECR repository (if needed)
4. ✓ Pushes image to ECR
5. ✓ Registers ECS task definition
6. ✓ Creates ECS cluster (if needed)
7. ✓ Creates CloudWatch Log Group
8. ✓ Creates/updates ECS service
9. ✓ Monitors deployment until service is stable

The script will display:
```
Service Name: acko-claims-engine-service
Status: ACTIVE
Running Count: 1
Desired Count: 1
```

### Step 5: Set Up Load Balancer (Optional but Recommended)

To expose your ECS service publicly, set up an Application Load Balancer (ALB):

```powershell
# Create ALB
aws elbv2 create-load-balancer `
    --name acko-alb `
    --subnets subnet-12345678 subnet-87654321 `
    --security-groups sg-12345678 `
    --region us-east-1

# Create target group
aws elbv2 create-target-group `
    --name acko-targets `
    --protocol HTTP `
    --port 8000 `
    --vpc-id vpc-12345678 `
    --region us-east-1

# Register ECS task with target group (done via ECS service)
```

### Step 6: Verify Deployment

Check service status:
```powershell
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].[serviceName,status,runningCount,desiredCount]' `
    --output table
```

View logs:
```powershell
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1
```

Get task details:
```powershell
aws ecs list-tasks `
    --cluster acko-production `
    --service-name acko-claims-engine-service `
    --region us-east-1
```

## Managing Your ECS Service

### Scale Up/Down
```powershell
# Scale to 3 tasks
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --desired-count 3 `
    --region us-east-1
```

### Update Service (New Image)
```powershell
# After pushing new image to ECR, force new deployment
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --force-new-deployment `
    --region us-east-1
```

### View Logs
```powershell
# Stream logs in real-time
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1

# View specific time range
aws logs filter-log-events `
    --log-group-name /ecs/acko-claims-engine `
    --start-time (Get-Date).AddHours(-1).Ticks `
    --region us-east-1
```

### Delete Service
```powershell
# First, scale down to 0
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --desired-count 0 `
    --region us-east-1

# Wait, then delete service
aws ecs delete-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --force `
    --region us-east-1
```

## Environment Variables & Secrets

Your application accesses secrets via AWS Secrets Manager:

```python
# In your code (aws_config.py):
import os
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "acko-insurance-models")
```

Secrets are injected from Secrets Manager:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `DATABASE_URL`

To update secrets:
```powershell
aws secretsmanager update-secret `
    --secret-id acko/database-url `
    --secret-string "postgresql://user:password@new-endpoint:5432/dbname" `
    --region us-east-1
```

## Troubleshooting

### Service fails to deploy
```powershell
# Check task definition
aws ecs describe-task-definition `
    --task-definition acko-claims-engine `
    --region us-east-1

# Check service events
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].events[0:5]'
```

### Container won't start
```powershell
# View logs
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1

# Check task details
aws ecs list-tasks --cluster acko-production --region us-east-1
aws ecs describe-tasks --cluster acko-production --tasks <task-arn> --region us-east-1
```

### Health check failing
- Ensure `/health` endpoint exists in your FastAPI app
- Check security group allows health check traffic
- Verify container is listening on port 8000

### Database connection issues
- Verify DATABASE_URL secret in Secrets Manager
- Check RDS security group allows inbound on port 5432
- Ensure RDS instance is publicly accessible (if needed)

## Costs

Typical monthly costs for this setup:
- **ECS Fargate (1 task, t3.small):** ~$15-20/month
- **ECR Storage:** ~$1-3/month
- **Data Transfer:** ~$0-5/month
- **RDS (db.t3.micro):** ~$30-50/month
- **CloudWatch Logs:** ~$1-5/month

**Total:** ~$50-80/month for a small production setup

## Next Steps

1. ✓ Set up **Auto-scaling** based on CPU/memory metrics
2. ✓ Configure **CloudWatch Alarms** for monitoring
3. ✓ Set up **CI/CD Pipeline** (GitHub Actions, CodePipeline)
4. ✓ Enable **ECS Exec** for debugging live containers
5. ✓ Configure **Application Load Balancer** with HTTPS
6. ✓ Set up **Route 53** for custom domain

---

**Need Help?**
- AWS ECS Documentation: https://docs.aws.amazon.com/ecs/
- FastAPI with Docker: https://fastapi.tiangolo.com/deployment/docker/
- AWS CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/ecs/
