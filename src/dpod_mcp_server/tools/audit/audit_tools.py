"""Audit Log Management Tools for DPoD MCP Server

Provides audit operations including export generation, status checking, result retrieval,
and comprehensive log analysis with automatic source and resource detection.
"""

import asyncio
import logging
import json
import gzip
import tempfile
import os
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError
)
from ..services.service_tools import _resolve_service_identifier, _resolve_client_identifier

from ...core.logging_utils import get_tool_logger


def _convert_date_format(date_str: str, is_start_date: bool = True) -> str:
    """Convert ISO date formats to RFC3339 format expected by API.
    
    Supports:
    1. YYYY-MM-DD or YYYY/MM/DD -> 2025-04-01T00:00:00Z (start) or 2025-04-01T23:59:59Z (end)
    2. YYYY-MM-DDTHH:MM:SSZ or YYYY/MM/DDTHH:MM:SSZ -> normalized to RFC3339
    
    Args:
        date_str: Date string in ISO format
        is_start_date: True if this is start_date (adds T00:00:00Z), False for end_date (adds T23:59:59Z)
        
    Returns:
        Date string in RFC3339 format
    """
    if not date_str:
        return date_str
    
    # If already has timestamp, normalize separators and return
    if 'T' in date_str:
        # Normalize separators (convert / to -)
        date_str = date_str.replace('/', '-')
        # Ensure it ends with Z
        if not date_str.endswith('Z'):
            date_str += 'Z'
        return date_str
    
    # Normalize separators (convert / to -)
    date_str = date_str.replace('/', '-')
    
    # Parse ISO date format (YYYY-MM-DD)
    if len(date_str) == 10:  # Date format
        parts = date_str.split('-')
        if len(parts) == 3:
            try:
                year, month, day = parts
                
                # Validate and format
                year = int(year)
                month = int(month)
                day = int(day)
                
                # Create RFC3339 date
                rfc_date = f"{year:04d}-{month:02d}-{day:02d}"
                
                # Add appropriate time
                if is_start_date:
                    return f"{rfc_date}T00:00:00Z"
                else:
                    return f"{rfc_date}T23:59:59Z"
                    
            except (ValueError, IndexError):
                # If parsing fails, return as-is
                pass
    
    # If we can't parse it, return as-is (will be validated later)
    return date_str


async def _resolve_actor_identifier(auth: DPoDAuth, service_name: str, actor_identifier: str) -> Optional[str]:
    """Resolve actor identifier based on service type.
    
    - HSM Services: Convert client names to UUIDs
    - CDSP/CTAAS Services: Use usernames as-is (no conversion)
    - Other Services: Use actor IDs as-is
    
    Args:
        auth: DPoDAuth instance
        service_name: Service name to search in
        actor_identifier: Client name, username, or UUID
        
    Returns:
        Resolved identifier if conversion needed, None if should use original
    """
    try:
        # First resolve service name to UUID
        service_uuid = await _resolve_service_identifier(auth, service_name, "actor resolution")
        
        # Check service type by looking up service details
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/service_instances/{service_uuid}"
        )
        
        if response.status_code != 200:
            return None
            
        service_data = response.json()
        service_type = service_data.get("serviceType", "").lower()
        
        # HSM Services: Convert client names to UUIDs
        hsm_service_types = [
            "hsm", "key_vault", "hsm_key_export", "ms_sql_server", "java_code_sign", 
            "ms_authenticode", "ms_adcs", "pki_private_key_protection", "digital_signing", 
            "oracle_tde_database", "hyperledger", "luna_dke", "cyberark_digital_vault", 
            "luna_hsm_backup", "payshield_na", "payshield_eu", "p2pe", "codesign-secure", 
            "kt_ses", "kt_pki", "garasign", "pkiaas", "suredrop", "a24_hsm", 
            "ascertia_pki", "codesign", "pk_sign_cloud", "kf_command", "pk_sign_sw", 
            "ven_platform", "signpath"
        ]
        
        if "hsm" in service_type or service_type in hsm_service_types:
            try:
                # For HSM services, try to resolve client name to UUID
                client_uuid = await _resolve_client_identifier(auth, service_uuid, actor_identifier, "audit log filtering")
                return client_uuid
            except ValueError:
                # Client not found, return None (will use original actor_identifier)
                return None
        
        # CDSP/CTAAS Services: Use usernames as-is (no conversion needed)
        elif service_type == "ctaas":
            # For CDSP services, usernames are used directly - no conversion needed
            return None
        
        # Other Services: Use actor IDs as-is (no conversion needed)
        else:
            return None
        
    except Exception as e:
        get_tool_logger("audit").warning(f"Error resolving actor identifier: {e}")
        return None


