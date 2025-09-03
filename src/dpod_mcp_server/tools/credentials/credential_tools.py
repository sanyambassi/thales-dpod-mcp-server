"""Client Credential Management Tools for DPoD MCP Server"""

import logging
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_integer_param
)

async def manage_credentials(
    ctx: Context,
    action: str = Field(description="Operation to perform: list, get, create, update, delete, reset_secret"),
    credential_id: Optional[str] = Field(default=None, description="UUID of credential (required for get, update, delete)"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for credential operations"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    name: Optional[str] = Field(default=None, description="Credential name for create/update operations"),
    type: Optional[str] = Field(default=None, description="Credential type for create/update operations"),
    client_id: Optional[str] = Field(default=None, description="UUID of client (required for get, update, delete, reset_secret)"),
    role: Optional[str] = Field(default=None, description="Client role for create/update operations"),
    service_ids: Optional[List[str]] = Field(default=None, description="List of service IDs to assign client to"),
    subscriber_groups: Optional[List[str]] = Field(default=None, description="List of subscriber group IDs to assign client to")
) -> Dict[str, Any]:
    """Credential management operations.
    
    Actions:
    - list: List all credentials with pagination and filtering
    - get: Get details of a specific credential
    - create: Create a new credential
    - update: Update an existing credential
    - delete: Delete a credential
    - reset_secret: Reset the secret for a client credential
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    from ...core.logging_utils import get_tool_logger
    tool_logger = get_tool_logger("credentials")
    tool_logger.info(f"Starting credential operation: {action}")
    await ctx.info(f"Starting credential operation: {action}")
    
    try:
        await ctx.report_progress(0, 100, f"Starting credential operation: {action}")
        
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
            await ctx.info("Starting client listing workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating pagination and filter parameters...")
            
            await ctx.report_progress(50, 100, "Executing client listing...")
            await ctx.info("Executing client listing from DPoD API...")
            
            result = await _list_clients(auth, page=page, size=size, role=role, service_ids=service_ids)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Client listing completed, finalizing response...")
            
        elif action == "get":
            if not client_id:
                error_msg = "client_id is required for get action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting client retrieval workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating client ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing client retrieval...")
            await ctx.info("Executing client retrieval from DPoD API...")
            
            result = await _get_client(auth, client_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Client retrieval completed, finalizing response...")
            
        elif action == "create":
            if not all([name, role]):
                error_msg = "name and role are required for create action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting client creation workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating client creation parameters...")
            
            await ctx.report_progress(50, 100, "Executing client creation...")
            await ctx.info("Executing client creation via DPoD API...")
            
            result = await _create_client(auth, name, role, service_ids=service_ids, subscriber_groups=subscriber_groups)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Client creation completed, finalizing response...")
            
        elif action == "update":
            if not client_id:
                error_msg = "client_id is required for update action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting client update workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating client update parameters...")
            
            await ctx.report_progress(50, 100, "Executing client update...")
            await ctx.info("Executing client update via DPoD API...")
            
            result = await _update_client(auth, client_id, name=name)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Client update completed, finalizing response...")
            
        elif action == "delete":
            if not client_id:
                error_msg = "client_id is required for delete action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting client deletion workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating client ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing client deletion...")
            await ctx.info("Executing client deletion via DPoD API...")
            
            result = await _delete_client(auth, client_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Client deletion completed, finalizing response...")
            
        elif action == "reset_secret":
            if not client_id:
                error_msg = "client_id is required for reset_secret action"
                await ctx.error(error_msg)
                raise ValueError(error_msg)
                
            await ctx.report_progress(30, 100, "Starting workflow...")
            await ctx.info("Starting client secret reset workflow...")
            
            await ctx.report_progress(40, 100, "Validating parameters...")
            await ctx.info("Validating client ID parameter...")
            
            await ctx.report_progress(50, 100, "Executing secret reset...")
            await ctx.info("Executing client secret reset via DPoD API...")
            
            result = await _reset_client_secret(auth, client_id)
            
            await ctx.report_progress(80, 100, "Completed, finalizing...")
            await ctx.info("Client secret reset completed, finalizing response...")
            
        else:
            error_msg = f"Unknown action: {action}"
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed credential operation: {action}")
        await ctx.info(f"Completed credential operation: {action}")
        tool_logger.info(f"Completed credential operation: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in credential operation {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        raise

async def _list_clients(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List client credentials in a DPoD tenant."""
    try:
        page = validate_optional_param(kwargs.get("page"), lambda x: validate_integer_param(x, "page", min_value=0), "page") or 0
        size = validate_optional_param(kwargs.get("size"), lambda x: validate_integer_param(x, "size", min_value=1, max_value=100), "size") or 50
        role = validate_optional_param(kwargs.get("role"), lambda x: validate_string_param(x, "Role"), "role")
        service_ids = kwargs.get("service_ids")
        
        params = {"page": page, "size": size}
        if role:
            params["role"] = role
        if service_ids:
            params["serviceIds"] = service_ids
            
        response = await auth.make_authenticated_request("GET", "/v1/credentials/clients", params=params)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to list clients: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _get_client(auth: DPoDAuth, client_id: str) -> Dict[str, Any]:
    """Get details of a specific client credential."""
    try:
        client_uuid = validate_uuid(client_id, "client_id")
        response = await auth.make_authenticated_request("GET", f"/v1/credentials/clients/{client_uuid}")
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to get client: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _create_client(auth: DPoDAuth, name: str, role: str, **kwargs) -> Dict[str, Any]:
    """Create a new client credential."""
    try:
        client_data = {
            "name": validate_string_param(name, "Name"),
            "role": validate_string_param(role, "Role")
        }
        if kwargs.get("service_ids"):
            client_data["serviceIds"] = kwargs.get("service_ids")
        if kwargs.get("subscriber_groups"):
            client_data["subscriberGroups"] = kwargs.get("subscriber_groups")

        response = await auth.make_authenticated_request("POST", "/v1/credentials/clients", json_data=client_data)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to create client: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _update_client(auth: DPoDAuth, client_id: str, **kwargs) -> Dict[str, Any]:
    """Update an existing client credential."""
    try:
        client_uuid = validate_uuid(client_id, "client_id")
        update_data = {}
        if kwargs.get("name"):
            update_data["name"] = validate_string_param(kwargs.get("name"), "Name")

        if not update_data:
            return {"success": False, "error": "No fields to update"}

        response = await auth.make_authenticated_request("PATCH", f"/v1/credentials/clients/{client_uuid}", json_data=update_data)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to update client: {response.status_code}", "details": response.text}

        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _delete_client(auth: DPoDAuth, client_id: str) -> Dict[str, Any]:
    """Delete a client credential."""
    try:
        client_uuid = validate_uuid(client_id, "client_id")
        response = await auth.make_authenticated_request("DELETE", f"/v1/credentials/clients/{client_uuid}")
        
        if response.status_code != 204:
            return {"success": False, "error": f"Failed to delete client: {response.status_code}", "details": response.text}

        return {"success": True, "message": "Client deleted successfully"}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _reset_client_secret(auth: DPoDAuth, client_id: str) -> Dict[str, Any]:
    """Reset a client credential's secret."""
    try:
        client_uuid = validate_uuid(client_id, "client_id")
        response = await auth.make_authenticated_request("POST", f"/v1/credentials/clients/{client_uuid}/resetSecret")
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to reset client secret: {response.status_code}", "details": response.text}

        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
