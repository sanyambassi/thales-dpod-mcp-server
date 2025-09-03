#!/usr/bin/env python3
"""
Product Management Tools for DPoD MCP Server

Provides product operations for viewing service plans and features.
"""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, ValidationError
)

async def manage_products(
    ctx: Context,
    action: str = Field(description="Operation to perform: get_product_plans"),
    product_id: Optional[str] = Field(default=None, description="UUID of product (not used for get_product_plans)"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    service_type: Optional[str] = Field(default=None, description="Service type filter for get_product_plans (required)"),
    category: Optional[str] = Field(default=None, description="Category filter for list operations")
) -> Dict[str, Any]:
    """Product catalog management operations.
    
    Actions:
    - get_product_plans: Get available plans for a specific service type
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.products")
    tool_logger.info(f"Starting product operation: {action}")
    
    try:
        await ctx.info(f"Starting product operation: {action}")
        await ctx.report_progress(0, 100, f"Starting product operation: {action}")
        
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
        
        # Only one action supported: get_product_plans
        if action == "get_product_plans":
            if not service_type:
                error_msg = "service_type is required for get_product_plans action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting product plans retrieval workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating service type parameter...")
            
            await ctx.report_progress(50, 100, "Executing product plans retrieval...")
            await ctx.info("Executing product plans retrieval from DPoD API...")
            
            result = await _get_product_plans(auth, service_type)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Product plans retrieval completed, finalizing response...")
        else:
            error_msg = f"Unknown action: {action}. Only 'get_product_plans' is supported."
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed product operation: {action}")
        await ctx.info(f"Completed product operation: {action}")
        tool_logger.info(f"Completed product operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in product operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        return {"success": False, "error": str(e)}


async def _get_product_plans(auth: DPoDAuth, service_type: str) -> Dict[str, Any]:
    """Get product plans for a specific service type."""
    tool_logger = logging.getLogger("dpod.tools.products")
    try:
        # Validate service type
        validated_service_type = validate_string_param(service_type, "Service Type", min_length=1, max_length=50)
        
        # Make API request to get product plans
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/backoffice/products/{validated_service_type}"
        )
        
        if response.status_code == 200:
            product_data = response.json()
            
            # Debug logging
            tool_logger.info(f"Product response type: {type(product_data)}, Keys: {list(product_data.keys()) if isinstance(product_data, dict) else 'N/A'}")
            
            # Handle the actual response structure
            if isinstance(product_data, dict) and "plans" in product_data:
                # Single plan object (as per sample data)
                plans_data = product_data["plans"]
                plans_count = 1
                message = f"Successfully retrieved plan for {validated_service_type}"
                tool_logger.info(f"Processing single plan response for {validated_service_type}")
            elif isinstance(product_data, list):
                # Array of plans
                plans_data = product_data
                plans_count = len(product_data)
                message = f"Successfully retrieved {plans_count} plans for {validated_service_type}"
                tool_logger.info(f"Processing array of {plans_count} plans for {validated_service_type}")
            else:
                # Fallback
                plans_data = product_data
                plans_count = 1 if product_data else 0
                message = f"Successfully retrieved product data for {validated_service_type}"
                tool_logger.info(f"Processing fallback response for {validated_service_type}")
            
            return {
                "success": True,
                "service_type": validated_service_type,
                "product": product_data,
                "plans_data": plans_data,
                "plans_count": plans_count,
                "message": message
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Product not found for service type: {validated_service_type}",
                "service_type": validated_service_type,
                "status_code": 404
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get product plans: {response.status_code}",
                "details": response.text,
                "service_type": validated_service_type,
                "status_code": response.status_code
            }
            
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)} 