# AWS ECS Deployment - Getting Started

You now have a **complete AWS ECS deployment setup** for your ACKO Claims Engine FastAPI application!

## 📦 What's Included

- ✅ **ECS Task Definition** - Production-ready Fargate configuration
- ✅ **Deployment Scripts** - Automated PowerShell and Bash scripts
- ✅ **IAM Setup** - Secure role and policy configuration
- ✅ **Documentation** - Comprehensive guides and references
- ✅ **Health Checks** - Built-in monitoring and status checks
- ✅ **Auto-scaling** - Ready for CPU-based auto-scaling
- ✅ **Security** - Secrets Manager integration for sensitive data

---

## 🚀 Quick Start (Choose One)

### Option 1: Windows (PowerShell)
```powershell
# Step 1: Set up IAM and secrets (one-time)
.\setup-ecs-iam.ps1

# Step 2: Deploy to ECS
.\deploy-ecs.ps1
```

### Option 2: Linux/Mac (Bash)
```bash
# Step 1: Set up IAM and secrets (one-time)
chmod +x setup-ecs-iam.ps1  # If using PowerShell Core
./setup-ecs-iam.ps1

# Or with separate setup script (create one from deploy-ecs.sh)
chmod +x deploy-ecs.sh
./deploy-ecs.sh
```

---

## 📋 Pre-Deployment Checklist

Before running the deployment scripts, ensure you have:

### ✅ AWS Setup
- [ ] AWS account with active credentials
- [ ] AWS CLI installed and configured (`aws --version`)
- [ ] Verify credentials: `aws sts get-caller-identity`

### ✅ Networking
- [ ] VPC created with at least 2 subnets
- [ ] Security group with:
  - Inbound: TCP port 8000 (from ALB or 0.0.0.0/0)
  - Outbound: All traffic
- [ ] Note your **Subnet IDs** and **Security Group ID**

### ✅ Database
- [ ] RDS PostgreSQL instance running
- [ ] Security group allows inbound on port 5432
- [ ] Know your **database connection string**

### ✅ Local Environment
- [ ] Docker installed (`docker --version`)
- [ ] Docker daemon running
- [ ] PowerShell 5.1+ (Windows) or Bash (Linux/Mac)

---

## 📚 Documentation Files

| File | Purpose | When to Read |
|------|---------|--------------|
| **ECS_DEPLOYMENT_SUMMARY.md** | Complete overview of deployment | First - to understand the setup |
| **ECS_DEPLOYMENT_CHECKLIST.md** | Step-by-step checklist | Before and during deployment |
| **ECS_DEPLOYMENT_GUIDE.md** | Comprehensive guide with details | For detailed implementation info |
| **ECS_COMMANDS_REFERENCE.md** | AWS CLI command reference | When managing the service |
| **HEALTH_CHECK_SETUP.md** | Health check endpoint info | If customizing health checks |

---

## 🔧 Configuration Files

### Before Deploying - IMPORTANT!

Edit **`deploy-ecs.ps1`** (or `deploy-ecs.sh` for Linux) around line 140:

```powershell
# Replace with your actual subnet and security group IDs
$SubnetIds = "subnet-12345678,subnet-87654321"    # ← UPDATE THIS
$SecurityGroupIds = "sg-12345678"                  # ← UPDATE THIS
```

Get your IDs:
```powershell
# List subnets
aws ec2 describe-subnets --region us-east-1 --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output table

# List security groups
aws ec2 describe-security-groups --region us-east-1 --query 'SecurityGroups[*].[GroupId,GroupName]' --output table
```

---

## 🎯 Deployment Steps

### Step 1: Run IAM Setup (One-Time)
```powershell
.\setup-ecs-iam.ps1
```

This will:
- ✓ Create `ecsTaskExecutionRole` 
- ✓ Create `ecsTaskRole`
- ✓ Store secrets in AWS Secrets Manager

**You'll be prompted for:**
- AWS Access Key ID
- AWS Secret Access Key
- Database URL (e.g., `postgresql://user:password@endpoint:5432/dbname`)

### Step 2: Update Deployment Script
Edit `deploy-ecs.ps1` with your VPC subnet and security group IDs (see above).

### Step 3: Run Deployment Script
```powershell
.\deploy-ecs.ps1
```

The script will:
1. Build Docker image
2. Login to ECR
3. Push image to ECR
4. Register task definition
5. Create ECS cluster
6. Create CloudWatch logs
7. Create ECS service
8. Monitor deployment

**Expected time:** 5-10 minutes

### Step 4: Verify Deployment
```powershell
# Check service status
aws ecs describe-services `
    --cluster acko-production `
    --services acko-claims-engine-service `
    --region us-east-1 `
    --query 'services[0].[serviceName,status,runningCount,desiredCount]' `
    --output table

