# AWS S3 & PostgreSQL RDS - Quick Start Guide

## What's Been Added

This implementation adds:
1. **AWS S3 Integration** - Store ML models (.pkl), images, and forms organized by Customer ID and Claim ID
2. **PostgreSQL RDS** - Live database queries for real-time dashboard updates
3. **Automated Storage** - Claims automatically upload documents to S3 with references in RDS
4. **Model Versioning** - Track ML models in S3 with metadata in RDS

---

## Files Added/Modified

### New Files
- **`aws_config.py`** - AWS S3 client and utilities
- **`database_rds.py`** - PostgreSQL ORM models and configuration
- **`claims_service_s3.py`** - Service layer for claims + S3 uploads
- **`init_database.py`** - Database initialization script
- **`AWS_RDS_INTEGRATION.md`** - Comprehensive technical documentation

### Modified Files
- **`.env.example`** - Added AWS and RDS environment variables
- **`requirements.txt`** - Added boto3, psycopg2-binary
- **`app/routers/claims.py`** - New endpoints for S3-based claim creation

---

## Quick Setup (5 minutes)

### 1. Copy environment template

```bash
cp .env.example .env
```

### 2. Edit `.env` with your AWS and RDS credentials

```env
# AWS S3
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
S3_BUCKET_NAME=acko-insurance-models

# PostgreSQL RDS
DB_HOST=your-rds-instance.us-east-1.rds.amazonaws.com
DB_USER=acko_admin
DB_PASSWORD=your_password
DB_NAME=acko_insurance
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize database

```bash
python init_database.py
```

Expected output:
```
✓ Environment: VERIFIED
✓ AWS S3: VERIFIED
✓ Database: INITIALIZED
```

### 5. Start the app

```bash
uvicorn main:app --reload
```

---

## Usage Examples

### Example 1: Create a Claim with S3 Uploads

**Using cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/claims/create-claim-with-s3 \
  -F "customer_id=CUST123" \
  -F "policy_id=POL456" \
  -F "vehicle_type=Car" \
  -F "vehicle_model=Honda City" \
  -F "city=Mumbai" \
  -F "state=Maharashtra" \
  -F "incident_date=2024-06-01" \
  -F "damage_severity=moderate" \
  -F "image=@/path/to/claim_photo.jpg" \
  -F 'form_data={"damage_type":"collision","witnesses":2}'
```

**Response:**
```json
{
  "success": true,
  "claim_id": "CLM-A1B2C3D4",
  "image_stored": true,
  "form_stored": true,
  "approval_probability": 0.82,
  "fraud_probability": 0.15,
  "status": "pending"
}
```

---

### Example 2: Retrieve Claim with S3 URLs

**Using cURL:**
```bash
curl http://127.0.0.1:8000/api/claims/claim/CLM-A1B2C3D4
```

**Response:**
```json
{
  "id": "CLM-A1B2C3D4",
  "customer_id": "CUST123",
  "vehicle": "Car Honda City",
  "damage_severity": "moderate",
  "approval_probability": 0.82,
  "fraud_probability": 0.15,
  "image_url": "https://s3.amazonaws.com/...presigned_url...",
  "form_url": "https://s3.amazonaws.com/...presigned_url..."
}
```

---

### Example 3: Get All Customer Claims (Live from RDS)

**Using cURL:**
```bash
curl http://127.0.0.1:8000/api/claims/customer/CUST123/claims
```

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
      "approval_probability": 0.82,
      "status": "pending"
    }
  ]
}
```

---

### Example 4: Save ML Model to S3

**Python code:**
```python
from database_rds import SessionLocal
from claims_service_s3 import ModelService
import joblib

db = SessionLocal()

# Train model
model = joblib.load("models/trained_damage_classifier.pkl")

# Save to S3 with metadata
ModelService.save_model_to_s3(
    db=db,
    model_path="models/trained_damage_classifier.pkl",
    model_name="damage_classifier",
    model_type="image_classifier",
    version="2.0.0",
    accuracy=0.94,
    description="CNN-based damage classification"
)
```

---

### Example 5: Load ML Model from S3

**Python code:**
```python
from database_rds import SessionLocal
from claims_service_s3 import ModelService, ClaimsService
from aws_config import download_model_from_s3
import joblib

db = SessionLocal()

# Get S3 key for model
s3_key = ModelService.load_model_from_s3(
    db=db,
    model_name="damage_classifier",
    version="2.0.0"
)

# Download and load
download_model_from_s3(s3_key.split("/")[1], "models/loaded_model.pkl")
model = joblib.load("models/loaded_model.pkl")

# Use model for predictions...
```

---

## Data Storage Organization

### S3 Structure
```
s3://acko-insurance-models/
├── models/                    # ML Models
│   ├── damage_classifier_1.0.0.pkl
│   └── fraud_detector_2.1.0.pkl
│
└── uploads/                   # Customer Claims
    ├── customer_CUST123/
    │   └── claim_CLM-ABC123/
    │       ├── claim_image_1.jpg
    │       └── claim_form_CLM-ABC123.json
    │
    └── customer_CUST456/
        └── claim_CLM-DEF456/
            └── ...
```

### RDS Tables
```
customers          → Customer info
policies           → Insurance policies
claims             → All claims with S3 references
quotations         → Quotations
model_metadata     → ML model versions and performance
```

---

## Dashboard Integration

The management dashboard can now query **live data from RDS**:

```python
# Get fraud-flagged claims (escalation desk)
from database_rds import SessionLocal
from claims_service_s3 import ClaimsService

db = SessionLocal()
escalations = ClaimsService.get_dashboard_escalations(db)

# Returns real-time data from RDS for the 4D chart
```

---

## API Documentation

Full API docs available at: **http://127.0.0.1:8000/docs**

Key endpoints:
- `POST /api/claims/create-claim-with-s3` - Create claim with S3 uploads
- `GET /api/claims/claim/{claim_id}` - Get claim details
- `GET /api/claims/customer/{customer_id}/claims` - Get customer claims (live)

---

## Troubleshooting

### Error: "No module named 'database_rds'"
```bash
# Make sure you're in the project root directory
cd /path/to/final\ project
python init_database.py
```

### Error: "Could not connect to S3"
```bash
# Check AWS credentials in .env
# Test with: aws s3 ls
# Make sure S3 bucket exists
```

### Error: "Could not connect to RDS"
```bash
# Check DB_HOST format (should include .rds.amazonaws.com)
# Verify security group allows port 5432
# Test with: psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME>
```

---

## Performance Tips

1. **Dashboard Caching** - Cache RDS queries with 5-min TTL
2. **S3 Uploads** - Use S3 Transfer Acceleration for faster uploads
3. **Model Loading** - Cache loaded models in memory
4. **Batch Operations** - Process multiple claims in batches

---

## Security Checklist

- [ ] AWS credentials in `.env` (never commit)
- [ ] RDS password uses strong characters
- [ ] S3 bucket policy restricts public access
- [ ] RDS security group restricted to app servers
- [ ] Enable RDS encryption
- [ ] Enable RDS automated backups

---

## Next Steps

1. **Configure AWS & RDS** - Follow setup above
2. **Initialize Database** - Run `python init_database.py`
3. **Test Endpoints** - Use provided cURL examples
4. **Integrate Dashboard** - Update dashboard queries to use RDS
5. **Monitor** - Check CloudWatch metrics

---

For detailed documentation, see: [AWS_RDS_INTEGRATION.md](AWS_RDS_INTEGRATION.md)
