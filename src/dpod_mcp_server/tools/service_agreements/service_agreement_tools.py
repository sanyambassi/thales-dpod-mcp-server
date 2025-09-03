#!/usr/bin/env python3
"""
Service Agreement Management Tools for DPoD MCP Server

Provides service agreement operations including viewing, approving, and rejecting agreements.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid,
    ValidationError
)

async def manage_service_agreements(
    ctx: Context,
    action: str = Field(description="Operation to perform: get_agreement, approve_agreement, reject_agreement"),
    agreement_id: Optional[str] = Field(default=None, description="UUID of service agreement (not used for current actions)"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for service agreement operations (required)"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    status: Optional[str] = Field(default=None, description="Status filter for list operations")
) -> Dict[str, Any]:
    """Service agreement management operations.
    
    Actions:
    - get_agreement: Get details of a specific service agreement
    - approve_agreement: Approve a service agreement
    - reject_agreement: Reject a service agreement
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.service_agreements")
    tool_logger.info(f"Starting service agreement operation: {action}")
    
    try:
        await ctx.info(f"Starting service agreement operation: {action}")
        await ctx.report_progress(0, 100, f"Starting service agreement operation: {action}")
        
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
        
        # Check if tenant_id is provided
        if not tenant_id:
            error_msg = "tenant_id is required for all service agreement actions"
            await ctx.error(error_msg)
            raise ValueError(error_msg)
        
        # Define write actions that require special permissions
        write_actions = {"approve_agreement", "reject_agreement"}
        
        if action in write_actions and config.read_only_mode:
            error_msg = f"Server is in read-only mode. Action '{action}' is not allowed."
            tool_logger.warning(error_msg)
            await ctx.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "action": action,
                "read_only_mode": True
            }
        
        if action == "get_agreement":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting service agreement retrieval workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating tenant ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing agreement retrieval...")
            await ctx.info("Executing service agreement retrieval from DPoD API...")
            
            result = await _get_service_agreement(auth, tenant_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Service agreement retrieval completed, finalizing response...")
            
        elif action == "approve_agreement":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting service agreement approval workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating tenant ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing agreement approval...")
            await ctx.info("Executing service agreement approval via DPoD API...")
            
            result = await _approve_service_agreement(auth, tenant_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Service agreement approval completed, finalizing response...")
            
        elif action == "reject_agreement":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting service agreement rejection workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating tenant ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing agreement rejection...")
            await ctx.info("Executing service agreement rejection via DPoD API...")
            
            result = await _reject_service_agreement(auth, tenant_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Service agreement rejection completed, finalizing response...")
            
        else:
            error_msg = f"Unknown action: {action}"
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed service agreement operation: {action}")
        await ctx.info(f"Completed service agreement operation: {action}")
        tool_logger.info(f"Completed service agreement operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in service agreement operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        return {"success": False, "error": str(e)}


async def _get_service_agreement(auth: DPoDAuth, tenant_id: str) -> Dict[str, Any]:
    """Get service agreement details for a tenant."""
    try:
        # Validate tenant ID
        validated_tenant_id = validate_uuid(tenant_id, "tenant_id")
        
        # Make API request to get service agreement
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/backoffice/serviceAgreements/{validated_tenant_id}"
        )
        
        if response.status_code == 200:
            agreement_data = response.json()
            
            # Analyze tenant status based on response data
            tenant_status = _analyze_tenant_status(agreement_data)
            
            return {
                "success": True,
                "tenant_id": validated_tenant_id,
                "agreement": agreement_data,
                "tenant_status": tenant_status,
                "message": "Successfully retrieved service agreement"
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Service agreement not found for tenant: {validated_tenant_id}",
                "tenant_id": validated_tenant_id,
                "status_code": 404
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get service agreement: {response.status_code}",
                "details": response.text,
                "tenant_id": validated_tenant_id,
                "status_code": response.status_code
            }
            
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analyze_tenant_status(agreement_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze tenant status based on service agreement response."""
    try:
        current_date = datetime.now(timezone.utc)
        
        # Extract dates from response
        acceptance = agreement_data.get("acceptance", {})
        agreement_date = acceptance.get("agreementDate")
        end_of_agreement_date = acceptance.get("endOfAgreementDate")
        
        # Extract additional information
        terms = agreement_data.get("terms", {})
        submission = agreement_data.get("submission", {})
        
        # Determine tenant status based on business logic
        if agreement_date:
            # Has acceptedDate - tenant is a Subscriber
            tenant_status = "Subscriber"
            status_reason = "Service agreement has been accepted"
        else:
            # No acceptedDate - check evaluation status
            if end_of_agreement_date:
                try:
                    end_date = datetime.fromisoformat(end_of_agreement_date.replace('Z', '+00:00'))
                    if current_date > end_date:
                        tenant_status = "Expired"
                        status_reason = "Evaluation period has expired"
                    else:
                        tenant_status = "Evaluation Tenant"
                        status_reason = "Currently in evaluation period"
                except (ValueError, TypeError):
                    tenant_status = "Evaluation Tenant"
                    status_reason = "Currently in evaluation period (date parsing issue)"
            else:
                tenant_status = "Evaluation Tenant"
                status_reason = "Currently in evaluation period"
        
        # Extract service information
        service_breakdown = {}
        if "mbus" in terms:
            for mbu in terms["mbus"]:
                service_type = mbu.get("serviceType", {}).get("shortCode", "UNKNOWN")
                quantity = mbu.get("quantity", 0)
                service_breakdown[service_type] = quantity
        
        return {
            "status": tenant_status,
            "reason": status_reason,
            "agreement_date": agreement_date,
            "end_of_agreement_date": end_of_agreement_date,
            "tenant_name": submission.get("tenantName"),
            "tenant_id": submission.get("tenantID"),
            "submitted_date": submission.get("submittedDate"),
            "service_breakdown": service_breakdown,
            "agreement_duration_months": terms.get("duration"),
            "analysis_timestamp": current_date.isoformat()
        }
        
    except Exception as e:
        return {
            "status": "Unknown",
            "reason": f"Error analyzing status: {str(e)}",
            "error": str(e)
        }


async def _approve_service_agreement(auth: DPoDAuth, tenant_id: str) -> Dict[str, Any]:
    """Approve a tenant service agreement."""
    try:
        # Validate tenant ID
        validated_tenant_id = validate_uuid(tenant_id, "tenant_id")
        
        # Prepare approval data
        approval_data = {}
        
        # Make API request to approve service agreement
        response = await auth.make_authenticated_request(
            "PATCH",
            f"/v1/backoffice/serviceAgreements/{validated_tenant_id}",
            json_data=approval_data
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "tenant_id": validated_tenant_id,
                "action": "approved",
                "message": "Service agreement approved successfully",
                "approval_data": approval_data
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Service agreement not found for tenant: {validated_tenant_id}",
                "tenant_id": validated_tenant_id,
                "status_code": 404
            }
        elif response.status_code == 409:
            return {
                "success": False,
                "error": "Service agreement conflict - not submitted or already approved",
                "tenant_id": validated_tenant_id,
                "status_code": 409
            }
        else:
            return {
                "success": False,
                "error": f"Failed to approve service agreement: {response.status_code}",
                "details": response.text,
                "tenant_id": validated_tenant_id,
                "status_code": response.status_code
            }
            
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _reject_service_agreement(auth: DPoDAuth, tenant_id: str) -> Dict[str, Any]:
    """Reject a tenant service agreement."""
    try:
        # Validate tenant ID
        validated_tenant_id = validate_uuid(tenant_id, "tenant_id")
        
        # Make API request to reject service agreement
        response = await auth.make_authenticated_request(
            "DELETE",
            f"/v1/backoffice/serviceAgreements/{validated_tenant_id}"
        )
        
        if response.status_code == 204:
            return {
                "success": True,
                "tenant_id": validated_tenant_id,
                "action": "rejected",
                "message": "Service agreement rejected successfully"
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Service agreement not found for tenant: {validated_tenant_id}",
                "status_code": 404
            }
        elif response.status_code == 409:
            return {
                "success": False,
                "error": "Service agreement conflict - not submitted or already approved",
                "tenant_id": validated_tenant_id,
                "status_code": 409
            }
        else:
            return {
                "success": False,
                "error": f"Failed to reject service agreement: {response.status_code}",
                "details": response.text,
                "tenant_id": validated_tenant_id,
                "status_code": response.status_code
            }
            
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)} 