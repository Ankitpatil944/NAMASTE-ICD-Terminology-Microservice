"""
Tests for concept translation functionality.
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


class TestTranslateEndpoints:
    """Test translation endpoints."""
    
    def test_translate_concept_post(self, client, populated_db):
        """Test concept translation using POST method."""
        request_data = {
            "system": "namaste",
            "code": "NAM-AY-0001"
        }
        
        response = client.post("/translate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resourceType"] == "Parameters"
        assert "parameter" in data
        
        # Check parameter structure
        if data["parameter"]:
            # Should have target, equivalence, and confidence parameters
            param_names = [param["name"] for param in data["parameter"]]
            assert "target" in param_names
            assert "equivalence" in param_names
            assert "confidence" in param_names
    
    def test_translate_concept_get(self, client, populated_db):
        """Test concept translation using GET method."""
        response = client.get("/translate/namaste/NAM-AY-0001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resourceType"] == "Parameters"
        assert "parameter" in data
    
    def test_translate_concept_not_found(self, client, populated_db):
        """Test translation of non-existent concept."""
        request_data = {
            "system": "namaste",
            "code": "INVALID-CODE"
        }
        
        response = client.post("/translate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty parameters
        assert data["resourceType"] == "Parameters"
        assert data["parameter"] == []
    
    def test_translate_invalid_system(self, client, populated_db):
        """Test translation with invalid system."""
        request_data = {
            "system": "invalid_system",
            "code": "NAM-AY-0001"
        }
        
        response = client.post("/translate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty parameters
        assert data["resourceType"] == "Parameters"
        assert data["parameter"] == []
    
    def test_translate_missing_fields(self, client, populated_db):
        """Test translation with missing required fields."""
        # Missing code
        request_data = {
            "system": "namaste"
        }
        
        response = client.post("/translate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_translate_empty_system(self, client, populated_db):
        """Test translation with empty system."""
        request_data = {
            "system": "",
            "code": "NAM-AY-0001"
        }
        
        response = client.post("/translate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_translate_empty_code(self, client, populated_db):
        """Test translation with empty code."""
        request_data = {
            "system": "namaste",
            "code": ""
        }
        
        response = client.post("/translate", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestMappingEndpoints:
    """Test mapping-related endpoints."""
    
    def test_list_mappings(self, client, populated_db):
        """Test listing concept mappings."""
        response = client.get("/mappings")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "searchset"
        assert "total" in data
        assert "entry" in data
        
        # Check entry structure
        if data["entry"]:
            entry = data["entry"][0]
            assert "resource" in entry
            resource = entry["resource"]
            assert resource["resourceType"] == "ConceptMap"
            assert "group" in resource
    
    def test_list_mappings_with_source_filter(self, client, populated_db):
        """Test listing mappings with source system filter."""
        response = client.get("/mappings?source_system=namaste")
        
        assert response.status_code == 200
        data = response.json()
        
        # All mappings should have namaste as source
        for entry in data["entry"]:
            group = entry["resource"]["group"][0]
            assert "namaste" in group["source"]
    
    def test_list_mappings_with_target_filter(self, client, populated_db):
        """Test listing mappings with target system filter."""
        response = client.get("/mappings?target_system=icd11")
        
        assert response.status_code == 200
        data = response.json()
        
        # All mappings should have icd11 as target
        for entry in data["entry"]:
            group = entry["resource"]["group"][0]
            assert "icd11" in group["target"]
    
    def test_list_mappings_with_limit(self, client, populated_db):
        """Test listing mappings with limit."""
        response = client.get("/mappings?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entry"]) <= 3
    
    def test_mapping_statistics(self, client, populated_db):
        """Test getting mapping statistics."""
        response = client.get("/mappings/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_mappings" in data
        assert "namaste_source_mappings" in data
        assert "icd11_target_mappings" in data
        assert "equivalence_distribution" in data
        
        # Check that we have some mappings
        assert data["total_mappings"] > 0
        assert data["namaste_source_mappings"] > 0
        assert data["icd11_target_mappings"] > 0


class TestTranslationLogic:
    """Test translation logic and data integrity."""
    
    def test_translation_confidence_scores(self, client, populated_db):
        """Test that translation confidence scores are valid."""
        response = client.get("/translate/namaste/NAM-AY-0001")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find confidence parameter
        confidence_params = [p for p in data["parameter"] if p["name"] == "confidence"]
        
        if confidence_params:
            confidence = confidence_params[0]["valueDecimal"]
            assert 0.0 <= confidence <= 1.0
    
    def test_translation_equivalence_values(self, client, populated_db):
        """Test that translation equivalence values are valid."""
        response = client.get("/translate/namaste/NAM-AY-0001")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find equivalence parameter
        equivalence_params = [p for p in data["parameter"] if p["name"] == "equivalence"]
        
        if equivalence_params:
            equivalence = equivalence_params[0]["valueString"]
            valid_equivalences = [
                "equivalent", "wider", "narrower", "specializes", 
                "generalizes", "relatedto"
            ]
            assert equivalence in valid_equivalences
    
    def test_translation_target_structure(self, client, populated_db):
        """Test that translation target has proper structure."""
        response = client.get("/translate/namaste/NAM-AY-0001")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find target parameter
        target_params = [p for p in data["parameter"] if p["name"] == "target"]
        
        if target_params:
            target = target_params[0]["valueCodeableConcept"]
            assert "coding" in target
            
            coding = target["coding"][0]
            assert "system" in coding
            assert "code" in coding
            assert "display" in coding
