#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Scope Management Module

Handles scope detection, validation, and tool filtering based on API scopes.
"""

import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from .auth import DPoDAuth
from .config import DPoDConfig

class ScopeManager:
    """Manages DPoD API scopes and tool access control."""
    
    def __init__(self, config: DPoDConfig, auth: DPoDAuth):
        self.config = config
        self.auth = auth
        self.logger = logging.getLogger(__name__)
        
        # Define scope hierarchy (highest to lowest privilege)
        self.scope_hierarchy = [
            "dpod.tenant.api_spadmin",    # Full API access
            "dpod.tenant.api_appowner",   # Limited API access
            "dpod.tenant.api_service"     # Service-specific API access
        ]
        
        # Define tool-to-scope mappings based on DPoD_API_Security_Scopes.md
        self.tool_scope_mappings = {
            # Tenant Management
            "manage_tenants": {
                "dpod.tenant.api_spadmin": ["list", "get", "create", "update", "delete", "get_usage", "get_settings", "update_settings", "get_hierarchy", "get_admin", "get_children", "get_hostname", "get_quotas", "get_services_summary", "get_services_summary_file", "get_logo", "set_logo"],
                "dpod.tenant.api_appowner": ["get_quotas"],
                "dpod.tenant.api_service": []  # No access
            },
            
            # Service Management
            "manage_services": {
                "dpod.tenant.api_spadmin": ["list_services", "get_service_instance", "create_service_instance", "update_service_instance", "delete_service_instance", "bind_client", "list_service_clients", "get_service_client", "delete_service_client", "get_creation_example"],
                "dpod.tenant.api_appowner": ["list_services", "get_service_instance", "create_service_instance", "update_service_instance", "delete_service_instance", "bind_client", "list_service_clients", "get_service_client", "delete_service_client", "get_creation_example"],
                "dpod.tenant.api_service": ["get_service_instance", "bind_client", "list_service_clients", "get_service_client"]  # Limited to specific service
            },
            
            # Users
            "manage_users": {
                "dpod.tenant.api_spadmin": ["list", "get", "create", "update", "delete", "get_profile", "change_password", "reset_mfa_token"],
                "dpod.tenant.api_appowner": [],  # No access - restricted to spadmin only
                "dpod.tenant.api_service": []  # No access
            },
            
            # Audit Logs
            "manage_audit_logs": {
                "dpod.tenant.api_spadmin": ["generate_export", "get_export", "get_result", "get_status", "get_logs"],
                "dpod.tenant.api_appowner": ["generate_export", "get_export", "get_result", "get_status", "get_logs"],
                "dpod.tenant.api_service": ["get_logs"]  # Limited access
            },
            
            # Reports
            "manage_reports": {
                "dpod.tenant.api_spadmin": ["get_service_summary", "get_usage_billing"],
                "dpod.tenant.api_appowner": ["get_service_summary", "get_usage_billing"],
                "dpod.tenant.api_service": ["get_service_summary"]  # Limited access
            },
            
            # Tiles (Service Catalog)
            "manage_tiles": {
                "dpod.tenant.api_spadmin": ["list_tiles", "update_tile"],  # Can list and update tiles
                "dpod.tenant.api_appowner": ["list_tiles", "get_tile_details", "get_tile_plans"],  # Can list, get details, and get plans
                "dpod.tenant.api_service": []  # No access to tiles
            },
            
            # Products
            "manage_products": {
                "dpod.tenant.api_spadmin": ["get_product_plans"],
                "dpod.tenant.api_appowner": ["get_product_plans"],
                "dpod.tenant.api_service": ["get_product_plans"]
            },
            
            # Service Agreements
            "manage_service_agreements": {
                "dpod.tenant.api_spadmin": ["get_agreement", "approve_agreement", "reject_agreement"],
                "dpod.tenant.api_appowner": ["get_agreement"],
                "dpod.tenant.api_service": ["get_agreement"]  # Based on Swagger: both api_appowner and api_service can access
            },
            
            # Subscriptions
            "manage_subscriptions": {
                "dpod.tenant.api_spadmin": ["list_subscriptions"],
                "dpod.tenant.api_appowner": ["list_subscriptions"],
                "dpod.tenant.api_service": []  # No access
            },
            
            # Subscriber Groups
            "manage_subscriber_groups": {
                "dpod.tenant.api_spadmin": [],  # No access to subscriber groups - restricted to appowner only
                "dpod.tenant.api_appowner": ["get"],  # Only get details action
                "dpod.tenant.api_service": []  # No access
            },
            
            # Credentials - Based on Swagger: /credentials/clients endpoints
            "manage_credentials": {
                "dpod.tenant.api_spadmin": ["list", "get", "create", "update", "delete", "reset_secret"],
                "dpod.tenant.api_appowner": [],  # No access to credentials - restricted to spadmin only
                "dpod.tenant.api_service": []  # No access to credentials
            },
            
            # System (always accessible)
            "manage_scopes": {
                "dpod.tenant.api_spadmin": ["check_auth", "validate_token", "get_scope_permissions"],
                "dpod.tenant.api_appowner": ["check_auth", "validate_token", "get_scope_permissions"],
                "dpod.tenant.api_service": ["check_auth", "validate_token", "get_scope_permissions"]
            },
            
            # DPoD Availability (always accessible)
            "check_dpod_availability": {
                "dpod.tenant.api_spadmin": ["check_dpod_status"],
                "dpod.tenant.api_appowner": ["check_dpod_status"],
                "dpod.tenant.api_service": ["check_dpod_status"]
            }
        }
        
        # Current detected scopes
        self.detected_scopes: List[str] = []
        self.api_scopes: List[str] = [] # New attribute to store only API scopes
        self.primary_scope: Optional[str] = None
        self.allowed_tools: Set[str] = set()
        self.tool_action_permissions: Dict[str, Dict[str, List[str]]] = {}
        
    async def detect_scopes(self) -> Dict[str, Any]:
        """Detect API scopes from the current authentication token.
        
        Returns:
            Dict with scope detection results
        """
        try:
            self.logger.info("Detecting API scopes from authentication token...")
            
            # Get token validation info
            token_info = await self.auth.validate_token_permissions()
            
            if not token_info.get("valid"):
                error_msg = f"Token validation failed: {token_info.get('error', 'Unknown error')}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "detected_scopes": [],
                    "primary_scope": None
                }
            
            # Extract scopes from token
            all_scopes = token_info.get("scopes", [])
            self.logger.info(f"All token scopes: {all_scopes}")
            
            # Filter for API-related scopes only (those containing 'api_')
            api_scopes = [scope for scope in all_scopes if "api_" in scope]
            self.logger.info(f"Filtered API scopes: {api_scopes}")
            self.logger.info(f"API scopes count: {len(api_scopes)}")
            
            if not api_scopes:
                error_msg = "No API scopes found in token. Server cannot start without API access."
                self.logger.error(error_msg)
                self.logger.error(f"Available scopes: {all_scopes}")
                self.logger.error(f"API scope filter result: {api_scopes}")
                return {
                    "success": False,
                    "error": error_msg,
                    "detected_scopes": [],
                    "primary_scope": None
                }
            
            # Store detected scopes (both all scopes and API scopes)
            self.detected_scopes = all_scopes
            self.api_scopes = api_scopes
            self.logger.info(f"Detected all scopes: {all_scopes}")
            self.logger.info(f"Detected API scopes: {api_scopes}")
            
            # Determine primary scope (highest privilege) from API scopes only
            self.primary_scope = self._determine_primary_scope(api_scopes)
            self.logger.info(f"Primary API scope: {self.primary_scope}")
            
            # Build tool permissions based on API scopes only
            self._build_tool_permissions()
            
            return {
                "success": True,
                "detected_scopes": all_scopes,
                "api_scopes": api_scopes,
                "primary_scope": self.primary_scope,
                "allowed_tools": list(self.allowed_tools),
                "tool_count": len(self.allowed_tools)
            }
            
        except Exception as e:
            error_msg = f"Scope detection failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "detected_scopes": [],
                "primary_scope": None
            }
    
    def _determine_primary_scope(self, api_scopes: List[str]) -> str:
        """Determine the primary scope based on hierarchy."""
        for scope in self.scope_hierarchy:
            if scope in api_scopes:
                return scope
        
        # If no match found, return the first API scope
        return api_scopes[0] if api_scopes else "unknown"
    
    def _build_tool_permissions(self) -> None:
        """Build tool permissions based on detected scopes."""
        self.allowed_tools.clear()
        self.tool_action_permissions.clear()
        
        for tool_name, scope_actions in self.tool_scope_mappings.items():
            tool_allowed = False
            tool_permissions = {}
            
            # Check if tool is accessible with any of the detected scopes
            for scope in self.api_scopes: # Iterate over API scopes only
                if scope in scope_actions:
                    actions = scope_actions[scope]
                    # Tool is accessible if scope exists, regardless of whether actions list is empty
                    tool_allowed = True
                    tool_permissions[scope] = actions
            
            if tool_allowed:
                self.allowed_tools.add(tool_name)
                self.tool_action_permissions[tool_name] = tool_permissions
        
        self.logger.info(f"Built permissions for {len(self.allowed_tools)} tools")
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for the current scope."""
        return tool_name in self.allowed_tools
    
    def get_allowed_actions(self, tool_name: str, scope: Optional[str] = None) -> List[str]:
        """Get allowed actions for a tool and scope.
        
        Args:
            tool_name: Name of the tool
            scope: Specific scope to check (if None, uses primary scope)
            
        Returns:
            List of allowed actions
        """
        if not self.is_tool_allowed(tool_name):
            return []
        
        if scope is None:
            scope = self.primary_scope
        
        tool_permissions = self.tool_action_permissions.get(tool_name, {})
        return tool_permissions.get(scope, [])
    
    def is_action_allowed(self, tool_name: str, action: str, scope: Optional[str] = None) -> bool:
        """Check if a specific action is allowed for a tool and scope.
        
        Args:
            tool_name: Name of the tool
            action: Action to check
            scope: Specific scope to check (if None, uses primary scope)
            
        Returns:
            True if action is allowed, False otherwise
        """
        if not self.is_tool_allowed(tool_name):
            return False
        
        if scope is None:
            scope = self.primary_scope
        
        tool_permissions = self.tool_action_permissions.get(tool_name, {})
        scope_actions = tool_permissions.get(scope, [])
        
        return action in scope_actions
    
    def get_scope_summary(self) -> Dict[str, Any]:
        """Get a summary of the current scope configuration."""
        # Build tool permissions structure for the summary
        tool_permissions = {}
        for tool_name in sorted(self.allowed_tools):
            tool_perms = self.tool_action_permissions.get(tool_name, {})
            # For each tool, get the actions for the primary scope
            primary_actions = tool_perms.get(self.primary_scope, [])
            tool_permissions[tool_name] = {
                "allowed_actions": primary_actions,
                "all_scopes": list(tool_perms.keys()),
                "scope_actions": {scope: actions for scope, actions in tool_perms.items()}
            }
        
        return {
            "success": True,  # Add success field
            "detected_scopes": self.detected_scopes,
            "api_scopes": self.api_scopes,
            "primary_scope": self.primary_scope,
            "allowed_tools": list(self.allowed_tools),
            "tool_count": len(self.allowed_tools),
            "scope_hierarchy": self.scope_hierarchy,
            "tool_permissions": tool_permissions  # Add the missing field
        }
    
    def get_tool_permissions_summary(self) -> Dict[str, Any]:
        """Get a detailed summary of tool permissions."""
        summary = {}
        for tool_name in sorted(self.allowed_tools):
            tool_perms = self.tool_action_permissions.get(tool_name, {})
            summary[tool_name] = {
                "scopes": list(tool_perms.keys()),
                "actions": {scope: actions for scope, actions in tool_perms.items()}
            }
        return summary 