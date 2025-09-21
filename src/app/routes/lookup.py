"""
Terminology lookup and search API routes for NAMASTE ICD Service.

Handles terminology search and autocomplete functionality.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.services.namaste_loader import NamasteLoader
from app.services.icd11_client import ICD11Client
from app.schema import SearchRequest, SearchResponse, SearchResult

router = APIRouter()


@router.get(
    "/terms",
    response_model=SearchResponse,
    summary="Search Terminology",
    description="Search for terminology concepts across NAMASTE and ICD-11 systems"
)
async def search_terms(
    q: str = Query(..., description="Search query string", min_length=1, max_length=200),
    system: Optional[str] = Query(None, description="Terminology system to search (namaste, icd11, or all)"),
    limit: int = Query(10, description="Maximum number of results", ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for terminology concepts across multiple systems.
    
    Args:
        q: Search query string
        system: Terminology system to search (namaste, icd11, or all)
        limit: Maximum number of results
        db: Database session
        
    Returns:
        Search results with concepts and mappings
        
    Raises:
        HTTPException: If search fails
    """
    start_time = time.time()
    
    try:
        all_results = []
        
        # Search NAMASTE concepts
        if not system or system in ["namaste", "all"]:
            namaste_loader = NamasteLoader(db)
            namaste_results = await namaste_loader.search(
                query=q,
                system="namaste",
                limit=limit
            )
            all_results.extend(namaste_results)
        
        # Search ICD-11 concepts
        if not system or system in ["icd11", "all"]:
            icd11_client = ICD11Client()
            icd11_results = await icd11_client.search(q, limit=limit)
            
            # Convert ICD-11 results to SearchResult format
            for concept_data in icd11_results:
                search_result = SearchResult(
                    concept=concept_data,
                    mappings=[],  # ICD-11 results don't include mappings
                    relevance_score=0.5  # Default relevance for ICD-11
                )
                all_results.append(search_result)
        
        # Sort all results by relevance score
        all_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        
        # Limit results
        all_results = all_results[:limit]
        
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return SearchResponse(
            query=q,
            system=system,
            total_results=len(all_results),
            results=all_results,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching terminology: {str(e)}"
        )


@router.get(
    "/autocomplete",
    response_model=SearchResponse,
    summary="Autocomplete Terminology",
    description="Get autocomplete suggestions for terminology concepts"
)
async def autocomplete_terms(
    q: str = Query(..., description="Search query string", min_length=1, max_length=200),
    system: Optional[str] = Query(None, description="Terminology system to search"),
    limit: int = Query(5, description="Maximum number of suggestions", ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Get autocomplete suggestions for terminology concepts.
    
    Args:
        q: Search query string
        system: Terminology system to search
        limit: Maximum number of suggestions
        db: Database session
        
    Returns:
        Autocomplete suggestions
        
    Raises:
        HTTPException: If autocomplete fails
    """
    try:
        # Use the main search function with a smaller limit for autocomplete
        search_response = await search_terms(
            q=q,
            system=system,
            limit=limit,
            db=db
        )
        
        return search_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting autocomplete suggestions: {str(e)}"
        )


@router.get(
    "/suggestions",
    summary="Get Search Suggestions",
    description="Get search suggestions based on partial input"
)
async def get_search_suggestions(
    q: str = Query(..., description="Partial search query", min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get search suggestions based on partial input.
    
    Args:
        q: Partial search query
        db: Database session
        
    Returns:
        List of search suggestions
    """
    try:
        # Get suggestions from NAMASTE concepts
        namaste_loader = NamasteLoader(db)
        namaste_results = await namaste_loader.search(
            query=q,
            system="namaste",
            limit=5
        )
        
        suggestions = []
        for result in namaste_results:
            suggestions.append({
                "text": result.concept.display,
                "value": result.concept.code,
                "system": result.concept.system,
                "type": "concept"
            })
        
        # Add common search terms
        common_terms = [
            "fever", "headache", "cough", "pain", "digestion",
            "respiratory", "skin", "mental", "sleep", "energy"
        ]
        
        for term in common_terms:
            if q.lower() in term.lower():
                suggestions.append({
                    "text": term,
                    "value": term,
                    "system": "common",
                    "type": "keyword"
                })
        
        return {
            "query": q,
            "suggestions": suggestions[:10]  # Limit to 10 suggestions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting search suggestions: {str(e)}"
        )
