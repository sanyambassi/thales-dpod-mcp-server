"""Service Management Tools for DPoD MCP Server"""

import logging
import asyncio
import os
import tempfile
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field
from uuid import UUID

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_json_data, validate_integer_param,
    validate_create_params, validate_service_name, validate_service_plan
)
from ...core.logging_utils import get_tool_logger

# Enhanced helper function with AI guidance
def get_service_creation_example(service_type: str = None) -> dict:
    """Get complete example for creating different service types.
    
    ⚠️  AI ASSISTANT WARNING ⚠️
    Before using this function, ensure you have selected the CORRECT service type
    by thoroughly reading tile descriptions and matching user requirements.
    
    IMPORTANT: These examples show the EXACT API call structure.
    - tenant_id, subscriber_id, and subscriber_groups are NOT needed
    - They are automatically handled by the DPoD (Data Protection on Demand) platform
    - Only the parameters shown below are required/optional
    
    For MCP tool usage:
    - Use 'configuration' parameter to pass createParams content
    - For HSM services, you can either:
      1. Include deviceType in configuration: {"deviceType": "cryptovisor_fips"}
      2. Use device_type parameter: device_type="cryptovisor_fips"
      3. Omit both - defaults to "cryptovisor"
    
    Args:
        service_type: The service type to get example for
        
    Returns:
        Complete service creation example with correct parameter placement
    """
    examples = {
        "ctaas": {
            "name": "My-CipherTrust-Service",
            "serviceType": "ctaas",
            "servicePlan": "Tenant",
            "createParams": {
                "cluster": "gcp-us-east1",
                "initial_admin_password": "SecurePassword123!"
            },
            "ai_guidance": "CipherTrust Data Security Platform - for key management and data encryption. REQUIRED: cluster, initial_admin_password. OPTIONAL: tenant_rot_anchor (only include if you want to override the default 'hsmod')."
        },
        "key_vault": {
            "name": "My-Luna-Cloud-HSM-Service",
            "serviceType": "key_vault",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "Use for GENERAL cryptographic operations, NOT for specific integrations or backup"
        },
        "hsm": {
            "name": "My-Luna-Cloud-HSM-Service", 
            "serviceType": "hsm",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "Use for GENERAL cryptographic operations, NOT for specific integrations or backup"
        },
        "luna_hsm_backup": {
            "name": "My-Backup-HSM-Service",
            "serviceType": "luna_hsm_backup",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for backing up on-premises Luna HSMs to the cloud"
        },
        "ms_sql_server": {
            "name": "My-SQL-Server-HSM-Service",
            "serviceType": "ms_sql_server",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for Microsoft SQL Server cryptographic operations"
        },
        "oracle_tde_database": {
            "name": "My-Oracle-TDE-Service",
            "serviceType": "oracle_tde_database",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for Oracle TDE database encryption"
        },
        "pki_private_key_protection": {
            "name": "My-PKI-Service",
            "serviceType": "pki_private_key_protection",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for PKI Certificate Authority private key protection"
        },
        "digital_signing": {
            "name": "My-Digital-Signing-Service",
            "serviceType": "digital_signing", 
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for digital signing of software and firmware packages"
        },
        "salesforce_key_broker": {
            "name": "My-Salesforce-KeyBroker",
            "serviceType": "salesforce_key_broker",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for Salesforce Shield key management (currently disabled)"
        },
        "hyperledger": {
            "name": "My-Hyperledger-Service",
            "serviceType": "hyperledger",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for Hyperledger Fabric blockchain cryptographic operations"
        },
        "payshield_na": {
            "name": "My-PayShield-NA-Service",
            "serviceType": "payshield_na",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for payment processing in North America region"
        },
        "payshield_eu": {
            "name": "My-PayShield-EU-Service",
            "serviceType": "payshield_eu",
            "servicePlan": "single_hsm",
            "createParams": {
                "deviceType": "cryptovisor"
            },
            "ai_guidance": "SPECIFICALLY for payment processing in Europe region"
        }
    }
    
    if service_type:
        if service_type in examples:
            return examples[service_type]
        else:
            return {
                "error": f"Service type '{service_type}' not found in examples",
                "available_types": list(examples.keys()),
                "ai_guidance": "Use manage_tiles tool to search for available service types and their descriptions"
            }
    
    return {
        "message": "Complete example for creating different service types",
        "examples": examples,
        "ai_guidance": "Choose the service type that MOST SPECIFICALLY matches your use case. Avoid generic services when specialized ones exist."
    }


async def _resolve_service_identifier(auth: DPoDAuth, service_identifier: str, operation: str = "operation") -> str:
    """Smart utility function that converts service names to UUIDs.
    
    This function automatically handles both UUID and name-based service identification:
    - If a UUID is provided, it validates and returns it directly
    - If a name is provided, it searches for the service and extracts the UUID
    - Provides clear error messages when services aren't found
    
    Args:
        auth: DPoDAuth instance for API calls
        service_identifier: Either a UUID or service name
        operation: Description of the operation being performed (for error messages)
        
    Returns:
        Valid UUID string for the service
        
    Raises:
        ValueError: If the service cannot be found or the identifier is invalid
    """
    if not service_identifier:
        raise ValueError(f"Service identifier is required for {operation}")
    
    tool_logger = get_tool_logger("service")
    
    # Check if it's a UUID or a name
    is_uuid = False
    try:
        if len(service_identifier) == 36 and '-' in service_identifier:
            UUID(service_identifier)
            is_uuid = True
            tool_logger.info(f"Using provided UUID for {operation}: {service_identifier}")
            return service_identifier
    except ValueError:
        tool_logger.info(f"Identifier '{service_identifier}' is not a valid UUID, treating as service name")
    
    # If it's not a valid UUID, we need to find the service by name
    if not is_uuid:
        tool_logger.info(f"Searching for service by name: '{service_identifier}'")
        # Use /v1/service_instances to get provisioned services
        search_result = await _list_service_instances(auth, page=0, size=100, status=None, service_type=None)
        service_list = search_result.get("instances", [])
        found_service = None
        # First, try exact match (case-sensitive)
        for instance in service_list:
            instance_name = instance.get("name")
            if instance_name == service_identifier:
                found_service = instance
                break
        # If not found, try case-insensitive match
        if not found_service:
            for instance in service_list:
                instance_name = instance.get("name")
                if instance_name and instance_name.lower() == service_identifier.lower():
                    found_service = instance
                    break
        if found_service:
            # Found the service, use its UUID
            service_uuid = found_service.get("service_id")
            if not service_uuid:
                raise ValueError(f"Found service by name '{service_identifier}' but could not get UUID from response")
            tool_logger.info(f"Found service '{service_identifier}' with UUID: {service_uuid}")
            return service_uuid
        else:
            # Service not found by name
            available_services = [i.get('name') for i in service_list]
            tool_logger.info(f"Service '{service_identifier}' not found. Available services: {available_services}")
            if available_services:
                raise ValueError(f"Service not found by name '{service_identifier}'. Available services: {available_services}")
            else:
                raise ValueError(f"Service not found by name '{service_identifier}'. No services found in account.")
    
    # This should never be reached, but just in case
    raise ValueError(f"Unable to resolve service identifier: {service_identifier}")


