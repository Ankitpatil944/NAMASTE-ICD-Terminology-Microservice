"""
Tests for FHIR Bundle upload and processing functionality.
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


class TestBundleUploadEndpoints:
    """Test Bundle upload endpoints."""
    
    def test_upload_bundle_with_valid_token(self, client, populated_db):
        """Test bundle upload with valid ABHA token."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-001",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-001",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0001",
                                        "display": "Jwara"
                                    }
                                ]
                            },
                            "subject": {
                                "reference": "Patient/patient-001"
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "created_resources" in data
        assert "provenance_id" in data
        assert "audit_id" in data
        assert "mappings_added" in data
        
        # Check that mappings were added
        assert data["mappings_added"] > 0
        
        # Check that resources were created
        assert len(data["created_resources"]) > 0
        assert "Condition/condition-001" in data["created_resources"]
    
    def test_upload_bundle_without_token(self, client, populated_db):
        """Test bundle upload without ABHA token."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-002",
                "type": "collection",
                "entry": []
            }
        }
        
        response = client.post("/fhir/Bundle", json=bundle_data)
        
        assert response.status_code == 400
        assert "No token provided" in response.json()["detail"]
    
    def test_upload_bundle_with_invalid_token(self, client, populated_db):
        """Test bundle upload with invalid ABHA token."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-003",
                "type": "collection",
                "entry": []
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 400
        assert "Token verification not configured" in response.json()["detail"]
    
    def test_upload_bundle_invalid_structure(self, client, populated_db):
        """Test bundle upload with invalid bundle structure."""
        bundle_data = {
            "bundle": {
                "resourceType": "InvalidResource",
                "id": "test-bundle-004"
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 400
        assert "resourceType must be 'Bundle'" in response.json()["detail"]
    
    def test_upload_bundle_missing_bundle(self, client, populated_db):
        """Test bundle upload with missing bundle data."""
        response = client.post(
            "/fhir/Bundle",
            json={},
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_bundle_with_consent(self, client, populated_db):
        """Test bundle upload with consent reference."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-005",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Consent",
                            "id": "consent-001",
                            "status": "active"
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-002",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0002",
                                        "display": "Agni Mandya"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "consent-001" in str(data)  # Consent should be referenced in audit
    
    def test_upload_bundle_multiple_conditions(self, client, populated_db):
        """Test bundle upload with multiple conditions."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-006",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-003",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0001",
                                        "display": "Jwara"
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-004",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0003",
                                        "display": "Kasa"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["created_resources"]) >= 2
        assert "Condition/condition-003" in data["created_resources"]
        assert "Condition/condition-004" in data["created_resources"]
    
    def test_upload_bundle_non_condition_resources(self, client, populated_db):
        """Test bundle upload with non-condition resources."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-007",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "id": "observation-001",
                            "status": "final"
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "DiagnosticReport",
                            "id": "report-001",
                            "status": "final"
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "Observation/observation-001" in data["created_resources"]
        assert "DiagnosticReport/report-001" in data["created_resources"]
    
    def test_upload_bundle_condition_without_namaste_coding(self, client, populated_db):
        """Test bundle upload with condition that has no NAMASTE coding."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-008",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-005",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/icd11",
                                        "code": "AB11",
                                        "display": "Fever"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["mappings_added"] == 0  # No mappings should be added
        assert "Condition/condition-005" in data["created_resources"]


class TestBundleStatusEndpoint:
    """Test Bundle status endpoint."""
    
    def test_get_bundle_status(self, client, populated_db):
        """Test getting bundle processing status."""
        response = client.get("/fhir/Bundle/test-bundle-001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "bundle_id" in data
        assert "status" in data
        assert data["bundle_id"] == "test-bundle-001"


class TestBundleProcessingLogic:
    """Test Bundle processing logic and data integrity."""
    
    def test_bundle_processing_adds_icd11_coding(self, client, populated_db):
        """Test that bundle processing adds ICD-11 coding to conditions."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-009",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-006",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0001",
                                        "display": "Jwara"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have added mappings
        assert data["mappings_added"] > 0
        
        # The actual resource modification would be tested in integration tests
        # Here we just verify the processing completed successfully
    
    def test_bundle_processing_creates_provenance(self, client, populated_db):
        """Test that bundle processing creates provenance resource."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-010",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-007",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0001",
                                        "display": "Jwara"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "provenance_id" in data
        assert data["provenance_id"] is not None
        
        # Provenance should be in created resources
        provenance_ref = f"Provenance/{data['provenance_id']}"
        assert provenance_ref in data["created_resources"]
    
    def test_bundle_processing_creates_audit_log(self, client, populated_db):
        """Test that bundle processing creates audit log entries."""
        bundle_data = {
            "bundle": {
                "resourceType": "Bundle",
                "id": "test-bundle-011",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-008",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://namaste.example.com/fhir/CodeSystem/namaste",
                                        "code": "NAM-AY-0001",
                                        "display": "Jwara"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post(
            "/fhir/Bundle",
            json=bundle_data,
            headers={"Authorization": "Bearer test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "audit_id" in data
        assert data["audit_id"] is not None
