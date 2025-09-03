"""
System Management Tools for DPoD MCP Server

Provides system operations including authentication, token validation, and server information.
"""

import logging
from typing import Dict, Any
from fastmcp import Context
from pydantic import Field
from datetime import datetime


async def manage_scopes(
    ctx: Context,
    action: str = Field(description="Operation to perform: check_auth, validate_token, get_scope_permissions")
) -> Dict[str, Any]:
    """Scope and permission management operations.
    
    Actions:
    - check_auth: Check current OAuth authentication status and token validity
    - validate_token: Validate OAuth token permissions and scopes
    - get_scope_permissions: Get detailed breakdown of allowed tools and actions for current scope
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    from src.dpod_mcp_server.core.auth import DPoDAuth
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.scopes")
    tool_logger.info(f"Starting scope operation: {action}")
    
    try:
        await ctx.report_progress(0, 100, f"Starting scope operation: {action}")
        
        # Define read-only vs write actions (all scope actions are read-only)
        read_actions = {"check_auth", "validate_token", "get_scope_permissions"}
        write_actions = set()  # No write actions in scope management
        
        # Check read-only mode for write actions (none exist, but keeping pattern consistent)
        if action in write_actions and config.read_only_mode:
            return {
                "success": False,
                "error": f"Server is in read-only mode. Action '{action}' is not allowed.",
                "action": action,
                "read_only_mode": True
            }
        
        if action == "check_auth":
            result = await _check_authentication(auth)
        elif action == "validate_token":
            result = await _validate_token(auth)
        elif action == "get_scope_permissions":
            result = await _get_scope_permissions(scope_manager)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        await ctx.report_progress(100, 100, f"Completed scope operation: {action}")
        tool_logger.info(f"Completed scope operation: {action}")
        return result
        
    except Exception as e:
        tool_logger.error(f"Error in scope operation {action}: {e}")
        raise


async def _get_scope_permissions(scope_manager) -> Dict[str, Any]:
    """Get detailed breakdown of allowed tools and actions for current scope."""
    try:
        # Get current scope information
        scope_info = scope_manager.get_scope_summary()
        
        if not scope_info.get("success"):
            return {
                "success": False,
                "error": "Failed to get scope information",
                "details": scope_info.get("error", "Unknown error")
            }
        
        # Get detailed tool permissions
        tool_permissions = {}
        total_tools = 0
        accessible_tools = 0
        restricted_tools = 0
        
        for tool_name, tool_info in scope_info.get("tool_permissions", {}).items():
            total_tools += 1
            allowed_actions = tool_info.get("allowed_actions", [])
            
            if allowed_actions:
                accessible_tools += 1
                tool_permissions[tool_name] = allowed_actions
            else:
                restricted_tools += 1
                tool_permissions[tool_name] = []
        
        return {
            "success": True,
            "current_scope": scope_info.get("primary_scope", "unknown"),
            "allowed_tools": tool_permissions,
            "summary": {
                "total_tools": total_tools,
                "accessible_tools": accessible_tools,
                "restricted_tools": restricted_tools,
                "access_percentage": round((accessible_tools / total_tools * 100), 1) if total_tools > 0 else 0
            },
            "message": f"Scope permissions retrieved for {scope_info.get('primary_scope', 'unknown')}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get scope permissions: {str(e)}"
        }


async def _check_authentication(auth) -> Dict[str, Any]:
    """Check current OAuth authentication status and token validity.
    
    Verifies the current OAuth 2.0 client credentials authentication status with the DPoD (Data Protection on Demand) platform.
    
    Returns:
        Authentication status including:
        - status: Current authentication status (not_configured, authenticated, error)
        - message: Detailed status message
        - timestamp: When the check was performed
        - base_url: Current DPoD API base URL
        - auth_url: OAuth token endpoint URL
        - current_scopes: List of OAuth scopes currently granted
        - available_scopes: All available DPoD OAuth scopes
        - scope_permissions: Detailed permission breakdown
        
    Note: This tool helps verify that your client credentials are working and what permissions you have access to.
    """
    try:
        # Check if credentials are configured
        if not auth.config.client_id or not auth.config.client_secret:
            return {
                "status": "not_configured",
                "message": "DPOD_CLIENT_ID and DPOD_CLIENT_SECRET not set",
                "timestamp": datetime.now().isoformat(),
                "required_scopes": []
            }
        
        # Try to get a token
        token_info = await auth.get_token()
        
        if token_info.get("success"):
            # Get current scopes from the token
            current_scopes = token_info.get("scopes", [])
            
            # Update the config with current scopes for other tools to use
            auth.config.oauth_scopes = current_scopes
            
            return {
                "status": "authenticated",
                "message": "Successfully authenticated with DPoD",
                "timestamp": datetime.now().isoformat(),
                "base_url": auth.config.dpod_base_url,
                "auth_url": auth.config.dpod_auth_url,
                "current_scopes": current_scopes,
                "available_scopes": current_scopes,
                "scope_permissions": {
                    "can_manage_tenants": any("dpod.tenant.api_spadmin" in scope for scope in current_scopes),
                    "can_manage_services": any("dpod.tenant.api_" in scope for scope in current_scopes),
                    "can_access_services": any("dpod.tenant.api_appowner" in scope or "dpod.tenant.api_service" in scope for scope in current_scopes)
                }
            }
        else:
            return {
                "status": "error",
                "message": token_info.get("error", "Authentication failed"),
                "timestamp": datetime.now().isoformat(),
                "required_scopes": []
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "required_scopes": []
        }


async def _validate_token(auth) -> Dict[str, Any]:
    """Comprehensive JWT token validation and introspection.
    
    Provides detailed analysis of the current OAuth access token including:
    - JWT payload validation
    - Scope verification
    - Expiration analysis
    - Token introspection
    
    Returns:
        Comprehensive token validation results including:
        - token_valid: Whether token is currently valid
        - expires_at: Token expiration timestamp
        - scopes: Available OAuth scopes
        - client_id: OAuth client identifier
        - issuer: Token issuer
        - audience: Token audience
        - time_until_expiry: Seconds until token expires
        - cached: Whether token is cached in memory
    """
    try:
        # First ensure we have a valid token
        await auth.ensure_valid_token()
        
        # Get detailed token introspection
        introspection_result = await auth.introspect_token()
        
        if not introspection_result.get("success"):
            return {
                "success": False,
                "error": introspection_result.get("error", "Token introspection failed"),
                "timestamp": datetime.now().isoformat()
            }
        
        token_data = introspection_result.get("token_data", {})
        
        # Calculate time until expiry
        expires_at = token_data.get("exp")
        time_until_expiry = None
        if expires_at:
            now = datetime.now().timestamp()
            time_until_expiry = int(expires_at - now)
        
        return {
            "success": True,
            "token_valid": token_data.get("active", False),
            "expires_at": expires_at,
            "scopes": token_data.get("scope", "").split() if token_data.get("scope") else [],
            "client_id": token_data.get("client_id"),
            "issuer": token_data.get("iss"),
            "audience": token_data.get("aud"),
            "time_until_expiry": time_until_expiry,
            "cached": token_data.get("cached", False),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 