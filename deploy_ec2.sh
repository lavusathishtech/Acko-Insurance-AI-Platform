#!/bin/bash
# Deploy ACKO AI Claims Engine to an EC2 instance
# Prerequisites: AWS CLI configured, Docker installed on EC2, ECR repository created

set -e

# Variables (replace with your values)
AWS_REGION="us-east-1"
ECR_REPO="<your_account_id>.dkr.ecr.${AWS_REGION}.amazonaws.com/acko-claims-engine"
IMAGE_TAG="latest"
INSTANCE_ID=""  # optional: specify an existing EC2 instance ID
KEY_PAIR="my-key-pair"
SECURITY_GROUP="sg-xxxxxxxx"
INSTANCE_TYPE="t3.medium"
MODEL_S3_BUCKET="my-model-bucket"

# 1. Build Docker image
docker build -t acko-claims-engine:${IMAGE_TAG} .

# 2. Log in to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO%%/*}

# 3. Tag and push image
docker tag acko-claims-engine:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}
docker push ${ECR_REPO}:${IMAGE_TAG}

# 4. Launch EC2 instance (if not using an existing one)
if [ -z "${INSTANCE_ID}" ]; then
  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316  # Amazon Linux 2 AMI
    --instance-type ${INSTANCE_TYPE} \
    --key-name ${KEY_PAIR} \
    --security-group-ids ${SECURITY_GROUP} \
    --region ${AWS_REGION} \
    --query 'Instances[0].InstanceId' --output text)
  echo "Launched EC2 instance ${INSTANCE_ID}"
fi

# 5. Wait for instance to be running
aws ec2 wait instance-running --instance-ids ${INSTANCE_ID} --region ${AWS_REGION}

# 6. Get public DNS
PUBLIC_DNS=$(aws ec2 describe-instances --instance-ids ${INSTANCE_ID} --region ${AWS_REGION} --query 'Reservations[0].Instances[0].PublicDnsName' --output text)

# 7. Install Docker on the instance (Amazon Linux 2)
ssh -o StrictHostKeyChecking=no -i "${KEY_PAIR}.pem" ec2-user@${PUBLIC_DNS} <<'EOF'
  sudo yum update -y
  sudo amazon-linux-extras enable docker
  sudo yum install -y docker
  sudo service docker start
  sudo usermod -a -G docker ec2-user
EOF

# 8. Pull and run the container on the instance
ssh -i "${KEY_PAIR}.pem" ec2-user@${PUBLIC_DNS} <<'EOF'
  docker pull ${ECR_REPO}:${IMAGE_TAG}
  docker run -d \
    -p 80:8000 \
    -e MODEL_S3_BUCKET=${MODEL_S3_BUCKET} \
    --name acko-claims-engine ${ECR_REPO}:${IMAGE_TAG}
EOF

echo "Deployment complete! Access the website at http://${PUBLIC_DNS}"
