# ECS Deployment Checklist

Complete this checklist to ensure successful ECS deployment of your ACKO Claims Engine.

## Pre-Deployment Checklist

### AWS Account Setup
- [ ] AWS account created and active
- [ ] AWS CLI installed locally (`aws --version`)
- [ ] AWS CLI configured with credentials (`aws configure`)
- [ ] AWS credentials are valid (`aws sts get-caller-identity`)
- [ ] AWS account has necessary permissions (EC2, ECS, ECR, IAM, RDS, Secrets Manager)

### Local Environment
- [ ] Docker installed (`docker --version`)
- [ ] Docker daemon running
- [ ] PowerShell 5.1+ (Windows) or Bash (Linux/Mac)
- [ ] Git installed (for version control)
- [ ] Project files ready and tested locally

### Network Setup
- [ ] VPC created in AWS
- [ ] At least 2 subnets in different AZs (for high availability)
- [ ] Internet Gateway attached to VPC
- [ ] Route tables configured
- [ ] Security group created with:
  - [ ] Inbound rule: TCP 8000 (from ALB or 0.0.0.0/0)
  - [ ] Outbound rule: All traffic (or specific services)
- [ ] Subnet IDs noted: `______________________________`
- [ ] Security Group ID noted: `_____________________`

### Database
- [ ] RDS PostgreSQL instance created
- [ ] RDS security group allows inbound on port 5432 from ECS security group
- [ ] Database name: `_____________________________`
- [ ] Database user: `_____________________________`
- [ ] Database password: `_____________________________` (keep secure)
- [ ] Connection string format: `postgresql://user:password@endpoint:5432/dbname`

### AWS S3
- [ ] S3 bucket created: `acko-insurance-models`
- [ ] Bucket versioning enabled (optional)
- [ ] Bucket encryption enabled (optional)
- [ ] CORS policy configured (if needed)

---

## Step 1: IAM Setup & Secrets Manager

### Run IAM Setup Script
```
✓ Completed
```
- [ ] Run: `.\setup-ecs-iam.ps1`
- [ ] Enter AWS Access Key ID
- [ ] Enter AWS Secret Access Key
- [ ] Enter Database URL
- [ ] Verify secrets created:
  ```powershell
  aws secretsmanager list-secrets --region us-east-1 --query 'SecretList[*].Name'
  ```
  Expected output:
  ```
  acko/aws-access-key-id
  acko/aws-secret-access-key
  acko/database-url
  ```

### Verify IAM Roles Created
- [ ] `ecsTaskExecutionRole` exists
- [ ] `ecsTaskRole` exists
- [ ] Both roles have correct trust relationships
- [ ] Both roles have correct policies attached

**Verification Commands:**
```powershell
aws iam get-role --role-name ecsTaskExecutionRole
aws iam get-role --role-name ecsTaskRole
aws secretsmanager list-secrets --filters Key=name,Values=acko
```

---

## Step 2: Configuration Updates

### Update Task Definition
- [ ] Open `ecs-task-definition.json`
- [ ] Verify all placeholders are present:
  - [ ] `<AWS_ACCOUNT_ID>` (will be replaced by script)
  - [ ] `<AWS_REGION>` (will be replaced by script)
  - [ ] Port 8000 is correct
  - [ ] Log group name: `/ecs/acko-claims-engine`
- [ ] Save file

### Update Deployment Script
- [ ] Open `deploy-ecs.ps1`
- [ ] Update network configuration (around line 140):
  ```powershell
  $SubnetIds = "subnet-XXXXX,subnet-YYYYY"
  $SecurityGroupIds = "sg-ZZZZ"
  ```
- [ ] Replace with your actual subnet and security group IDs
- [ ] Save file

---

## Step 3: Docker Image Verification

### Build Docker Image Locally
```
✓ Completed
```
- [ ] Docker image builds without errors
- [ ] Image is created: `docker images | grep acko-claims-engine`
- [ ] Image runs locally: `docker run -p 8000:8000 acko-claims-engine:latest`
- [ ] Application starts successfully
- [ ] Health check endpoint works: `curl http://localhost:8000/health`
- [ ] Stop local container

**Verification:**
```powershell
docker ps  # Should be empty after stopping
```

---

## Step 4: Deploy to ECS

