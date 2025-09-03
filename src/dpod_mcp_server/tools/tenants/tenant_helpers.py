#!/usr/bin/env python3
"""
Tenant Management Helper Functions for DPoD MCP Server

Internal helper functions separated from main tools to maintain FastMCP compliance.
"""

import logging
from typing import Dict, Any, Optional
from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_json_data, validate_integer_param
)


async def _list_tenants(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List all tenants in the DPoD account.
    
    Returns a paginated list of tenants with the following fields:
    - content: The array of tenants
    - number: Current page number
    - size: Number of elements in this response
    - totalElements: Total number of elements
    - totalPages: Total number of pages
    """
    try:
        # Validate parameters
        page = validate_optional_param(
            kwargs.get("page"),
            lambda x: validate_integer_param(x, "page", min_value=0),
            "page"
        ) or 0
        
        size = validate_optional_param(
            kwargs.get("size"),
            lambda x: validate_integer_param(x, "size", min_value=1, max_value=100),
            "size"
        ) or 50
        
        status = validate_optional_param(
            kwargs.get("status"),
            lambda x: validate_string_param(x, "status", min_length=1, max_length=50),
            "status"
        )
        
        parent_id = validate_optional_param(
            kwargs.get("parent_id"),
            lambda x: validate_uuid(x, "Parent ID"),
            "parent_id"
        )
        
        # Prepare query parameters
        params = {"page": page, "size": size}
        if status:
            params["status"] = status
        if parent_id:
            params["parentId"] = parent_id
        
        # Make API request - using swagger spec base path /v1
        response = await auth.make_authenticated_request(
            "GET", 
            "/v1/tenants",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to list tenants: {response.status_code}",
                "details": response.text
            }
        
        tenants_data = response.json()
        
        return {
            "success": True,
            "content": tenants_data.get("content", []),
            "number": tenants_data.get("number", page),
            "size": tenants_data.get("size", len(tenants_data.get("content", []))),
            "totalElements": tenants_data.get("totalElements", 0),
            "totalPages": tenants_data.get("totalPages", 0)
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get details of a specific tenant by ID.
    
    Returns tenant details including ID, name, company information,
    billing address, account status, and other tenant-specific fields.
    """
    try:
        # Validate parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        
        # Make API request - using swagger spec endpoint
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tenants/{tenant_id}"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant: {response.status_code}",
                "details": response.text
            }
        
        # Return the tenant data directly as per API spec
        return {
            "success": True,
            **response.json()
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _create_tenant(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Create a new tenant."""
    try:
        # Validate required parameters
        name = validate_string_param(kwargs.get("name"), "Name", min_length=1, max_length=100)
        company_name = validate_string_param(kwargs.get("company_name"), "Company Name", min_length=1, max_length=100)
        billing_address = validate_json_data(kwargs.get("billing_address"), "Billing Address")
        account_type = validate_string_param(kwargs.get("account_type"), "Account Type", min_length=1, max_length=20)
        hostname = validate_string_param(kwargs.get("hostname"), "Hostname", min_length=1, max_length=100)
        admin_given_name = validate_string_param(kwargs.get("admin_given_name"), "Admin Given Name", min_length=1, max_length=50)
        admin_family_name = validate_string_param(kwargs.get("admin_family_name"), "Admin Family Name", min_length=1, max_length=50)
        admin_email = validate_string_param(kwargs.get("admin_email"), "Admin Email", min_length=1, max_length=100)
        admin_phone_number = validate_string_param(kwargs.get("admin_phone_number"), "Admin Phone Number", min_length=1, max_length=20)
        
        # Validate optional parameters
        department_name = validate_optional_param(
            kwargs.get("department_name"),
            lambda x: validate_string_param(x, "Department Name", min_length=1, max_length=100),
            "department_name"
        )
        
        service_quota = validate_optional_param(
            kwargs.get("service_quota"),
            lambda x: validate_integer_param(x, "Service Quota", min_value=1),
            "service_quota"
        )
        
        admin_password = validate_optional_param(
            kwargs.get("admin_password"),
            lambda x: validate_string_param(x, "Admin Password", min_length=8, max_length=100),
            "admin_password"
        )
        
        # Prepare tenant data
        tenant_data = {
            "name": name,
            "companyName": company_name,
            "billingAddress": billing_address,
            "accountType": account_type,
            "hostname": hostname,
            "admin": {
                "givenName": admin_given_name,
                "familyName": admin_family_name,
                "email": admin_email,
                "phoneNumber": admin_phone_number
            }
        }
        
        if department_name:
            tenant_data["departmentName"] = department_name
        if service_quota:
            tenant_data["serviceQuota"] = service_quota
        if admin_password:
            tenant_data["admin"]["password"] = admin_password
        
        # Make API request
        response = await auth.make_authenticated_request(
            "POST",
            "/v1/tenants",
            json_data=tenant_data
        )
        
        if response.status_code not in [200, 201]:
            return {
                "success": False,
                "error": f"Failed to create tenant: {response.status_code}",
                "details": response.text
            }
        
        created_tenant = response.json()
        
        return {
            "success": True,
            "tenant": created_tenant,
            "message": "Tenant created successfully"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_tenant(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Update an existing tenant."""
    try:
        # Validate required parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        
        # Validate optional parameters
        name = validate_optional_param(
            kwargs.get("name"),
            lambda x: validate_string_param(x, "Name", min_length=1, max_length=100),
            "name"
        )
        
        description = validate_optional_param(
            kwargs.get("description"),
            lambda x: validate_string_param(x, "Description", min_length=1, max_length=500),
            "description"
        )
        
        configuration = validate_optional_param(
            kwargs.get("configuration"),
            lambda x: validate_json_data(x, "Configuration"),
            "configuration"
        )
        
        # Prepare update data
        update_data = {}
        if name:
            update_data["name"] = name
        if description:
            update_data["description"] = description
        if configuration:
            update_data["configuration"] = configuration
        
        if not update_data:
            return {"success": False, "error": "No fields to update"}
        
        # Make API request
        response = await auth.make_authenticated_request(
            "PUT",
            f"/v1/tenants/{tenant_id}",
            json_data=update_data
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to update tenant: {response.status_code}",
                "details": response.text
            }
        
        updated_tenant = response.json()
        
        return {
            "success": True,
            "tenant": updated_tenant,
            "message": "Tenant updated successfully"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _delete_tenant(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Delete a tenant."""
    try:
        # Validate required parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        force = kwargs.get("force", False)
        
        # Prepare query parameters
        params = {}
        if force:
            params["force"] = "true"
        
        # Make API request
        response = await auth.make_authenticated_request(
            "DELETE",
            f"/v1/tenants/{tenant_id}",
            params=params
        )
        
        if response.status_code not in [200, 202, 204]:
            return {
                "success": False,
                "error": f"Failed to delete tenant: {response.status_code}",
                "details": response.text
            }
        
        return {
            "success": True,
            "message": "Tenant deleted successfully"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_usage(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get usage statistics for a tenant."""
    try:
        # Validate required parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        period = validate_string_param(kwargs.get("period"), "Period", min_length=1, max_length=10)
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tenants/{tenant_id}/usage",
            params={"period": period}
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant usage: {response.status_code}",
                "details": response.text
            }
        
        usage_data = response.json()
        
        return {
            "success": True,
            "usage": usage_data,
            "tenant_id": tenant_id,
            "period": period
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_settings(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get tenant settings.
    
    Returns settings including automaticTenantOnboarding status.
    """
    try:
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/tenants/settings"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant settings: {response.status_code}",
                "details": response.text
            }
        
        # Return the settings directly as per API spec
        return {
            "success": True,
            **response.json()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_tenant_settings(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Update tenant settings.
    
    Supports enabling/disabling automatic tenant onboarding via PATCH operation.
    """
    try:
        # Validate required parameters
        settings = validate_json_data(kwargs.get("settings"), "Settings")
        
        # Make API request - use PATCH as specified in the API spec
        response = await auth.make_authenticated_request(
            "PATCH",
            "/v1/tenants/settings",
            json_data=settings
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to update tenant settings: {response.status_code}",
                "details": response.text
            }
        
        # Return settings directly as per API spec
        return {
            "success": True,
            **response.json()
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_hierarchy(auth: DPoDAuth) -> Dict[str, Any]:
    """Get tenant hierarchy.
    
    Returns a tree representation of the Parent Tenant's Child Tenants.
    Only includes Tenants that have a valid account status (active or disabled).
    """
    try:
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/tenants/hierarchy"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant hierarchy: {response.status_code}",
                "details": response.text
            }
        
        # Return the hierarchy data directly as per API spec
        return {
            "success": True,
            **response.json()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_admin(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get details for a tenant's primary administrator.
    
    Returns details for the identified Tenant's Primary Administrator including
    givenName, familyName, phoneNumber, and email.
    """
    try:
        # Validate parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tenants/{tenant_id}/admin"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant admin: {response.status_code}",
                "details": response.text
            }
        
        # Return the admin data directly as per API spec
        return {
            "success": True,
            **response.json()
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_children(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Return a list of a Parent Tenant's Child Tenant IDs.
    
    Returns a list of the Child Tenant UUIDs under the identified Parent Tenant.
    """
    try:
        # Validate parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tenants/{tenant_id}/children"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant children: {response.status_code}",
                "details": response.text
            }
        
        # Return the list of child tenant IDs
        return {
            "success": True,
            "children": response.json()
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_hostname(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Return a tenant hostname.
    
    Returns hostname of the identified Tenant.
    """
    try:
        # Validate parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tenants/{tenant_id}/hostname"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant hostname: {response.status_code}",
                "details": response.text
            }
        
        # Return the hostname string
        return {
            "success": True,
            "hostname": response.text
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_quotas(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Return the service quota information for a tenant.
    
    Returns the service quota information of the identified Tenant.
    """
    try:
        # Validate parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tenants/{tenant_id}/quotas"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant quotas: {response.status_code}",
                "details": response.text
            }
        
        # Return the quota information directly as per API spec
        return {
            "success": True,
            **response.json()
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_services_summary(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Return the service summary.
    
    Returns a list of all the active Services. The list is composed of all the active
    Services belonging to the Child Tenants.
    """
    try:
        # Validate optional parameters
        service_type = validate_optional_param(
            kwargs.get("service_type"),
            lambda x: validate_string_param(x, "Service Type", min_length=1, max_length=100),
            "service_type"
        )
        
        # Prepare query parameters
        params = {}
        if service_type:
            params["serviceType"] = service_type
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/tenants/servicesSummary",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get services summary: {response.status_code}",
                "details": response.text
            }
        
        # Return the services summary data
        return {
            "success": True,
            "summary": response.json()
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_services_summary_file(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Return the service summary file.
    
    Returns a summary file of all the active Services belonging to the Child Tenants.
    """
    try:
        # Validate optional parameters
        service_type = validate_optional_param(
            kwargs.get("service_type"),
            lambda x: validate_string_param(x, "Service Type", min_length=1, max_length=100),
            "service_type"
        )
        
        # Prepare query parameters
        params = {}
        if service_type:
            params["serviceType"] = service_type
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/tenants/servicesSummaryFile",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get services summary file: {response.status_code}",
                "details": response.text
            }
        
        # Return the CSV content
        return {
            "success": True,
            "file_content": response.text,
            "content_type": response.headers.get("Content-Type", "text/csv")
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tenant_logo(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Return a tenant logo.
    
    Returns the logo image linked to the identified Tenant. If none exists or the current
    Tenant is not a Service Provider, the Parent Tenant's logo is returned.
    """
    try:
        # Validate parameters if tenant_id is provided
        tenant_id = validate_optional_param(
            kwargs.get("tenant_id"),
            lambda x: validate_uuid(x, "tenant_id"),
            "tenant_id"
        )
        
        # Make API request to the appropriate endpoint
        if tenant_id:
            url = f"/v1/tenants/{tenant_id}/logo"
        else:
            url = "/v1/tenants/logo"
            
        # Set headers
        headers = {}
        if kwargs.get("forwarded_host"):
            headers["X-Forwarded-Host"] = kwargs.get("forwarded_host")
        
        # Make API request expecting binary image data
        response = await auth.make_authenticated_request(
            "GET",
            url,
            headers=headers
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tenant logo: {response.status_code}",
                "details": response.text
            }
        
        # Return the logo binary data
        return {
            "success": True,
            "logo_data": response.content,
            "content_type": response.headers.get("Content-Type", "image/png")
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _set_tenant_logo(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Set a tenant logo.
    
    Set the Service Provider Tenant's logo image. The image must be a PNG file,
    512 KB maximum and exactly 240x96 pixels.
    """
    try:
        # Validate required parameters
        tenant_id = validate_uuid(kwargs.get("tenant_id"), "tenant_id")
        logo_data = kwargs.get("logo_data")
        
        if not logo_data:
            return {"success": False, "error": "Logo image data is required"}
        
        # Make API request
        headers = {"Content-Type": "image/png"}
        response = await auth.make_authenticated_request(
            "PUT",
            f"/v1/tenants/{tenant_id}/logo",
            headers=headers,
            data=logo_data
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to set tenant logo: {response.status_code}",
                "details": response.text
            }
        
        return {
            "success": True,
            "message": "Tenant logo updated successfully"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)} 