"""
NAMASTE terminology loader service.

Handles loading NAMASTE concepts from CSV files and provides search functionality.
"""

import pandas as pd
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models import Concept, Mapping
from app.schema import ConceptResponse, SearchResult, MappingResponse


class NamasteLoader:
    """Service for loading and managing NAMASTE terminology concepts."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def load_from_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Load NAMASTE concepts from CSV file into database.
        
        Args:
            csv_path: Path to the CSV file containing NAMASTE concepts
            
        Returns:
            Dictionary with loading statistics
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_columns = ['code', 'display', 'definition']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            loaded_count = 0
            skipped_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Check if concept already exists
                    existing = await self.db.execute(
                        select(Concept).where(
                            and_(
                                Concept.system == "namaste",
                                Concept.code == row['code']
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        skipped_count += 1
                        continue
                    
                    # Create new concept
                    concept = Concept(
                        system="namaste",
                        code=row['code'],
                        display=row['display'],
                        definition=row.get('definition', ''),
                        language=row.get('language', 'en'),
                        source=row.get('source', 'NAMASTE CSV'),
                        version=row.get('version', '1.0'),
                        metadata={
                            'category': row.get('category', ''),
                            'subcategory': row.get('subcategory', ''),
                            'sanskrit_name': row.get('sanskrit_name', ''),
                            'english_name': row.get('english_name', ''),
                            'dosha_relation': row.get('dosha_relation', ''),
                            'body_part': row.get('body_part', ''),
                            'severity': row.get('severity', ''),
                            'treatment_approach': row.get('treatment_approach', '')
                        }
                    )
                    
                    self.db.add(concept)
                    loaded_count += 1
                    
                except Exception as e:
                    print(f"Error loading concept {row.get('code', 'unknown')}: {e}")
                    skipped_count += 1
                    continue
            
            await self.db.commit()
            
            return {
                'loaded': loaded_count,
                'skipped': skipped_count,
                'total_processed': len(df),
                'success': True
            }
            
        except Exception as e:
            await self.db.rollback()
            return {
                'loaded': 0,
                'skipped': 0,
                'total_processed': 0,
                'success': False,
                'error': str(e)
            }
    
    async def search(self, query: str, system: Optional[str] = None, limit: int = 10) -> List[SearchResult]:
        """
        Search for concepts using case-insensitive substring matching.
        
        Args:
            query: Search query string
            system: Terminology system to search (namaste, icd11, or None for all)
            limit: Maximum number of results
            
        Returns:
            List of search results with concepts and mappings
        """
        # Build base query
        base_query = select(Concept)
        
        # Add system filter if specified
        if system:
            base_query = base_query.where(Concept.system == system)
        
        # Add text search conditions
        search_conditions = or_(
            Concept.display.ilike(f"%{query}%"),
            Concept.definition.ilike(f"%{query}%"),
            Concept.code.ilike(f"%{query}%")
        )
        
        # Add metadata search for NAMASTE concepts
        if not system or system == "namaste":
            search_conditions = or_(
                search_conditions,
                Concept.metadata['sanskrit_name'].astext.ilike(f"%{query}%"),
                Concept.metadata['english_name'].astext.ilike(f"%{query}%"),
                Concept.metadata['category'].astext.ilike(f"%{query}%"),
                Concept.metadata['subcategory'].astext.ilike(f"%{query}%")
            )
        
        base_query = base_query.where(search_conditions)
        base_query = base_query.limit(limit)
        
        # Execute query
        result = await self.db.execute(base_query)
        concepts = result.scalars().all()
        
        # Convert to search results with mappings
        search_results = []
        for concept in concepts:
            # Get mappings for this concept
            mappings_query = select(Mapping).where(
                or_(
                    and_(Mapping.source_system == concept.system, Mapping.source_code == concept.code),
                    and_(Mapping.target_system == concept.system, Mapping.target_code == concept.code)
                )
            )
            mappings_result = await self.db.execute(mappings_query)
            mappings = mappings_result.scalars().all()
            
            # Convert to response models
            concept_response = ConceptResponse(
                system=concept.system,
                code=concept.code,
                display=concept.display,
                definition=concept.definition,
                language=concept.language,
                source=concept.source,
                version=concept.version,
                metadata=concept.metadata
            )
            
            mapping_responses = [
                MappingResponse(
                    source_system=mapping.source_system,
                    source_code=mapping.source_code,
                    target_system=mapping.target_system,
                    target_code=mapping.target_code,
                    equivalence=mapping.equivalence,
                    confidence=mapping.confidence,
                    method=mapping.method,
                    evidence=mapping.evidence,
                    curator=mapping.curator
                )
                for mapping in mappings
            ]
            
            # Calculate simple relevance score based on match position
            relevance_score = self._calculate_relevance_score(query, concept)
            
            search_results.append(SearchResult(
                concept=concept_response,
                mappings=mapping_responses,
                relevance_score=relevance_score
            ))
        
        # Sort by relevance score (highest first)
        search_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        
        return search_results
    
    def _calculate_relevance_score(self, query: str, concept: Concept) -> float:
        """
        Calculate relevance score for search results.
        
        Args:
            query: Search query
            concept: Concept to score
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        query_lower = query.lower()
        score = 0.0
        
        # Exact code match gets highest score
        if concept.code.lower() == query_lower:
            score += 1.0
        elif concept.code.lower().startswith(query_lower):
            score += 0.9
        elif query_lower in concept.code.lower():
            score += 0.7
        
        # Display name matching
        if concept.display.lower() == query_lower:
            score += 0.8
        elif concept.display.lower().startswith(query_lower):
            score += 0.6
        elif query_lower in concept.display.lower():
            score += 0.4
        
        # Definition matching
        if concept.definition and query_lower in concept.definition.lower():
            score += 0.3
        
        # Metadata matching for NAMASTE concepts
        if concept.system == "namaste" and concept.metadata:
            metadata = concept.metadata
            for field in ['sanskrit_name', 'english_name', 'category', 'subcategory']:
                if field in metadata and query_lower in str(metadata[field]).lower():
                    score += 0.2
        
        return min(score, 1.0)
    
    async def get_codesystem(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        Get NAMASTE CodeSystem in FHIR format.
        
        Args:
            page: Page number (1-based)
            page_size: Number of concepts per page
            
        Returns:
            FHIR CodeSystem resource
        """
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get concepts
        query = select(Concept).where(Concept.system == "namaste")
        query = query.offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        concepts = result.scalars().all()
        
        # Convert to FHIR format
        fhir_concepts = []
        for concept in concepts:
            fhir_concept = {
                "code": concept.code,
                "display": concept.display,
                "definition": concept.definition or ""
            }
            
            # Add designations for NAMASTE-specific fields
            designations = []
            if concept.metadata:
                if concept.metadata.get('sanskrit_name'):
                    designations.append({
                        "language": "sa",
                        "value": concept.metadata['sanskrit_name']
                    })
                if concept.metadata.get('english_name'):
                    designations.append({
                        "language": "en",
                        "value": concept.metadata['english_name']
                    })
            
            if designations:
                fhir_concept["designation"] = designations
            
            fhir_concepts.append(fhir_concept)
        
        return {
            "resourceType": "CodeSystem",
            "id": "namaste",
            "url": "http://namaste.example.com/fhir/CodeSystem/namaste",
            "version": "1.0",
            "name": "NAMASTE Traditional Medicine Terminology",
            "status": "active",
            "content": "complete",
            "concept": fhir_concepts
        }
    
    async def get_concept_by_code(self, code: str) -> Optional[ConceptResponse]:
        """
        Get a specific concept by its code.
        
        Args:
            code: Concept code to retrieve
            
        Returns:
            Concept response or None if not found
        """
        result = await self.db.execute(
            select(Concept).where(
                and_(Concept.system == "namaste", Concept.code == code)
            )
        )
        concept = result.scalar_one_or_none()
        
        if not concept:
            return None
        
        return ConceptResponse(
            system=concept.system,
            code=concept.code,
            display=concept.display,
            definition=concept.definition,
            language=concept.language,
            source=concept.source,
            version=concept.version,
            metadata=concept.metadata
        )