### Run Deployment Script
```
✓ Completed
```
- [ ] Open PowerShell in project directory
- [ ] Run: `.\deploy-ecs.ps1`
- [ ] Script completes without errors
- [ ] All steps show success messages:
  - [ ] Docker image built successfully
  - [ ] ECR login successful
  - [ ] Image pushed to ECR
  - [ ] Task definition registered
  - [ ] ECS cluster created
  - [ ] CloudWatch log group created
  - [ ] ECS service created
  - [ ] Service deployment stabilized

### Monitor Deployment
```powershell
# Watch logs as it deploys
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1
```

---

## Step 5: Post-Deployment Verification

### Check Service Status
- [ ] Service status is ACTIVE
- [ ] Running count = Desired count
- [ ] No failed tasks

**Command:**
```powershell
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].[serviceName,status,runningCount,desiredCount]' `
    --output table
```

### Check Task Status
- [ ] At least 1 task running
- [ ] Task status is RUNNING
- [ ] Health check is HEALTHY

**Command:**
```powershell
aws ecs list-tasks `
    --cluster acko-production `
    --service-name acko-claims-engine-service `
    --region us-east-1
```

### Check CloudWatch Logs
- [ ] Logs are being written to `/ecs/acko-claims-engine`
- [ ] No error messages in logs
- [ ] Application initialization messages visible

**Command:**
```powershell
aws logs tail /ecs/acko-claims-engine --region us-east-1 --max-items 50
```

### Verify Container Health
- [ ] Health check passes consistently
- [ ] No restarts happening
- [ ] Task stays in RUNNING state

**Command:**
```powershell
aws ecs describe-tasks `
    --cluster acko-production `
    --tasks <TASK_ARN> `
    --region us-east-1 `
    --query 'tasks[0].[lastStatus,healthStatus,containerInstanceArn]'
```

---

## Step 6: Optional - Set Up Load Balancer (Recommended)

### Create Application Load Balancer
- [ ] ALB created
- [ ] Target group created
- [ ] Health check path: `/health`
- [ ] Health check interval: 30 seconds
- [ ] Healthy threshold: 2
- [ ] Unhealthy threshold: 3
- [ ] ECS service linked to target group

### Verify ALB
- [ ] ALB is in ACTIVE state
- [ ] Target group has 1 healthy target
- [ ] ALB DNS name is working
- [ ] Can access application via ALB URL

---

## Step 7: Optional - Configure Auto-Scaling

### Set Up Auto-Scaling Target
- [ ] Scalable target registered
- [ ] Min capacity: 1
- [ ] Max capacity: 10

### Create Scaling Policy
- [ ] Target tracking policy created
- [ ] Metric: ECS Service Average CPU Utilization
- [ ] Target value: 70%
- [ ] Scale-out cooldown: 60 seconds
- [ ] Scale-in cooldown: 300 seconds

**Verification:**
```powershell
aws application-autoscaling describe-scalable-targets `
    --service-namespace ecs `
    --resource-id service/acko-production/acko-claims-engine-service `
    --region us-east-1
