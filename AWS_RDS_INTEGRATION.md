# AWS S3 & PostgreSQL RDS Integration Guide

## Overview

ACKO platform now integrates with:
- **AWS S3** for storing ML models (.pkl files), claim images, and form data
- **PostgreSQL RDS** for live data queries on every refresh

All claim documents are organized by **Customer ID** and **Claim ID** in S3, and claim data is persisted in RDS for real-time dashboard updates.

---

## Architecture

### Data Flow

```
Upload Form/Image → FastAPI → S3 Upload + RDS Record
                                    ↓
Dashboard Query → RDS Query (Live Data) → Display
                                    ↓
Model Prediction → S3 Model Store → Load for Inference
```

### Storage Organization

**S3 Bucket Structure:**
```
s3://acko-insurance-models/
├── models/
│   ├── damage_classifier_v1.pkl
│   ├── fraud_detector_v2.pkl
│   └── approval_predictor_v1.pkl
└── uploads/
    ├── customer_C123/
    │   ├── claim_CLM-ABC123/
    │   │   ├── claim_image_1.jpg
    │   │   ├── claim_image_2.jpg
    │   │   └── claim_form_CLM-ABC123.json
    │   └── claim_CLM-DEF456/
    │       ├── claim_image.jpg
    │       └── claim_form_CLM-DEF456.json
    └── customer_C456/
        └── claim_CLM-GHI789/
            └── ...
```

**RDS Tables:**
- `customers` - Customer information
- `policies` - Insurance policies
- `claims` - Claims with S3 references
- `quotations` - Policy quotations
- `model_metadata` - ML model tracking

---

## Setup Instructions

### 1. AWS S3 Configuration

#### Create S3 Bucket

```bash
aws s3 mb s3://acko-insurance-models --region us-east-1
```

#### Create IAM User for App Access

```bash
aws iam create-user --user-name acko-s3-access
aws iam create-access-key --user-name acko-s3-access
```

#### Attach S3 Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::acko-insurance-models",
                "arn:aws:s3:::acko-insurance-models/*"
            ]
        }
    ]
}
```

#### Add to `.env`

```env
AWS_ACCESS_KEY_ID=your_access_key_from_iam
AWS_SECRET_ACCESS_KEY=your_secret_key_from_iam
AWS_REGION=us-east-1
S3_BUCKET_NAME=acko-insurance-models
```

---

### 2. PostgreSQL RDS Setup

#### Create RDS Instance

```bash
aws rds create-db-instance \
    --db-instance-identifier acko-insurance-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username acko_admin \
    --master-user-password 'YourSecurePassword123!' \
    --allocated-storage 20 \
    --region us-east-1
```

#### Get RDS Endpoint

```bash
aws rds describe-db-instances \
    --db-instance-identifier acko-insurance-db \
    --query 'DBInstances[0].Endpoint.Address'
```

#### Add to `.env`

```env
DB_HOST=acko-insurance-db.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=acko_insurance
DB_USER=acko_admin
DB_PASSWORD=YourSecurePassword123!
```

#### Initialize Database Tables

```bash
python -c "from database_rds import init_db; init_db()"
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages added:
- `boto3` - AWS SDK
- `psycopg2-binary` - PostgreSQL driver
- `sqlalchemy` - ORM

---

## API Endpoints

### Create Claim with S3 Uploads

**POST** `/api/claims/create-claim-with-s3`

**Request:**
```json
{
    "customer_id": "CUST123",
    "policy_id": "POL456",
    "vehicle_type": "Car",
    "vehicle_model": "Honda City",
    "city": "Mumbai",
    "state": "Maharashtra",
    "incident_date": "2024-06-01",
    "description": "Front bumper damage due to collision",
    "damage_severity": "moderate",
    "claim_amount": 50000,
    "idv": 350000,
    "image": <file>,
    "form_data": "{\"damage_type\": \"collision\", \"witnesses\": 2}"
}
```

**Response:**
```json
{
    "success": true,
    "claim_id": "CLM-A1B2C3D4",
    "customer_id": "CUST123",
    "approval_probability": 0.82,
    "fraud_probability": 0.15,
    "image_stored": true,
    "form_stored": true,
    "status": "pending",
    "message": "Claim created successfully and uploaded to S3"
}
```

---

### Get Claim Details

**GET** `/api/claims/claim/{claim_id}`

**Response:**
```json
{
    "id": "CLM-A1B2C3D4",
    "customer_id": "CUST123",
    "vehicle_type": "Car",
    "vehicle_model": "Honda City",
    "damage_severity": "moderate",
    "claim_amount": 50000,
    "approval_probability": 0.82,
    "fraud_probability": 0.15,
    "status": "pending",
    "created_at": "2024-06-01T10:30:00",
    "image_url": "https://acko-insurance-models.s3.amazonaws.com/uploads/customer_CUST123/claim_CLM-A1B2C3D4/image.jpg?X-Amz-Signature=...",
    "form_url": "https://acko-insurance-models.s3.amazonaws.com/uploads/customer_CUST123/claim_CLM-A1B2C3D4/claim_form_CLM-A1B2C3D4.json?X-Amz-Signature=..."
}
```

---

### Get Customer Claims

**GET** `/api/claims/customer/{customer_id}/claims`

**Response:**
```json
{
    "customer_id": "CUST123",
    "total_claims": 3,
    "claims": [
        {
            "id": "CLM-A1B2C3D4",
            "vehicle": "Car Honda City",
            "amount": 50000,
            "status": "pending",
            "approval_probability": 0.82,
            "fraud_probability": 0.15,
            "created_at": "2024-06-01T10:30:00"
        }
    ]
}
```

