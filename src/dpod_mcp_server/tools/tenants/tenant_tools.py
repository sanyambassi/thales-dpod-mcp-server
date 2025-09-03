"""Tenant Management Tools for DPoD MCP Server"""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_json_data, validate_integer_param
)
# Import helper functions from separate module to maintain FastMCP compliance
from .tenant_helpers import (
    _list_tenants, _get_tenant, _create_tenant, _update_tenant, _delete_tenant,
    _get_tenant_usage, _get_tenant_settings, _update_tenant_settings, _get_tenant_hierarchy,
    _get_tenant_admin, _get_tenant_children, _get_tenant_hostname, _get_tenant_quotas,
    _get_services_summary, _get_services_summary_file, _get_tenant_logo, _set_tenant_logo
)


async def manage_tenants(
    ctx: Context,
    action: str = Field(description="Operation to perform: list, get, create, update, delete, get_usage, get_settings, update_settings, get_hierarchy, get_admin, get_children, get_hostname, get_quotas, get_services_summary, get_services_summary_file, get_logo, set_logo"),
    tenant_id: Optional[str] = Field(default=None, description="UUID of tenant (required for get, update, delete, get_usage, get_admin, get_children, get_hostname, get_quotas, set_logo)"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    status: Optional[str] = Field(default=None, description="Status filter for list operations (active, inactive, suspended)"),
    parent_id: Optional[str] = Field(default=None, description="Parent tenant ID filter for list operation"),
    name: Optional[str] = Field(default=None, description="Tenant name for create/update operations"),
    company_name: Optional[str] = Field(default=None, description="Company name for tenant creation"),
    billing_address: Optional[Dict[str, str]] = Field(default=None, description="Billing address dictionary with street, city, state, postal_code, country"),
    account_type: Optional[str] = Field(default=None, description="Account type: subscriber or trial"),
    hostname: Optional[str] = Field(default=None, description="Unique hostname for tenant (e.g., company.dpod.local)"),
    admin_given_name: Optional[str] = Field(default=None, description="Admin first name for tenant creation"),
    admin_family_name: Optional[str] = Field(default=None, description="Admin last name for tenant creation"),
    admin_email: Optional[str] = Field(default=None, description="Admin email address for tenant creation"),
    admin_phone_number: Optional[str] = Field(default=None, description="Admin phone number for tenant creation"),
    department_name: Optional[str] = Field(default=None, description="Department name for tenant creation"),
    service_quota: Optional[int] = Field(default=None, description="Maximum number of services allowed for tenant"),
    admin_password: Optional[str] = Field(default=None, description="Admin password for tenant creation"),
    description: Optional[str] = Field(default=None, description="Description for tenant update operations"),
    configuration: Optional[Dict[str, Any]] = Field(default=None, description="Configuration object for tenant update operations"),
    force: bool = Field(default=False, description="Force deletion even if dependencies exist"),
    period: str = Field(default="30d", description="Usage period for get_usage (e.g., 7d, 30d, 90d)"),
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Settings dictionary for update_settings operation"),
    service_type: Optional[str] = Field(default=None, description="Service type filter for services summary operations"),
    forwarded_host: Optional[str] = Field(default=None, description="Original request host for logo operations"),
    logo_data: Optional[bytes] = Field(default=None, description="PNG image data for set_logo operation (240x96 pixels, max 512KB)")
) -> Dict[str, Any]:
    """Tenant management operations.
    
    Actions: 
    - list: List all tenants with pagination and filtering
    - get: Get details of a specific tenant
    - create: Create a new tenant 
    - update: Update an existing tenant
    - delete: Delete a tenant
    - get_usage: Get usage statistics for a tenant
    - get_settings: Get tenant settings
    - update_settings: Update tenant settings
    - get_hierarchy: Get tenant hierarchy tree
    - get_admin: Get tenant's primary administrator details
    - get_children: Get list of child tenant IDs
    - get_hostname: Get tenant hostname
    - get_quotas: Get tenant service quotas
    - get_services_summary: Get summary of active services
    - get_services_summary_file: Get CSV file of services summary
    - get_logo: Get tenant logo image
    - set_logo: Set tenant logo image
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    # Dual logging: server-side + MCP protocol
    tool_logger = logging.getLogger("dpod.tools.tenant")
    tool_logger.info(f"Starting tenant operation: {action}")
    await ctx.info(f"Starting tenant operation: {action}")
    
    try:
        await ctx.report_progress(0, 100, f"Starting tenant operation: {action}")
        
        # Define read-only vs write actions
        read_actions = {"list", "get", "get_usage", "get_settings", "get_hierarchy", "get_admin", 
                        "get_children", "get_hostname", "get_quotas", "get_services_summary", 
                        "get_services_summary_file"}
        write_actions = {"create", "update", "delete", "update_settings"}
        
        # Check read-only mode for write actions
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
            # Enhanced progress reporting for listing tenants
            await ctx.report_progress(15, 100, "Starting tenant listing workflow...")
            await ctx.info("Starting tenant listing workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving tenant list...")
            await ctx.info(f"Retrieving tenants (page {page}, size {size})")
            
            result = await _list_tenants(auth, page=page, size=size, status=status, parent_id=parent_id)
            
            await ctx.report_progress(90, 100, "Tenant listing completed, finalizing...")
            await ctx.info("Tenant listing completed successfully")
            
        elif action == "get":
            # Enhanced progress reporting for getting tenant
            await ctx.report_progress(15, 100, "Starting tenant retrieval workflow...")
            await ctx.info("Starting tenant retrieval workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for get action")
                raise ValueError("tenant_id required for get action")
            
            await ctx.report_progress(25, 100, "Retrieving tenant details...")
            await ctx.info(f"Retrieving details for tenant: {tenant_id}")
            
            result = await _get_tenant(auth, tenant_id=tenant_id)
            
            await ctx.report_progress(90, 100, "Tenant retrieval completed, finalizing...")
            await ctx.info("Tenant retrieval completed successfully")
            
        elif action == "create":
            # Enhanced progress reporting for creating tenant
            await ctx.report_progress(15, 100, "Starting tenant creation workflow...")
            await ctx.info("Starting tenant creation workflow...")
            
            if not all([name, company_name, billing_address, account_type, hostname, 
                       admin_given_name, admin_family_name, admin_email, admin_phone_number]):
                await ctx.error("Missing required fields for tenant creation")
                raise ValueError("Missing required fields for tenant creation")
            
            await ctx.report_progress(25, 100, "Validating tenant parameters...")
            await ctx.info(f"Creating tenant: {name}")
            
            result = await _create_tenant(
                auth, name=name, company_name=company_name, billing_address=billing_address,
                account_type=account_type, hostname=hostname, admin_given_name=admin_given_name,
                admin_family_name=admin_family_name, admin_email=admin_email,
                admin_phone_number=admin_phone_number, department_name=department_name,
                service_quota=service_quota, admin_password=admin_password
            )
            
            await ctx.report_progress(90, 100, "Tenant creation completed, finalizing...")
            await ctx.info("Tenant creation completed successfully")
            
        elif action == "update":
            # Enhanced progress reporting for updating tenant
            await ctx.report_progress(15, 100, "Starting tenant update workflow...")
            await ctx.info("Starting tenant update workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for update action")
                raise ValueError("tenant_id required for update action")
            
            await ctx.report_progress(25, 100, "Updating tenant details...")
            await ctx.info(f"Updating tenant: {tenant_id}")
            
            result = await _update_tenant(
                auth, tenant_id=tenant_id, name=name, description=description, configuration=configuration
            )
            
            await ctx.report_progress(90, 100, "Tenant update completed, finalizing...")
            await ctx.info("Tenant update completed successfully")
            
        elif action == "delete":
            # Enhanced progress reporting for deleting tenant
            await ctx.report_progress(15, 100, "Starting tenant deletion workflow...")
            await ctx.info("Starting tenant deletion workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for delete action")
                raise ValueError("tenant_id required for delete action")
            
            await ctx.report_progress(25, 100, "Deleting tenant...")
            await ctx.info(f"Deleting tenant: {tenant_id}")
            
            result = await _delete_tenant(auth, tenant_id=tenant_id, force=force)
            
            await ctx.report_progress(90, 100, "Tenant deletion completed, finalizing...")
            await ctx.info("Tenant deletion completed successfully")
            
        elif action == "get_usage":
            # Enhanced progress reporting for getting tenant usage
            await ctx.report_progress(15, 100, "Starting usage retrieval workflow...")
            await ctx.info("Starting usage retrieval workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for get_usage action")
                raise ValueError("tenant_id required for get_usage action")
            
            await ctx.report_progress(25, 100, "Retrieving tenant usage...")
            await ctx.info(f"Retrieving usage for tenant: {tenant_id} (period: {period})")
            
            result = await _get_tenant_usage(auth, tenant_id=tenant_id, period=period)
            
            await ctx.report_progress(90, 100, "Usage retrieval completed, finalizing...")
            await ctx.info("Usage retrieval completed successfully")
            
        elif action == "get_settings":
            # Enhanced progress reporting for getting tenant settings
            await ctx.report_progress(15, 100, "Starting settings retrieval workflow...")
            await ctx.info("Starting settings retrieval workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving tenant settings...")
            await ctx.info("Retrieving current tenant settings")
            
            result = await _get_tenant_settings(auth)
            
            await ctx.report_progress(90, 100, "Settings retrieval completed, finalizing...")
            await ctx.info("Settings retrieval completed successfully")
            
        elif action == "update_settings":
            # Enhanced progress reporting for updating tenant settings
            await ctx.report_progress(15, 100, "Starting settings update workflow...")
            await ctx.info("Starting settings update workflow...")
            
            if not settings:
                await ctx.error("Settings are required for update_settings action")
                raise ValueError("settings required for update_settings action")
            
            await ctx.report_progress(25, 100, "Updating tenant settings...")
            await ctx.info("Updating tenant settings")
            
            result = await _update_tenant_settings(auth, settings=settings)
            
            await ctx.report_progress(90, 100, "Settings update completed, finalizing...")
            await ctx.info("Settings update completed successfully")
            
        elif action == "get_hierarchy":
            # Enhanced progress reporting for getting tenant hierarchy
            await ctx.report_progress(15, 100, "Starting hierarchy retrieval workflow...")
            await ctx.info("Starting hierarchy retrieval workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving tenant hierarchy...")
            await ctx.info("Retrieving tenant hierarchy tree")
            
            result = await _get_tenant_hierarchy(auth)
            
            await ctx.report_progress(90, 100, "Hierarchy retrieval completed, finalizing...")
            await ctx.info("Hierarchy retrieval completed successfully")
        elif action == "get_admin":
            # Enhanced progress reporting for getting tenant admin
            await ctx.report_progress(15, 100, "Starting admin retrieval workflow...")
            await ctx.info("Starting admin retrieval workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for get_admin action")
                raise ValueError("tenant_id required for get_admin action")
            
            await ctx.report_progress(25, 100, "Retrieving tenant admin details...")
            await ctx.info(f"Retrieving admin details for tenant: {tenant_id}")
            
            result = await _get_tenant_admin(auth, tenant_id=tenant_id)
            
            await ctx.report_progress(90, 100, "Admin retrieval completed, finalizing...")
            await ctx.info("Admin retrieval completed successfully")
            
        elif action == "get_children":
            # Enhanced progress reporting for getting tenant children
            await ctx.report_progress(15, 100, "Starting children retrieval workflow...")
            await ctx.info("Starting children retrieval workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for get_children action")
                raise ValueError("tenant_id required for get_children action")
            
            await ctx.report_progress(25, 100, "Retrieving tenant children...")
            await ctx.info(f"Retrieving children for tenant: {tenant_id}")
            
            result = await _get_tenant_children(auth, tenant_id=tenant_id)
            
            await ctx.report_progress(90, 100, "Children retrieval completed, finalizing...")
            await ctx.info("Children retrieval completed successfully")
            
        elif action == "get_hostname":
            # Enhanced progress reporting for getting tenant hostname
            await ctx.report_progress(15, 100, "Starting hostname retrieval workflow...")
            await ctx.info("Starting hostname retrieval workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for get_hostname action")
                raise ValueError("tenant_id required for get_hostname action")
            
            await ctx.report_progress(25, 100, "Retrieving tenant hostname...")
            await ctx.info(f"Retrieving hostname for tenant: {tenant_id}")
            
            result = await _get_tenant_hostname(auth, tenant_id=tenant_id)
            
            await ctx.report_progress(90, 100, "Hostname retrieval completed, finalizing...")
            await ctx.info("Hostname retrieval completed successfully")
            
        elif action == "get_quotas":
            # Enhanced progress reporting for getting tenant quotas
            await ctx.report_progress(15, 100, "Starting quotas retrieval workflow...")
            await ctx.info("Starting quotas retrieval workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for get_quotas action")
                raise ValueError("tenant_id required for get_quotas action")
            
            await ctx.report_progress(25, 100, "Retrieving tenant quotas...")
            await ctx.info(f"Retrieving quotas for tenant: {tenant_id}")
            
            result = await _get_tenant_quotas(auth, tenant_id=tenant_id)
            
            await ctx.report_progress(90, 100, "Quotas retrieval completed, finalizing...")
            await ctx.info("Quotas retrieval completed successfully")
            
        elif action == "get_services_summary":
            # Enhanced progress reporting for getting services summary
            await ctx.report_progress(15, 100, "Starting services summary workflow...")
            await ctx.info("Starting services summary workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving services summary...")
            await ctx.info(f"Retrieving services summary (type: {service_type or 'all'})")
            
            result = await _get_services_summary(auth, service_type=service_type)
            
            await ctx.report_progress(90, 100, "Services summary completed, finalizing...")
            await ctx.info("Services summary completed successfully")
            
        elif action == "get_services_summary_file":
            # Enhanced progress reporting for getting services summary file
            await ctx.report_progress(15, 100, "Starting services summary file workflow...")
            await ctx.info("Starting services summary file workflow...")
            
            await ctx.report_progress(25, 100, "Generating services summary file...")
            await ctx.info(f"Generating services summary file (type: {service_type or 'all'})")
            
            result = await _get_services_summary_file(auth, service_type=service_type)
            
            await ctx.report_progress(90, 100, "Services summary file completed, finalizing...")
            await ctx.info("Services summary file completed successfully")
            
        elif action == "get_logo":
            # Enhanced progress reporting for getting tenant logo
            await ctx.report_progress(15, 100, "Starting logo retrieval workflow...")
            await ctx.info("Starting logo retrieval workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving tenant logo...")
            await ctx.info(f"Retrieving logo for tenant: {tenant_id or 'current'}")
            
            result = await _get_tenant_logo(auth, tenant_id=tenant_id, forwarded_host=forwarded_host)
            
            await ctx.report_progress(90, 100, "Logo retrieval completed, finalizing...")
            await ctx.info("Logo retrieval completed successfully")
            
        elif action == "set_logo":
            # Enhanced progress reporting for setting tenant logo
            await ctx.report_progress(15, 100, "Starting logo setting workflow...")
            await ctx.info("Starting logo setting workflow...")
            
            if not tenant_id:
                await ctx.error("Tenant ID is required for set_logo action")
                raise ValueError("tenant_id required for set_logo action")
            if not logo_data:
                await ctx.error("Logo data is required for set_logo action")
                raise ValueError("logo_data required for set_logo action")
            
            await ctx.report_progress(25, 100, "Setting tenant logo...")
            await ctx.info(f"Setting logo for tenant: {tenant_id}")
            
            result = await _set_tenant_logo(auth, tenant_id=tenant_id, logo_data=logo_data)
            
            await ctx.report_progress(90, 100, "Logo setting completed, finalizing...")
            await ctx.info("Logo setting completed successfully")
            
        else:
            await ctx.error(f"Unknown action: {action}")
            raise ValueError(f"Unknown action: {action}")
        
        await ctx.report_progress(100, 100, f"Completed tenant operation: {action}")
        tool_logger.info(f"Completed tenant operation: {action}")
        await ctx.info(f"Completed tenant operation: {action}")
        return result
        
    except Exception as e:
        tool_logger.error(f"Error in tenant operation {action}: {e}")
        await ctx.error(f"Error in tenant operation {action}: {str(e)}")
        raise 