```

---

## Step 8: Optional - Configure Monitoring & Alarms

### Create CloudWatch Alarms
- [ ] CPU Utilization alarm (threshold: 80%)
- [ ] Memory Utilization alarm (threshold: 80%)
- [ ] Task Count alarm (threshold < desired)
- [ ] Log Errors alarm (PATTERN: ERROR)

### Create SNS Notifications
- [ ] SNS topic created: `acko-alerts`
- [ ] Email subscription added
- [ ] Alarms linked to SNS topic

---

## Testing & Validation

### Test Application
- [ ] Access application (via ALB or task ENI)
- [ ] Test API endpoints
- [ ] Test database connectivity
- [ ] Test S3 access
- [ ] Test chatbot functionality (if applicable)
- [ ] Monitor logs for errors

### Test Scaling
- [ ] Monitor CPU under load
- [ ] Verify auto-scaling triggers correctly
- [ ] Verify new tasks start successfully
- [ ] Check load balancing across tasks

### Test Updates
- [ ] Make code change locally
- [ ] Build new Docker image
- [ ] Push to ECR
- [ ] Deploy new image: `.\deploy-ecs.ps1 --force-new-deployment`
- [ ] Verify service updates without downtime
- [ ] Check logs for new version

---

## Security Checklist

### Secrets & Credentials
- [ ] Secrets stored in AWS Secrets Manager (not in code)
- [ ] Environment variables configured in task definition
- [ ] AWS credentials never logged
- [ ] Database password never exposed
- [ ] Secrets rotated periodically (set calendar reminder)

### Network Security
- [ ] Security group only allows necessary ports
- [ ] VPC endpoints used for S3 access (optional)
- [ ] RDS security group restricts access
- [ ] ECS tasks in private subnet (if behind ALB)
- [ ] No public IP unless necessary

### IAM Permissions
- [ ] Execution role has minimal permissions
- [ ] Task role has minimal permissions
- [ ] No * (wildcard) permissions
- [ ] Regular audit of permissions

### Image Security
- [ ] Docker image scanned for vulnerabilities
- [ ] Base image is up to date
- [ ] Dependencies are from trusted sources
- [ ] No secrets in Dockerfile

---

## Troubleshooting Checklist

If deployment fails, check:

### Deployment Script Fails
- [ ] AWS CLI credentials are valid
- [ ] Docker daemon is running
- [ ] Security group and subnet IDs are correct
- [ ] ECR repository doesn't already exist
- [ ] Permissions are adequate

### Task Fails to Start
- [ ] Docker image builds locally without errors
- [ ] All environment variables are set
- [ ] All secrets exist in Secrets Manager
- [ ] Health check endpoint exists
- [ ] Port 8000 is not blocked

### Application Crashes
- [ ] Check CloudWatch logs: `aws logs tail /ecs/acko-claims-engine --follow`
- [ ] Verify database connection string
- [ ] Check S3 bucket access
- [ ] Verify all required environment variables
- [ ] Check application code for startup errors

### Health Check Fails
- [ ] Verify `/health` endpoint exists in app
- [ ] Ensure endpoint returns status 200
- [ ] Check security group allows health check traffic
- [ ] Monitor logs for application errors
- [ ] Increase health check timeout if needed

### Service Won't Stabilize
- [ ] Check service events: `aws ecs describe-services --cluster acko-production ...`
- [ ] Check task logs for errors
- [ ] Verify networking configuration
- [ ] Check container exit codes
- [ ] Examine task definition

---

## Rollback Plan

If deployment is problematic:

### Immediate Rollback
```powershell
# 1. Get previous task definition version
aws ecs describe-task-definition `
    --task-definition acko-claims-engine:2 `
    --region us-east-1

# 2. Update service to previous version
aws ecs update-service `
    --cluster acko-production `
    --service acko-claims-engine-service `
    --task-definition acko-claims-engine:2 `
    --region us-east-1

# 3. Verify rollback
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].[serviceName,status,runningCount,desiredCount]'
```

- [ ] Rollback completed
- [ ] Service restored to previous version
- [ ] Application accessible again
- [ ] Issues investigated

---

## Maintenance Schedule

### Weekly
- [ ] Check CloudWatch logs for errors
- [ ] Monitor costs in AWS billing
- [ ] Verify auto-scaling is working

### Monthly
- [ ] Review application performance metrics
- [ ] Check for security updates
- [ ] Update Docker base image if needed
- [ ] Review IAM permissions

### Quarterly
- [ ] Rotate AWS credentials
- [ ] Update application dependencies
- [ ] Test disaster recovery plan
- [ ] Review and optimize costs

### Yearly
- [ ] Comprehensive security audit
- [ ] Architecture review
- [ ] Capacity planning
- [ ] Update documentation

---

## Final Sign-Off

- [ ] All checklist items completed
- [ ] Application is live on ECS
- [ ] Monitoring and alerts configured
- [ ] Team trained on management
- [ ] Documentation updated
- [ ] Rollback plan tested

**Deployed By:** ________________________  
**Date:** ________________________  
**Notes:** ________________________________________________________________________

---

## Support Resources

- **AWS ECS Documentation:** https://docs.aws.amazon.com/ecs/
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **AWS CLI Reference:** https://docs.aws.amazon.com/cli/latest/reference/ecs/
- **This Project Guide:** See `ECS_DEPLOYMENT_GUIDE.md`
- **Command Reference:** See `ECS_COMMANDS_REFERENCE.md`
