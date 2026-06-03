#!/usr/bin/env python3
"""Database migration and initialization script for ACKO platform."""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def init_database():
    """Initialize RDS database tables."""
    try:
        from database_rds import engine, Base, SessionLocal
        
        print("=" * 60)
        print("ACKO Platform - Database Initialization")
        print("=" * 60)
        print()
        
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
        print()
        
        # List created tables
        print("Tables created:")
        for table_name in Base.metadata.tables:
            print(f"  - {table_name}")
        print()
        
        # Verify connection
        db = SessionLocal()
        try:
            result = db.execute("SELECT 1")
            print("✓ Database connection verified")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
        finally:
            db.close()
        
        print()
        print("=" * 60)
        print("Database initialization completed successfully!")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"✗ Error: {e}")
        print("Make sure you have installed required packages:")
        print("  pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        return False


def verify_s3_config():
    """Verify AWS S3 configuration."""
    try:
        from aws_config import s3_client, S3_BUCKET_NAME, AWS_REGION
        
        print()
        print("=" * 60)
        print("AWS S3 Configuration Verification")
        print("=" * 60)
        print()
        
        print(f"Bucket Name: {S3_BUCKET_NAME}")
        print(f"Region: {AWS_REGION}")
        print()
        
        # Test connection
        print("Testing S3 connection...")
        try:
            response = s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"✓ S3 bucket accessible: {S3_BUCKET_NAME}")
        except Exception as e:
            print(f"✗ S3 connection error: {e}")
            print("Make sure AWS credentials are set in .env")
            return False
        
        print()
        print("=" * 60)
        print("S3 configuration verified!")
        print("=" * 60)
        return True
        
    except ImportError:
        print("⚠ AWS integration not configured (aws_config module missing)")
        return False
    except Exception as e:
        print(f"✗ Error verifying S3: {e}")
        return False


def verify_environment():
    """Verify environment variables are set."""
    print()
    print("=" * 60)
    print("Environment Variables Check")
    print("=" * 60)
    print()
    
    required_vars = {
        "DB_HOST": "PostgreSQL RDS hostname",
        "DB_USER": "PostgreSQL username",
        "DB_PASSWORD": "PostgreSQL password",
        "DB_NAME": "Database name",
        "AWS_ACCESS_KEY_ID": "AWS access key",
        "AWS_SECRET_ACCESS_KEY": "AWS secret key",
        "S3_BUCKET_NAME": "S3 bucket name",
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var, "")
        if value:
            print(f"✓ {var:<25} = {value[:20]}{'...' if len(value) > 20 else ''}")
        else:
            print(f"✗ {var:<25} = <NOT SET>")
            missing_vars.append(var)
    
    print()
    
    if missing_vars:
        print("Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print()
        print("Set them in .env file:")
        print("  cp .env.example .env")
        print("  # Edit .env with your credentials")
        return False
    else:
        print("✓ All required environment variables are set")
        return True


def main():
    """Run all initialization steps."""
    print()
    print("Starting ACKO Platform initialization...")
    print()
    
    # Step 1: Check environment
    print("Step 1: Checking environment variables...")
    if not verify_environment():
        print("\n⚠ Some environment variables are missing.")
        print("Please set them in .env file and try again.")
        return False
    
    # Step 2: Verify S3 config
    print("\nStep 2: Verifying AWS S3 configuration...")
    s3_ok = verify_s3_config()
    
    # Step 3: Initialize database
    print("\nStep 3: Initializing database...")
    if not init_database():
        print("\n✗ Database initialization failed")
        return False
    
    # Summary
    print()
    print("=" * 60)
    print("INITIALIZATION SUMMARY")
    print("=" * 60)
    print(f"✓ Environment: VERIFIED")
    print(f"{'✓' if s3_ok else '✗'} AWS S3: {'VERIFIED' if s3_ok else 'NEEDS CONFIG'}")
    print(f"✓ Database: INITIALIZED")
    print()
    print("Next steps:")
    print("  1. Start the application: uvicorn main:app --reload")
    print("  2. Access dashboard: http://127.0.0.1:8000")
    print("  3. API documentation: http://127.0.0.1:8000/docs")
    print()
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
