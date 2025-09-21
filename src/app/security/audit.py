"""
Audit logging module for NAMASTE ICD Service.

Handles audit trail creation and management for compliance and debugging.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.models import AuditLog


async def record_audit(
    db: AsyncSession,
    actor: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None
) -> str:
    """
    Record an audit log entry.
    
    Args:
        db: Database session
        actor: Actor performing the action (user ID, system, etc.)
        action: Action performed (create, read, update, delete, search, translate, etc.)
        resource_type: Type of resource affected (Concept, Mapping, Bundle, etc.)
        resource_id: ID of the resource affected
        detail: Additional details about the action
        
    Returns:
        Audit log ID
    """
    try:
        audit_entry = AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {}
        )
        
        db.add(audit_entry)
        await db.commit()
        
        return str(audit_entry.id)
        
    except Exception as e:
        await db.rollback()
        print(f"Error recording audit log: {e}")
        raise


async def get_audit_logs(
    db: AsyncSession,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100
) -> list[AuditLog]:
    """
    Retrieve audit logs with optional filtering.
    
    Args:
        db: Database session
        actor: Filter by actor
        action: Filter by action
        resource_type: Filter by resource type
        limit: Maximum number of results
        
    Returns:
        List of audit log entries
    """
    query = select(AuditLog)
    
    if actor:
        query = query.where(AuditLog.actor == actor)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_audit_statistics(db: AsyncSession) -> Dict[str, Any]:
    """
    Get audit log statistics.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with audit statistics
    """
    # Count total audit entries
    total_result = await db.execute(select(AuditLog))
    total_entries = len(total_result.scalars().all())
    
    # Count by action
    action_stats = {}
    action_result = await db.execute(select(AuditLog.action))
    for action in action_result.scalars().all():
        action_stats[action] = action_stats.get(action, 0) + 1
    
    # Count by resource type
    resource_stats = {}
    resource_result = await db.execute(select(AuditLog.resource_type))
    for resource_type in resource_result.scalars().all():
        if resource_type:  # Skip None values
            resource_stats[resource_type] = resource_stats.get(resource_type, 0) + 1
    
    # Count by actor
    actor_stats = {}
    actor_result = await db.execute(select(AuditLog.actor))
    for actor in actor_result.scalars().all():
        actor_stats[actor] = actor_stats.get(actor, 0) + 1
    
    return {
        "total_entries": total_entries,
        "action_distribution": action_stats,
        "resource_type_distribution": resource_stats,
        "actor_distribution": actor_stats
    }


# Common action constants
ACTIONS = {
    "CREATE": "create",
    "READ": "read",
    "UPDATE": "update",
    "DELETE": "delete",
    "SEARCH": "search",
    "TRANSLATE": "translate",
    "UPLOAD": "upload",
    "DOWNLOAD": "download",
    "LOGIN": "login",
    "LOGOUT": "logout"
}

# Common resource type constants
RESOURCE_TYPES = {
    "CONCEPT": "Concept",
    "MAPPING": "Mapping",
    "BUNDLE": "Bundle",
    "CODESYSTEM": "CodeSystem",
    "CONCEPTMAP": "ConceptMap",
    "PROVENANCE": "Provenance",
    "AUDIT_LOG": "AuditLog"
}


def create_audit_detail(
    request_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    error_message: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a standardized audit detail dictionary.
    
    Args:
        request_id: Unique request identifier
        user_agent: User agent string
        ip_address: Client IP address
        endpoint: API endpoint accessed
        method: HTTP method used
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        error_message: Error message if any
        **kwargs: Additional details
        
    Returns:
        Dictionary with audit details
    """
    detail = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "error_message": error_message
    }
    
    # Add any additional details
    detail.update(kwargs)
    
    # Remove None values
    return {k: v for k, v in detail.items() if v is not None}
