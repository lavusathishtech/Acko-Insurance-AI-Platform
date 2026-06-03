from __future__ import annotations

import datetime as dt
from typing import Any, Optional
import json
import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.damage_ai import analyse_damage
from app.services.fraud import assess_fraud_risk
from app.services.insurance_logic import approval_probability
from damage_engine import estimate_claim_amount

# S3 and RDS integration
try:
    from database_rds import get_db
    from claims_service_s3 import ClaimsService, ModelService
    RDS_AVAILABLE = True
except ImportError:
    RDS_AVAILABLE = False
    print("⚠ RDS and S3 integration not available (database_rds module missing)")

router = APIRouter(tags=["claims"])


@router.post("/predict-claim")
async def predict_claim_endpoint(
    image: UploadFile = File(...),
    incident_date: str = Form(...),
    description: str = Form(""),
    idv: float = Form(350000),
) -> dict[str, Any]:
    file_bytes = await image.read()
    analysis, analysis_source = analyse_damage(file_bytes, description)
    estimated_amount = estimate_claim_amount(analysis, float(idv))
    prob = approval_probability(analysis, incident_date, description)
    fraud_risk, fraud_reasons = assess_fraud_risk(analysis, prob, description, len(file_bytes))
    status = "Instant approval likely" if prob >= 0.75 and fraud_risk == "low" else "Needs adjuster review"

    return {
        "estimated_amount": estimated_amount,
        "approval_probability": prob,
        "status": status,
        "analysis": analysis,
        "analysis_source": analysis_source,
        "fraud_risk": fraud_risk,
        "fraud_reasons": fraud_reasons,
        "claim_reference": f"CLM-{dt.datetime.now().strftime('%y%m%d%H%M%S')}",
    }


@router.post("/create-claim-with-s3")
async def create_claim_with_s3(
    customer_id: str = Form(...),
    policy_id: str = Form(...),
    vehicle_type: str = Form(...),
    vehicle_model: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    incident_date: str = Form(...),
    description: str = Form(""),
    damage_severity: str = Form("minor"),
    claim_amount: float = Form(0),
    idv: float = Form(350000),
    image: UploadFile = File(None),
    form_data: Optional[str] = Form(None),
    db: Session = Depends(get_db) if RDS_AVAILABLE else None,
) -> dict[str, Any]:
    """Create a claim with image and form uploads to S3, data stored in RDS."""
    
    if not RDS_AVAILABLE:
        raise HTTPException(status_code=500, detail="RDS integration not configured")
    
    # Save uploaded image temporarily
    image_path = None
    if image:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                content = await image.read()
                tmp_file.write(content)
                image_path = tmp_file.name
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
    
    try:
        # Analyze damage
        file_bytes = await image.read() if image else b""
        analysis, analysis_source = analyse_damage(file_bytes, description) if file_bytes else ({}, "no_image")
        estimated_amount = estimate_claim_amount(analysis, float(idv)) if analysis else claim_amount
        prob = approval_probability(analysis, incident_date, description) if analysis else 0.5
        fraud_risk, fraud_reasons = assess_fraud_risk(analysis, prob, description, len(file_bytes)) if analysis else ("low", [])
        
        # Prepare damage data
        damage_data = {
            "severity": damage_severity,
            "severity_score": {"minor": 1, "moderate": 2, "severe": 3, "total_loss": 4}.get(damage_severity, 1),
            "claim_amount": estimated_amount,
            "approval_probability": prob,
            "approval_percent": int(prob * 100),
            "fraud_probability": 0.5 if fraud_risk == "medium" else (0.8 if fraud_risk == "high" else 0.2),
            "description": description,
        }
        
        # Prepare vehicle data
        vehicle_data = {
            "vehicle_type": vehicle_type,
            "vehicle_model": vehicle_model,
            "city": city,
            "state": state,
        }
        
        # Parse form data if provided
        form_json = json.loads(form_data) if form_data else None
        
        # Create claim in RDS with S3 uploads
        result = ClaimsService.create_claim_with_uploads(
            db=db,
            customer_id=customer_id,
            policy_id=policy_id,
            vehicle_data=vehicle_data,
            damage_data=damage_data,
            image_path=image_path,
            form_data=form_json,
        )
        
        return {
            "success": True,
            "claim_id": result["claim_id"],
            "customer_id": result["customer_id"],
            "approval_probability": result["approval_probability"],
            "fraud_probability": result["fraud_probability"],
            "image_stored": result["image_s3_key"] is not None,
            "form_stored": result["form_s3_key"] is not None,
            "status": result["status"],
            "message": "Claim created successfully and uploaded to S3",
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating claim: {str(e)}")
    
    finally:
        # Clean up temporary file
        if image_path and os.path.exists(image_path):
            os.remove(image_path)


@router.get("/claim/{claim_id}")
async def get_claim(
    claim_id: str,
    db: Session = Depends(get_db) if RDS_AVAILABLE else None,
) -> dict[str, Any]:
    """Get claim details from RDS with presigned S3 URLs for images/forms."""
    
    if not RDS_AVAILABLE:
        raise HTTPException(status_code=500, detail="RDS integration not configured")
    
    claim = ClaimsService.get_claim_details(db, claim_id)
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return claim


@router.get("/customer/{customer_id}/claims")
async def get_customer_claims(
    customer_id: str,
    db: Session = Depends(get_db) if RDS_AVAILABLE else None,
) -> dict[str, Any]:
    """Get all claims for a customer with live RDS data."""
    
    if not RDS_AVAILABLE:
        raise HTTPException(status_code=500, detail="RDS integration not configured")
    
    claims = ClaimsService.get_customer_claims(db, customer_id)
    
    return {
        "customer_id": customer_id,
        "total_claims": len(claims),
        "claims": claims,
    }
