"""PostgreSQL RDS configuration and ORM models for ACKO platform."""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# RDS Configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "acko_insurance")
DB_USER = os.getenv("DB_USER", "acko_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Database connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Customer(Base):
    """Customer model."""
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    city = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Policy(Base):
    """Insurance policy model."""
    __tablename__ = "policies"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    vehicle_type = Column(String)
    vehicle_model = Column(String)
    vehicle_year = Column(Integer)
    idv = Column(Float)
    annual_premium = Column(Float)
    policy_type = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class Claim(Base):
    """Insurance claim model."""
    __tablename__ = "claims"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    policy_id = Column(String, nullable=True)
    vehicle_type = Column(String)
    vehicle_model = Column(String)
    damage_severity = Column(String)
    damage_severity_score = Column(Integer)
    claim_amount = Column(Float)
    approval_probability = Column(Float)
    approval_percent = Column(Float)
    fraud_probability = Column(Float)
    claim_approved = Column(Boolean, default=False)
    incident_date = Column(DateTime)
    city = Column(String)
    state = Column(String)
    description = Column(Text, nullable=True)
    image_s3_key = Column(String, nullable=True)
    form_s3_key = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Quotation(Base):
    """Insurance quotation model."""
    __tablename__ = "quotations"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, nullable=True, index=True)
    vehicle_type = Column(String)
    vehicle_model = Column(String)
    vehicle_year = Column(Integer)
    idv = Column(Float)
    annual_premium = Column(Float)
    base_premium = Column(Float)
    ncb_discount = Column(Float)
    gst_amount = Column(Float)
    policy_type = Column(String)
    city = Column(String)
    fuel_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelMetadata(Base):
    """Track ML model versions stored in S3."""
    __tablename__ = "model_metadata"
    
    id = Column(String, primary_key=True, index=True)
    model_name = Column(String, index=True)
    s3_key = Column(String)
    model_type = Column(String)  # e.g., "damage_classifier", "approval_predictor"
    version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    accuracy = Column(Float, nullable=True)
    description = Column(Text, nullable=True)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables initialized")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
