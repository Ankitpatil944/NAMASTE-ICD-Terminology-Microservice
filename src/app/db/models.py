"""
Database models for NAMASTE ICD Service.

SQLAlchemy models for concepts, mappings, and audit logging.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, DateTime, JSON, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class Concept(Base):
    """
    Model for storing terminology concepts from various systems.
    
    Supports NAMASTE, ICD-11, and other terminology systems.
    """
    __tablename__ = "concepts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    system: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    display: Mapped[str] = mapped_column(String(500), nullable=False)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<Concept(system='{self.system}', code='{self.code}', display='{self.display}')>"


class Mapping(Base):
    """
    Model for storing concept mappings between different terminology systems.
    
    Maps concepts from source systems (e.g., NAMASTE) to target systems (e.g., ICD-11).
    """
    __tablename__ = "mappings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_system: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_code: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_system: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_code: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    equivalence: Mapped[str] = mapped_column(
        String(20), 
        default="relatedto", 
        nullable=False,
        comment="FHIR ConceptMapEquivalence: equivalent, wider, narrower, specializes, generalizes, relatedto"
    )
    confidence: Mapped[float] = mapped_column(
        Float, 
        default=0.5, 
        nullable=False,
        comment="Confidence score between 0.0 and 1.0"
    )
    method: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Mapping method used (e.g., 'automatic', 'manual', 'expert_review')"
    )
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True,
        comment="Evidence supporting the mapping"
    )
    curator: Mapped[Optional[str]] = mapped_column(
        String(200), 
        nullable=True,
        comment="Person or system that created/validated the mapping"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<Mapping({self.source_system}:{self.source_code} -> {self.target_system}:{self.target_code})>"


class AuditLog(Base):
    """
    Model for audit logging of all operations.
    
    Tracks who performed what action on which resource for compliance and debugging.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    detail: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(actor='{self.actor}', action='{self.action}', resource='{self.resource_type}:{self.resource_id}')>"
