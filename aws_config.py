"""AWS S3 and RDS configuration for ACKO platform."""

import os
import boto3
from botocore.exceptions import ClientError

# AWS Configuration from environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "acko-insurance-models")
S3_MODELS_PREFIX = "models/"
S3_UPLOADS_PREFIX = "uploads/"

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def upload_model_to_s3(model_path: str, model_name: str) -> str:
    """Upload a joblib model file to S3 and return the S3 key."""
    try:
        s3_key = f"{S3_MODELS_PREFIX}{model_name}"
        s3_client.upload_file(model_path, S3_BUCKET_NAME, s3_key)
        print(f"✓ Model uploaded to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
        return s3_key
    except ClientError as e:
        print(f"✗ Error uploading model to S3: {e}")
        return None


def download_model_from_s3(model_name: str, local_path: str) -> bool:
    """Download a joblib model file from S3."""
    try:
        s3_key = f"{S3_MODELS_PREFIX}{model_name}"
        s3_client.download_file(S3_BUCKET_NAME, s3_key, local_path)
        print(f"✓ Model downloaded from S3: {local_path}")
        return True
    except ClientError as e:
        print(f"✗ Error downloading model from S3: {e}")
        return False


def upload_image_to_s3(image_path: str, customer_id: str, claim_id: str) -> str:
    """Upload a claim image to S3 organized by customer and claim ID."""
    try:
        filename = os.path.basename(image_path)
        s3_key = f"{S3_UPLOADS_PREFIX}customer_{customer_id}/claim_{claim_id}/{filename}"
        s3_client.upload_file(image_path, S3_BUCKET_NAME, s3_key)
        print(f"✓ Image uploaded to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
        return s3_key
    except ClientError as e:
        print(f"✗ Error uploading image to S3: {e}")
        return None


def upload_form_to_s3(form_data: dict, customer_id: str, claim_id: str, filename: str) -> str:
    """Upload form data (JSON) to S3."""
    try:
        import json
        from io import BytesIO
        
        json_data = json.dumps(form_data).encode('utf-8')
        s3_key = f"{S3_UPLOADS_PREFIX}customer_{customer_id}/claim_{claim_id}/{filename}"
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=json_data)
        print(f"✓ Form uploaded to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
        return s3_key
    except ClientError as e:
        print(f"✗ Error uploading form to S3: {e}")
        return None


def list_customer_uploads(customer_id: str) -> list:
    """List all uploads for a specific customer."""
    try:
        prefix = f"{S3_UPLOADS_PREFIX}customer_{customer_id}/"
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        files = [obj["Key"] for obj in response.get("Contents", [])]
        return files
    except ClientError as e:
        print(f"✗ Error listing customer uploads: {e}")
        return []


def get_s3_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL for accessing an S3 object."""
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiration,
        )
        return url
    except ClientError as e:
        print(f"✗ Error generating presigned URL: {e}")
        return None
