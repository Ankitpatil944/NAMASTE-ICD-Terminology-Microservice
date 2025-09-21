"""
Translation API routes for NAMASTE ICD Service.

Handles concept translation between different terminology systems.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.db.session import get_db
from app.services.mapping_service import MappingService
from app.schema import TranslateRequest, TranslateResponse, TranslationCandidate

router = APIRouter()


@router.post(
    "/translate",
    response_model=TranslateResponse,
    summary="Translate Concept",
    description="Translate a concept from one terminology system to another"
)
async def translate_concept(
    request: TranslateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Translate a concept from one terminology system to another.
    
    Args:
        request: Translation request with system and code
        db: Database session
        
    Returns:
        FHIR Parameters resource with translation candidates
        
    Raises:
        HTTPException: If translation fails
    """
    try:
        mapping_service = MappingService(db)
        candidates = await mapping_service.translate(
            system=request.system,
            code=request.code
        )
        
        if not candidates:
            # Return empty parameters if no translations found
            return TranslateResponse(
                resourceType="Parameters",
                parameter=[]
            )
        
        # Convert candidates to FHIR Parameters format
        parameters = []
        
        for candidate in candidates:
            # Add target concept parameter
            parameters.append({
                "name": "target",
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": f"http://terminology.hl7.org/CodeSystem/{candidate.target_system}",
                            "code": candidate.target_code,
                            "display": candidate.target_display or ""
                        }
                    ]
                }
            })
            
            # Add equivalence parameter
            parameters.append({
                "name": "equivalence",
                "valueCode": candidate.equivalence
            })
            
            # Add confidence parameter
            parameters.append({
                "name": "confidence",
                "valueDecimal": candidate.confidence
            })
            
            # Add method parameter if available
            if candidate.method:
                parameters.append({
                    "name": "method",
                    "valueString": candidate.method
                })
            
            # Add evidence parameter if available
            if candidate.evidence:
                parameters.append({
                    "name": "evidence",
                    "valueString": str(candidate.evidence)
                })
        
        return TranslateResponse(
            resourceType="Parameters",
            parameter=parameters
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error translating concept: {str(e)}"
        )


@router.get(
    "/translate/{system}/{code}",
    response_model=TranslateResponse,
    summary="Translate Concept (GET)",
    description="Translate a concept using GET method"
)
async def translate_concept_get(
    system: str,
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Translate a concept using GET method.
    
    Args:
        system: Source terminology system
        code: Source concept code
        db: Database session
        
    Returns:
        FHIR Parameters resource with translation candidates
    """
    request = TranslateRequest(system=system, code=code)
    return await translate_concept(request, db)


@router.get(
    "/mappings",
    summary="List Concept Mappings",
    description="List all concept mappings with optional filtering"
)
async def list_mappings(
    source_system: str = None,
    target_system: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List concept mappings with optional filtering.
    
    Args:
        source_system: Filter by source system
        target_system: Filter by target system
        limit: Maximum number of results
        db: Database session
        
    Returns:
        List of concept mappings
    """
    try:
        mapping_service = MappingService(db)
        mappings = await mapping_service.get_mappings(
            source_system=source_system,
            target_system=target_system,
            limit=limit
        )
        
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(mappings),
            "entry": [
                {
                    "resource": {
                        "resourceType": "ConceptMap",
                        "id": f"{mapping.source_system}-{mapping.source_code}-to-{mapping.target_system}-{mapping.target_code}",
                        "sourceUri": f"http://terminology.hl7.org/CodeSystem/{mapping.source_system}",
                        "targetUri": f"http://terminology.hl7.org/CodeSystem/{mapping.target_system}",
                        "group": [
                            {
                                "source": f"http://terminology.hl7.org/CodeSystem/{mapping.source_system}",
                                "target": f"http://terminology.hl7.org/CodeSystem/{mapping.target_system}",
                                "element": [
                                    {
                                        "code": mapping.source_code,
                                        "target": [
                                            {
                                                "code": mapping.target_code,
                                                "equivalence": mapping.equivalence,
                                                "comment": f"Confidence: {mapping.confidence}"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
                for mapping in mappings
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing mappings: {str(e)}"
        )


@router.get(
    "/mappings/statistics",
    summary="Get Mapping Statistics",
    description="Get statistics about concept mappings"
)
async def get_mapping_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get statistics about concept mappings.
    
    Args:
        db: Database session
        
    Returns:
        Mapping statistics
    """
    try:
        mapping_service = MappingService(db)
        stats = await mapping_service.get_mapping_statistics()
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting mapping statistics: {str(e)}"
        )
