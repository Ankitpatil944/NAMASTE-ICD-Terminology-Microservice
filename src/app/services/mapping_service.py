"""
Concept mapping service for NAMASTE ICD Service.

Handles mapping between NAMASTE and ICD-11 terminologies with confidence scoring.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models import Mapping, Concept
from app.schema import MappingResponse, TranslationCandidate


class MappingService:
    """Service for managing concept mappings between terminology systems."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def translate(self, system: str, code: str) -> List[TranslationCandidate]:
        """
        Translate a concept from one system to another.
        
        Args:
            system: Source terminology system
            code: Source concept code
            
        Returns:
            List of translation candidates with confidence scores
        """
        # Find all mappings for this concept
        mappings_query = select(Mapping).where(
            and_(Mapping.source_system == system, Mapping.source_code == code)
        )
        
        result = await self.db.execute(mappings_query)
        mappings = result.scalars().all()
        
        # Convert to translation candidates
        candidates = []
        for mapping in mappings:
            # Get target concept details
            target_concept = await self._get_concept(mapping.target_system, mapping.target_code)
            
            candidate = TranslationCandidate(
                target_system=mapping.target_system,
                target_code=mapping.target_code,
                target_display=target_concept.display if target_concept else None,
                equivalence=mapping.equivalence,
                confidence=mapping.confidence,
                method=mapping.method,
                evidence=mapping.evidence
            )
            candidates.append(candidate)
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return candidates
    
    async def add_mapping(
        self,
        source_system: str,
        source_code: str,
        target_system: str,
        target_code: str,
        equivalence: str = "relatedto",
        confidence: float = 0.5,
        method: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        curator: Optional[str] = None
    ) -> bool:
        """
        Add a new concept mapping.
        
        Args:
            source_system: Source terminology system
            source_code: Source concept code
            target_system: Target terminology system
            target_code: Target concept code
            equivalence: FHIR ConceptMapEquivalence value
            confidence: Confidence score (0.0-1.0)
            method: Mapping method used
            evidence: Evidence supporting the mapping
            curator: Person/system that created the mapping
            
        Returns:
            True if mapping was added successfully
        """
        try:
            # Check if mapping already exists
            existing = await self.db.execute(
                select(Mapping).where(
                    and_(
                        Mapping.source_system == source_system,
                        Mapping.source_code == source_code,
                        Mapping.target_system == target_system,
                        Mapping.target_code == target_code
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                return False  # Mapping already exists
            
            # Create new mapping
            mapping = Mapping(
                source_system=source_system,
                source_code=source_code,
                target_system=target_system,
                target_code=target_code,
                equivalence=equivalence,
                confidence=confidence,
                method=method,
                evidence=evidence,
                curator=curator
            )
            
            self.db.add(mapping)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            print(f"Error adding mapping: {e}")
            return False
    
    async def get_mappings(
        self,
        source_system: Optional[str] = None,
        target_system: Optional[str] = None,
        limit: int = 100
    ) -> List[MappingResponse]:
        """
        Get concept mappings with optional filtering.
        
        Args:
            source_system: Filter by source system
            target_system: Filter by target system
            limit: Maximum number of results
            
        Returns:
            List of mapping responses
        """
        query = select(Mapping)
        
        if source_system:
            query = query.where(Mapping.source_system == source_system)
        
        if target_system:
            query = query.where(Mapping.target_system == target_system)
        
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        mappings = result.scalars().all()
        
        return [
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
    
    async def seed_default_mappings(self) -> Dict[str, int]:
        """
        Seed the database with default NAMASTE to ICD-11 mappings.
        
        Returns:
            Dictionary with seeding statistics
        """
        # Default mappings for common NAMASTE concepts
        default_mappings = [
            {
                "source_system": "namaste",
                "source_code": "NAM-AY-0001",
                "target_system": "icd11",
                "target_code": "AB11",
                "equivalence": "relatedto",
                "confidence": 0.8,
                "method": "expert_review",
                "evidence": {
                    "reviewer": "Dr. Ayurveda Expert",
                    "review_date": "2024-01-15",
                    "notes": "Traditional fever concept maps to general fever category"
                },
                "curator": "NAMASTE Team"
            },
            {
                "source_system": "namaste",
                "source_code": "NAM-AY-0002",
                "target_system": "icd11",
                "target_code": "AB12",
                "equivalence": "relatedto",
                "confidence": 0.7,
                "method": "expert_review",
                "evidence": {
                    "reviewer": "Dr. Ayurveda Expert",
                    "review_date": "2024-01-15",
                    "notes": "Digestive disorder maps to digestive system category"
                },
                "curator": "NAMASTE Team"
            },
            {
                "source_system": "namaste",
                "source_code": "NAM-AY-0003",
                "target_system": "icd11",
                "target_code": "AB13",
                "equivalence": "relatedto",
                "confidence": 0.9,
                "method": "expert_review",
                "evidence": {
                    "reviewer": "Dr. Ayurveda Expert",
                    "review_date": "2024-01-15",
                    "notes": "High confidence mapping for respiratory condition"
                },
                "curator": "NAMASTE Team"
            },
            {
                "source_system": "namaste",
                "source_code": "NAM-AY-0004",
                "target_system": "icd11",
                "target_code": "AB14",
                "equivalence": "relatedto",
                "confidence": 0.6,
                "method": "expert_review",
                "evidence": {
                    "reviewer": "Dr. Ayurveda Expert",
                    "review_date": "2024-01-15",
                    "notes": "Skin condition with moderate confidence"
                },
                "curator": "NAMASTE Team"
            },
            {
                "source_system": "namaste",
                "source_code": "NAM-AY-0005",
                "target_system": "icd11",
                "target_code": "AB15",
                "equivalence": "relatedto",
                "confidence": 0.8,
                "method": "expert_review",
                "evidence": {
                    "reviewer": "Dr. Ayurveda Expert",
                    "review_date": "2024-01-15",
                    "notes": "Mental health condition mapping"
                },
                "curator": "NAMASTE Team"
            }
        ]
        
        added_count = 0
        skipped_count = 0
        
        for mapping_data in default_mappings:
            success = await self.add_mapping(**mapping_data)
            if success:
                added_count += 1
            else:
                skipped_count += 1
        
        return {
            "added": added_count,
            "skipped": skipped_count,
            "total": len(default_mappings)
        }
    
    async def _get_concept(self, system: str, code: str) -> Optional[Concept]:
        """
        Get a concept by system and code.
        
        Args:
            system: Terminology system
            code: Concept code
            
        Returns:
            Concept object or None if not found
        """
        result = await self.db.execute(
            select(Concept).where(
                and_(Concept.system == system, Concept.code == code)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_mapping_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about concept mappings.
        
        Returns:
            Dictionary with mapping statistics
        """
        # Count total mappings
        total_result = await self.db.execute(select(Mapping))
        total_mappings = len(total_result.scalars().all())
        
        # Count by source system
        namaste_mappings_result = await self.db.execute(
            select(Mapping).where(Mapping.source_system == "namaste")
        )
        namaste_mappings = len(namaste_mappings_result.scalars().all())
        
        # Count by target system
        icd11_mappings_result = await self.db.execute(
            select(Mapping).where(Mapping.target_system == "icd11")
        )
        icd11_mappings = len(icd11_mappings_result.scalars().all())
        
        # Count by equivalence type
        equivalence_stats = {}
        equivalence_result = await self.db.execute(select(Mapping.equivalence))
        for equivalence in equivalence_result.scalars().all():
            equivalence_stats[equivalence] = equivalence_stats.get(equivalence, 0) + 1
        
        return {
            "total_mappings": total_mappings,
            "namaste_source_mappings": namaste_mappings,
            "icd11_target_mappings": icd11_mappings,
            "equivalence_distribution": equivalence_stats,
            "average_confidence": 0.0  # TODO: Calculate actual average
        }
