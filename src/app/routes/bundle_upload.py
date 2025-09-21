"""
FHIR Bundle upload and processing API routes for NAMASTE ICD Service.

Handles FHIR Bundle ingestion with automatic concept mapping and audit logging.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.mapping_service import MappingService
from app.security.auth import verify_abha_token, extract_token_from_header
from app.security.audit import record_audit, ACTIONS, RESOURCE_TYPES, create_audit_detail
from app.schema import BundleUploadRequest, BundleUploadResponse

router = APIRouter()


@router.post(
    "/Bundle",
    response_model=BundleUploadResponse,
    summary="Upload FHIR Bundle",
    description="Upload and process a FHIR Bundle with automatic concept mapping"
)
async def upload_bundle(
    request: BundleUploadRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process a FHIR Bundle with automatic concept mapping.
    
    Args:
        request: Bundle upload request
        authorization: Authorization header with ABHA token
        db: Database session
        
    Returns:
        Bundle upload response with processing results
        
    Raises:
        HTTPException: If bundle processing fails
    """
    start_time = datetime.utcnow()
    bundle_id = str(uuid.uuid4())
    created_resources = []
    errors = []
    mappings_added = 0
    
    try:
        # Verify ABHA token
        token = extract_token_from_header(authorization)
        user_info = await verify_abha_token(token)
        actor = user_info.get("actor", "unknown")
        
        # Validate bundle structure
        bundle = request.bundle
        if bundle.get("resourceType") != "Bundle":
            raise HTTPException(
                status_code=400,
                detail="Invalid bundle: resourceType must be 'Bundle'"
            )
        
        # Check for consent reference in bundle entries
        consent_ref = None
        for entry in bundle.get("entry", []):
            if entry.get("resource", {}).get("resourceType") == "Consent":
                consent_ref = entry.get("resource", {}).get("id")
                break
        
        # Process bundle entries
        mapping_service = MappingService(db)
        
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id", str(uuid.uuid4()))
            
            # Process Condition resources
            if resource_type == "Condition":
                try:
                    # Extract NAMASTE coding from Condition
                    namaste_coding = None
                    for coding in resource.get("code", {}).get("coding", []):
                        if coding.get("system") == "http://namaste.example.com/fhir/CodeSystem/namaste":
                            namaste_coding = coding
                            break
                    
                    if namaste_coding:
                        # Get translation to ICD-11
                        translations = await mapping_service.translate(
                            system="namaste",
                            code=namaste_coding.get("code")
                        )
                        
                        if translations:
                            # Add ICD-11 coding to Condition
                            icd11_coding = {
                                "system": "http://terminology.hl7.org/CodeSystem/icd11",
                                "code": translations[0].target_code,
                                "display": translations[0].target_display or "",
                                "userSelected": False
                            }
                            
                            # Add to existing coding array
                            if "code" not in resource:
                                resource["code"] = {"coding": []}
                            if "coding" not in resource["code"]:
                                resource["code"]["coding"] = []
                            
                            resource["code"]["coding"].append(icd11_coding)
                            mappings_added += 1
                    
                    # Add provenance information
                    resource["meta"] = resource.get("meta", {})
                    resource["meta"]["extension"] = resource["meta"].get("extension", [])
                    resource["meta"]["extension"].append({
                        "url": "http://namaste.example.com/fhir/StructureDefinition/bundle-processing",
                        "valueString": f"Processed by NAMASTE ICD Service at {datetime.utcnow().isoformat()}"
                    })
                    
                    created_resources.append(f"Condition/{resource_id}")
                    
                except Exception as e:
                    errors.append(f"Error processing Condition {resource_id}: {str(e)}")
                    continue
            
            # Process other resource types
            elif resource_type in ["Observation", "DiagnosticReport", "Procedure"]:
                created_resources.append(f"{resource_type}/{resource_id}")
            
            # Record audit for each resource
            try:
                await record_audit(
                    db=db,
                    actor=actor,
                    action=ACTIONS["CREATE"],
                    resource_type=resource_type,
                    resource_id=resource_id,
                    detail=create_audit_detail(
                        bundle_id=bundle_id,
                        consent_ref=consent_ref,
                        resource_type=resource_type,
                        mappings_added=mappings_added
                    )
                )
            except Exception as e:
                errors.append(f"Error recording audit for {resource_type}/{resource_id}: {str(e)}")
        
        # Create provenance resource
        provenance_id = str(uuid.uuid4())
        provenance = {
            "resourceType": "Provenance",
            "id": provenance_id,
            "recorded": datetime.utcnow().isoformat(),
            "activity": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/provenance-activity-type",
                        "code": "create",
                        "display": "Create"
                    }
                ]
            },
            "agent": [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/provenance-agent-type",
                                "code": "author",
                                "display": "Author"
                            }
                        ]
                    },
                    "who": {
                        "display": actor
                    }
                }
            ],
            "entity": [
                {
                    "role": "source",
                    "what": {
                        "reference": f"Bundle/{bundle_id}"
                    }
                }
            ]
        }
        
        created_resources.append(f"Provenance/{provenance_id}")
        
        # Record bundle processing audit
        audit_id = await record_audit(
            db=db,
            actor=actor,
            action=ACTIONS["UPLOAD"],
            resource_type=RESOURCE_TYPES["BUNDLE"],
            resource_id=bundle_id,
            detail=create_audit_detail(
                bundle_id=bundle_id,
                consent_ref=consent_ref,
                resources_processed=len(created_resources),
                mappings_added=mappings_added,
                processing_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
        )
        
        return BundleUploadResponse(
            success=True,
            message="Bundle processed successfully",
            created_resources=created_resources,
            provenance_id=provenance_id,
            audit_id=audit_id,
            mappings_added=mappings_added,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Record error audit
        try:
            await record_audit(
                db=db,
                actor=actor if 'actor' in locals() else "unknown",
                action=ACTIONS["UPLOAD"],
                resource_type=RESOURCE_TYPES["BUNDLE"],
                resource_id=bundle_id,
                detail=create_audit_detail(
                    bundle_id=bundle_id,
                    error_message=str(e),
                    processing_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            )
        except:
            pass  # Don't fail on audit error
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing bundle: {str(e)}"
        )


@router.get(
    "/Bundle/{bundle_id}",
    summary="Get Bundle Processing Status",
    description="Get the processing status of a previously uploaded bundle"
)
async def get_bundle_status(
    bundle_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the processing status of a previously uploaded bundle.
    
    Args:
        bundle_id: Bundle identifier
        db: Database session
        
    Returns:
        Bundle processing status
    """
    try:
        # This would typically query a bundle processing status table
        # For now, return a placeholder response
        return {
            "bundle_id": bundle_id,
            "status": "processed",
            "message": "Bundle processing status retrieval not yet implemented"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting bundle status: {str(e)}"
        )
