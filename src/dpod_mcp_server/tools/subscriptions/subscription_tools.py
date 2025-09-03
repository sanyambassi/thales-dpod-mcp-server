#!/usr/bin/env python3
"""
Subscription Management Tools for DPoD MCP Server

Provides subscription operations for viewing tenant service subscriptions and billing information.
"""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError
)

async def manage_subscriptions(
    ctx: Context,
    action: str = Field(description="Operation to perform: list_subscriptions"),
    subscription_id: Optional[str] = Field(default=None, description="UUID of subscription (not used for list_subscriptions)"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for subscription operations"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    status: Optional[str] = Field(default=None, description="Status filter for list operations"),
    service_type: Optional[str] = Field(default=None, description="Service type filter for list operations")
) -> Dict[str, Any]:
    """Subscription management operations.
    
    Actions:
    - list_subscriptions: List all subscriptions with pagination and filtering
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.subscriptions")
    tool_logger.info(f"Starting subscription operation: {action}")
    
    try:
        await ctx.info(f"Starting subscription operation: {action}")
        await ctx.report_progress(0, 100, f"Starting subscription operation: {action}")
        
        # Validate token before proceeding
        await ctx.report_progress(10, 100, "Validating authentication token...")
        await ctx.info("Validating authentication token...")
        token_validation = await auth.validate_token_permissions()
        
        if not token_validation.get("valid"):
            error_msg = f"Authentication failed: {token_validation.get('error', 'Unknown error')}"
            tool_logger.error(error_msg)
            await ctx.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "token_validation": token_validation
            }
        
        await ctx.report_progress(20, 100, "Token validation successful")
        await ctx.info(f"Token validation successful - User: {token_validation.get('user_id')}, Scopes: {token_validation.get('scopes')}")
        tool_logger.info(f"Token validation successful - User: {token_validation.get('user_id')}, Scopes: {token_validation.get('scopes')}")
        
        # Only one action supported: list_subscriptions
        if action == "list_subscriptions":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting subscription listing workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating optional parameters...")
            
            await ctx.report_progress(50, 100, "Executing subscription retrieval...")
            await ctx.info("Executing subscription retrieval from DPoD API...")
            
            result = await _list_subscriptions(auth, tenant_id=tenant_id, service_type=service_type)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Subscription retrieval completed, finalizing response...")
        else:
            error_msg = f"Unknown action: {action}. Only 'list_subscriptions' is supported."
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed subscription operation: {action}")
        await ctx.info(f"Completed subscription operation: {action}")
        tool_logger.info(f"Completed subscription operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in subscription operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        return {"success": False, "error": str(e)}


async def _list_subscriptions(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List tenant service subscriptions with optional filtering."""
    tool_logger = logging.getLogger("dpod.tools.subscriptions")
    try:
        # Validate optional parameters
        tenant_id = validate_optional_param(kwargs.get("tenant_id"), lambda x: validate_uuid(x, "tenant_id"), "tenant_id")
        service_type = validate_optional_param(kwargs.get("service_type"), lambda x: validate_string_param(x, "Service Type", max_length=255), "service_type")
        
        # Prepare query parameters (only add if provided)
        params = {}
        if tenant_id:
            params["tenantId"] = tenant_id
        if service_type:
            params["serviceType"] = service_type
        
        # Make API request to list subscriptions
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/backoffice/subscriptions",
            params=params
        )
        
        if response.status_code == 200:
            subscriptions_data = response.json()
            
            # Debug logging
            tool_logger.info(f"Response type: {type(subscriptions_data)}, Length: {len(subscriptions_data) if isinstance(subscriptions_data, list) else 'N/A'}")
            
            # Handle different response formats
            if isinstance(subscriptions_data, list):
                # Direct list response (as per sample data)
                subscriptions = subscriptions_data
                tool_logger.info(f"Processing direct list response with {len(subscriptions)} subscriptions")
            elif isinstance(subscriptions_data, dict) and "content" in subscriptions_data:
                # Paginated response with content field
                subscriptions = subscriptions_data.get("content", [])
                tool_logger.info(f"Processing paginated response with {len(subscriptions)} subscriptions")
            else:
                # Fallback - treat as list
                subscriptions = subscriptions_data if isinstance(subscriptions_data, list) else []
                tool_logger.info(f"Processing fallback response with {len(subscriptions)} subscriptions")
            
            # Analyze subscription status
            status_summary = _analyze_subscription_status(subscriptions)
            
            return {
                "success": True,
                "subscriptions": subscriptions,
                "filters_applied": {
                    "tenant_id": tenant_id,
                    "service_type": service_type
                },
                "status_summary": status_summary,
                "message": f"Successfully retrieved {len(subscriptions)} subscriptions"
            }
        elif response.status_code == 400:
            return {
                "success": False,
                "error": "Bad request - invalid parameters",
                "status_code": 400,
                "details": response.text
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Tenant not found",
                "status_code": 404,
                "details": response.text
            }
        else:
            return {
                "success": False,
                "error": f"Failed to list subscriptions: {response.status_code}",
                "details": response.text,
                "status_code": response.status_code
            }
            
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analyze_subscription_status(subscriptions: list) -> Dict[str, Any]:
    """Analyze subscription status and provide summary."""
    if not subscriptions:
        return {
            "total_subscriptions": 0,
            "active_subscriptions": 0,
            "trial_subscriptions": 0,
            "expired_subscriptions": 0,
            "cancelled_subscriptions": 0,
            "marketplace_breakdown": {},
            "service_type_breakdown": {},
            "billing_summary": {},
            "plan_breakdown": {}
        }
    
    # Initialize counters
    total = len(subscriptions)
    active = 0
    trial = 0
    expired = 0
    cancelled = 0
    marketplace_count = {}
    service_type_count = {}
    plan_count = {}
    billing_summary = {
        "term_subscriptions": 0,
        "monthly_subscriptions": 0,
        "auto_renewal": 0
    }
    
    for sub in subscriptions:
        # Count by state
        state = sub.get("state", "UNKNOWN")
        if state == "ACTIVE":
            active += 1
        elif state == "EXPIRED":
            expired += 1
        elif state == "CANCELLED":
            cancelled += 1
        
        # Count by type
        sub_type = sub.get("type", "UNKNOWN")
        if sub_type == "TRIAL":
            trial += 1
        
        # Count by marketplace
        marketplace = sub.get("marketplaceName", "UNKNOWN")
        marketplace_count[marketplace] = marketplace_count.get(marketplace, 0) + 1
        
        # Count by service type
        service_type = sub.get("serviceType", "UNKNOWN")
        service_type_count[service_type] = service_type_count.get(service_type, 0) + 1
        
        # Count by plan
        plan = sub.get("plan", "UNKNOWN")
        plan_count[plan] = plan_count.get(plan, 0) + 1
        
        # Count by billing type
        if "Term" in plan:
            billing_summary["term_subscriptions"] += 1
        elif "Monthly" in plan:
            billing_summary["monthly_subscriptions"] += 1
        
        # Count auto-renewal (handle both boolean and string values)
        auto_renewal = sub.get("autoRenewal", False)
        if auto_renewal in [True, "true", "true,"]:  # Handle the comma in sample data
            billing_summary["auto_renewal"] += 1
    
    return {
        "total_subscriptions": total,
        "active_subscriptions": active,
        "trial_subscriptions": trial,
        "expired_subscriptions": expired,
        "cancelled_subscriptions": cancelled,
        "marketplace_breakdown": marketplace_count,
        "service_type_breakdown": service_type_count,
        "plan_breakdown": plan_count,
        "billing_summary": billing_summary
    } 