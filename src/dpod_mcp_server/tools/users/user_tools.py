"""User Management Tools for DPoD MCP Server"""

import logging
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_json_data, validate_integer_param
)

async def manage_users(
    ctx: Context,
    action: str = Field(description="Operation to perform: list, get, create, update, delete, get_profile, change_password, reset_mfa_token"),
    user_id: Optional[str] = Field(default=None, description="UUID of user (required for get, update, delete, get_profile, change_password, reset_mfa_token)"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    status: Optional[str] = Field(default=None, description="Status filter for list operations (active, inactive, suspended)"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID filter for list operations"),
    username: Optional[str] = Field(default=None, description="Username for create/update operations"),
    email: Optional[str] = Field(default=None, description="Email address for create/update operations"),
    given_name: Optional[str] = Field(default=None, description="First name for create/update operations"),
    family_name: Optional[str] = Field(default=None, description="Last name for create/update operations"),
    phone_number: Optional[str] = Field(default=None, description="Phone number for create/update operations"),
    department_name: Optional[str] = Field(default=None, description="Department name for create/update operations"),
    job_title: Optional[str] = Field(default=None, description="Job title for create/update operations"),
    password: Optional[str] = Field(default=None, description="Password for create/update operations"),
    force_password_change: bool = Field(default=False, description="Force password change on next login"),
    mfa_enabled: bool = Field(default=False, description="Enable MFA for user"),
    groups: Optional[List[str]] = Field(default=None, description="List of group IDs to assign user to"),
    description: Optional[str] = Field(default=None, description="Description for user update operations"),
    configuration: Optional[Dict[str, Any]] = Field(default=None, description="Configuration object for user update operations"),
    account_role: Optional[str] = Field(default=None, description="Account role for user creation"),
    email_hints: Optional[Dict[str, Any]] = Field(default=None, description="Email hints for user creation"),
    subscriber_groups: Optional[List[str]] = Field(default=None, description="List of subscriber group IDs to assign user to"),
    old_password: Optional[str] = Field(default=None, description="Current password for change_password action"),
    new_password: Optional[str] = Field(default=None, description="New password for change_password action")
) -> Dict[str, Any]:
    """User management operations.
    
    Actions:
    - list: List all users with pagination and filtering
    - get: Get details of a specific user
    - create: Create a new user
    - update: Update an existing user
    - delete: Delete a user
    - get_profile: Get user profile information
    - change_password: Change user password
    - reset_mfa_token: Reset user's MFA token
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.user")
    tool_logger.info(f"Starting user operation: {action}")
    await ctx.info(f"Starting user operation: {action}")
    
    try:
        await ctx.report_progress(0, 100, f"Starting user operation: {action}")
        
        write_actions = {"create", "update", "delete", "change_password", "reset_mfa_token"}
        
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
            # Enhanced progress reporting for listing users
            await ctx.report_progress(15, 100, "Starting user listing workflow...")
            await ctx.info("Starting user listing workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving user list...")
            await ctx.info(f"Retrieving users (page {page}, size {size})")
            
            result = await _list_users(auth, tenant_id=tenant_id, page=page, size=size)
            
            await ctx.report_progress(90, 100, "User listing completed, finalizing...")
            await ctx.info("User listing completed successfully")
            
        elif action == "get":
            # Enhanced progress reporting for getting user
            await ctx.report_progress(15, 100, "Starting user retrieval workflow...")
            await ctx.info("Starting user retrieval workflow...")
            
            if not user_id:
                await ctx.error("User ID is required for get action")
                raise ValueError("user_id is required for get action")
            
            await ctx.report_progress(25, 100, "Retrieving user details...")
            await ctx.info(f"Retrieving details for user: {user_id}")
            
            result = await _get_user(auth, user_id)
            
            await ctx.report_progress(90, 100, "User retrieval completed, finalizing...")
            await ctx.info("User retrieval completed successfully")
            
        elif action == "create":
            # Enhanced progress reporting for creating user
            await ctx.report_progress(15, 100, "Starting user creation workflow...")
            await ctx.info("Starting user creation workflow...")
            
            if not all([username, given_name, family_name, account_role, email_hints]):
                await ctx.error("Missing required fields for user creation")
                raise ValueError("Missing required fields for user creation")
            
            await ctx.report_progress(25, 100, "Validating user parameters...")
            await ctx.info(f"Creating user: {username}")
            
            result = await _create_user(auth, username=username, given_name=given_name, family_name=family_name, 
                                        phone_number=phone_number, password=password, account_role=account_role, 
                                        subscriber_groups=subscriber_groups, tenant_id=tenant_id, email_hints=email_hints)
            
            await ctx.report_progress(90, 100, "User creation completed, finalizing...")
            await ctx.info("User creation completed successfully")
            
        elif action == "update":
            # Enhanced progress reporting for updating user
            await ctx.report_progress(15, 100, "Starting user update workflow...")
            await ctx.info("Starting user update workflow...")
            
            if not user_id:
                await ctx.error("User ID is required for update action")
                raise ValueError("user_id is required for update action")
            
            await ctx.report_progress(25, 100, "Updating user details...")
            await ctx.info(f"Updating user: {user_id}")
            
            result = await _update_user(auth, user_id, given_name=given_name, family_name=family_name, phone_number=phone_number)
            
            await ctx.report_progress(90, 100, "User update completed, finalizing...")
            await ctx.info("User update completed successfully")
            
        elif action == "delete":
            # Enhanced progress reporting for deleting user
            await ctx.report_progress(15, 100, "Starting user deletion workflow...")
            await ctx.info("Starting user deletion workflow...")
            
            if not user_id:
                await ctx.error("User ID is required for delete action")
                raise ValueError("user_id is required for delete action")
            
            await ctx.report_progress(25, 100, "Deleting user...")
            await ctx.info(f"Deleting user: {user_id}")
            
            result = await _delete_user(auth, user_id)
            
            await ctx.report_progress(90, 100, "User deletion completed, finalizing...")
            await ctx.info("User deletion completed successfully")
            
        elif action == "get_profile":
            # Enhanced progress reporting for getting profile
            await ctx.report_progress(15, 100, "Starting profile retrieval workflow...")
            await ctx.info("Starting profile retrieval workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving user profile...")
            await ctx.info("Retrieving current user profile")
            
            result = await _get_user_profile(auth)
            
            await ctx.report_progress(90, 100, "Profile retrieval completed, finalizing...")
            await ctx.info("Profile retrieval completed successfully")
            
        elif action == "change_password":
            # Enhanced progress reporting for changing password
            await ctx.report_progress(15, 100, "Starting password change workflow...")
            await ctx.info("Starting password change workflow...")
            
            if not all([old_password, new_password]):
                await ctx.error("Old password and new password are required for change_password action")
                raise ValueError("old_password and new_password are required for change_password action")
            
            await ctx.report_progress(25, 100, "Changing password...")
            await ctx.info("Changing user password")
            
            result = await _change_password(auth, old_password, new_password)
            
            await ctx.report_progress(90, 100, "Password change completed, finalizing...")
            await ctx.info("Password change completed successfully")
            
        elif action == "reset_mfa_token":
            # Enhanced progress reporting for resetting MFA token
            await ctx.report_progress(15, 100, "Starting MFA token reset workflow...")
            await ctx.info("Starting MFA token reset workflow...")
            
            if not user_id:
                await ctx.error("User ID is required for reset_mfa_token action")
                raise ValueError("user_id is required for reset_mfa_token action")
            
            await ctx.report_progress(25, 100, "Resetting MFA token...")
            await ctx.info(f"Resetting MFA token for user: {user_id}")
            
            result = await _reset_mfa_token(auth, user_id, tenant_id=tenant_id)
            
            await ctx.report_progress(90, 100, "MFA token reset completed, finalizing...")
            await ctx.info("MFA token reset completed successfully")
            
        else:
            await ctx.error(f"Unknown action: {action}")
            raise ValueError(f"Unknown action: {action}")
            
        await ctx.report_progress(100, 100, f"Completed user operation: {action}")
        tool_logger.info(f"Completed user operation: {action}")
        await ctx.info(f"Completed user operation: {action}")
        return result
        
    except Exception as e:
        tool_logger.error(f"Error in user operation {action}: {e}")
        await ctx.error(f"Error in user operation {action}: {str(e)}")
        raise

async def _list_users(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List users in a DPoD tenant."""
    try:
        page = validate_optional_param(kwargs.get("page"), lambda x: validate_integer_param(x, "page", min_value=0), "page") or 0
        size = validate_optional_param(kwargs.get("size"), lambda x: validate_integer_param(x, "size", min_value=1, max_value=100), "size") or 50
        tenant_id = validate_optional_param(kwargs.get("tenant_id"), lambda x: validate_uuid(x, "Tenant ID"), "tenant_id")
        
        params = {"page": page, "size": size}
        if tenant_id:
            params["tenantId"] = tenant_id
            
        response = await auth.make_authenticated_request("GET", "/v1/users", params=params)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to list users: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _get_user(auth: DPoDAuth, user_id: str) -> Dict[str, Any]:
    """Get details of a specific user."""
    try:
        user_uuid = validate_uuid(user_id, "user_id")
        response = await auth.make_authenticated_request("GET", f"/v1/users/{user_uuid}")
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to get user: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _create_user(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Create a new user."""
    try:
        user_data = {
            "username": validate_string_param(kwargs.get("username"), "Username"),
            "givenName": validate_string_param(kwargs.get("given_name"), "Given Name"),
            "familyName": validate_string_param(kwargs.get("family_name"), "Family Name"),
            "accountRole": validate_string_param(kwargs.get("account_role"), "Account Role"),
            "emailHints": validate_json_data(kwargs.get("email_hints"), "Email Hints")
        }
        if kwargs.get("phone_number"):
            user_data["phoneNumber"] = kwargs.get("phone_number")
        if kwargs.get("password"):
            user_data["password"] = kwargs.get("password")
        if kwargs.get("subscriber_groups"):
            user_data["subscriberGroups"] = kwargs.get("subscriber_groups")
        if kwargs.get("tenant_id"):
            user_data["tenantId"] = validate_uuid(kwargs.get("tenant_id"), "Tenant ID")

        response = await auth.make_authenticated_request("POST", "/v1/users", json_data=user_data)
        
        if response.status_code != 201:
            return {"success": False, "error": f"Failed to create user: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _update_user(auth: DPoDAuth, user_id: str, **kwargs) -> Dict[str, Any]:
    """Update an existing user."""
    try:
        user_uuid = validate_uuid(user_id, "user_id")
        update_data = {}
        if kwargs.get("given_name"):
            update_data["givenName"] = validate_string_param(kwargs.get("given_name"), "Given Name")
        if kwargs.get("family_name"):
            update_data["familyName"] = validate_string_param(kwargs.get("family_name"), "Family Name")
        if kwargs.get("phone_number"):
            update_data["phoneNumber"] = kwargs.get("phone_number")

        if not update_data:
            return {"success": False, "error": "No fields to update"}

        response = await auth.make_authenticated_request("PATCH", f"/v1/users/{user_uuid}", json_data=update_data)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to update user: {response.status_code}", "details": response.text}

        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _delete_user(auth: DPoDAuth, user_id: str) -> Dict[str, Any]:
    """Delete a user."""
    try:
        user_uuid = validate_uuid(user_id, "user_id")
        response = await auth.make_authenticated_request("DELETE", f"/v1/users/{user_uuid}")
        
        if response.status_code != 204:
            return {"success": False, "error": f"Failed to delete user: {response.status_code}", "details": response.text}

        return {"success": True, "message": "User deleted successfully"}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _get_user_profile(auth: DPoDAuth) -> Dict[str, Any]:
    """Get the current user's profile."""
    try:
        response = await auth.make_authenticated_request("GET", "/v1/users/profile")
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to get user profile: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _change_password(auth: DPoDAuth, old_password: str, new_password: str) -> Dict[str, Any]:
    """Change the current user's password."""
    try:
        password_data = {
            "oldPassword": validate_string_param(old_password, "Old Password"),
            "newPassword": validate_string_param(new_password, "New Password")
        }
        response = await auth.make_authenticated_request("PATCH", "/v1/users/changePassword", json_data=password_data)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to change password: {response.status_code}", "details": response.text}
            
        return {"success": True, **response.json()}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _reset_mfa_token(auth: DPoDAuth, user_id: str, **kwargs) -> Dict[str, Any]:
    """Reset a user's MFA token."""
    try:
        user_uuid = validate_uuid(user_id, "user_id")
        tenant_id = validate_optional_param(kwargs.get("tenant_id"), lambda x: validate_uuid(x, "Tenant ID"), "tenant_id")
        
        params = {}
        if tenant_id:
            params["tenantId"] = tenant_id

        response = await auth.make_authenticated_request("POST", f"/v1/users/{user_uuid}/resetMfaToken", params=params)
        
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to reset MFA token: {response.status_code}", "details": response.text}

        return {"success": True, "message": "MFA token reset successfully"}

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
