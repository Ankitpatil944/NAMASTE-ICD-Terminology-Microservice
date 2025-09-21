"""
WHO ICD-11 API client service.

Handles communication with WHO ICD-11 API for terminology search and retrieval.
"""

import httpx
from typing import List, Dict, Any, Optional
from app.config import settings


class ICD11Client:
    """Client for WHO ICD-11 API operations."""
    
    def __init__(self):
        self.base_url = "https://id.who.int/icd/release/11/2025-01/mms"
        self.client_id = settings.icd11_client_id
        self.client_secret = settings.icd11_client_secret
        self._access_token: Optional[str] = None
    
    async def _get_access_token(self) -> Optional[str]:
        """
        Get access token for WHO ICD-11 API.
        
        Returns:
            Access token or None if authentication fails
        """
        # TODO: Implement real OAuth2 flow for WHO ICD-11 API
        # For now, return None to indicate no authentication configured
        if not self.client_id or not self.client_secret:
            return None
        
        # TODO: Replace with actual OAuth2 token endpoint
        # Expected flow:
        # 1. POST to https://id.who.int/icd/token
        # 2. Send client_id, client_secret, grant_type=client_credentials
        # 3. Receive access_token and expires_in
        # 4. Cache token until expiration
        
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search WHO ICD-11 terminology.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of ICD-11 concepts matching the query
        """
        try:
            # Get access token if available
            token = await self._get_access_token()
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            # Build search URL
            search_url = f"{self.base_url}/search"
            params = {
                "q": query,
                "limit": limit,
                "useFlexisearch": "true",
                "flatResults": "true"
            }
            
            # Make HTTP request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    search_url,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse response and extract concepts
                concepts = []
                if "destinationEntities" in data:
                    for entity in data["destinationEntities"][:limit]:
                        concept = self._parse_icd11_entity(entity)
                        if concept:
                            concepts.append(concept)
                
                return concepts
                
        except httpx.HTTPError as e:
            print(f"HTTP error calling WHO ICD-11 API: {e}")
            return []
        except Exception as e:
            print(f"Error searching WHO ICD-11: {e}")
            return []
    
    def _parse_icd11_entity(self, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse WHO ICD-11 API entity response into standardized format.
        
        Args:
            entity: Raw entity from WHO ICD-11 API
            
        Returns:
            Parsed concept dictionary or None if parsing fails
        """
        try:
            # Extract basic information
            code = entity.get("theCode", "")
            title = entity.get("title", "")
            definition = entity.get("definition", "")
            
            if not code or not title:
                return None
            
            # Extract additional metadata
            metadata = {
                "icd11_id": entity.get("id", ""),
                "isLeaf": entity.get("isLeaf", False),
                "parent": entity.get("parent", ""),
                "children": entity.get("children", []),
                "inclusion": entity.get("inclusion", ""),
                "exclusion": entity.get("exclusion", ""),
                "codingNote": entity.get("codingNote", ""),
                "browserUrl": entity.get("browserUrl", ""),
                "foundation_uri": entity.get("foundation_uri", ""),
                "linearization_uri": entity.get("linearization_uri", "")
            }
            
            # Clean up empty values
            metadata = {k: v for k, v in metadata.items() if v}
            
            return {
                "system": "icd11",
                "code": code,
                "display": title,
                "definition": definition,
                "language": "en",
                "source": "WHO ICD-11",
                "version": "2025-01",
                "metadata": metadata
            }
            
        except Exception as e:
            print(f"Error parsing ICD-11 entity: {e}")
            return None
    
    async def get_concept_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific ICD-11 concept by its code.
        
        Args:
            code: ICD-11 code to retrieve
            
        Returns:
            Concept dictionary or None if not found
        """
        try:
            # Get access token if available
            token = await self._get_access_token()
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            # Build concept URL
            concept_url = f"{self.base_url}/concept/{code}"
            
            # Make HTTP request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    concept_url,
                    headers=headers
                )
                response.raise_for_status()
                
                entity = response.json()
                return self._parse_icd11_entity(entity)
                
        except httpx.HTTPError as e:
            print(f"HTTP error getting ICD-11 concept {code}: {e}")
            return None
        except Exception as e:
            print(f"Error getting ICD-11 concept {code}: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check WHO ICD-11 API health and connectivity.
        
        Returns:
            Health status dictionary
        """
        try:
            # Try a simple search to test connectivity
            results = await self.search("fever", limit=1)
            
            return {
                "status": "healthy",
                "api_accessible": True,
                "authentication": "configured" if self.client_id else "not_configured",
                "test_query_results": len(results),
                "base_url": self.base_url
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "authentication": "configured" if self.client_id else "not_configured",
                "error": str(e),
                "base_url": self.base_url
            }
