"""
FHIR CodeSystem API routes for NAMASTE ICD Service.

Handles FHIR R4 CodeSystem resource operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.services.namaste_loader import NamasteLoader
from app.schema import FHIRCodeSystem, ErrorResponse

router = APIRouter()


@router.get(
    "/CodeSystem/namaste",
    response_model=FHIRCodeSystem,
    summary="Get NAMASTE CodeSystem",
    description="Retrieve the NAMASTE terminology CodeSystem in FHIR R4 format"
)
async def get_namaste_codesystem(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of concepts per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get NAMASTE CodeSystem in FHIR R4 format.
    
    Args:
        page: Page number (1-based)
        page_size: Number of concepts per page
        db: Database session
        
    Returns:
        FHIR CodeSystem resource
        
    Raises:
        HTTPException: If CodeSystem not found or error occurs
    """
    try:
        loader = NamasteLoader(db)
        codesystem_data = await loader.get_codesystem(page=page, page_size=page_size)
        
        if not codesystem_data:
            raise HTTPException(
                status_code=404,
                detail="NAMASTE CodeSystem not found"
            )
        
        return codesystem_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving NAMASTE CodeSystem: {str(e)}"
        )


@router.get(
    "/CodeSystem/namaste/{code}",
    summary="Get NAMASTE Concept by Code",
    description="Retrieve a specific NAMASTE concept by its code"
)
async def get_namaste_concept(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific NAMASTE concept by its code.
    
    Args:
        code: NAMASTE concept code
        db: Database session
        
    Returns:
        Concept information
        
    Raises:
        HTTPException: If concept not found
    """
    try:
        loader = NamasteLoader(db)
        concept = await loader.get_concept_by_code(code)
        
        if not concept:
            raise HTTPException(
                status_code=404,
                detail=f"NAMASTE concept with code '{code}' not found"
            )
        
        return concept
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving NAMASTE concept: {str(e)}"
        )


@router.get(
    "/CodeSystem",
    summary="List Available CodeSystems",
    description="List all available terminology CodeSystems"
)
async def list_codesystems():
    """
    List all available terminology CodeSystems.
    
    Returns:
        List of available CodeSystems
    """
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "entry": [
            {
                "resource": {
                    "resourceType": "CodeSystem",
                    "id": "namaste",
                    "url": "http://namaste.example.com/fhir/CodeSystem/namaste",
                    "version": "1.0",
                    "name": "NAMASTE Traditional Medicine Terminology",
                    "status": "active",
                    "content": "complete",
                    "description": "Traditional medicine terminology system"
                }
            },
            {
                "resource": {
                    "resourceType": "CodeSystem",
                    "id": "icd11",
                    "url": "https://id.who.int/icd/release/11/2025-01/mms",
                    "version": "2025-01",
                    "name": "ICD-11",
                    "status": "active",
                    "content": "complete",
                    "description": "International Classification of Diseases, 11th Revision"
                }
            }
        ]
    }