# View logs
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1
```

---

## 📊 What Gets Created

### AWS ECS Resources
- **Cluster:** `acko-production`
- **Service:** `acko-claims-engine-service`
- **Task Definition:** `acko-claims-engine` (Fargate)
- **Log Group:** `/ecs/acko-claims-engine`

### AWS ECR Resources
- **Repository:** `acko-claims-engine`
- **Image:** Latest tag with your image

### AWS IAM Resources
- **Execution Role:** `ecsTaskExecutionRole`
- **Task Role:** `ecsTaskRole`
- **Policies:** S3 access, Secrets Manager access

### AWS Secrets Manager
- **AWS Access Key ID:** `acko/aws-access-key-id`
- **AWS Secret Access Key:** `acko/aws-secret-access-key`
- **Database URL:** `acko/database-url`

---

## 🔍 Common Tasks

### View Service Status
```powershell
aws ecs describe-services --cluster acko-production --services acko-claims-engine-service --region us-east-1 --query 'services[0].[serviceName,status,runningCount,desiredCount]' --output table
```

### Scale Service
```powershell
# Scale to 3 tasks
aws ecs update-service --cluster acko-production --service acko-claims-engine-service --desired-count 3 --region us-east-1
```

### Deploy New Version
```powershell
# After pushing new image to ECR
aws ecs update-service --cluster acko-production --service acko-claims-engine-service --force-new-deployment --region us-east-1
```

### View Logs
```powershell
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1
```

---

## 🔐 Security Notes

### Secrets Management
- ✅ AWS credentials stored in **Secrets Manager** (encrypted)
- ✅ Database password stored in **Secrets Manager** (encrypted)
- ✅ Never stored in code or environment files

### Network Security
- ✅ ECS tasks in private subnets (optional, configurable)
- ✅ Security group restricts inbound traffic
- ✅ IAM roles follow least privilege principle

### Image Security
- ✅ Python 3.12-slim base image (minimal)
- ✅ No secrets in Dockerfile
- ✅ Production environment variables configured

---

## ⚠️ Important Notes

### Before First Deployment
1. **Update subnet and security group IDs** in `deploy-ecs.ps1`
2. **Verify AWS credentials** are working
3. **Ensure Docker is running** locally
4. **Test Docker image locally** first

### During Deployment
1. Script may take 5-10 minutes
2. You'll see various AWS API calls being made
3. This is normal - let it complete
4. Watch for error messages in red

### After Deployment
1. Check logs immediately: `aws logs tail /ecs/acko-claims-engine --follow`
2. Monitor for at least 5 minutes
3. Verify health checks pass
4. Check database connectivity in logs

### Cost Awareness
- **ECS Fargate (1 task, 512 CPU):** ~$15-20/month
- **ECR Storage:** ~$1-3/month
- **CloudWatch Logs:** ~$1-5/month
- **Data Transfer:** ~$5-10/month
- **RDS (db.t3.micro):** ~$30-50/month
- **Total:** ~$50-90/month for small production setup

---

## 🚨 Troubleshooting

### Script fails immediately
```powershell
# Check AWS credentials
aws sts get-caller-identity

# Check Docker
docker ps
```

### Task fails to start
```powershell
# Check logs immediately
aws logs tail /ecs/acko-claims-engine --follow --region us-east-1

# Check task status
aws ecs list-tasks --cluster acko-production --region us-east-1
```

### Service won't stabilize
```powershell
# Check service events
aws ecs describe-services --cluster acko-production --services acko-claims-engine-service --region us-east-1 --query 'services[0].events'
```

---

## 📖 Learn More

### AWS Documentation
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/launch_types.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)

### FastAPI & Docker
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Additional Guides
- See `ECS_DEPLOYMENT_GUIDE.md` for comprehensive details
- See `ECS_COMMANDS_REFERENCE.md` for CLI command examples
- See `ECS_DEPLOYMENT_CHECKLIST.md` for step-by-step checklist

---

## 🎓 Next Steps

After successful deployment:

1. **Set up Load Balancer** (optional but recommended)
   - ALB in front of ECS service
   - HTTPS/SSL certificate
   - Custom domain

2. **Configure Auto-Scaling**
   - CPU-based scaling (1-10 tasks)
   - Reference: `ecs-auto-scaling.json`

3. **Enable Monitoring**
   - CloudWatch alarms for CPU, memory
   - SNS notifications
   - Custom dashboards

4. **Set up CI/CD**
   - GitHub Actions
   - Automatic ECR push on git push
   - Automatic ECS deployment

5. **Schedule Backups**
   - RDS automated backups
   - S3 versioning
   - Secrets rotation

---

## 💬 Need Help?

1. **Check the logs first:**
   ```powershell
   aws logs tail /ecs/acko-claims-engine --follow --region us-east-1
   ```

2. **Review the checklists:**
   - See `ECS_DEPLOYMENT_CHECKLIST.md`
   - See `ECS_DEPLOYMENT_GUIDE.md`

3. **Look up AWS CLI commands:**
   - See `ECS_COMMANDS_REFERENCE.md`

4. **Verify prerequisites:**
   - AWS credentials working
   - Docker running
   - Network configured
   - Secrets created

---

## ✅ Deployment Complete!

Your ACKO Claims Engine is now running on AWS ECS!

### Service Details
- **Cluster:** `acko-production`
- **Service:** `acko-claims-engine-service`
- **Task Definition:** `acko-claims-engine`
- **Desired Tasks:** 1 (auto-scales to 10)
- **Health Check:** `/health`
- **Log Group:** `/ecs/acko-claims-engine`

### Status
- Monitor logs: `aws logs tail /ecs/acko-claims-engine --follow --region us-east-1`
- Check service: `aws ecs describe-services --cluster acko-production --services acko-claims-engine-service --region us-east-1`

---

**Last Updated:** June 1, 2026  
**Version:** 1.0.0  
**Status:** Ready for Production
