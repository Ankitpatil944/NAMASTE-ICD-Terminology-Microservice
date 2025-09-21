"""
Tests for terminology lookup and search functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.session import get_db, init_db
from app.services.namaste_loader import NamasteLoader
from app.services.mapping_service import MappingService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def db_session():
    """Create test database session."""
    await init_db()
    async with get_db() as session:
        yield session


@pytest.fixture
async def populated_db(db_session: AsyncSession):
    """Populate database with test data."""
    # Load sample concepts
    loader = NamasteLoader(db_session)
    result = await loader.load_from_csv("data/namaste_sample.csv")
    assert result['success'], f"Failed to load concepts: {result.get('error')}"
    
    # Seed mappings
    mapping_service = MappingService(db_session)
    await mapping_service.seed_default_mappings()
    
    return db_session


class TestSearchEndpoints:
    """Test search and lookup endpoints."""
    
    def test_search_terms_basic(self, client, populated_db):
        """Test basic terminology search."""
        response = client.get("/autocomplete/terms?q=fever")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "total_results" in data
        assert "results" in data
        assert data["query"] == "fever"
        assert data["total_results"] > 0
        
        # Check result structure
        if data["results"]:
            result = data["results"][0]
            assert "concept" in result
            assert "mappings" in result
            assert "relevance_score" in result
            
            concept = result["concept"]
            assert "system" in concept
            assert "code" in concept
            assert "display" in concept
    
    def test_search_terms_with_system_filter(self, client, populated_db):
        """Test search with system filter."""
        response = client.get("/autocomplete/terms?q=fever&system=namaste")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["system"] == "namaste"
        
        # All results should be from namaste system
        for result in data["results"]:
            assert result["concept"]["system"] == "namaste"
    
    def test_search_terms_with_limit(self, client, populated_db):
        """Test search with limit parameter."""
        response = client.get("/autocomplete/terms?q=fever&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) <= 5
    
    def test_search_terms_empty_query(self, client, populated_db):
        """Test search with empty query."""
        response = client.get("/autocomplete/terms?q=")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_terms_long_query(self, client, populated_db):
        """Test search with query too long."""
        long_query = "a" * 201  # Exceeds max length
        response = client.get(f"/autocomplete/terms?q={long_query}")
        
        assert response.status_code == 422  # Validation error
    
    def test_autocomplete_endpoint(self, client, populated_db):
        """Test autocomplete endpoint."""
        response = client.get("/autocomplete/autocomplete?q=fever&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "total_results" in data
        assert "results" in data
        assert len(data["results"]) <= 3
    
    def test_suggestions_endpoint(self, client, populated_db):
        """Test search suggestions endpoint."""
        response = client.get("/autocomplete/suggestions?q=fev")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "suggestions" in data
        assert data["query"] == "fev"
        
        # Check suggestion structure
        if data["suggestions"]:
            suggestion = data["suggestions"][0]
            assert "text" in suggestion
            assert "value" in suggestion
            assert "system" in suggestion
            assert "type" in suggestion


class TestCodeSystemEndpoints:
    """Test CodeSystem endpoints."""
    
    def test_get_namaste_codesystem(self, client, populated_db):
        """Test getting NAMASTE CodeSystem."""
        response = client.get("/fhir/CodeSystem/namaste")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resourceType"] == "CodeSystem"
        assert data["id"] == "namaste"
        assert data["name"] == "NAMASTE Traditional Medicine Terminology"
        assert "concept" in data
        
        # Check concept structure
        if data["concept"]:
            concept = data["concept"][0]
            assert "code" in concept
            assert "display" in concept
            assert "definition" in concept
    
    def test_get_namaste_codesystem_with_pagination(self, client, populated_db):
        """Test CodeSystem pagination."""
        response = client.get("/fhir/CodeSystem/namaste?page=1&page_size=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["concept"]) <= 5
    
    def test_get_namaste_concept_by_code(self, client, populated_db):
        """Test getting specific NAMASTE concept."""
        response = client.get("/fhir/CodeSystem/namaste/NAM-AY-0001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["system"] == "namaste"
        assert data["code"] == "NAM-AY-0001"
        assert data["display"] == "Jwara"
    
    def test_get_namaste_concept_not_found(self, client, populated_db):
        """Test getting non-existent concept."""
        response = client.get("/fhir/CodeSystem/namaste/INVALID-CODE")
        
        assert response.status_code == 404
    
    def test_list_codesystems(self, client, populated_db):
        """Test listing available CodeSystems."""
        response = client.get("/fhir/CodeSystem")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "searchset"
        assert "entry" in data
        
        # Check that NAMASTE and ICD-11 are listed
        systems = [entry["resource"]["id"] for entry in data["entry"]]
        assert "namaste" in systems
        assert "icd11" in systems


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "namaste-icd-service"
        assert "version" in data
        assert "database" in data
        assert "icd11_api" in data
        assert "abha_auth" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "NAMASTE ICD Service"
        assert "endpoints" in data
        assert "docs" in data
        assert "health" in data
