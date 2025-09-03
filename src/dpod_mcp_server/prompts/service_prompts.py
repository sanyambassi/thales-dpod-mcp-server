#!/usr/bin/env python3
"""DPoD Service Prompts"""

from typing import Optional
from fastmcp import Context
from pydantic import Field

async def get_service_logs(
    start_date: str = Field(description="Start date for logs (REQUIRED - supports: YYYY-MM-DD or YYYY/MM/DD)"),
    end_date: str = Field(description="End date for logs (REQUIRED - supports: YYYY-MM-DD or YYYY/MM/DD)"),
    service_name: Optional[str] = Field(default=None, description="Service name to get logs for"),
    source_filter: Optional[str] = Field(default=None, description="Source filter ('cdsp', 'thales/cloudhsm/123456789', or service name)"),
    action_filter: Optional[str] = Field(default=None, description="Action filter (e.g., 'Create Key', 'LUNA_VERIFY', 'Delete User')"),
    status_filter: Optional[str] = Field(default=None, description="Status filter (e.g., 'success', 'LUNA_RET_OK', 'LUNA_RET_BAD_PARAMETER')"),
    ctx: Context = None
) -> str:
    """Get comprehensive audit logs for a DPoD service within a date range.
    
    Usage Options:
    1. By Service Name: Provide service_name (auto-detects source and resource_id)
    2. By Source: Provide source_filter with:
       - 'cdsp' for CDSP services
       - 'thales/cloudhsm/123456789' for HSM services (with partition ID)
       - Service name (auto-detects source and resource_id)
    3. No service filter: Only provide dates to get logs for all services
    
    All parameters except start_date and end_date are optional.
    """
    
    # Build filter parameters string
    filter_params = []
    if source_filter:
        filter_params.append(f"source_filter='{source_filter}'")
    if action_filter:
        filter_params.append(f"action_filter='{action_filter}'")
    if status_filter:
        filter_params.append(f"status_filter='{status_filter}'")
    
    filter_string = f"\n4. Additional filters: {', '.join(filter_params)}" if filter_params else ""
    
    # Determine the service identifier for the workflow description
    if service_name:
        service_identifier = f"service '{service_name}'"
        service_param = f"service_name='{service_name}'"
    elif source_filter:
        service_identifier = f"source '{source_filter}'"
        service_param = f"source_filter='{source_filter}'"
    else:
        service_identifier = "all services"
        service_param = "no service filter (logs for all services)"
    
    return f"""Use the manage_audit_logs tool to retrieve logs for {service_identifier}.

Execute this workflow:
1. Call manage_audit_logs with action='get_logs'
2. Use start_date='{start_date}' and end_date='{end_date}' for the date range
3. {service_param}{filter_string}
4. IMPORTANT: Only include filter parameters that have actual values. If a filter parameter is None, null, empty, or not specified, DO NOT include it in the tool call.
5. The tool will automatically:
   - Generate an export job (with all filters: service/source, date range, action, status)
   - Wait for completion
   - Download and analyze the logs
   - Return a comprehensive summary

This provides a complete audit trail for {service_identifier} from {start_date} to {end_date}.

            Enhanced Features:
            - Flexible service identification: Use either service_name (auto-detects source/resource_id) or source_filter
            - ISO date formats: Supports YYYY-MM-DD or YYYY/MM/DD with automatic timestamp conversion
            - Auto-conversion: Automatically converts dates to proper format (adds T00:00:00Z for start, T23:59:59Z for end)
            - Service-specific filtering: Action and status values vary by service type
              * CDSP actions: "Create Key", "Delete User", "Update Policy"
              * HSM actions: "LUNA_VERIFY", "LUNA_CANCEL_CRYPTO_OPERATION", "LUNA_CREATE_OBJECT"
              * CDSP status: "success", "failure"
              * HSM status: "LUNA_RET_OK", "LUNA_RET_BAD_PARAMETER", "LUNA_RET_CRYPTO_ERROR"
            - API-level filtering: All filters applied during export generation for efficiency
            
            Usage Examples:
            - By service name: service_name="MyHSMService", start_date="2025-04-01", end_date="2025-04-30"
            - By CDSP source: source_filter="cdsp", start_date="2025/04/01", end_date="2025/04/30"
            - By HSM source: source_filter="thales/cloudhsm/123456789", start_date="2025-04-01", end_date="2025-04-30"
            - By service name via source: source_filter="MyHSMService", start_date="2025/04/01", end_date="2025/04/30"
            - All services: start_date="2025-04-01", end_date="2025-04-30" (no service filter)
            
            CRITICAL: When calling the tool, only include parameters that have actual values. 
            Do NOT include action_filter, status_filter, or source_filter if they are None, null, empty, or not specified.
            Only include the parameters that were explicitly provided by the user.
            
            Note: Date formats supported are YYYY-MM-DD or YYYY/MM/DD. Simple dates automatically get appropriate timestamps."""