async def manage_audit_logs(
    ctx: Context,
    action: str = Field(description="Operation to perform: generate_export, get_export, get_result, get_status, get_logs"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for audit log operations"),
    export_id: Optional[str] = Field(default=None, description="Export ID for get_export, get_result, get_status operations"),
    start_date: Optional[str] = Field(default=None, description="Start date for log operations (supports: YYYY-MM-DD or YYYY/MM/DD)"),
    end_date: Optional[str] = Field(default=None, description="End date for log operations (supports: YYYY-MM-DD or YYYY/MM/DD)"),
    service_name: Optional[str] = Field(default=None, description="Service name to filter logs for (auto-detects source and resource_id)"),
    resource_id: Optional[str] = Field(default=None, description="Service UUID or name to filter logs for (if name, auto-detects source and resource_id)"),
    source_filter: Optional[str] = Field(default=None, description="Source/origin to filter logs by (e.g., thales/cloudhsm/123456789 or cdsp)"),
    actor_id: Optional[str] = Field(default=None, description="Actor ID or client name to filter logs by (for HSM services, client names are auto-resolved to UUIDs)"),
    action_filter: Optional[str] = Field(default=None, description="Specific action to filter logs by (e.g., 'Create Key', 'Delete User')"),
    status_filter: Optional[str] = Field(default=None, description="Status to filter logs by (e.g., 'success', 'LUNA_RET_OK', error codes)"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)")
) -> Dict[str, Any]:
    """Audit log management operations.
    
    Actions:
    - generate_export: Generate a new audit log export
    - get_export: Get details of a specific export
    - get_result: Get the result of a completed export
    - get_status: Get the status of an export
    - get_logs: Get audit logs directly with filtering
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    get_tool_logger("audit").info(f"Starting audit operation: {action}")
    
    try:
        # 1. MCP Context Logging (NEW)
        await ctx.info(f"Starting audit operation: {action}")
        
        # 2. Progress Reporting (EXISTING)
        await ctx.report_progress(0, 100, f"Starting audit operation: {action}")
        
        # Validate token before proceeding
        await ctx.report_progress(5, 100, "Validating authentication token...")
        token_validation = await auth.validate_token_permissions()
        
        if not token_validation.get("valid"):
            error_msg = f"Authentication failed: {token_validation.get('error', 'Unknown error')}"
            # 3. MCP Context Error Logging (NEW)
            await ctx.error(f"Authentication failed: {token_validation.get('error', 'Unknown error')}")
            get_tool_logger("audit").error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "token_validation": token_validation
            }
        
        await ctx.report_progress(10, 100, "Token validation successful")
        # 4. MCP Context Info Logging (NEW)
        await ctx.info(f"Token validation successful - User: {token_validation.get('user_id')}, Scopes: {token_validation.get('scopes')}")
        get_tool_logger("audit").info(f"Token validation successful - User: {token_validation.get('user_id')}, Scopes: {token_validation.get('scopes')}")
        
        # Define read-only vs write actions
        read_actions = {"get_export", "get_result", "get_status"}
        write_actions = {"generate_export", "get_logs"}  # Starting export job is a write action
        
        # Check read-only mode for write actions
        if action in write_actions and config.read_only_mode:
            await ctx.warning(f"Server is in read-only mode. Action '{action}' is not allowed.")
            return {
                "success": False,
                "error": f"Server is in read-only mode. Action '{action}' is not allowed.",
                "action": action,
                "read_only_mode": True
            }
        
        # Validate service identifier parameters
        service_identifiers = [param for param in [service_name, resource_id, source_filter] if param]
        if len(service_identifiers) > 1:
            await ctx.error("Cannot specify multiple service identifiers. Please provide only one of: service_name, resource_id, or source_filter.")
            return {
                "success": False,
                "error": "Cannot specify multiple service identifiers. Please provide only one of: service_name, resource_id, or source_filter.",
                "action": action
            }
        
        # Resolve service identifier (service_name, resource_id, or source_filter)
        resolved_service_name = None
        resolved_source = None
        resolved_resource_id = None
        if service_name:
            resolved_service_name = service_name
            await ctx.info(f"Using service_name: {service_name}")
        elif resource_id:
            # Check if resource_id is a UUID or a name
            if len(resource_id) == 36 and resource_id.count('-') == 4:
                # It's a UUID, use it directly as service_name for resolution
                resolved_service_name = resource_id
                await ctx.info(f"Using resource_id as UUID: {resource_id}")
            else:
                # It's a name, use it as service_name
                resolved_service_name = resource_id
                await ctx.info(f"Using resource_id as service name: {resource_id}")
        elif source_filter:
            # Smart source_filter handling:
            # 1. If "cdsp" -> use as source
            # 2. If "thales/cloudhsm/<partitionID>" -> use as source  
            # 3. Otherwise -> treat as service name and convert to resource_id
            if source_filter.lower() == "cdsp":
                resolved_source = source_filter
                await ctx.info(f"Using source_filter as CDSP source: {source_filter}")
            elif source_filter.startswith("thales/cloudhsm/"):
                resolved_source = source_filter
                await ctx.info(f"Using source_filter as HSM source: {source_filter}")
            else:
                # Treat as service name
                resolved_service_name = source_filter
                await ctx.info(f"Using source_filter as service name: {source_filter}")
        
        # Convert date formats to RFC3339 if needed
        converted_start_date = None
        converted_end_date = None
        if start_date:
            converted_start_date = _convert_date_format(start_date, is_start_date=True)
            await ctx.info(f"Converted start_date: {start_date} -> {converted_start_date}")
        if end_date:
            converted_end_date = _convert_date_format(end_date, is_start_date=False)
            await ctx.info(f"Converted end_date: {end_date} -> {converted_end_date}")
        
        # Resolve actor identifier if provided
        resolved_actor_id = None
        if actor_id and resolved_service_name:
            resolved_actor_id = await _resolve_actor_identifier(auth, resolved_service_name, actor_id)
            if resolved_actor_id:
                await ctx.info(f"Resolved actor_id '{actor_id}' to UUID: {resolved_actor_id}")
            else:
                # For CDSP services, actor_id is the UUID of the CDSP user
                # Let's check if this is a CDSP service and handle accordingly
                try:
                    service_uuid = await _resolve_service_identifier(auth, resolved_service_name, "actor validation")
                    response = await auth.make_authenticated_request("GET", f"/v1/service_instances/{service_uuid}")
                    if response.status_code == 200:
                        service_data = response.json()
                        service_type = service_data.get("serviceType", "").lower()
                        if service_type == "ctaas":
                            await ctx.warning(f"Actor ID '{actor_id}' may not be supported for CDSP services. Skipping actor filter.")
                            resolved_actor_id = None
                        else:
                            await ctx.info(f"Using actor_id as-is: {actor_id}")
                            resolved_actor_id = actor_id
                    else:
                        await ctx.info(f"Using actor_id as-is: {actor_id}")
                        resolved_actor_id = actor_id
                except Exception as e:
                    await ctx.warning(f"Could not validate service type for actor_id: {e}. Using as-is.")
                    resolved_actor_id = actor_id
        elif actor_id:
            resolved_actor_id = actor_id
            await ctx.info(f"Using actor_id: {actor_id}")
        

        if action == "generate_export":
            # Enhanced progress reporting for export generation
            await ctx.report_progress(15, 100, "Starting export generation workflow...")
            await ctx.info("Starting export generation workflow...")
            
            await ctx.report_progress(25, 100, "Generating audit log export...")
            await ctx.info(f"Generating export for date range: {start_date} to {end_date}")
            
            result = await _generate_audit_log_export(
                auth, tenant_id=tenant_id, start_date=converted_start_date or start_date, end_date=converted_end_date or end_date
            )
            
            await ctx.report_progress(90, 100, "Export generation completed, finalizing...")
            await ctx.info("Export generation completed successfully")
            
        elif action == "get_logs":
            # Enhanced progress reporting for complete log workflow
            await ctx.report_progress(15, 100, "Starting complete log retrieval workflow...")
            await ctx.info("Starting complete log retrieval workflow...")
            
            await ctx.report_progress(25, 100, "Executing complete audit log workflow...")
            await ctx.info(f"Retrieving logs for date range: {start_date} to {end_date}")
            
            result = await _get_audit_logs_complete_workflow(
                ctx, auth, tenant_id=tenant_id, start_date=converted_start_date or start_date, end_date=converted_end_date or end_date,
                service_name=resolved_service_name, source=resolved_source, actor_id=resolved_actor_id, action_filter=action_filter, status_filter=status_filter
            )
            
            await ctx.report_progress(90, 100, "Log retrieval completed, finalizing...")
            await ctx.info("Log retrieval completed successfully")
            
        elif action == "get_export":
            # Enhanced progress reporting for getting export
            await ctx.report_progress(15, 100, "Starting export retrieval workflow...")
            await ctx.info("Starting export retrieval workflow...")
            
            if not export_id:
                await ctx.error("Export ID is required for get_export action")
                raise ValueError("export_id required for get_export action")
            
            await ctx.report_progress(25, 100, "Retrieving export details...")
            await ctx.info(f"Retrieving export: {export_id}")
            
            result = await _get_audit_log_export(auth, export_id=export_id)
            
            await ctx.report_progress(90, 100, "Export retrieval completed, finalizing...")
            await ctx.info("Export retrieval completed successfully")
            
        elif action == "get_result":
            # Enhanced progress reporting for getting result
            await ctx.report_progress(15, 100, "Starting result retrieval workflow...")
            await ctx.info("Starting result retrieval workflow...")
            
            if not export_id:
                await ctx.error("Export ID is required for get_result action")
                raise ValueError("export_id required for get_result action")
            
            await ctx.report_progress(25, 100, "Retrieving export result...")
            await ctx.info(f"Retrieving result for export: {export_id}")
            
            result = await _get_audit_log_result(auth, export_id=export_id)
            
            await ctx.report_progress(90, 100, "Result retrieval completed, finalizing...")
            await ctx.info("Result retrieval completed successfully")
            
        elif action == "get_status":
            # Enhanced progress reporting for getting status
            await ctx.report_progress(15, 100, "Starting status retrieval workflow...")
            await ctx.info("Starting status retrieval workflow...")
            
            if not export_id:
                await ctx.error("Export ID is required for get_status action")
                raise ValueError("export_id required for get_status action")
            
            await ctx.report_progress(25, 100, "Retrieving export status...")
            await ctx.info(f"Retrieving status for export: {export_id}")
            
            result = await _get_audit_log_status(auth, export_id=export_id)
            
            await ctx.report_progress(90, 100, "Status retrieval completed, finalizing...")
            await ctx.info("Status retrieval completed successfully")
            
        else:
            await ctx.error(f"Unknown action: {action}")
            raise ValueError(f"Unknown action: {action}")
        
        # 5. MCP Context Completion Logging (NEW)
        await ctx.info(f"Completed audit operation: {action}")
        await ctx.report_progress(100, 100, f"Completed audit operation: {action}")
        get_tool_logger("audit").info(f"Completed audit operation: {action}")
        return result
        
    except Exception as e:
        # 6. MCP Context Error Logging (NEW)
        await ctx.error(f"Error in audit operation {action}: {str(e)}")
        get_tool_logger("audit").error(f"Error in audit operation {action}: {e}")
        raise


async def _get_audit_logs_complete_workflow(
    ctx: Context,
    auth: DPoDAuth,
    tenant_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: Optional[str] = None,
    service_name: Optional[str] = None,
    actor_id: Optional[str] = None,
    action_filter: Optional[str] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Complete audit log workflow: export, download, extract, and analyze logs.
    
    This is the main function that handles the complete audit log retrieval process.
    """
    try:
        await ctx.report_progress(10, 100, "Starting complete audit log workflow...")
        
        # Step 1: Set default dates if not provided (last 7 days)
        if not start_date or not end_date:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            # Use the dates as provided (they should already be converted to RFC3339 format)
            start_date_str = start_date
            end_date_str = end_date
        
        await ctx.report_progress(20, 100, f"Using date range: {start_date_str} to {end_date_str}")
        
        # Step 2: Handle service identification (service_name or source)
        if service_name:
            print(f"DEBUG: Service name provided: {service_name}")
            await ctx.report_progress(30, 100, f"Detecting service details for: {service_name}")
            print("DEBUG: About to call _detect_service_details")
            service_details = await _detect_service_details(auth, service_name)
            print(f"DEBUG: _detect_service_details returned: {service_details}")
            if service_details and "source" in service_details and "resource_id" in service_details:
                source = service_details.get("source")
                resource_id = service_details.get("resource_id")
                await ctx.report_progress(35, 100, f"Service detected: source={source}, resource_id={resource_id}")
            else:
                print(f"DEBUG: Service details validation failed: {service_details}")
                return {
                    "success": False,
                    "error": f"Could not find service with name: {service_name}"
                }
        elif source:
            # Use the provided source directly
            await ctx.report_progress(30, 100, f"Using provided source: {source}")
            print(f"DEBUG: Using provided source: {source}")
        else:
            print("DEBUG: No service identifier provided")
        
        # Step 3: Generate audit log export
        await ctx.report_progress(40, 100, "Generating audit log export...")
        export_result = await _generate_audit_log_export(
            auth, tenant_id=tenant_id, start_date=start_date_str, end_date=end_date_str,
            source=source, actor_id=actor_id, 
            action=action_filter, status=status_filter
        )
        
        if not export_result.get("success"):
            return export_result
        
        export_job = export_result.get("export_job", {})
        job_id = export_job.get("jobId")
        
        if not job_id:
            return {
                "success": False,
                "error": "No job ID received from export generation"
            }
        
        await ctx.report_progress(50, 100, f"Export job created: {job_id}")
        
        # Step 4: Wait for export completion and get download link
        await ctx.report_progress(60, 100, "Waiting for export completion...")
        download_url = await _wait_for_export_completion(ctx, auth, job_id)
        
        if not download_url:
            return {
                "success": False,
                "error": "Export job failed or timed out"
            }
        
        await ctx.report_progress(70, 100, "Export completed, downloading file...")
        
        # Step 5: Download and extract the gzip file
        temp_file_path = await _download_and_extract_logs(ctx, auth, download_url)
        
        if not temp_file_path:
            return {
                "success": False,
                "error": "Failed to download or extract audit logs"
            }
        
        await ctx.report_progress(85, 100, "Analyzing audit logs...")
        
        # Step 6: Analyze and format the logs
        try:
            analysis_result = await _analyze_audit_logs(temp_file_path)
            
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
                await ctx.report_progress(95, 100, "Temporary files cleaned up")
            except Exception as cleanup_error:
                get_tool_logger("audit").warning(f"Failed to cleanup temp file {temp_file_path}: {cleanup_error}")
            
            await ctx.report_progress(100, 100, "Audit log analysis completed")
            
            return {
                "success": True,
                "export_job": export_job,
                "analysis": analysis_result,
                "message": "Audit logs retrieved and analyzed successfully",
                "formatted_summary": _format_audit_summary_for_display(analysis_result)
            }
            
        except Exception as analysis_error:
            # Clean up temp file even if analysis fails
            try:
                os.unlink(temp_file_path)
            except:
                pass
            raise analysis_error
            
    except Exception as e:
        get_tool_logger("audit").error(f"Error in complete audit log workflow: {e}")
        return {"success": False, "error": str(e)}


async def _detect_service_details(auth: DPoDAuth, service_name: str) -> Optional[Dict[str, str]]:
    """Detect service details (source and resource_id) from service name or UUID."""
    try:
        # Use smart identifier resolution for resource_id
        resource_id = await _resolve_service_identifier(auth, service_name, "audit log lookup")
        # Get service instances to find the service details
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/service_instances"
        )
        if response.status_code != 200:
            return None
        services = response.json().get("content", [])
        target_service = None
        for service in services:
            if service.get("service_id") == resource_id:
                target_service = service
                break
        if not target_service:
            return None
        service_type = target_service.get("serviceType")
        partition_serial = target_service.get("partition_serial_number")
        # Determine source based on service type
        if service_type == "ctaas":
            source = "cdsp"
        elif partition_serial:
            source = f"thales/cloudhsm/{partition_serial}"
        else:
            source = None
        return {
            "source": source,
            "resource_id": resource_id
        }
    except Exception as e:
        get_tool_logger("audit").error(f"Error detecting service details: {e}")
        return None