async def _resolve_client_identifier(auth: DPoDAuth, service_id: str, client_identifier: str, operation: str = "operation") -> str:
    """Smart utility function that converts client names to UUIDs."""
    if not client_identifier:
        raise ValueError(f"Client identifier is required for {operation}")
    # If it's already a UUID, return it
    try:
        if len(client_identifier) == 36 and '-' in client_identifier:
            UUID(client_identifier)
            return client_identifier
    except Exception:
        pass
    # Otherwise, look up by name
    clients_result = await _list_service_clients(auth, service_id=service_id)
    if not clients_result.get("success"):
        raise ValueError(f"Failed to list service clients: {clients_result.get('error')}")
    for client in clients_result.get("clients", []):
        if client.get("name") == client_identifier:
            return client.get("id") or client.get("clientId")
    raise ValueError(f"Client '{client_identifier}' not found for service '{service_id}'")


def validate_service_selection(user_request: str, selected_service_type: str, available_services: list) -> dict:
    """Validate that the selected service type matches the user's request.
    
    ⚠️  AI ASSISTANT VALIDATION FUNCTION ⚠️
    Use this function to validate your service selection before proceeding.
    
    Args:
        user_request: The user's original request/requirement
        selected_service_type: The service type you're planning to use
        available_services: List of available services from manage_tiles
        
    Returns:
        Validation result with recommendations
    """
    validation_result = {
        "valid": False,
        "warnings": [],
        "recommendations": [],
        "selected_service": None,
        "better_alternatives": []
    }
    
    # Find the selected service details
    selected_service = None
    for service in available_services:
        if service.get("shortCode") == selected_service_type or service.get("id") == selected_service_type:
            selected_service = service
            break
    
    if not selected_service:
        validation_result["warnings"].append(f"Selected service type '{selected_service_type}' not found in available services")
        return validation_result
    
    validation_result["selected_service"] = selected_service
    
    # Check for common mistakes
    common_mistakes = {
        "backup": {
            "wrong_choice": ["key_vault", "hsm"],
            "correct_choice": "luna_hsm_backup",
            "explanation": "For backup operations, use 'Luna HSM Backup' not general HSM services"
        },
        "sql server": {
            "wrong_choice": ["key_vault", "hsm", "luna_hsm_backup"],
            "correct_choice": "ms_sql_server",
            "explanation": "For SQL Server encryption, use 'Luna Cloud HSM for Microsoft SQL Server'"
        },
        "oracle": {
            "wrong_choice": ["key_vault", "hsm", "luna_hsm_backup"],
            "correct_choice": "oracle_tde_database",
            "explanation": "For Oracle TDE, use 'Luna Cloud HSM for Oracle TDE'"
        },
        "payment": {
            "wrong_choice": ["key_vault", "hsm"],
            "correct_choice": ["payshield_na", "payshield_eu"],
            "explanation": "For payment processing, use payShield Cloud HSM services"
        }
    }
    
    # Check user request against common patterns
    user_request_lower = user_request.lower()
    for pattern, mistake_info in common_mistakes.items():
        if pattern in user_request_lower:
            if selected_service_type in mistake_info["wrong_choice"]:
                validation_result["warnings"].append(mistake_info["explanation"])
                validation_result["better_alternatives"].append(mistake_info["correct_choice"])
    
    # Check if there are more specific services available
    if selected_service_type in ["key_vault", "hsm"]:
        # These are generic services - check if more specific ones exist
        specific_services = []
        for service in available_services:
            if service.get("shortCode") in ["ms_sql_server", "oracle_tde_database", "luna_hsm_backup", "pki_private_key_protection"]:
                specific_services.append(service)
        
        if specific_services:
            validation_result["warnings"].append("Generic HSM service selected when more specific alternatives exist")
            validation_result["better_alternatives"].extend([s.get("shortCode") for s in specific_services])
    
    # Final validation
    if not validation_result["warnings"]:
        validation_result["valid"] = True
        validation_result["recommendations"].append("Service selection appears appropriate for the use case")
    else:
        validation_result["recommendations"].append("Review the warnings and consider using a more specific service type")
    
    return validation_result


