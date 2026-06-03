# Add a health check endpoint to your FastAPI application
# This is required for ECS task health checks

# Add this to your main.py or app/main.py:

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="ACKO Claims Engine", version="1.0.0")

# Health check endpoint for ECS
@app.get("/health")
async def health_check():
    """
    Health check endpoint for ECS Task definition.
    ECS will periodically call this to ensure the container is healthy.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "acko-claims-engine",
            "version": "1.0.0"
        }
    )

# Readiness check endpoint
@app.get("/ready")
async def readiness_check():
    """
    Readiness check - verify dependencies are available
    """
    try:
        # Check database connection
        # Check S3 access
        # Check other critical services
        return JSONResponse(
            status_code=200,
            content={"status": "ready"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(e)}
        )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("ACKO Claims Engine starting up...")
    # Load models from S3
    # Initialize database connections
    # Warm up ML models
    print("ACKO Claims Engine ready to serve requests!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("ACKO Claims Engine shutting down...")
    # Close database connections
    # Save state if needed
    print("ACKO Claims Engine shutdown complete!")

# All your existing routes
# @app.post("/claims")
# @app.get("/dashboard")
# etc.