async def _wait_for_export_completion(ctx: Context, auth: DPoDAuth, job_id: str, max_wait_time: int = 300) -> Optional[str]:
    """Wait for export job completion and return download URL."""
    import time
    
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            response = await auth.make_authenticated_request(
                "GET",
                f"/v1/audit-log-exports/{job_id}"
            )
            
            if response.status_code != 200:
                await ctx.report_progress(65, 100, f"Failed to check export status: {response.status_code}")
                return None
            
            export_job = response.json()
            state = export_job.get("state")
            location = export_job.get("location")
            
            if state == "SUCCEEDED" and location:
                return location
            elif state == "FAILED":
                await ctx.report_progress(65, 100, "Export job failed")
                return None
            elif state == "CANCELLED":
                await ctx.report_progress(65, 100, "Export job was cancelled")
                return None
            
            # Wait before checking again
            await ctx.report_progress(65, 100, f"Export job status: {state}, waiting...")
            await asyncio.sleep(10)
            
        except Exception as e:
            get_tool_logger("audit").error(f"Error checking export status: {e}")
            await asyncio.sleep(10)
    
    await ctx.report_progress(65, 100, "Export job timed out")
    return None


async def _download_and_extract_logs(ctx: Context, auth: DPoDAuth, download_url: str) -> Optional[str]:
    """Download gzip file and extract to temporary location."""
    import tempfile
    import httpx
    
    try:
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file = tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.json',
            delete=False,
            dir=temp_dir
        )
        temp_file_path = temp_file.name
        temp_file.close()
        
        await ctx.report_progress(75, 100, f"Downloading to: {temp_file_path}")
        
        # Download the file
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", download_url) as response:
                if response.status_code != 200:
                    raise Exception(f"Download failed with status: {response.status_code}")
                
                with open(temp_file_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        
        await ctx.report_progress(80, 100, "File downloaded, extracting...")
        
        # Check if it's a gzip file and extract if needed
        with open(temp_file_path, 'rb') as f:
            magic = f.read(2)
            f.seek(0)
            
            if magic.startswith(b'\x1f\x8b'):  # gzip magic number
                # Extract gzip content
                with gzip.open(temp_file_path, 'rt', encoding='utf-8') as gz_file:
                    content = gz_file.read()
                
                # Write extracted content back to temp file
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                await ctx.report_progress(82, 100, "Gzip file extracted")
        
        return temp_file_path
        
    except Exception as e:
        get_tool_logger("audit").error(f"Error downloading/extracting logs: {e}")
        # Clean up temp file if it exists
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass
        return None


async def _analyze_audit_logs(temp_file_path: str) -> Dict[str, Any]:
    """Analyze audit logs and return pretty formatted results."""
    
    # LUNA action code descriptions from Thales documentation
    LUNA_ACTION_DESCRIPTIONS = {
        "LUNA_CANCEL_CRYPTO_OPERATION": "Cancels the crypto operation",
        "LUNA_CLONE_AS_SOURCE": "Clones an object from the source token",
        "LUNA_CLONE_AS_TARGET": "Clones an object to the target token",
        "LUNA_CLONE_AS_TARGET_INIT": "Initializes cloning an object to the target token",
        "LUNA_CLONE_CONFIGURE_POLICY": "Enables and disables cloning cipher suites",
        "LUNA_CLONE_GET_POLICY": "Used to query the status and the names of all cloning cipher suites",
        "LUNA_CREATE_OBJECT": "Creates an object",
        "LUNA_DECRYPT": "Decrypts encrypted data",
        "LUNA_DECRYPT_END": "Finishes a decryption operation",
        "LUNA_DECRYPT_INIT": "Initializes a decryption operation",
        "LUNA_DECRYPT_SINGLEPART": "Decrypts encrypted single-part data",
        "LUNA_DERIVE_KEY": "Derives a key from a base key",
        "LUNA_DERIVE_KEY_AND_WRAP": "Derives a key from a base key and wraps (encrypt) the key",
        "LUNA_DESTROY_OBJECT": "Destroys an object",
        "LUNA_DIGEST": "Digests single-part data",
        "LUNA_DIGEST_END": "Finishes a multiple-part digesting operation",
        "LUNA_DIGEST_INIT": "Initializes a message-digesting operation",
        "LUNA_DIGEST_KEY": "Digests a key",
        "LUNA_DIGEST_KEY_VALUE": "Digests a key value",
        "LUNA_ENCRYPT": "Encrypts data",
        "LUNA_ENCRYPT_END": "Finishes a multiple-part encryption operation",
        "LUNA_ENCRYPT_INIT": "Initializes a multiple-part encryption operation",
        "LUNA_ENCRYPT_SINGLEPART": "Encrypts single-part data",
        "LUNA_GENERATE_DOMAIN_PARAM": "Generated domain parameters",
        "LUNA_GENERATE_KEY": "Generates a secret key",
        "LUNA_GENERATE_KEY_PAIR": "Generates a public-key/private-key pair",
        "LUNA_GEN_KCV": "Generate a key check sum value",
        "LUNA_INIT_PIN": "Initializes the users PIN",
        "LUNA_LOGIN": "Logs in to a token",
        "LUNA_MODIFY_OBJECT": "Updates an object",
        "LUNA_PARTITION_INIT": "Initializes the HSM partition",
        "LUNA_PARTITION_ZEROIZE": "Zeroize the HSM partition",
        "LUNA_REPLICATE_AS_SOURCE": "Replicate an object from the source token",
        "LUNA_REPLICATE_AS_TARGET": "Replicate an object to the target token",
        "LUNA_REPLICATE_AS_TARGET_INIT": "Initializes replicating an object to the target token",
        "LUNA_SET_PIN": "Modifies the PIN of the current user",
        "LUNA_SIGN": "Signs data",
        "LUNA_SIGN_END": "Finishes a multi-part sign operation",
        "LUNA_SIGN_INIT": "Initializes a multi-part sign operation",
        "LUNA_SIGN_SINGLEPART": "Signs single-part data",
        "LUNA_UNWRAP_KEY": "Unwraps a key",
        "LUNA_VERIFY": "Verifies a signature on data",
        "LUNA_VERIFY_END": "Finishes a multi-part verification operation",
        "LUNA_VERIFY_INIT": "Initializes a multi-part verification operation",
        "LUNA_VERIFY_SINGLEPART": "Verifies a signature on single-part data",
        "LUNA_WRAP_KEY": "Wraps a key"
    }
    
    # CTAAS/CDSP action descriptions
    CTAAS_ACTION_DESCRIPTIONS = {
        "Create Key Version": "Creates a new version of an existing key",
        "Create Token": "Creates a new authentication token",
        "Create Key": "Creates a new cryptographic key",
        "Update User": "Updates user information or permissions",
        "Create Connection": "Establishes a new connection to the service",
        "Create connection": "Establishes a new connection to the service",
        "Delete Key": "Deletes a cryptographic key",
        "Delete Key Version": "Deletes a specific version of a key",
        "Update Key": "Updates key properties or metadata",
        "Rotate Key": "Rotates a key to a new version",
        "Encrypt": "Encrypts data using a key",
        "Decrypt": "Decrypts data using a key",
        "Sign": "Signs data using a key",
        "Verify": "Verifies a signature",
        "Wrap Key": "Wraps (encrypts) a key for export",
        "Unwrap Key": "Unwraps (decrypts) an imported key",
        "Generate Key": "Generates a new cryptographic key",
        "Import Key": "Imports a key into the service",
        "Export Key": "Exports a key from the service",
        "Get Key": "Retrieves key information",
        "List Keys": "Lists available keys",
        "Create Policy": "Creates a new access policy",
        "Update Policy": "Updates an existing policy",
        "Delete Policy": "Deletes a policy",
        "Create Role": "Creates a new user role",
        "Update Role": "Updates an existing role",
        "Delete Role": "Deletes a user role",
        "Create User": "Creates a new user account",
        "Delete User": "Deletes a user account",
        "Login": "User authentication/login",
        "Logout": "User logout",
        "Change Password": "Changes user password",
        "Reset Password": "Resets user password",
        "Create Certificate": "Creates a new certificate",
        "Delete Certificate": "Deletes a certificate",
        "Update Certificate": "Updates certificate properties",
        "Revoke Certificate": "Revokes a certificate",
        "Create CA": "Creates a new Certificate Authority",
        "Delete CA": "Deletes a Certificate Authority",
        "Update CA": "Updates Certificate Authority properties",
        "Create CSR": "Creates a Certificate Signing Request",
        "Sign CSR": "Signs a Certificate Signing Request",
        "Create Secret": "Creates a new secret",
        "Delete Secret": "Deletes a secret",
        "Update Secret": "Updates secret properties",
        "Get Secret": "Retrieves secret value",
        "List Secrets": "Lists available secrets",
        "Create Vault": "Creates a new vault",
        "Delete Vault": "Deletes a vault",
        "Update Vault": "Updates vault properties",
        "Create Backup": "Creates a backup of data",
        "Restore Backup": "Restores data from backup",
        "Create Snapshot": "Creates a snapshot of current state",
        "Delete Snapshot": "Deletes a snapshot",
        "Create Audit Log": "Creates an audit log entry",
        "Get Audit Logs": "Retrieves audit log entries",
        "Create Event": "Creates a new event",
        "Update Event": "Updates an event",
        "Delete Event": "Deletes an event",
        "Create Alert": "Creates a new alert",
        "Update Alert": "Updates an alert",
        "Delete Alert": "Deletes an alert",
        "Create Rule": "Creates a new rule",
        "Update Rule": "Updates a rule",
        "Delete Rule": "Deletes a rule",
        "Create Group": "Creates a new group",
        "Update Group": "Updates group properties",
        "Delete Group": "Deletes a group",
        "Add User to Group": "Adds a user to a group",
        "Remove User from Group": "Removes a user from a group",
        "Create Permission": "Creates a new permission",
        "Update Permission": "Updates a permission",
        "Delete Permission": "Deletes a permission",
        "Grant Permission": "Grants a permission to a user/role",
        "Revoke Permission": "Revokes a permission from a user/role",
        # Additional actions from CTAAS error reference pages
        "Use Key": "Uses a key for cryptographic operations",
        "Find Keys": "Searches for keys matching criteria",
        "Find Key": "Searches for a specific key",
        "Versions": "Lists key versions",
        "Read Key": "Reads key information",
        "Destroy Key": "Destroys a key permanently",
        "Update Key": "Updates key properties",
        "Create Connection": "Creates a connection to external service",
        "Test Connection": "Tests connectivity to external service",
        "Add SNMP Community": "Adds SNMP community configuration",
        "Update SNMP Community": "Updates SNMP community settings",
        "Add SNMP User": "Adds SNMP user configuration",
        "Add SNMP Management Station": "Adds SNMP management station",
        "Terminating KMIP Connection": "Terminates KMIP connection",
        "RegisterKmipClient": "Registers a KMIP client",
        "CreateKmipClient RegistrationToken": "Creates KMIP client registration token",
        "CreateKmipClient Profile": "Creates KMIP client profile",
        "CreateKmip ClientProfile": "Creates KMIP client profile",
        "Get HSM Server": "Retrieves HSM server information",
        "Find HSM Servers": "Searches for HSM servers",
        "Setup HSM Server": "Sets up HSM server configuration",
        "Add HSM Server": "Adds HSM server to configuration",
        "Delete HSM Server": "Removes HSM server from configuration",
        # CTE (CipherTrust Transparent Encryption) actions
        "Create CTE Policy": "Creates a new CTE policy",
        "Update CTE Policy": "Updates an existing CTE policy",
        "Update CTE PolicyXML": "Updates CTE policy XML configuration",
        "Create CTE PolicyAuditRecord": "Creates a CTE policy audit record",
        "Create CTE SecurityRule": "Creates a new CTE security rule",
        "Create CTE LDTRule": "Creates a new CTE LDT (Logical Data Type) rule",
        "Create CTE KeyMeta": "Creates CTE key metadata",
        "Create CTE KeyRule": "Creates a new CTE key rule",
        "Delete CTE Policy": "Deletes a CTE policy"
    }
    
    try:
        logs = []
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    log_entry = json.loads(line)
                    logs.append(log_entry)
                except json.JSONDecodeError as e:
                    get_tool_logger("audit").warning(f"Invalid JSON on line {line_num}: {e}")
                    continue
        
        if not logs:
            return {
                "total_logs": 0,
                "message": "No audit logs found in the specified time range"
            }
        
        # Note: All filtering (actor_id, action_filter, status_filter) is now done at the API level
        # during export generation, so no additional filtering is needed here
        
        # Analyze logs
        total_logs = len(logs)
        actions = {}
        statuses = {}
        sources = {}
        time_range = {"earliest": None, "latest": None}
        
        for log in logs:
            # Count actions
            action = log.get("action", "UNKNOWN")
            actions[action] = actions.get(action, 0) + 1
            
            # Count statuses
            status = log.get("status", "UNKNOWN")
            statuses[status] = statuses.get(status, 0) + 1
            
            # Count sources
            source = log.get("source", "UNKNOWN")
            sources[source] = sources.get(source, 0) + 1
            
            # Track time range
            log_time = log.get("time")
            if log_time:
                if not time_range["earliest"] or log_time < time_range["earliest"]:
                    time_range["earliest"] = log_time
                if not time_range["latest"] or log_time > time_range["latest"]:
                    time_range["latest"] = log_time
        
        # Create action summary - descriptions only for LUNA actions (CTAAS has too many)
        action_summary = {}
        for action, count in actions.items():
            # Only add descriptions for LUNA actions to keep output clean
            description = LUNA_ACTION_DESCRIPTIONS.get(action)
            if description:
                action_summary[action] = {
                    "count": count,
                    "description": description
                }
            else:
                # For CTAAS actions, just show the count
                action_summary[action] = {
                    "count": count
                }
        
        # Sort actions by count (descending)
        sorted_actions = sorted(action_summary.items(), key=lambda x: x[1]["count"], reverse=True)
        
        # Create pretty formatted summary
        summary = {
            "total_logs": total_logs,
            "time_range": time_range,
            "action_summary": {
                "total_unique_actions": len(actions),
                "most_common_actions": sorted_actions[:10],  # Top 10 actions
                "all_actions": action_summary
            },
            "status_summary": {
                "total_unique_statuses": len(statuses),
                "status_breakdown": dict(sorted(statuses.items()))
            },
            "source_summary": {
                "total_unique_sources": len(sources),
                "source_breakdown": dict(sorted(sources.items()))
            },
            "recent_activity": logs[:10] if len(logs) > 10 else logs  # Show last 10 logs
        }
        
        return summary
        
    except Exception as e:
        get_tool_logger("audit").error(f"Error analyzing audit logs: {e}")
        return {
            "error": f"Failed to analyze audit logs: {str(e)}",
            "total_logs": 0
        }


async def _generate_audit_log_export(
    auth: DPoDAuth,
    tenant_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: Optional[str] = None,
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Generate an audit log export file for a specified time period.
    
    Creates an audit log export job that will generate a downloadable file containing
    audit logs for the specified time period with optional filtering.
    
    Args:
        tenant_id: Optional UUID of tenant to filter logs (if not provided, logs from all accessible tenants will be exported)
        start_date: Start date/time in RFC3339 format (e.g., "2022-03-14T00:00:00Z")
        end_date: End date/time in RFC3339 format (e.g., "2022-03-14T16:00:00Z")
        source: Filter by origin/source of the action (e.g., "thales/cloudhsm/123456789")
        actor_id: Filter by actor ID (e.g., client UUID for HSM services)
        action: Filter by specific action (e.g., "Create Key", "Delete User")
        status: Filter by status (e.g., "success", "LUNA_RET_OK", error codes)
        
    Returns:
        Export job information including:
        - jobId: Unique identifier for the export job
        - startedAt: When the job started
        - endedAt: When the job completed
        - state: Current job state (ACTIVE, SUCCEEDED, FAILED)
        - location: Download URL when complete (null while processing)
        
    Note: 
        - Time period can be up to 31 days maximum
        - Job processing may take several minutes
        - Use get_audit_log_export to check job status and get download URL
        - All filters (source, resourceId, actorId, action, status) are applied during export generation
        - If tenant_id is not provided, logs from all accessible tenants will be exported
        
    Requires: dpod.tenant.spadmin or dpod.tenant.api_spadmin scope
    """
    try:
        # Validate required parameters
        validated_tenant_id = None
        if tenant_id:
            validated_tenant_id = validate_uuid(tenant_id, "tenant_id")
        
        # Make start_date and end_date required as per OpenAPI spec
        if not start_date or not end_date:
            return {
                "success": False, 
                "error": "start_date and end_date are required parameters"
            }
        
        validated_start_date = validate_string_param(start_date, "Start Date", min_length=20, max_length=30)
        validated_end_date = validate_string_param(end_date, "End Date", min_length=20, max_length=30)
        
        # Validate optional filters
        validated_source = None
        if source:
            validated_source = validate_string_param(source, "Source", min_length=1, max_length=100)
        
        validated_actor_id = None
        if actor_id:
            validated_actor_id = validate_string_param(actor_id, "Actor ID", min_length=1, max_length=100)
            
        validated_action = None
        if action:
            validated_action = validate_string_param(action, "Action", min_length=1, max_length=100)
            
        validated_status = None
        if status:
            validated_status = validate_string_param(status, "Status", min_length=1, max_length=100)
        
        # Prepare export data - use parameter names that match OpenAPI spec
        export_data = {
            "from": validated_start_date,
            "to": validated_end_date
        }
        
        # Add optional filters if provided
        if validated_tenant_id:
            export_data["tenantId"] = validated_tenant_id
            
        if validated_source:
            export_data["source"] = validated_source
            
        if validated_actor_id:
            export_data["actorId"] = validated_actor_id
            
        if validated_action:
            export_data["action"] = validated_action
            
        if validated_status:
            export_data["status"] = validated_status
        
        # Make API request - use endpoint that matches OpenAPI spec
        response = await auth.make_authenticated_request(
            "POST",
            "/v1/audit-log-exports",
            json_data=export_data
        )
        
        if response.status_code not in [200, 201]:
            return {
                "success": False,
                "error": f"Failed to generate audit log export: {response.status_code}",
                "details": response.text
            }
        
        export_job = response.json()
        
        return {
            "success": True,
            "export_job": {
                "jobId": export_job.get("jobId"),
                "startedAt": export_job.get("startedAt"),
                "endedAt": export_job.get("endedAt"),
                "state": export_job.get("state"),
                "location": export_job.get("location")
            },
            "message": "Audit log export job created successfully"
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_audit_log_export(auth: DPoDAuth, export_id: str) -> Dict[str, Any]:
    """Get the status of an audit log export job.
    
    Returns the current status and download information for an audit log export job.
    
    Args:
        export_id: The unique identifier of the export job from generate_audit_log_export
        
    Returns:
        Export job status including:
        - jobId: Unique identifier for the export job
        - startedAt: When the job started
        - endedAt: When the job completed
        - state: Current job state (ACTIVE, SUCCEEDED, FAILED)
        - location: Download URL when complete (null while processing)
        - progress: Job completion percentage (0-100)
        
    Note:
        - Use generate_audit_log_export to create new export jobs
        - Check this endpoint periodically to monitor job progress
        - Download URL is only available when state is SUCCEEDED
    """
    try:
        # Validate parameters
        validated_export_id = validate_uuid(export_id, "export_id")
        
        # Make API request - use endpoint that matches OpenAPI spec
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/audit-log-exports/{validated_export_id}"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get audit log export: {response.status_code}",
                "details": response.text
            }
        
        export_job = response.json()
        
        return {
            "success": True,
            "export_job": {
                "jobId": export_job.get("jobId"),
                "startedAt": export_job.get("startedAt"),
                "endedAt": export_job.get("endedAt"),
                "state": export_job.get("state"),
                "location": export_job.get("location"),
                "progress": export_job.get("progress", 0)
            }
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_audit_log_status(auth: DPoDAuth, export_id: str) -> Dict[str, Any]:
    """Get the status of an audit log export job (alias for get_audit_log_export).
    
    This is an alias for get_audit_log_export to maintain compatibility.
    """
    return await _get_audit_log_export(auth, export_id=export_id)


async def _get_audit_log_result(auth: DPoDAuth, export_id: str) -> Dict[str, Any]:
    """Get the result of an audit log export job (alias for get_audit_log_export).
    
    This is an alias for get_audit_log_export to maintain compatibility.
    """
    return await _get_audit_log_export(auth, export_id=export_id) 


def _format_audit_summary_for_display(analysis_result: Dict[str, Any]) -> str:
    """Format audit analysis results into a user-friendly display string."""
    try:
        if not analysis_result or "error" in analysis_result:
            return f"Error: {analysis_result.get('error', 'Unknown error')}"
        
        total_logs = analysis_result.get("total_logs", 0)
        if total_logs == 0:
            return "No audit logs found in the specified time range"
        
        # Format time range
        time_range = analysis_result.get("time_range", {})
        earliest = time_range.get("earliest", "Unknown")
        latest = time_range.get("latest", "Unknown")
        
        # Format action summary
        action_summary = analysis_result.get("action_summary", {})
        most_common_actions = action_summary.get("most_common_actions", [])
        
        # Build the formatted output
        output = []
        output.append(f"📊 **Audit Log Summary**")
        output.append(f"Total logs: {total_logs:,}")
        output.append(f"Time period: {earliest} to {latest}")
        output.append("")
        
        if most_common_actions:
            output.append("🔍 **Most Common Operations:**")
            for action, details in most_common_actions:
                count = details["count"]
                description = details["description"]
                output.append(f"  • {action}: {count:,} operations - {description}")
            output.append("")
        
        # Add status summary
        status_summary = analysis_result.get("status_summary", {})
        status_breakdown = status_summary.get("status_breakdown", {})
        if status_breakdown:
            output.append("✅ **Status Breakdown:**")
            for status, count in sorted(status_breakdown.items(), key=lambda x: x[1], reverse=True):
                output.append(f"  • {status}: {count:,}")
            output.append("")
        
        # Add source summary
        source_summary = analysis_result.get("source_summary", {})
        source_breakdown = source_summary.get("source_breakdown", {})
        if source_breakdown:
            output.append("🏢 **Source Breakdown:**")
            for source, count in sorted(source_breakdown.items(), key=lambda x: x[1], reverse=True):
                output.append(f"  • {source}: {count:,}")
            output.append("")
        
        # Add recent activity summary
        recent_activity = analysis_result.get("recent_activity", [])
        if recent_activity:
            output.append("🕒 **Recent Activity (Last 10 operations):**")
            for i, log in enumerate(recent_activity[:10], 1):
                action = log.get("action", "UNKNOWN")
                time = log.get("time", "Unknown")
                status = log.get("status", "Unknown")
                source = log.get("source", "Unknown")
                
                # Get action description
                action_desc = ""
                if "action_summary" in analysis_result and "all_actions" in analysis_result["action_summary"]:
                    all_actions = analysis_result["action_summary"]["all_actions"]
                    if action in all_actions:
                        action_desc = f" - {all_actions[action]['description']}"
                
                output.append(f"  {i}. {time} | {action}{action_desc}")
                output.append(f"     Status: {status} | Source: {source}")
                if i < len(recent_activity[:10]):
                    output.append("")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error formatting summary: {str(e)}" 