async def create_hsm_service(
    service_type: str = Field(description="Type of HSM service. Available types: key_vault, hsm_key_export, ms_sql_server, java_code_sign, ms_authenticode, ms_adcs, pki_private_key_protection, digital_signing, oracle_tde_database, hyperledger, luna_dke, cyberark_digital_vault, luna_hsm_backup, payshield_na, payshield_eu, p2pe, ctaas, codesign-secure, kt_ses, kt_pki, garasign, pkiaas, suredrop, a24_hsm, ascertia_pki, codesign, pk_sign_cloud, kf_command, pk_sign_sw, ven_platform, signpath"),
    service_name: str = Field(description="Name for the service (4-45 characters)"),
    service_plan: str = Field(description="Service plan (e.g., single_hsm, dual_hsm, multi_hsm, trial, standard)"),
    device_type: str = Field(description="Device type (cryptovisor or cryptovisor_fips, it is optional and defaults to cryptovisor_fips)", default="cryptovisor_fips"),
    ctx: Context = None
) -> str:
    """Create a new HSM service with comprehensive configuration."""
    
    return f"""Use the manage_services tool to create a new HSM service.

Execute this workflow:
1. Call manage_services with action='create_service_instance'
2. Set parameters:
   - name: '{service_name}'
   - service_type: '{service_type}'
   - service_plan: '{service_plan}'
   - device_type: '{device_type}'
3. The tool will automatically include deviceType in configuration
4. Monitor provisioning status and return service details
5. Verify the service is active and ready for use

Creating {service_type} HSM service '{service_name}' with {service_plan} plan and {device_type} device type.

Note: Choose the most specific service type for your use case."""


async def create_ctaas_service(
    cluster: str = Field(description="Cluster for the CTAAS service deployment (e.g., gcp-europe-west3, gcp-us-east1)"),
    service_name: str = Field(description="Name for the service (4-45 characters)"),
    initial_admin_password: str = Field(description="Initial admin password for the CTAAS service (minimum 8 characters)"),
    service_plan: str = Field(description="Service plan (e.g., Tenant)", default="Tenant"),
    ctx: Context = None
) -> str:
    """Create a new CTAAS service in the specified cluster."""
    
    return f"""Use the manage_services tool to create a new CTAAS service.

Execute this workflow:
1. Call manage_services with action='create_service_instance'
2. Set parameters:
   - name: '{service_name}'
   - service_type: 'ctaas'
   - service_plan: '{service_plan}'
   - configuration: {{'cluster': '{cluster}', 'initial_admin_password': '{initial_admin_password}'}}
3. The tool will automatically set serviceType='ctaas' and servicePlan='Tenant' if not specified
4. Monitor the provisioning status
5. Return the service details and verify it's active
6. Confirm the service is ready for CipherTrust Data Security Platform operations

Creating CTAAS service '{service_name}' in {cluster} cluster with {service_plan} plan and initial admin password configured.

Note: Supported clusters include gcp-europe-west3 and gcp-us-east1. The serviceType and servicePlan are automatically set for CTAAS services."""


async def create_hsm_client(
    service_name: str = Field(description="Name of the HSM service to bind the client to (required)"),
    client_name: str = Field(description="Name for the client (1-64 characters, must be unique for the service)"),
    download_path: Optional[str] = Field(description="Directory path where the client configuration file should be saved (optional, defaults to system temp directory)", default=None),
    os_type: str = Field(description="Operating system type (linux or windows)", default="linux"),
    ctx: Context = None
) -> str:
    """Create and download an HSM service client configuration file to a specified location."""
    
    return f"""Use the manage_services tool to create an HSM service client and download the configuration file.

Execute this workflow:
1. Call manage_services with action='bind_client'
2. Set parameters:
   - service_id: '{service_name}' (service name or UUID)
   - client_name: '{client_name}'
   - os_type: '{os_type}'{f'''
   - download_path: '{download_path}''' if download_path else ''}
3. The tool will:
   - Bind the client to the HSM service
   - Download the client configuration file
   - Save it to: {download_path if download_path else 'system temp directory'}
4. Return the file path and client details

Creating HSM client '{client_name}' for service '{service_name}' on {os_type} platform.
Configuration file will be saved to: {download_path if download_path else 'system temp directory'}

Note: The client configuration file contains certificates and connection details needed to connect to the HSM service.""" 