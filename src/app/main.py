"""
NAMASTE ICD Service - FastAPI Application Entry Point

A FHIR R4-compliant terminology microservice integrating NAMASTE terminologies
with WHO ICD-11 TM2 and Biomedicine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routes import codesystem, lookup, translate, bundle_upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    print("🚀 Starting NAMASTE ICD Service...")
    print(f"📊 Database: {settings.database_url}")
    print(f"🔍 ICD-11 API: {'Configured' if settings.icd11_client_id else 'Not configured'}")
    print(f"🔐 ABHA Auth: {'Configured' if settings.abha_introspection_url else 'Development mode'}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down NAMASTE ICD Service...")


# Create FastAPI application
app = FastAPI(
    title="NAMASTE ICD Service",
    description="FHIR R4-compliant terminology microservice integrating NAMASTE with WHO ICD-11",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(codesystem.router, prefix="/fhir", tags=["FHIR CodeSystem"])
app.include_router(lookup.router, prefix="/autocomplete", tags=["Terminology Lookup"])
app.include_router(translate.router, prefix="", tags=["Translation"])
app.include_router(bundle_upload.router, prefix="/fhir", tags=["FHIR Bundle"])


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": "namaste-icd-service",
        "version": "0.1.0",
        "database": "connected",  # TODO: Add actual DB health check
        "icd11_api": "configured" if settings.icd11_client_id else "not_configured",
        "abha_auth": "configured" if settings.abha_introspection_url else "development_mode"
    }


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "message": "NAMASTE ICD Service",
        "description": "FHIR R4-compliant terminology microservice",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "fhir_codesystem": "/fhir/CodeSystem/namaste",
            "autocomplete": "/autocomplete/terms",
            "translate": "/translate",
            "bundle_upload": "/fhir/Bundle"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