---

## Usage Examples

### Python - Save Model to S3

```python
from database_rds import SessionLocal
from claims_service_s3 import ModelService

db = SessionLocal()

# Train your model
model = train_model()

# Save to S3 and register in RDS
ModelService.save_model_to_s3(
    db=db,
    model_path="models/damage_classifier.pkl",
    model_name="damage_classifier",
    model_type="image_classifier",
    version="1.0.0",
    accuracy=0.94,
    description="CNN-based damage severity classifier"
)
```

### Python - Load Model from S3

```python
from database_rds import SessionLocal
from claims_service_s3 import ModelService
import joblib

db = SessionLocal()

# Get S3 key for latest model version
s3_key = ModelService.load_model_from_s3(
    db=db,
    model_name="damage_classifier"
)

# Download and load
from aws_config import download_model_from_s3
download_model_from_s3(s3_key.split("/")[1], "models/damage_classifier_temp.pkl")
model = joblib.load("models/damage_classifier_temp.pkl")
```

### Python - Create Claim with Uploads

```python
from database_rds import SessionLocal
from claims_service_s3 import ClaimsService

db = SessionLocal()

result = ClaimsService.create_claim_with_uploads(
    db=db,
    customer_id="CUST123",
    policy_id="POL456",
    vehicle_data={
        "vehicle_type": "Car",
        "vehicle_model": "Honda City",
        "city": "Mumbai",
        "state": "Maharashtra",
    },
    damage_data={
        "severity": "moderate",
        "severity_score": 2,
        "claim_amount": 50000,
        "approval_probability": 0.82,
        "approval_percent": 82,
        "fraud_probability": 0.15,
        "description": "Collision damage"
    },
    image_path="path/to/claim_image.jpg",
    form_data={
        "damage_type": "collision",
        "witnesses": 2,
        "police_report": "FIR123456"
    }
)

print(f"Claim created: {result['claim_id']}")
print(f"Image stored: {result['image_s3_key']}")
print(f"Form stored: {result['form_s3_key']}")
```

### Dashboard - Query Live Data from RDS

```python
from database_rds import SessionLocal
from claims_service_s3 import ClaimsService

db = SessionLocal()

# Get all fraud-flagged claims (escalation desk)
escalations = ClaimsService.get_dashboard_escalations(db)

# Returns:
# [
#     {
#         "id": "CLM-A1B2C3D4",
#         "vehicle": "Car Honda City",
#         "region": "Maharashtra",
#         "payout": "₹ 50,000",
#         "fraud_score": 75,
#         "justification": "High fraud risk detected"
#     }
# ]
```

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region for S3 and RDS | `us-east-1` |
| `S3_BUCKET_NAME` | S3 bucket for storage | `acko-insurance-models` |
| `DB_HOST` | RDS database hostname | `acko-db.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com` |
| `DB_PORT` | RDS port | `5432` |
| `DB_NAME` | Database name | `acko_insurance` |
| `DB_USER` | Database user | `acko_admin` |
| `DB_PASSWORD` | Database password | `YourSecurePassword123!` |

---

## Troubleshooting

### S3 Connection Issues

```bash
# Test AWS credentials
aws s3 ls --profile default

# If error: InvalidAccessKeyId or AccessDenied
# 1. Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# 2. Verify IAM policy includes S3 permissions
# 3. Check S3 bucket exists: aws s3 ls s3://acko-insurance-models
```

### RDS Connection Issues

```bash
# Test PostgreSQL connection
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME>

# If connection refused:
# 1. Check DB_HOST is correct (has .rds.amazonaws.com)
# 2. Verify security group allows port 5432
# 3. Check RDS instance is in Available state
# 4. Verify credentials: aws rds describe-db-instances
```

### Model Upload Failures

```python
# Check S3 permissions
from aws_config import s3_client

try:
    response = s3_client.head_bucket(Bucket='acko-insurance-models')
    print("✓ S3 bucket accessible")
except Exception as e:
    print(f"✗ S3 error: {e}")
```

---

## Security Best Practices

1. **Never commit `.env` with real credentials** - Use `.env.example` as template
2. **Rotate AWS credentials** - Change keys every 90 days
3. **Use RDS encryption** - Enable storage encryption for RDS
4. **Set S3 bucket policies** - Restrict public access
5. **Enable RDS backups** - Set automated backups to 30 days
6. **Use VPC security groups** - Restrict RDS access to app servers only
7. **Set IAM policy scope** - Restrict S3 access to specific bucket/prefix

---

## Monitoring

### CloudWatch Metrics

```bash
# Monitor S3 uploads
aws cloudwatch get-metric-statistics \
    --namespace AWS/S3 \
    --metric-name NumberOfObjects \
    --dimensions Name=BucketName,Value=acko-insurance-models \
    --start-time 2024-06-01T00:00:00Z \
    --end-time 2024-06-02T00:00:00Z \
    --period 3600
```

### RDS Monitoring

```bash
# Check RDS performance
aws rds describe-db-instances \
    --db-instance-identifier acko-insurance-db \
    --query 'DBInstances[0].[DBInstanceStatus,StorageUsed,DBInstanceClass]'
```

---

## Performance Optimization

- **S3**: Enable S3 Transfer Acceleration for faster uploads
- **RDS**: Add read replicas for high-traffic dashboards
- **Caching**: Cache dashboard queries with 5-minute TTL
- **Batch Operations**: Batch multiple claims for bulk imports
