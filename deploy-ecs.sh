#!/bin/bash
# AWS ECS Deployment Script for ACKO Claims Engine (Linux/Mac version)
# Prerequisites: AWS CLI configured, Docker installed locally, AWS ECR repository created

set -e

# Default parameters
AWS_REGION="${1:-us-east-1}"
AWS_ACCOUNT_ID="${2:-}"
ECR_REPO_NAME="${3:-acko-claims-engine}"
IMAGE_TAG="${4:-latest}"
ECS_CLUSTER_NAME="${5:-acko-production}"
ECS_SERVICE_NAME="${6:-acko-claims-engine-service}"
ECS_TASK_DEFINITION="${7:-acko-claims-engine}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# 1. Get AWS Account ID if not provided
if [ -z "$AWS_ACCOUNT_ID" ]; then
    log "$CYAN" "Fetching AWS Account ID..."
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log "$GREEN" "AWS Account ID: $AWS_ACCOUNT_ID"
fi

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME"

# 2. Build Docker Image
log "$CYAN" "Building Docker image..."
docker build -t "$ECR_REPO_NAME:$IMAGE_TAG" .
if [ $? -ne 0 ]; then
    log "$RED" "Docker build failed!"
    exit 1
fi
log "$GREEN" "Docker image built successfully"

# 3. Login to ECR
log "$CYAN" "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
if [ $? -ne 0 ]; then
    log "$RED" "ECR login failed!"
    exit 1
fi
log "$GREEN" "ECR login successful"

# 4. Create ECR repository if it doesn't exist
log "$CYAN" "Checking ECR repository..."
REPO_EXISTS=$(aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" --query 'repositories[0].repositoryUri' --output text 2>/dev/null || echo "")
if [ -z "$REPO_EXISTS" ]; then
    log "$CYAN" "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region "$AWS_REGION"
    log "$GREEN" "ECR repository created"
else
    log "$GREEN" "ECR repository already exists: $REPO_EXISTS"
fi

# 5. Tag and push image to ECR
log "$CYAN" "Tagging and pushing Docker image to ECR..."
docker tag "$ECR_REPO_NAME:$IMAGE_TAG" "$ECR_URI:$IMAGE_TAG"
docker push "$ECR_URI:$IMAGE_TAG"
if [ $? -ne 0 ]; then
    log "$RED" "Docker push failed!"
    exit 1
fi
log "$GREEN" "Image pushed to ECR: $ECR_URI:$IMAGE_TAG"

# 6. Update ECS task definition with correct AWS account and region
log "$CYAN" "Updating ECS task definition..."
sed -e "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" \
    -e "s|<AWS_REGION>|$AWS_REGION|g" \
    ecs-task-definition.json > ecs-task-definition-updated.json

# Register/update task definition
log "$CYAN" "Registering ECS task definition..."
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition-updated.json \
    --region "$AWS_REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)
log "$GREEN" "Task definition registered: $TASK_DEF_ARN"

# 7. Create ECS Cluster if it doesn't exist
log "$CYAN" "Checking ECS cluster..."
CLUSTER_EXISTS=$(aws ecs describe-clusters --clusters "$ECS_CLUSTER_NAME" --region "$AWS_REGION" --query 'clusters[0].clusterName' --output text 2>/dev/null || echo "")
if [ -z "$CLUSTER_EXISTS" ] || [ "$CLUSTER_EXISTS" = "None" ]; then
    log "$CYAN" "Creating ECS cluster: $ECS_CLUSTER_NAME"
    aws ecs create-cluster --cluster-name "$ECS_CLUSTER_NAME" --region "$AWS_REGION"
    log "$GREEN" "ECS cluster created"
else
    log "$GREEN" "ECS cluster already exists: $ECS_CLUSTER_NAME"
fi

# 8. Create CloudWatch Log Group
log "$CYAN" "Checking CloudWatch Log Group..."
LOG_GROUP_EXISTS=$(aws logs describe-log-groups --log-group-name-prefix "/ecs/acko-claims-engine" --region "$AWS_REGION" --query 'logGroups[0].logGroupName' --output text 2>/dev/null || echo "")
if [ -z "$LOG_GROUP_EXISTS" ] || [ "$LOG_GROUP_EXISTS" = "None" ]; then
    log "$CYAN" "Creating CloudWatch Log Group..."
    aws logs create-log-group --log-group-name "/ecs/acko-claims-engine" --region "$AWS_REGION"
    aws logs put-retention-policy --log-group-name "/ecs/acko-claims-engine" --retention-in-days 7 --region "$AWS_REGION"
    log "$GREEN" "CloudWatch Log Group created"
else
    log "$GREEN" "CloudWatch Log Group already exists"
fi

# 9. Create or Update ECS Service
log "$CYAN" "Checking ECS service..."
SERVICE_EXISTS=$(aws ecs describe-services --cluster "$ECS_CLUSTER_NAME" --services "$ECS_SERVICE_NAME" --region "$AWS_REGION" --query 'services[0].serviceName' --output text 2>/dev/null || echo "")

if [ -z "$SERVICE_EXISTS" ] || [ "$SERVICE_EXISTS" = "None" ]; then
    log "$CYAN" "Creating ECS service: $ECS_SERVICE_NAME"
    
    # Note: Update these with your actual subnet and security group IDs
    SUBNET_IDS="subnet-12345678,subnet-87654321"  # Replace with your subnet IDs
    SECURITY_GROUP_IDS="sg-12345678"              # Replace with your security group ID
    
    log "$RED" "⚠️  UPDATE THE FOLLOWING BEFORE RUNNING:"
    log "$RED" "  Subnet IDs: $SUBNET_IDS"
    log "$RED" "  Security Group IDs: $SECURITY_GROUP_IDS"
    log "$RED" ""
    
    read -p "Press Enter to continue with deployment, or Ctrl+C to cancel..."
    
    aws ecs create-service \
        --cluster "$ECS_CLUSTER_NAME" \
        --service-name "$ECS_SERVICE_NAME" \
        --task-definition "$ECS_TASK_DEFINITION" \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_IDS],assignPublicIp=ENABLED}" \
        --region "$AWS_REGION"
    
    log "$GREEN" "ECS service created"
else
    log "$CYAN" "Updating ECS service: $ECS_SERVICE_NAME"
    aws ecs update-service \
        --cluster "$ECS_CLUSTER_NAME" \
        --service "$ECS_SERVICE_NAME" \
        --task-definition "$ECS_TASK_DEFINITION:1" \
        --force-new-deployment \
        --region "$AWS_REGION"
    
    log "$GREEN" "ECS service updated"
fi

# 10. Monitor deployment
log "$CYAN" "Waiting for service to stabilize (this may take a few minutes)..."
aws ecs wait services-stable \
    --cluster "$ECS_CLUSTER_NAME" \
    --services "$ECS_SERVICE_NAME" \
    --region "$AWS_REGION"

if [ $? -eq 0 ]; then
    log "$GREEN" "Service deployed and stabilized successfully!"
    
    # Get service details
    log "$CYAN" "Getting service details..."
    aws ecs describe-services \
        --cluster "$ECS_CLUSTER_NAME" \
        --services "$ECS_SERVICE_NAME" \
        --region "$AWS_REGION" \
        --query 'services[0].[serviceName,status,runningCount,desiredCount]' \
        --output table
else
    log "$RED" "Service deployment failed or timed out"
    exit 1
fi

# Cleanup
rm -f ecs-task-definition-updated.json

log "$GREEN" "Deployment completed successfully!"
log "$CYAN" "Service URL will be available through your load balancer or ALB"