async def manage_services(
    ctx: Context,
    action: str = Field(..., description="Action to perform"),
    service_id: Optional[str] = Field(default=None, description="Service ID or name for get, update, delete, or bind_client actions"),
    name: Optional[str] = Field(default=None, description="Service name for create_service_instance action (4-45 characters)"),
    service_type: Optional[str] = Field(default=None, description="Service type for service creation"),
    configuration: Optional[Dict[str, Any]] = Field(default=None, description="Service configuration parameters (createParams in API)"),
    page: int = Field(default=0, description="Page number for pagination (0-based)"),
    size: int = Field(default=50, description="Page size for pagination (max 100)"),
    status: Optional[str] = Field(default=None, description="Filter services by status"),
    force: bool = Field(default=False, description="Force deletion even if dependencies exist"),
    tile_id: Optional[str] = Field(default=None, description="Tile ID for service creation (takes precedence over service_type)"),
    service_plan: Optional[str] = Field(default=None, description="Service plan name for service creation"),
    device_type: Optional[str] = Field(default=None, description="Device type for Luna Cloud HSM services (cryptovisor or cryptovisor_fips)"),
    client_name: Optional[str] = Field(default=None, description="Client name for bind_client action (1-64 characters)"),
    os_type: Optional[str] = Field(default="linux", description="OS type for bind_client action (linux or windows)"),
    download_path: Optional[str] = Field(default=None, description="Directory path where client configuration file should be saved (optional, defaults to system temp directory)"),
    client_id: Optional[str] = Field(default=None, description="Client ID for get_service_client and delete_service_client actions"),
    description: Optional[str] = Field(default=None, description="Service description for update_service_instance action")
) -> Dict[str, Any]:
    """Service instance management operations.
    
    Actions: list_services, get_service_instance, create_service_instance, 
             update_service_instance, delete_service_instance, list_categories, list_types, 
             bind_client, list_service_clients, get_service_client, delete_service_client
    
    ⚠️  CRITICAL DISTINCTION FOR AI ASSISTANTS ⚠️
    
    This tool manages PROVISIONED service instances (actual deployed services).
    For available service types (catalog), use the separate manage_tiles tool.
    
    DPoD API Endpoints:
    - Service Catalog (Tiles): GET /v1/tiles → use manage_tiles tool
    - Service Instances: GET /v1/service_instances → use this tool (list_service_instances)
    
    Service Creation Schema (POST /v1/service_instances):
    - Required: name (4-45 chars), servicePlan, createParams (object)
    - Optional: serviceType, tileId
    - deviceType: "cryptovisor" or "cryptovisor_fips" (goes inside createParams for HSM services)
    - NOT needed: tenant_id, subscriber_id, subscriber_groups (these are handled automatically)
    
    MCP Parameter Mapping:
    - configuration → createParams (in API request body)
    - device_type → createParams.deviceType (for HSM services)
    
    Enhanced Smart Identifier Functionality:
    - ALL operations (get, update, delete, bind_client) now accept either UUID or service name
    - If a name is provided, the system automatically searches for the service and extracts the UUID
    - This makes it easier to manage services without having to look up UUIDs manually
    - The system maintains API compliance by using UUIDs for all actual API calls
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    if not config:
        raise ValueError("Configuration not provided - dependency injection failed")
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = get_tool_logger("service")
    tool_logger.info(f"Starting service operation: {action}")
    
    try:
        # 1. MCP Context Logging (NEW)
        await ctx.info(f"Starting service operation: {action}")
        
        # 2. Progress Reporting (EXISTING)
        await ctx.report_progress(0, 100, f"Starting service operation: {action}")
        
        # Validate token before proceeding
        await ctx.report_progress(5, 100, "Validating authentication token...")
        token_validation = await auth.validate_token_permissions()
        
        if not token_validation.get("valid"):
            error_msg = f"Authentication failed: {token_validation.get('error', 'Unknown error')}"
            # 3. MCP Context Error Logging (NEW)
            await ctx.error(f"Authentication failed: {token_validation.get('error', 'Unknown error')}")
            tool_logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "token_validation": token_validation
            }
        
        await ctx.report_progress(10, 100, "Token validation successful")
        # 4. MCP Context Info Logging (NEW)
        await ctx.info(f"Token validation successful - User: {token_validation.get('user_id')}, Scopes: {token_validation.get('scopes')}")
        tool_logger.info(f"Token validation successful - User: {token_validation.get('user_id')}, Scopes: {token_validation.get('scopes')}")
        
        # Define read-only vs write actions
        read_actions = {"list_services", "get_service_instance", "list_categories", "list_types", "get_creation_example", "list_service_clients", "get_service_client"}
        write_actions = {"create_service_instance", "update_service_instance", "delete_service_instance", "bind_client", "delete_service_client"}
        
        # Check read-only mode for write actions
        if action in write_actions and config.read_only_mode:
            await ctx.warning(f"Server is in read-only mode. Action '{action}' is not allowed.")
            return {
                "success": False,
                "error": f"Server is in read-only mode. Action '{action}' is not allowed.",
                "action": action,
                "read_only_mode": True
            }
        
        if action == "list_services":
            # Enhanced progress reporting for listing services
            await ctx.report_progress(15, 100, "Starting service listing workflow...")
            await ctx.info("Starting service listing workflow...")
            
            await ctx.report_progress(25, 100, "Querying provisioned service instances...")
            await ctx.info(f"Retrieving services (page {page}, size {size})")
            
            # Query provisioned service instances
            result = await _list_service_instances(auth, page=page, size=size, status=status, service_type=service_type)
            
            await ctx.report_progress(90, 100, "Service listing completed, finalizing...")
            await ctx.info("Service listing completed successfully")
        elif action == "get_service_instance":
            # Enhanced progress reporting for getting service instance
            await ctx.report_progress(15, 100, "Starting service retrieval workflow...")
            await ctx.info("Starting service retrieval workflow...")
            
            if not service_id:
                await ctx.error("Service ID is required for get_service_instance action")
                raise ValueError("service_id required for get_service_instance action")
            
            await ctx.report_progress(25, 100, "Retrieving service instance details...")
            await ctx.info(f"Retrieving details for service: {service_id}")
            
            result = await _get_service_instance(auth, instance_id=service_id)
            
            await ctx.report_progress(90, 100, "Service retrieval completed, finalizing...")
            await ctx.info("Service retrieval completed successfully")
        elif action == "create_service_instance":
            # Enhanced progress reporting for service creation
            await ctx.report_progress(15, 100, "Starting service creation workflow...")
            await ctx.info("Starting service creation workflow...")
            
            if not name:
                return {
                    "success": False,
                    "error": "name is required for create_service_instance action. Must be 4-45 characters and can contain letters, numbers, hyphens, and underscores."
                }
            
            # Special handling for CTAAS services
            if service_type == "ctaas":
                await ctx.info("Creating CTAAS (CipherTrust Data Security Platform) service with automatic defaults")
                await ctx.info("Defaults: serviceType=ctaas, servicePlan=Tenant")
                await ctx.info("Required: cluster, initial_admin_password")
                await ctx.info("Optional: tenant_rot_anchor (only include if you want to override the default 'hsmod')")
            
            await ctx.report_progress(20, 100, "Validating service parameters...")
            await ctx.info("Validating service parameters...")
            
            # Configuration is optional - defaults will be applied for HSM services
            if configuration is None:
                configuration = {}
            
            # CTAAS-specific defaults and validation
            if service_type == "ctaas":
                # Ensure serviceType and servicePlan are set (will be handled in API call)
                if not service_plan:
                    service_plan = "Tenant"
                
                # Ensure serviceType is set for CTAAS
                if not service_type:
                    service_type = "ctaas"
                
                # Validate that required fields are present
                if "cluster" not in configuration:
                    await ctx.error("cluster is REQUIRED for CTAAS services")
                    return {
                        "success": False,
                        "error": "cluster is REQUIRED for CTAAS services. Must be one of: gcp-us-east1, gcp-europe-west3"
                    }
                
                if "initial_admin_password" not in configuration:
                    await ctx.error("initial_admin_password is REQUIRED for CTAAS services")
                    return {
                        "success": False,
                        "error": "initial_admin_password is REQUIRED for CTAAS services. Must be a string with at least 8 characters"
                    }
            
            # For HSM services, ensure device_type is included in configuration if provided but not in config
            hsm_service_types = [
                "hsm", "key_vault", "luna_hsm_backup", "hsm_key_export", 
                "ms_sql_server", "java_code_sign", "ms_authenticode", "ms_adcs",
                "pki_private_key_protection", "digital_signing", "oracle_tde_database",
                "hyperledger", "luna_dke", "cyberark_digital_vault"
            ]
            
            if service_type in hsm_service_types:
                if device_type and "deviceType" not in configuration:
                    configuration["deviceType"] = device_type
                elif "deviceType" not in configuration:
                    # Auto-include default deviceType for HSM services when not provided
                    configuration["deviceType"] = "cryptovisor"
            
            await ctx.report_progress(25, 100, "Validating configuration structure...")
            # Validate createParams structure
            try:
                validate_create_params(configuration, service_type=service_type)
            except ValidationError as e:
                await ctx.error(f"Configuration validation failed: {e}")
                return {
                    "success": False,
                    "error": f"Invalid configuration (createParams): {e}"
                }
            
            await ctx.report_progress(30, 100, "Validating service plan...")
            # Validate servicePlan - this is critical for service creation
            if not service_plan:
                if service_type in ["key_vault", "hsm"]:
                    await ctx.warning(f"Service plan is required for {service_type} services")
                    return {
                        "success": False,
                        "error": f"servicePlan is required for {service_type} services. Common plans: single_hsm, dual_hsm, multi_hsm, trial"
                    }
                elif service_type == "ctaas":
                    # CTAAS defaults to "Tenant" plan
                    service_plan = "Tenant"
                else:
                    await ctx.warning("Service plan is required for service creation")
                    return {
                        "success": False,
                        "error": "servicePlan is required for service creation. Use 'standard' for most services or check available plans."
                    }
            
            # Validate servicePlan format and compatibility
            try:
                validate_service_plan(service_plan, service_type=service_type)
            except ValidationError as e:
                await ctx.error(f"Service plan validation failed: {e}")
                return {
                    "success": False,
                    "error": f"Invalid servicePlan: {e}"
                }
            
            await ctx.report_progress(35, 100, "Validating device type configuration...")
            # Validate device_type if provided
            if device_type is not None and device_type not in ["cryptovisor", "cryptovisor_fips"]:
                await ctx.error(f"Invalid device type: {device_type}")
                return {
                    "success": False,
                    "error": f"Invalid device_type: {device_type}. Must be one of: cryptovisor, cryptovisor_fips"
                }
            
            await ctx.report_progress(40, 100, "Submitting service creation request...")
            await ctx.info(f"Creating service '{name}' with type '{service_type}' and plan '{service_plan}'")
            
            result = await _create_service_instance(
                auth, name=name, create_params=configuration,
                service_type=service_type, tile_id=tile_id, service_plan=service_plan, device_type=device_type
            )
            
            await ctx.report_progress(90, 100, "Service creation completed, finalizing...")
            await ctx.info("Service creation completed successfully")
        elif action == "update_service_instance":
            # Enhanced progress reporting for service update
            await ctx.report_progress(15, 100, "Starting service update workflow...")
            await ctx.info("Starting service update workflow...")
            
            if not service_id:
                await ctx.error("Service ID is required for update_service_instance action")
                raise ValueError("service_id required for update_service_instance action")
            
            await ctx.report_progress(25, 100, "Validating update parameters...")
            await ctx.info(f"Preparing to update service: {service_id}")
            
            result = await _update_service_instance(
                auth, instance_id=service_id, name=name, description=description, configuration=configuration
            )
            
            await ctx.report_progress(90, 100, "Service update completed, finalizing...")
            await ctx.info("Service update completed successfully")
        elif action == "delete_service_instance":
            # Enhanced progress reporting for service deletion
            await ctx.report_progress(15, 100, "Starting service deletion workflow...")
            await ctx.info("Starting service deletion workflow...")
            
            if not service_id:
                raise ValueError("service_id required for delete_service_instance action")
            
            await ctx.report_progress(25, 100, "Validating service identifier...")
            await ctx.info(f"Preparing to delete service: {service_id}")
            
            # The enhanced _delete_service_instance function handles both UUID and name-based deletion
            # It will automatically fetch the UUID if a name is provided
            await ctx.report_progress(40, 100, "Executing service deletion...")
            result = await _delete_service_instance(auth, instance_id=service_id, force=force)
            
            await ctx.report_progress(90, 100, "Service deletion completed, finalizing...")
            await ctx.info("Service deletion completed successfully")
            return result
        elif action == "list_categories":
            # Enhanced progress reporting for listing categories
            await ctx.report_progress(15, 100, "Starting category listing workflow...")
            await ctx.info("Starting category listing workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving service categories...")
            await ctx.info("Retrieving available service categories")
            
            result = await _list_service_categories(auth)
            
            await ctx.report_progress(90, 100, "Category listing completed, finalizing...")
            await ctx.info("Category listing completed successfully")
            
            return result
            
        elif action == "list_types":
            # Enhanced progress reporting for listing types
            await ctx.report_progress(15, 100, "Starting type listing workflow...")
            await ctx.info("Starting type listing workflow...")
            
            await ctx.report_progress(25, 100, "Retrieving service types...")
            await ctx.info("Retrieving available service types")
            
            result = await _list_service_types(auth)
            
            await ctx.report_progress(90, 100, "Type listing completed, finalizing...")
            await ctx.info("Type listing completed successfully")
            
            return result
            
        elif action == "get_creation_example":
            # Enhanced progress reporting for getting creation example
            await ctx.report_progress(15, 100, "Starting example generation workflow...")
            await ctx.info("Starting example generation workflow...")
            
            # Get complete example for creating a service
            # This shows the EXACT API call structure - no tenant_id needed!
            example_service_type = service_type or "key_vault"
            complete_example = get_service_creation_example(example_service_type)
            
            # Convert to manage_services action format - show 3 different approaches
            mcp_example_1 = {
                "action": "create_service_instance",
                "name": complete_example["name"],
                "service_type": complete_example["serviceType"],
                "service_plan": complete_example["servicePlan"],
                "configuration": complete_example["createParams"]
            }
            
            mcp_example_2 = {
                "action": "create_service_instance",
                "name": complete_example["name"],
                "service_type": complete_example["serviceType"],
                "service_plan": complete_example["servicePlan"]
            }
            
            mcp_example_3 = {
                "action": "create_service_instance",
                "name": complete_example["name"],
                "service_type": complete_example["serviceType"], 
                "service_plan": complete_example["servicePlan"]
            }
            
            # Add device_type for method 2 if it's in createParams for Luna HSM
            if "deviceType" in complete_example["createParams"]:
                mcp_example_2["device_type"] = complete_example["createParams"]["deviceType"]
            
            result = {
                "success": True,
                "api_format": complete_example,
                "mcp_method_1": {
                    "description": "Method 1: Use configuration parameter (explicit createParams)",
                    "example": mcp_example_1
                },
                "mcp_method_2": {
                    "description": "Method 2: Use device_type parameter (convenience - auto-moves to createParams)",
                    "example": mcp_example_2
                },
                "mcp_method_3": {
                    "description": "Method 3: Omit device type (auto-defaults to 'cryptovisor')",
                    "example": mcp_example_3
                },
                "message": f"Complete example for creating a {example_service_type} service instance with 3 different approaches"
            }
            
            await ctx.report_progress(90, 100, "Example generation completed, finalizing...")
            await ctx.info("Example generation completed successfully")
        elif action == "bind_client":
            # Enhanced progress reporting for client binding
            await ctx.report_progress(15, 100, "Starting client binding workflow...")
            await ctx.info("Starting client binding workflow...")
            
            if not service_id:
                await ctx.error("Service ID is required for bind_client action")
                return {
                    "success": False,
                    "error": "service_id is required for bind_client action"
                }
            
            if not client_name:
                await ctx.error("Client name is required for bind_client action")
                return {
                    "success": False,
                    "error": "client_name is required for bind_client action. Must be 1-64 characters and unique for the targeted service."
                }
            
            await ctx.report_progress(25, 100, "Validating client parameters...")
            await ctx.info(f"Preparing to bind client '{client_name}' to service: {service_id}")
            
            # Validate OS type
            if os_type and os_type not in ["linux", "windows"]:
                await ctx.error(f"Invalid OS type: {os_type}")
                return {
                    "success": False,
                    "error": f"Invalid os_type: {os_type}. Must be 'linux' or 'windows'"
                }
            
            await ctx.report_progress(40, 100, "Executing client binding...")
            result = await _bind_client_to_service(
                auth, service_id=service_id, client_name=client_name, os_type=os_type or "linux", download_path=download_path
            )
            
            await ctx.report_progress(90, 100, "Client binding completed, finalizing...")
            await ctx.info("Client binding completed successfully")
            
            return result
            
        elif action == "list_service_clients":
            # Enhanced progress reporting for listing service clients
            await ctx.report_progress(15, 100, "Starting service client listing workflow...")
            await ctx.info("Starting service client listing workflow...")
            
            if not service_id:
                await ctx.error("Service ID is required for list_service_clients action")
                return {
                    "success": False,
                    "error": "service_id is required for list_service_clients action"
                }
            
            await ctx.report_progress(25, 100, "Retrieving service clients...")
            await ctx.info(f"Retrieving service clients for service: {service_id}")
            
            result = await _list_service_clients(auth, service_id=service_id)
            
            await ctx.report_progress(90, 100, "Service client listing completed, finalizing...")
            await ctx.info("Service client listing completed successfully")
            
            return result
            
        elif action == "get_service_client":
            # Enhanced progress reporting for getting service client details
            await ctx.report_progress(15, 100, "Starting service client retrieval workflow...")
            await ctx.info("Starting service client retrieval workflow...")
            
            if not service_id:
                await ctx.error("Service ID is required for get_service_client action")
                return {
                    "success": False,
                    "error": "service_id is required for get_service_client action"
                }
            
            if not client_id:
                await ctx.error("Client ID is required for get_service_client action")
                return {
                    "success": False,
                    "error": "client_id is required for get_service_client action"
                }
            
            await ctx.report_progress(25, 100, "Retrieving service client details...")
            await ctx.info(f"Retrieving details for service client: {client_id}")
            
            result = await _get_service_client(auth, service_id=service_id, client_id=client_id)
            
            await ctx.report_progress(90, 100, "Service client retrieval completed, finalizing...")
            await ctx.info("Service client retrieval completed successfully")
            
            return result
            
        elif action == "delete_service_client":
            # Enhanced progress reporting for deleting service client
            await ctx.report_progress(15, 100, "Starting service client deletion workflow...")
            await ctx.info("Starting service client deletion workflow...")
            
            if not service_id:
                await ctx.error("Service ID is required for delete_service_client action")
                return {
                    "success": False,
                    "error": "service_id is required for delete_service_client action"
                }
            
            if not client_id:
                await ctx.error("Client ID is required for delete_service_client action")
                return {
                    "success": False,
                    "error": "client_id is required for delete_service_client action"
                }
            
            await ctx.report_progress(25, 100, "Deleting service client...")
            await ctx.info(f"Deleting service client: {client_id}")
            
            result = await _delete_service_client(auth, service_id=service_id, client_id=client_id)
            
            await ctx.report_progress(90, 100, "Service client deletion completed, finalizing...")
            await ctx.info("Service client deletion completed successfully")
            
            return result
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # 5. MCP Context Completion Logging (NEW)
        await ctx.info(f"Completed service operation: {action}")
        await ctx.report_progress(100, 100, f"Completed service operation: {action}")
        tool_logger.info(f"Completed service operation: {action}")
        return result
        
    except Exception as e:
        # 6. MCP Context Error Logging (NEW)
        await ctx.error(f"Error in service operation {action}: {str(e)}")
        tool_logger.error(f"Error in service operation {action}: {e}")
        raise


async def _list_service_instances(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List provisioned service instances."""
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
            lambda x: validate_string_param(x, "Status", min_length=1, max_length=50),
            "status"
        )
        
        service_type = validate_optional_param(
            kwargs.get("service_type"),
            lambda x: validate_string_param(x, "Service Type", min_length=1, max_length=100),
            "service_type"
        )
        
        # Prepare query parameters
        params = {"page": page, "size": size}
        if status:
            params["status"] = status
        if service_type:
            params["serviceType"] = service_type
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/service_instances",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to list service instances: {response.status_code}",
                "details": response.text
            }
        
        instances_data = response.json()
        
        return {
            "success": True,
            "instances": instances_data.get("content", []),
            "total_elements": instances_data.get("totalElements", 0),
            "total_pages": instances_data.get("totalPages", 0),
            "page": page,
            "size": size
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_service_instance(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get details of a specific service instance.
    
    This function automatically handles both UUID and name-based service identification:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the service and extracts the UUID
    - Then it performs the actual API call using the UUID
    """
    try:
        # Get the instance identifier (could be UUID or name)
        instance_identifier = kwargs.get("instance_id")
        
        if not instance_identifier:
            return {"success": False, "error": "instance_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, instance_identifier, "get_service_instance")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # Make API request using the resolved UUID
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/service_instances/{resolved_uuid}"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get service instance: {response.status_code}",
                "details": response.text
            }
        
        instance_data = response.json()
        
        return {
            "success": True,
            "instance": instance_data,
            "resolved_uuid": resolved_uuid,
            "original_identifier": instance_identifier
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _create_service_instance(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Create a new service instance."""
    try:
        # Validate required parameters
        name = validate_service_name(kwargs.get("name"))
        
        # Pass service_type to validation for service-specific validation
        service_type = kwargs.get("service_type")
        create_params = validate_create_params(kwargs.get("create_params"), service_type=service_type)
        
        # Validate optional parameters
        service_type = validate_optional_param(
            kwargs.get("service_type"),
            lambda x: validate_string_param(x, "Service Type", min_length=1, max_length=100),
            "service_type"
        )
        
        tile_id = validate_optional_param(
            kwargs.get("tile_id"),
            lambda x: validate_uuid(x, "Tile ID"),
            "tile_id"
        )
        
        service_plan = validate_optional_param(
            kwargs.get("service_plan"),
            lambda x: validate_service_plan(x, service_type=service_type),
            "service_plan"
        )
        
        device_type = validate_optional_param(
            kwargs.get("device_type"),
            lambda x: validate_string_param(x, "Device Type", min_length=1, max_length=50),
            "device_type"
        )
        
        # Prepare service data
        service_data = {
            "name": name,
            "createParams": create_params
        }
        
        # CTAAS-specific handling
        if service_type == "ctaas":
            # Always set serviceType for CTAAS
            service_data["serviceType"] = "ctaas"
            # Always set servicePlan for CTAAS (defaults to "Tenant")
            service_data["servicePlan"] = service_plan or "Tenant"
            # Note: tenant_rot_anchor is only included if user explicitly provides it
        else:
            # For other service types, set parameters if provided
            if service_type:
                service_data["serviceType"] = service_type
            if service_plan:
                service_data["servicePlan"] = service_plan
        
        if tile_id:
            service_data["tileId"] = tile_id
        # Define HSM service types that need deviceType parameter
        hsm_service_types = [
            "hsm", "key_vault", "luna_hsm_backup", "hsm_key_export", 
            "ms_sql_server", "java_code_sign", "ms_authenticode", "ms_adcs",
            "pki_private_key_protection", "digital_signing", "oracle_tde_database",
            "hyperledger", "luna_dke", "cyberark_digital_vault"
        ]
        
        # For HSM services, ensure deviceType is in createParams
        if service_type in hsm_service_types:
            if device_type and "deviceType" not in service_data["createParams"]:
                service_data["createParams"]["deviceType"] = device_type
            elif "deviceType" not in service_data["createParams"]:
                # Auto-include default deviceType for HSM services
                service_data["createParams"]["deviceType"] = "cryptovisor"
        
        # Make API request with retry logic
        response = None
        for attempt in range(3):
            response = await auth.make_authenticated_request(
                "POST",
                "/v1/service_instances",
                json_data=service_data
            )
            if response.status_code < 500:
                break
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

        if response is None:
            return {"success": False, "error": "Failed to get a response from the server."}

        if response.status_code not in [200, 201, 202]:
            return {
                "success": False,
                "error": f"Failed to create service instance: {response.status_code}",
                "details": response.text
            }

        # Handle successful responses
        if response.text:
            try:
                created_instance = response.json()
                return {
                    "success": True,
                    "instance": created_instance,
                    "message": "Service instance created successfully"
                }
            except ValueError:
                # Handle cases where response is not valid JSON
                return {
                    "success": True,
                    "status": "pending",
                    "message": "Service instance creation accepted, but response was not valid JSON."
                }
        else:
            # Handle empty responses
            return {
                "success": True,
                "status": "pending",
                "message": "Service instance creation accepted and is in progress."
            }

    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_service_instance(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Update an existing service instance.
    
    This function automatically handles both UUID and name-based service identification:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the service and extracts the UUID
    - Then it performs the actual update using the UUID
    """
    try:
        # Get the instance identifier (could be UUID or name)
        instance_identifier = kwargs.get("instance_id")
        
        if not instance_identifier:
            return {"success": False, "error": "instance_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, instance_identifier, "update_service_instance")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # Validate optional parameters
        name = validate_optional_param(
            kwargs.get("name"),
            lambda x: validate_string_param(x, "Name", min_length=4, max_length=45),
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
        
        # Make API request using the resolved UUID
        response = await auth.make_authenticated_request(
            "PUT",
            f"/v1/service_instances/{resolved_uuid}",
            json_data=update_data
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to update service instance: {response.status_code}",
                "details": response.text
            }
        
        updated_instance = response.json()
        
        return {
            "success": True,
            "instance": updated_instance,
            "message": "Service instance updated successfully",
            "resolved_uuid": resolved_uuid,
            "original_identifier": instance_identifier
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _delete_service_instance(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Delete a service instance.
    
    This function automatically handles both UUID and name-based deletion:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the service and extracts the UUID
    - Then it performs the actual deletion using the UUID
    """
    try:
        # Get the instance identifier (could be UUID or name)
        instance_identifier = kwargs.get("instance_id")
        force = kwargs.get("force", False)
        
        if not instance_identifier:
            return {"success": False, "error": "instance_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, instance_identifier, "delete_service_instance")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        from ...core.logging_utils import get_tool_logger
        tool_logger = get_tool_logger("service")
        tool_logger.info(f"Proceeding with deletion using resolved UUID: {resolved_uuid}")
        
        # Prepare query parameters
        params = {}
        if force:
            params["force"] = "true"
            tool_logger.info("Force deletion enabled")
        
        # Make API request using the resolved UUID
        tool_logger.info(f"Sending DELETE request to /v1/service_instances/{resolved_uuid}")
        response = await auth.make_authenticated_request(
            "DELETE",
            f"/v1/service_instances/{resolved_uuid}",
            params=params
        )
        
        if response.status_code not in [200, 202, 204]:
            return {
                "success": False,
                "error": f"Failed to delete service instance: {response.status_code}",
                "details": response.text
            }
        
        tool_logger.info(f"Service instance {resolved_uuid} deleted successfully (HTTP {response.status_code})")
        return {
            "success": True,
            "message": "Service instance deleted successfully",
            "deleted_uuid": resolved_uuid,
            "original_identifier": instance_identifier,
            "http_status": response.status_code
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        from ...core.logging_utils import get_tool_logger
        tool_logger = get_tool_logger("service")
        tool_logger.error(f"Unexpected error in _delete_service_instance: {e}")
        return {"success": False, "error": str(e)}


async def _list_service_categories(auth: DPoDAuth) -> Dict[str, Any]:
    """List available service categories."""
    try:
        # Make API request - this is a global endpoint that doesn't require authentication
        response = await auth.make_unauthenticated_request(
            "GET",
            "/v1/service_categories"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to list service categories: {response.status_code}",
                "details": response.text
            }
        
        categories_data = response.json()
        
        return {
            "success": True,
            "categories": categories_data
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_service_types(auth: DPoDAuth) -> Dict[str, Any]:
    """List available service types."""
    try:
        # Make API request - this is a global endpoint that doesn't require authentication
        response = await auth.make_unauthenticated_request(
            "GET",
            "/v1/service_types"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to list service types: {response.status_code}",
                "details": response.text
            }
        
        types_data = response.json()
        
        return {
            "success": True,
            "types": types_data
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)} 

async def _bind_client_to_service(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Bind a client to a service instance.
    
    This function automatically handles both UUID and name-based service identification:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the service and extracts the UUID
    - Then it performs the actual client binding using the UUID
    """
    try:
        # Get the service identifier (could be UUID or name)
        service_identifier = kwargs.get("service_id")
        client_name = validate_string_param(kwargs.get("client_name"), "client_name", min_length=1, max_length=64)
        os_type = kwargs.get("os_type", "linux")
        download_path = kwargs.get("download_path")
        
        if not service_identifier:
            return {"success": False, "error": "service_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, service_identifier, "bind_client")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # Validate OS type
        if os_type not in ["linux", "windows"]:
            return {
                "success": False,
                "error": f"Invalid os_type: {os_type}. Must be 'linux' or 'windows'"
            }
        
        # Prepare request payload
        payload = {
            "name": client_name,
            "os": os_type
        }
        
        # Make API request to bind client to service using the resolved UUID
        response = await auth.make_authenticated_request(
            "PUT",
            f"/v1/services/{resolved_uuid}/client",
            json_data=payload
        )
        
        if response.status_code not in [200, 201]:
            return {
                "success": False,
                "error": f"Failed to bind client to service: {response.status_code}",
                "details": response.text
            }
        
        # Handle binary file response from server
        file_info = None
        saved_file_path = None
        
        if response.content:
            try:
                # Check if response is binary (likely a client config file)
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                if 'application/octet-stream' in content_type or 'attachment' in content_disposition:
                    # This is a binary file download - SAVE IT!
                    file_info = {
                        "type": "binary_file",
                        "content_type": content_type,
                        "content_disposition": content_disposition,
                        "size_bytes": len(response.content),
                        "filename": None
                    }
                    
                    # Try to extract filename from content-disposition header
                    if 'filename=' in content_disposition:
                        filename_start = content_disposition.find('filename=') + 9
                        filename_end = content_disposition.find(';', filename_start)
                        if filename_end == -1:
                            filename_end = len(content_disposition)
                        file_info["filename"] = content_disposition[filename_start:filename_end].strip('"')
                    
                    # Save the binary file to specified location or temp directory
                    try:
                        # Determine the target directory
                        if download_path:
                            # Validate and use custom download path
                            if not os.path.exists(download_path):
                                try:
                                    os.makedirs(download_path, exist_ok=True)
                                except Exception as e:
                                    return {"success": False, "error": f"Failed to create download directory '{download_path}': {e}"}
                            target_dir = download_path
                        else:
                            # Use system temp directory as fallback
                            target_dir = tempfile.gettempdir()
                        
                        # Create a meaningful filename
                        base_filename = file_info["filename"] or f"client_config_{client_name}_{os_type}"
                        
                        # Ensure the filename is safe for the filesystem
                        safe_filename = "".join(c for c in base_filename if c.isalnum() or c in "._-")
                        if not safe_filename:
                            safe_filename = f"client_config_{client_name}_{os_type}"
                        
                        # Create the full file path
                        file_path = os.path.join(target_dir, safe_filename)
                        
                        # Write the binary content to the file
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        
                        saved_file_path = file_path
                        file_info["saved_path"] = file_path
                        file_info["download_directory"] = target_dir
                        file_info["custom_path"] = download_path is not None
                        
                        # For binary responses, we can't extract a client_id from the content
                        # The client_id might be in headers or the user needs to check the service
                        client_id = "binary_file_response"
                        
                    except Exception as save_error:
                        # If file saving fails, log it but don't fail the entire operation
                        file_info["save_error"] = str(save_error)
                        file_info["saved_path"] = None
                        client_id = "binary_file_response_save_failed"
                        
                else:
                    # Try to handle as text response
                    try:
                        client_id = response.text.strip('"') if response.text else None
                    except UnicodeDecodeError:
                        # If text decoding fails, use raw content info
                        client_id = f"binary_response_{len(response.content)}_bytes"
                        file_info = {
                            "type": "unknown_binary",
                            "size_bytes": len(response.content),
                            "note": "Response appears to be binary but content-type is not clearly specified"
                        }
            except Exception as e:
                # Fallback for any parsing errors
                client_id = f"response_parsing_error_{str(e)[:50]}"
                file_info = {
                    "type": "error",
                    "error": str(e),
                    "size_bytes": len(response.content) if response.content else 0
                }
        else:
            client_id = "no_content_response"
        
        return {
            "success": True,
            "message": f"Client '{client_name}' bound successfully to service {resolved_uuid}",
            "client_name": client_name,
            "service_id": resolved_uuid,
            "original_identifier": service_identifier,
            "os_type": os_type,
            "client_id": client_id,
            "file_response": file_info,
            "file_saved_to": saved_file_path,
            "note": f"Server returned a binary file which has been saved to: {saved_file_path}" if saved_file_path else "Server returned a binary file. This is likely a client configuration file that needs to be downloaded and saved.",
            "download_path_used": download_path or "system temp directory"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)} 

async def _list_service_clients(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List all service clients bound to a service instance.
    
    This function automatically handles both UUID and name-based service identification:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the service and extracts the UUID
    - Then it performs the actual API call using the UUID
    """
    try:
        # Get the service identifier (could be UUID or name)
        service_identifier = kwargs.get("service_id")
        
        if not service_identifier:
            return {"success": False, "error": "service_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, service_identifier, "list_service_clients")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # Make API request to list service clients using the resolved UUID
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/service_instances/{resolved_uuid}/bindings"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to list service clients: {response.status_code}",
                "details": response.text
            }
        
        clients_data = response.json()
        
        return {
            "success": True,
            "clients": clients_data.get("content", []),
            "total_elements": clients_data.get("totalElements", 0),
            "total_pages": clients_data.get("totalPages", 0),
            "resolved_uuid": resolved_uuid,
            "original_identifier": service_identifier
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_service_client(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get details of a specific service client.
    
    This function automatically handles both UUID and name-based client identification:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the client and extracts the UUID
    - Then it performs the actual API call using the UUID
    """
    try:
        # Get the service identifier (could be UUID or name)
        service_identifier = kwargs.get("service_id")
        client_id = kwargs.get("client_id")
        
        if not service_identifier:
            return {"success": False, "error": "service_id is required"}
        
        if not client_id:
            return {"success": False, "error": "client_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, service_identifier, "get_service_client")
            resolved_client_id = await _resolve_client_identifier(auth, resolved_uuid, client_id, "get_service_client")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # Make API request to get service client details using the resolved UUID
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/service_instances/{resolved_uuid}/bindings/{resolved_client_id}"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get service client: {response.status_code}",
                "details": response.text
            }
        
        client_data = response.json()
        
        return {
            "success": True,
            "client": client_data,
            "resolved_uuid": resolved_uuid,
            "resolved_client_id": resolved_client_id,
            "original_identifier": service_identifier,
            "client_id": client_id
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _delete_service_client(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Delete a specific service client.
    
    This function automatically handles both UUID and name-based client identification:
    - If a UUID is provided, it validates and uses it directly
    - If a name is provided, it searches for the client and extracts the UUID
    - Then it performs the actual deletion using the UUID
    """
    try:
        # Get the service identifier (could be UUID or name)
        service_identifier = kwargs.get("service_id")
        client_id = kwargs.get("client_id")
        
        if not service_identifier:
            return {"success": False, "error": "service_id is required"}
        
        if not client_id:
            return {"success": False, "error": "client_id is required"}
        
        # Use smart identifier resolution
        try:
            resolved_uuid = await _resolve_service_identifier(auth, service_identifier, "delete_service_client")
            resolved_client_id = await _resolve_client_identifier(auth, resolved_uuid, client_id, "delete_service_client")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # Make API request to delete service client using the resolved UUID
        response = await auth.make_authenticated_request(
            "DELETE",
            f"/v1/service_instances/{resolved_uuid}/bindings/{resolved_client_id}"
        )
        
        if response.status_code not in [200, 202, 204]:
            return {
                "success": False,
                "error": f"Failed to delete service client: {response.status_code}",
                "details": response.text
            }
        
        return {
            "success": True,
            "message": "Service client deleted successfully",
            "deleted_client_id": resolved_client_id,
            "resolved_uuid": resolved_uuid,
            "original_identifier": service_identifier,
            "http_status": response.status_code
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)} 