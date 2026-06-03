# models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
import datetime
from database import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    claims = relationship("Claim", back_populates="customer")
    quotations = relationship("Quotation", back_populates="customer")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="admin")  # admin, manager
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    vehicle_type = Column(String, nullable=False) # Car or Bike
    vehicle_model = Column(String, nullable=False)
    manufacturing_year = Column(Integer, nullable=False)
    incident_date = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    damage_severity = Column(String, nullable=True) # Low, Moderate, Severe
    affected_parts = Column(String, nullable=True) # e.g. Bumper, Headlight
    estimated_payout = Column(Float, default=0.0)
    approval_probability = Column(Float, default=0.0)
    status = Column(String, default="submitted") # submitted, approved, rejected
    image_path = Column(String, nullable=True)
    fraud_risk = Column(String, default="low") # low, medium, high
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="claims")

class Quotation(Base):
    __tablename__ = "quotations"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    vehicle_type = Column(String, nullable=False) # Car or Bike
    vehicle_model = Column(String, nullable=False)
    registration_year = Column(Integer, nullable=False)
    fuel_type = Column(String, nullable=False)
    city = Column(String, nullable=False)
    idv = Column(Float, nullable=False)
    ncb = Column(Float, default=0.0)
    base_premium = Column(Float, default=0.0)
    own_damage = Column(Float, default=0.0)
    third_party = Column(Float, default=0.0)
    ncb_discount = Column(Float, default=0.0)
    gst = Column(Float, default=0.0)
    final_premium = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="quotations")

class ChatbotLog(Base):
    __tablename__ = "chatbot_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    session_id = Column(String, nullable=True)
    user_message = Column(Text, nullable=False)
    bot_reply = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ManagerQuestion(Base):
    __tablename__ = "manager_questions"
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=True)
    natural_language_question = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    execution_result = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    user_role = Column(String, nullable=False) # customer, admin
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
