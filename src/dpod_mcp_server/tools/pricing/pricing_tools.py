#!/usr/bin/env python3
"""
Pricing Management Tools for DPoD MCP Server

Provides pricing operations for viewing service costs by country.
"""

import logging
from typing import Dict, Any, List, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, ValidationError
)

async def manage_pricing(
    ctx: Context,
    action: str = Field(description="Operation to perform: get_pricing_by_country"),
    country_code: str = Field(description="Country code for pricing (e.g., US, GB, DE)"),
    service_type: Optional[str] = Field(default=None, description="Service type filter for pricing")
) -> Dict[str, Any]:
    """Pricing information operations.
    
    Actions:
    - get_pricing_by_country: Get pricing information for a specific country
    
    Note: This is a global tool that doesn't require authentication.
    """
    # Get config from dependency injection
    from ...core.dependency_injection import get_config
    config = get_config()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    from ...core.logging_utils import get_tool_logger
    tool_logger = get_tool_logger("pricing")
    tool_logger.info(f"Starting pricing operation: {action}")
    
    try:
        await ctx.info(f"Starting pricing operation: {action}")
        await ctx.report_progress(0, 100, f"Starting pricing operation: {action}")
        
        # Note: No authentication required for pricing (global tool)
        await ctx.report_progress(10, 100, "Pricing is a public service - no authentication required")
        await ctx.info("Pricing is a public service - no authentication required")
        
        await ctx.report_progress(20, 100, "Starting pricing workflow...")
        await ctx.info("Starting pricing workflow...")
        
        # Only one action supported: get_pricing_by_country
        if action == "get_pricing_by_country":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting pricing workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating country code parameter...")
            
            await ctx.report_progress(50, 100, "Executing pricing retrieval...")
            await ctx.info("Executing pricing retrieval from DPoD API...")
            
            result = await _get_pricing_by_country(auth, country_code)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Pricing retrieval completed, finalizing response...")
        else:
            error_msg = f"Unknown action: {action}. Only 'get_pricing_by_country' is supported."
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed pricing operation: {action}")
        await ctx.info(f"Completed pricing operation: {action}")
        tool_logger.info(f"Completed pricing operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in pricing operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        return {"success": False, "error": str(e)}


async def _get_pricing_by_country(auth: DPoDAuth, country_code: str) -> Dict[str, Any]:
    """Get pricing information for all service types by country."""
    try:
        # Validate country code (ISO 3166-2 format)
        validated_country_code = validate_string_param(country_code, "Country Code", min_length=2, max_length=2)
        
        # Make API request to get pricing (unauthenticated - global tool)
        response = await auth.make_unauthenticated_request(
            "GET",
            "/v1/backoffice/pricing",
            params={"countryCode": validated_country_code}
        )
        
        if response.status_code == 200:
            pricing_data = response.json()
            
            # Analyze pricing data
            pricing_summary = _analyze_pricing_data(pricing_data)
            
            return {
                "success": True,
                "country_code": validated_country_code,
                "pricing": pricing_data,
                "pricing_summary": pricing_summary,
                "services_count": len(pricing_data),
                "message": f"Successfully retrieved pricing for {len(pricing_data)} services in {validated_country_code}"
            }
        elif response.status_code == 400:
            return {
                "success": False,
                "error": f"Invalid country code: {validated_country_code}",
                "country_code": validated_country_code,
                "status_code": 400
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Pricing not found for country: {validated_country_code}",
                "country_code": validated_country_code,
                "status_code": 404
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get pricing: {response.status_code}",
                "details": response.text,
                "country_code": validated_country_code,
                "status_code": response.status_code
            }
            
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analyze_pricing_data(pricing_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze pricing data and provide summary."""
    if not pricing_data:
        return {
            "total_services": 0,
            "currency_breakdown": {},
            "product_type_breakdown": {},
            "service_type_breakdown": {},
            "price_range": {"min": 0, "max": 0, "average": 0}
        }
    
    # Initialize counters
    total_services = len(pricing_data)
    currency_count = {}
    product_type_count = {}
    service_type_count = {}
    prices = []
    
    for item in pricing_data:
        # Count currencies
        price_info = item.get("price", {})
        currency = price_info.get("currency", "UNKNOWN")
        currency_count[currency] = currency_count.get(currency, 0) + 1
        
        # Count product types
        product_type = item.get("productType", "UNKNOWN")
        product_type_count[product_type] = product_type_count.get(product_type, 0) + 1
        
        # Count service types
        service_type = item.get("serviceType", "UNKNOWN")
        service_type_count[service_type] = service_type_count.get(service_type, 0) + 1
        
        # Collect prices
        price_value = price_info.get("value", 0)
        if price_value > 0:
            prices.append(price_value)
    
    # Calculate price statistics
    price_range = {"min": 0, "max": 0, "average": 0}
    if prices:
        price_range["min"] = min(prices)
        price_range["max"] = max(prices)
        price_range["average"] = sum(prices) / len(prices)
    
    return {
        "total_services": total_services,
        "currency_breakdown": currency_count,
        "product_type_breakdown": product_type_count,
        "service_type_breakdown": service_type_count,
        "price_range": price_range
    } 