"""Report Management Tools for DPoD MCP Server"""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_integer_param
)


async def manage_reports(
    ctx: Context,
    action: str = Field(description="Operation to perform: get_service_summary, get_usage_billing"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for report operations"),
    period: str = Field(default="30d", description="Report period (e.g., 7d, 30d, 90d)"),
    service_type: Optional[str] = Field(default=None, description="Service type filter for reports"),
    format: str = Field(default="json", description="Report format (json, csv, pdf)")
) -> Dict[str, Any]:
    """Report generation and management operations.
    
    Actions:
    - get_service_summary: Get summary report of services for a tenant
    - get_usage_billing: Get usage and billing report for a tenant
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.report")
    tool_logger.info(f"Starting report operation: {action}")
    
    try:
        await ctx.info(f"Starting report operation: {action}")
        await ctx.report_progress(0, 100, f"Starting report operation: {action}")
        
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
        
        # All actions are read-only, so no need to check read-only mode
        
        if action == "get_service_summary":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting service summary retrieval workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating service summary parameters...")
            
            await ctx.report_progress(50, 100, "Executing service summary retrieval...")
            await ctx.info("Executing service summary retrieval from DPoD API...")
            
            result = await _get_service_summary(auth)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Service summary retrieval completed, finalizing response...")
            
        elif action == "get_usage_billing":
            if not start_date or not end_date:
                error_msg = "start_date and end_date are required for get_usage_billing action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting usage billing report workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating billing report parameters...")
            
            await ctx.report_progress(50, 100, "Executing billing report generation...")
            await ctx.info("Executing usage billing report generation from DPoD API...")
            
            result = await _get_usage_billing_report(
                auth, 
                start_date=start_date, 
                end_date=end_date,
                tenant_id=tenant_id,
                short_code=short_code
            )
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Usage billing report generation completed, finalizing response...")
            
        else:
            error_msg = f"Unknown action: {action}. Valid actions: get_service_summary, get_usage_billing"
            await ctx.error(error_msg)
            raise ValueError(error_msg)
        
        await ctx.report_progress(100, 100, f"Completed report operation: {action}")
        await ctx.info(f"Completed report operation: {action}")
        tool_logger.info(f"Completed report operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in report operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        raise


async def _get_service_summary(auth: DPoDAuth) -> Dict[str, Any]:
    """Get summary of currently active services.
    
    Returns summary information about active services including:
    - tenantId: Tenant identifier
    - serviceType: Type of service
    - marketplaceName: Marketplace name
    - count: Number of active services
    
    Returns:
        Summary data with tenant, service type, marketplace, and count information
    """
    try:
        # Make API request to service instances summary endpoint
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/service_instances/summary"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get service summary: {response.status_code}",
                "details": response.text
            }
        
        summary_data = response.json()
        
        return {
            "success": True,
            "summary": summary_data,
            "total_services": len(summary_data) if isinstance(summary_data, list) else 0
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_usage_billing_report(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get usage billing report for specified time period.
    
    Returns a CSV file containing billing information for the specified time period.
    
    Args:
        start_date: Start date in format YYYY-MM-DDTHH:MM:SS.000Z (24 characters)
        end_date: End date in format YYYY-MM-DDTHH:MM:SS.999Z (24 characters)
        tenant_id: Optional tenant ID filter
        short_code: Optional service type short code filter
        
    Returns:
        CSV billing report data
        
    Note:
        - Date format must be exactly 24 characters: YYYY-MM-DDTHH:MM:SS.000Z
        - Time period can be up to 31 days maximum
        - Report is returned as CSV content
    """
    try:
        # Extract required parameters from kwargs
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        
        if not start_date or not end_date:
            return {
                "success": False,
                "error": "start_date and end_date are required parameters"
            }
        
        # Validate required parameters
        start_date = validate_string_param(start_date, "Start Date", min_length=24, max_length=24)
        end_date = validate_string_param(end_date, "End Date", min_length=24, max_length=24)
        
        # Validate optional parameters
        tenant_id = validate_optional_param(
            kwargs.get("tenant_id"),
            lambda x: validate_uuid(x, "Tenant ID"),
            "tenant_id"
        )
        
        short_code = validate_optional_param(
            kwargs.get("short_code"),
            lambda x: validate_string_param(x, "Short Code", min_length=1, max_length=50),
            "short_code"
        )
        
        # Prepare query parameters
        params = {
            "startDate": start_date,
            "endDate": end_date
        }
        
        if tenant_id:
            params["tenantId"] = tenant_id
        if short_code:
            params["shortCode"] = short_code
        
        # Make API request to usage billing report endpoint
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/service_instances/usageBillingReport",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get usage billing report: {response.status_code}",
                "details": response.text
            }
        
        # Get CSV content
        csv_content = response.text
        
        return {
            "success": True,
            "report_type": "usage_billing",
            "start_date": start_date,
            "end_date": end_date,
            "csv_content": csv_content,
            "content_length": len(csv_content),
            "message": "Usage billing report generated successfully"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)} 