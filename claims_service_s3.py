"""Claims service with S3 and RDS integration."""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from database_rds import Claim, ModelMetadata, get_db
from aws_config import (
    upload_image_to_s3,
    upload_form_to_s3,
    list_customer_uploads,
    get_s3_presigned_url,
    upload_model_to_s3,
    download_model_from_s3,
)


class ClaimsService:
    """Service for managing insurance claims with S3 and RDS integration."""
    
    @staticmethod
    def create_claim_with_uploads(
        db: Session,
        customer_id: str,
        policy_id: str,
        vehicle_data: dict,
        damage_data: dict,
        image_path: Optional[str] = None,
        form_data: Optional[dict] = None,
    ) -> Dict:
        """Create a claim and upload associated images/forms to S3."""
        
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        
        # Upload image to S3 if provided
        image_s3_key = None
        if image_path and os.path.exists(image_path):
            image_s3_key = upload_image_to_s3(image_path, customer_id, claim_id)
        
        # Upload form to S3 if provided
        form_s3_key = None
        if form_data:
            form_s3_key = upload_form_to_s3(
                form_data, 
                customer_id, 
                claim_id, 
                f"claim_form_{claim_id}.json"
            )
        
        # Create claim record in RDS
        claim = Claim(
            id=claim_id,
            customer_id=customer_id,
            policy_id=policy_id,
            vehicle_type=vehicle_data.get("vehicle_type"),
            vehicle_model=vehicle_data.get("vehicle_model"),
            damage_severity=damage_data.get("severity"),
            damage_severity_score=damage_data.get("severity_score", 0),
            claim_amount=damage_data.get("claim_amount", 0),
            approval_probability=damage_data.get("approval_probability", 0),
            approval_percent=damage_data.get("approval_percent", 0),
            fraud_probability=damage_data.get("fraud_probability", 0),
            incident_date=datetime.utcnow(),
            city=vehicle_data.get("city"),
            state=vehicle_data.get("state"),
            description=damage_data.get("description"),
            image_s3_key=image_s3_key,
            form_s3_key=form_s3_key,
            status="pending",
        )
        
        db.add(claim)
        db.commit()
        db.refresh(claim)
        
        return {
            "claim_id": claim_id,
            "customer_id": customer_id,
            "image_s3_key": image_s3_key,
            "form_s3_key": form_s3_key,
            "approval_probability": damage_data.get("approval_probability", 0),
            "fraud_probability": damage_data.get("fraud_probability", 0),
            "status": "pending",
        }
    
    @staticmethod
    def get_claim_details(db: Session, claim_id: str) -> Optional[Dict]:
        """Get claim details from RDS and generate presigned URLs for S3 assets."""
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        
        if not claim:
            return None
        
        return {
            "id": claim.id,
            "customer_id": claim.customer_id,
            "vehicle_type": claim.vehicle_type,
            "vehicle_model": claim.vehicle_model,
            "damage_severity": claim.damage_severity,
            "claim_amount": claim.claim_amount,
            "approval_probability": claim.approval_probability,
            "fraud_probability": claim.fraud_probability,
            "status": claim.status,
            "created_at": claim.created_at.isoformat(),
            "image_url": get_s3_presigned_url(claim.image_s3_key) if claim.image_s3_key else None,
            "form_url": get_s3_presigned_url(claim.form_s3_key) if claim.form_s3_key else None,
        }
    
    @staticmethod
    def get_customer_claims(db: Session, customer_id: str) -> List[Dict]:
        """Get all claims for a customer with live data from RDS."""
        claims = db.query(Claim).filter(Claim.customer_id == customer_id).all()
        
        return [
            {
                "id": claim.id,
                "vehicle": f"{claim.vehicle_type} {claim.vehicle_model}",
                "amount": claim.claim_amount,
                "status": claim.status,
                "approval_probability": claim.approval_probability,
                "fraud_probability": claim.fraud_probability,
                "created_at": claim.created_at.isoformat(),
            }
            for claim in claims
        ]
    
    @staticmethod
    def get_dashboard_escalations(db: Session) -> List[Dict]:
        """Get escalation desk data (fraud-flagged claims) from RDS."""
        escalations = db.query(Claim).filter(
            Claim.fraud_probability >= 0.5
        ).all()
        
        return [
            {
                "id": claim.id,
                "vehicle": f"{claim.vehicle_type} {claim.vehicle_model}",
                "region": claim.state,
                "payout": f"₹ {claim.claim_amount:,.0f}",
                "fraud_score": round(claim.fraud_probability * 100),
                "justification": "High fraud risk detected",
            }
            for claim in escalations
        ]
    
    @staticmethod
    def update_claim_status(db: Session, claim_id: str, status: str) -> bool:
        """Update claim status in RDS."""
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        
        if not claim:
            return False
        
        claim.status = status
        claim.updated_at = datetime.utcnow()
        db.commit()
        return True


class ModelService:
    """Service for managing ML models in S3 and RDS metadata."""
    
    @staticmethod
    def save_model_to_s3(
        db: Session,
        model_path: str,
        model_name: str,
        model_type: str,
        version: str,
        accuracy: Optional[float] = None,
        description: Optional[str] = None,
    ) -> bool:
        """Save a joblib model to S3 and register metadata in RDS."""
        
        # Upload model to S3
        s3_key = upload_model_to_s3(model_path, f"{model_name}_{version}.pkl")
        
        if not s3_key:
            return False
        
        # Store metadata in RDS
        metadata = ModelMetadata(
            id=f"MDL-{uuid.uuid4().hex[:8].upper()}",
            model_name=model_name,
            s3_key=s3_key,
            model_type=model_type,
            version=version,
            accuracy=accuracy,
            description=description,
        )
        
        db.add(metadata)
        db.commit()
        
        print(f"✓ Model saved to S3 and metadata stored in RDS: {model_name} v{version}")
        return True
    
    @staticmethod
    def load_model_from_s3(
        db: Session,
        model_name: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """Get the S3 key of a model, optionally specific version."""
        
        query = db.query(ModelMetadata).filter(ModelMetadata.model_name == model_name)
        
        if version:
            query = query.filter(ModelMetadata.version == version)
        
        metadata = query.order_by(ModelMetadata.created_at.desc()).first()
        
        if not metadata:
            return None
        
        return metadata.s3_key
    
    @staticmethod
    def get_model_versions(db: Session, model_name: str) -> List[Dict]:
        """Get all versions of a model with metadata."""
        
        models = db.query(ModelMetadata).filter(
            ModelMetadata.model_name == model_name
        ).order_by(ModelMetadata.created_at.desc()).all()
        
        return [
            {
                "version": m.version,
                "created_at": m.created_at.isoformat(),
                "accuracy": m.accuracy,
                "s3_key": m.s3_key,
            }
            for m in models
        ]
