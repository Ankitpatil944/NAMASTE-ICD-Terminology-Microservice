"""
Pydantic schemas for request/response validation in NAMASTE ICD Service.

Defines data models for API requests and responses with validation.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


# Request Models
class SearchRequest(BaseModel):
    """Request model for terminology search."""
    q: str = Field(..., description="Search query string", min_length=1, max_length=200)
    system: Optional[str] = Field(None, description="Terminology system to search (namaste, icd11, or all)")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)


class TranslateRequest(BaseModel):
    """Request model for code translation."""
    system: str = Field(..., description="Source terminology system", min_length=1, max_length=100)
    code: str = Field(..., description="Code to translate", min_length=1, max_length=100)


class BundleUploadRequest(BaseModel):
    """Request model for FHIR Bundle upload."""
    bundle: Dict[str, Any] = Field(..., description="FHIR Bundle resource")


# Response Models
class ConceptResponse(BaseModel):
    """Response model for a single concept."""
    system: str
    code: str
    display: str
    definition: Optional[str] = None
    language: str = "en"
    source: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MappingResponse(BaseModel):
    """Response model for a concept mapping."""
    source_system: str
    source_code: str
    target_system: str
    target_code: str
    equivalence: str
    confidence: float
    method: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    curator: Optional[str] = None


class SearchResult(BaseModel):
    """Response model for search results."""
    concept: ConceptResponse
    mappings: List[MappingResponse] = []
    relevance_score: Optional[float] = None


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str
    system: Optional[str] = None
    total_results: int
    results: List[SearchResult]
    execution_time_ms: Optional[float] = None


class TranslationCandidate(BaseModel):
    """Response model for translation candidates."""
    target_system: str
    target_code: str
    target_display: Optional[str] = None
    equivalence: str
    confidence: float
    method: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


class TranslateResponse(BaseModel):
    """Response model for translation endpoint (FHIR Parameters format)."""
    resourceType: str = "Parameters"
    parameter: List[Dict[str, Any]]


class BundleUploadResponse(BaseModel):
    """Response model for Bundle upload."""
    success: bool
    message: str
    created_resources: List[str] = []
    provenance_id: Optional[str] = None
    audit_id: Optional[str] = None
    mappings_added: int = 0
    errors: List[str] = []


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    service: str
    version: str
    database: str
    icd11_api: str
    abha_auth: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# FHIR Models (simplified)
class FHIRCodeSystem(BaseModel):
    """Simplified FHIR CodeSystem resource."""
    resourceType: str = "CodeSystem"
    id: str
    url: str
    version: str
    name: str
    status: str = "active"
    content: str = "complete"
    concept: List[Dict[str, Any]]


class FHIRConceptMap(BaseModel):
    """Simplified FHIR ConceptMap resource."""
    resourceType: str = "ConceptMap"
    id: str
    url: str
    version: str
    name: str
    status: str = "active"
    sourceUri: str
    targetUri: str
    group: List[Dict[str, Any]]


class FHIRProvenance(BaseModel):
    """Simplified FHIR Provenance resource."""
    resourceType: str = "Provenance"
    id: str
    recorded: datetime
    activity: Dict[str, Any]
    agent: List[Dict[str, Any]]
    entity: List[Dict[str, Any]]


# Error Models
class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
