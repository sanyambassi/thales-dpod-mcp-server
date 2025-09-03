#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Scope Wrapper Module

Provides scope validation wrapper for MCP tools.
"""

import logging
import functools
from typing import Callable, Any, Dict, Optional
from .scope_manager import ScopeManager

def scope_validate(scope_manager: ScopeManager = None, tool_name: str = None):
    """Decorator to add scope validation to MCP tools.
    
    Args:
        scope_manager: The scope manager instance to use for validation (optional, will use DI if not provided)
        tool_name: The name of the tool for scope validation (if None, will try to extract from function)
        
    Returns:
        Decorated function with scope validation
    """
    
    # Define global tools that don't require scope validation
    # If a tool is global, ALL its actions are automatically global
    GLOBAL_TOOLS = {
        "manage_pricing",           # Pricing information is public
        "check_dpod_availability",  # Platform status is public
        "_list_service_categories", # Internal function for service categories
        "_list_service_types"       # Internal function for service types
    }
    
    # Define global actions that don't require scope validation
    # These actions are global even when called within non-global tools
    GLOBAL_ACTIONS = {
        "list_categories",          # Service categories are public (action in manage_services)
        "list_types",               # Service types are public (action in manage_services)
    }
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get scope manager from parameter or dependency injection
            if scope_manager is None:
                from .dependency_injection import get_scope_manager
                current_scope_manager = get_scope_manager()
            else:
                current_scope_manager = scope_manager
            
            # Get tool name from parameter or function
            current_tool_name = tool_name or func.__name__
            
            # Check if this is a global tool that doesn't require scope validation
            if current_tool_name in GLOBAL_TOOLS:
                logging.getLogger(f"dpod.scope.{current_tool_name}").debug(f"Global tool '{current_tool_name}' - bypassing scope validation for all actions")
                return await func(*args, **kwargs)
            
            # Extract action parameter (usually the second parameter after ctx)
            action = None
            if len(args) > 1:
                # Check if second arg is action (first arg is ctx, second is action)
                if isinstance(args[1], str):
                    action = args[1]
                elif 'action' in kwargs:
                    action = kwargs['action']
            elif 'action' in kwargs:
                action = kwargs['action']
            
            # Note: We no longer need to check for global actions separately
            # If a tool is global, all its actions are global
            # If a tool is not global, all its actions require scope validation
            
            # Check if this is a global action within a tool (e.g., list_categories in manage_services)
            if action and action in GLOBAL_ACTIONS:
                logging.getLogger(f"dpod.scope.{current_tool_name}").debug(f"Global action '{action}' in tool '{current_tool_name}' - bypassing scope validation")
                return await func(*args, **kwargs)
            
            # Ensure scopes are up-to-date before validation
            if not current_scope_manager.detected_scopes:
                try:
                    await current_scope_manager.detect_scopes()
                except Exception as e:
                    logging.getLogger(f"dpod.scope.{current_tool_name}").error(f"Failed to refresh scopes: {e}")
                    return {
                        "success": False,
                        "error": "Failed to validate scopes. Please try again.",
                        "scope_restricted": True
                    }
            
            # Filter for API scopes only (those containing 'api_')
            api_scopes = [scope for scope in current_scope_manager.detected_scopes if "api_" in scope]
            
            # If no API scopes found, block all actions (except global tools)
            if not api_scopes:
                error_msg = f"No API scopes found in token. Tool '{current_tool_name}' requires API access."
                logging.getLogger(f"dpod.scope.{current_tool_name}").warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "tool": current_tool_name,
                    "current_scope": "none",
                    "scope_restricted": True
                }
            
            # Check if tool is allowed (using API scopes only)
            if not current_scope_manager.is_tool_allowed(current_tool_name):
                error_msg = f"Tool '{current_tool_name}' not allowed"
                logging.getLogger(f"dpod.scope.{current_tool_name}").warning(error_msg)
                
                # Return error response
                return {
                    "success": False,
                    "error": error_msg,
                    "tool": current_tool_name,
                    "current_scope": api_scopes[0] if api_scopes else "none",
                    "scope_restricted": True
                }
            
            # If action is specified, check if it's allowed
            if action:
                if not current_scope_manager.is_action_allowed(current_tool_name, action):
                    allowed_actions = current_scope_manager.get_allowed_actions(current_tool_name)
                    error_msg = f"Action '{action}' not allowed for tool '{current_tool_name}'"
                    logging.getLogger(f"dpod.scope.{current_tool_name}").warning(error_msg)
                    
                    # Return error response
                    return {
                        "success": False,
                        "error": error_msg,
                        "tool": current_tool_name,
                        "action": action,
                        "allowed_actions": allowed_actions,
                        "current_scope": api_scopes[0] if api_scopes else "none",
                        "scope_restricted": True
                    }
            
            # Scope validation passed, proceed with tool execution
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def get_scope_validation_error_response(
    tool_name: str, 
    action: Optional[str], 
    scope_manager: ScopeManager,
    error_type: str = "tool_not_allowed"
) -> Dict[str, Any]:
    """Generate a standardized scope validation error response.
    
    Args:
        tool_name: Name of the tool that was blocked
        action: Action that was attempted (if any)
        scope_manager: The scope manager instance
        error_type: Type of scope error
        
    Returns:
        Standardized error response dictionary
    """
    if error_type == "tool_not_allowed":
        error_msg = f"Tool '{tool_name}' not allowed"
    elif error_type == "action_not_allowed":
        error_msg = f"Action '{action}' not allowed for tool '{tool_name}'"
    else:
        error_msg = f"Scope validation failed for tool '{tool_name}'"
    
    # Get current scope (first API scope if available)
    current_scope = "none"
    if scope_manager.api_scopes:
        current_scope = scope_manager.api_scopes[0]
    
    response = {
        "success": False,
        "error": error_msg,
        "tool": tool_name,
        "current_scope": current_scope,
        "scope_restricted": True,
        "error_type": error_type
    }
    
    # Add action-specific fields
    if action:
        response["action"] = action
        if error_type == "action_not_allowed":
            response["allowed_actions"] = scope_manager.get_allowed_actions(tool_name)
    
    return response 