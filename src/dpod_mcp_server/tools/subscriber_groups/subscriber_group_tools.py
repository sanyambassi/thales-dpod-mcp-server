"""Subscriber Group Management Tools for DPoD MCP Server"""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_integer_param
)

async def manage_subscriber_groups(
    ctx: Context,
    action: str = Field(description="Operation to perform: list, get, create, update, delete"),
    group_id: Optional[str] = Field(default=None, description="UUID of subscriber group (required for get, update, delete)"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for subscriber group operations"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    name: Optional[str] = Field(default=None, description="Group name for create/update operations"),
    description: Optional[str] = Field(default=None, description="Group description for create/update operations")
) -> Dict[str, Any]:
    """Subscriber group management operations.
    
    Actions:
    - list: List all subscriber groups with pagination and filtering
    - get: Get details of a specific subscriber group
    - create: Create a new subscriber group
    - update: Update an existing subscriber group
    - delete: Delete a subscriber group
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.subscriber_group")
    tool_logger.info(f"Starting subscriber group operation: {action}")
    await ctx.info(f"Starting subscriber group operation: {action}")
    
    try:
        await ctx.report_progress(0, 100, f"Starting subscriber group operation: {action}")
        
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
        
        write_actions = {"create", "update", "delete"}
        
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

        if action == "list":
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting subscriber group listing workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating pagination parameters...")
            
            await ctx.report_progress(50, 100, "Executing group listing...")
            await ctx.info("Executing subscriber group listing from DPoD API...")
            
            result = await _list_subscriber_groups(auth, page=page, size=size)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Subscriber group listing completed, finalizing response...")
            
        elif action == "get":
            if not group_id:
                error_msg = "group_id is required for get action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting subscriber group retrieval workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating group ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing group retrieval...")
            await ctx.info("Executing subscriber group retrieval from DPoD API...")
            
            result = await _get_subscriber_group(auth, group_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Subscriber group retrieval completed, finalizing response...")
            
        elif action == "create":
            if not name:
                error_msg = "name is required for create action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting subscriber group creation workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating group creation parameters...")
            
            await ctx.report_progress(50, 100, "Executing group creation...")
            await ctx.info("Executing subscriber group creation via DPoD API...")
            
            result = await _create_subscriber_group(auth, name, description=description)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Subscriber group creation completed, finalizing response...")
            
        elif action == "update":
            if not group_id:
                error_msg = "group_id is required for update action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting subscriber group update workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating group update parameters...")
            
            await ctx.report_progress(50, 100, "Executing group update...")
            await ctx.info("Executing subscriber group update via DPoD API...")
            
            result = await _update_subscriber_group(auth, group_id, name=name, description=description)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Subscriber group update completed, finalizing response...")
            
        elif action == "delete":
            if not group_id:
                error_msg = "group_id is required for delete action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting subscriber group deletion workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating group ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing group deletion...")
            await ctx.info("Executing subscriber group deletion via DPoD API...")
            
            result = await _delete_subscriber_group(auth, group_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Subscriber group deletion completed, finalizing response...")
            
        else:
            error_msg = f"Unknown action: {action}"
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed subscriber group operation: {action}")
        await ctx.info(f"Completed subscriber group operation: {action}")
        tool_logger.info(f"Completed subscriber group operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in subscriber group operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        raise

async def _list_subscriber_groups(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List subscriber groups in a DPoD tenant."""
    try:
        page = validate_optional_param(kwargs.get("page"), lambda x: validate_integer_param(x, "page", min_value=0), "page") or 0
        size = validate_optional_param(kwargs.get("size"), lambda x: validate_integer_param(x, "size", min_value=1, max_value=100), "size") or 50
        
        params = {"page": page, "size": size}
            
        response = await auth.make_authenticated_request("GET", "/v1/subscriber_groups", params=params)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to list subscriber groups: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _get_subscriber_group(auth: DPoDAuth, group_id: str) -> Dict[str, Any]:
    """Get details of a specific subscriber group."""
    try:
        group_uuid = validate_uuid(group_id, "group_id")
        response = await auth.make_authenticated_request("GET", f"/v1/subscriber_groups/{group_uuid}")
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to get subscriber group: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _create_subscriber_group(auth: DPoDAuth, name: str, **kwargs) -> Dict[str, Any]:
    """Create a new subscriber group."""
    try:
        group_data = {
            "name": validate_string_param(name, "Name")
        }
        if kwargs.get("description"):
            group_data["description"] = validate_string_param(kwargs.get("description"), "Description")

        response = await auth.make_authenticated_request("POST", "/v1/subscriber_groups", json_data=group_data)
        
        if response.status_code != 201:
            return {"success": False, "error": f"Failed to create subscriber group: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _update_subscriber_group(auth: DPoDAuth, group_id: str, **kwargs) -> Dict[str, Any]:
    """Update an existing subscriber group."""
    try:
        group_uuid = validate_uuid(group_id, "group_id")
        update_data = {}
        if kwargs.get("name"):
            update_data["name"] = validate_string_param(kwargs.get("name"), "Name")
        if kwargs.get("description"):
            update_data["description"] = validate_string_param(kwargs.get("description"), "Description")

        if not update_data:
            return {"success": False, "error": "No fields to update"}

        response = await auth.make_authenticated_request("PATCH", f"/v1/subscriber_groups/{group_uuid}", json_data=update_data)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to update subscriber group: {response.status_code}", "details": response.text}

        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _delete_subscriber_group(auth: DPoDAuth, group_id: str) -> Dict[str, Any]:
    """Delete a subscriber group."""
    try:
        group_uuid = validate_uuid(group_id, "group_id")
        response = await auth.make_authenticated_request("DELETE", f"/v1/subscriber_groups/{group_uuid}")
        
        if response.status_code != 204:
            return {"success": False, "error": f"Failed to delete subscriber group: {response.status_code}", "details": response.text}

        return {"success": True, "message": "Subscriber group deleted successfully"}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
