"""
Authentication and authorization module for NAMASTE ICD Service.

Handles ABHA token verification and user authentication.
"""

import httpx
from typing import Optional, Dict, Any
from app.config import settings


async def verify_abha_token(token: Optional[str]) -> Dict[str, Any]:
    """
    Verify ABHA token and return user information.
    
    Args:
        token: Bearer token from Authorization header
        
    Returns:
        Dictionary with user information or error details
        
    Raises:
        ValueError: If token is invalid or verification fails
    """
    if not token:
        raise ValueError("No token provided")
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    # Development mode: accept "test" token
    if token == "test":
        return {
            "sub": "abha:example:123",
            "actor": "Dr. Demo",
            "name": "Demo User",
            "email": "demo@example.com",
            "roles": ["practitioner"],
            "active": True,
            "source": "development"
        }
    
    # Production mode: verify with ABHA introspection endpoint
    if settings.abha_introspection_url:
        return await _verify_with_abha_introspection(token)
    
    # No introspection URL configured - reject token
    raise ValueError("Token verification not configured")


async def _verify_with_abha_introspection(token: str) -> Dict[str, Any]:
    """
    Verify token with ABHA introspection endpoint.
    
    Args:
        token: Token to verify
        
    Returns:
        Dictionary with user information from introspection
        
    Raises:
        ValueError: If token is invalid or introspection fails
    """
    try:
        # TODO: Implement real ABHA introspection
        # Expected introspection request:
        # POST {ABHA_INTROSPECTION_URL}
        # Headers: {
        #     "Authorization": f"Bearer {token}",
        #     "Content-Type": "application/x-www-form-urlencoded"
        # }
        # Body: "token={token}"
        # 
        # Expected introspection response:
        # {
        #     "active": true,
        #     "sub": "abha:patient:123456789012",
        #     "actor": "Dr. John Doe",
        #     "name": "Dr. John Doe",
        #     "email": "john.doe@hospital.com",
        #     "roles": ["practitioner"],
        #     "scope": "patient/read patient/write",
        #     "exp": 1640995200,
        #     "iat": 1640908800
        # }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.abha_introspection_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"token": token}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get("active", False):
                    raise ValueError("Token is not active")
                
                return {
                    "sub": data.get("sub", ""),
                    "actor": data.get("actor", ""),
                    "name": data.get("name", ""),
                    "email": data.get("email", ""),
                    "roles": data.get("roles", []),
                    "scope": data.get("scope", ""),
                    "exp": data.get("exp"),
                    "iat": data.get("iat"),
                    "active": True,
                    "source": "abha_introspection"
                }
            else:
                raise ValueError(f"Token verification failed: {response.status_code}")
                
    except httpx.HTTPError as e:
        raise ValueError(f"Token verification service unavailable: {e}")
    except Exception as e:
        raise ValueError(f"Token verification error: {e}")


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string or None if not found
    """
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        return authorization[7:]
    
    return None


def has_required_role(user_info: Dict[str, Any], required_roles: list[str]) -> bool:
    """
    Check if user has any of the required roles.
    
    Args:
        user_info: User information from token verification
        required_roles: List of required roles
        
    Returns:
        True if user has at least one required role
    """
    user_roles = user_info.get("roles", [])
    return any(role in user_roles for role in required_roles)


def has_required_scope(user_info: Dict[str, Any], required_scope: str) -> bool:
    """
    Check if user has required scope.
    
    Args:
        user_info: User information from token verification
        required_scope: Required scope string
        
    Returns:
        True if user has the required scope
    """
    user_scope = user_info.get("scope", "")
    return required_scope in user_scope


# Common role constants
ROLES = {
    "PATIENT": "patient",
    "PRACTITIONER": "practitioner",
    "ADMIN": "admin",
    "SYSTEM": "system"
}

# Common scope constants
SCOPES = {
    "READ": "read",
    "WRITE": "write",
    "PATIENT_READ": "patient/read",
    "PATIENT_WRITE": "patient/write",
    "TERMINOLOGY_READ": "terminology/read",
    "TERMINOLOGY_WRITE": "terminology/write"
}
