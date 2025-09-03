"""Tile Management Tools for DPoD MCP Server"""

import logging
from typing import Dict, Any, Optional
from fastmcp import Context
from pydantic import Field

from ...core.auth import DPoDAuth
from ...core.validation import (
    validate_string_param, validate_uuid, validate_optional_param,
    ValidationError, validate_integer_param
)


async def manage_tiles(
    ctx: Context,
    action: str = Field(description="Operation to perform: list_tiles, search_tiles, get_tile_details, get_tile_plans"),
    tile_id: Optional[str] = Field(default=None, description="UUID of tile (required for get_tile_details, get_tile_plans)"),
    page: int = Field(default=0, description="Page number for list operations (0-based)"),
    size: int = Field(default=50, description="Page size for list operations (max 100)"),
    service_type: Optional[str] = Field(default=None, description="Service type filter for list operations"),
    category: Optional[str] = Field(default=None, description="Category filter for list operations"),
    provisionable: bool = Field(default=False, description="Filter for provisionable tiles only"),
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID filter for list operations")
) -> Dict[str, Any]:
    """Service catalog tile management operations.
    
    Actions:
    - list_tiles: List all available service tiles with pagination and filtering
    - search_tiles: Search tiles with advanced filtering options
    - get_tile_details: Get details of a specific service tile
    - get_tile_plans: Get creation example for a specific service tile
    """
    # Get config and scope_manager from dependency injection
    from ...core.dependency_injection import get_config, get_scope_manager
    config = get_config()
    scope_manager = get_scope_manager()
    
    # Create auth instance using injected config
    auth = DPoDAuth(config)
    
    tool_logger = logging.getLogger("dpod.tools.tiles")
    tool_logger.info(f"Starting tile operation: {action}")
    
    try:
        # 1. MCP Context Logging (NEW)
        await ctx.info(f"Starting tile operation: {action}")
        
        # 2. Progress Reporting (EXISTING)
        await ctx.report_progress(0, 100, f"Starting tile operation: {action}")
        
        # All tile operations are read-only
        read_actions = {"list_tiles", "search_tiles", "get_tile_details", "get_tile_plans"}
        
        if action not in read_actions:
            await ctx.error(f"Unknown tile action: {action}")
            raise ValueError(f"Unknown tile action: {action}")
        
        if action == "list_tiles":
            # Enhanced progress reporting for listing tiles
            await ctx.report_progress(15, 100, "Starting tile listing workflow...")
            await ctx.info("Starting tile listing workflow...")
            
            await ctx.report_progress(25, 100, "Querying service catalog...")
            await ctx.info(f"Retrieving tiles (page {page}, size {size})")
            
            # Query service catalog (tiles) - available service types
            result = await _list_tiles(auth, page=page, size=size, provisionable=provisionable, tenant_id=tenant_id, service_type=service_type)
            
            await ctx.report_progress(90, 100, "Tile listing completed, finalizing...")
            await ctx.info("Tile listing completed successfully")
            
        elif action == "search_tiles":
            # Enhanced progress reporting for searching tiles
            await ctx.report_progress(15, 100, "Starting tile search workflow...")
            await ctx.info("Starting tile search workflow...")
            
            await ctx.report_progress(25, 100, "Executing advanced tile search...")
            await ctx.info(f"Searching tiles with filters (page {page}, size {size})")
            
            # Advanced tile search with filtering
            result = await _search_tiles(auth, page=page, size=size, tenant_id=tenant_id, provisionable=provisionable, service_type=service_type)
            
            await ctx.report_progress(90, 100, "Tile search completed, finalizing...")
            await ctx.info("Tile search completed successfully")
            
        elif action == "get_tile_details":
            # Enhanced progress reporting for getting tile details
            await ctx.report_progress(15, 100, "Starting tile details workflow...")
            await ctx.info("Starting tile details workflow...")
            
            if not tile_id:
                await ctx.error("Tile ID is required for get_tile_details action")
                raise ValueError("tile_id required for get_tile_details action")
            
            await ctx.report_progress(25, 100, "Retrieving tile details...")
            await ctx.info(f"Retrieving details for tile: {tile_id}")
            
            result = await _get_tile_details(auth, tile_id=tile_id, provisionable=provisionable)
            
            await ctx.report_progress(90, 100, "Tile details retrieval completed, finalizing...")
            await ctx.info("Tile details retrieval completed successfully")
            
        elif action == "get_tile_plans":
            # Enhanced progress reporting for getting tile plans
            await ctx.report_progress(15, 100, "Starting tile plans workflow...")
            await ctx.info("Starting tile plans workflow...")
            
            if not tile_id:
                await ctx.error("Tile ID is required for get_tile_plans action")
                raise ValueError("tile_id required for get_tile_plans action")
            
            await ctx.report_progress(25, 100, "Retrieving tile plans...")
            await ctx.info(f"Retrieving plans for tile: {tile_id}")
            
            result = await _get_tile_plans(auth, tile_id=tile_id)
            
            await ctx.report_progress(90, 100, "Tile plans retrieval completed, finalizing...")
            await ctx.info("Tile plans retrieval completed successfully")
            
        else:
            raise ValueError(f"Unknown tile action: {action}")
        
        # 3. MCP Context Completion Logging (NEW)
        await ctx.info(f"Completed tile operation: {action}")
        await ctx.report_progress(100, 100, f"Completed tile operation: {action}")
        tool_logger.info(f"Completed tile operation: {action}")
        return result
        
    except Exception as e:
        # 4. MCP Context Error Logging (NEW)
        await ctx.error(f"Error in tile operation {action}: {str(e)}")
        tool_logger.error(f"Error in tile operation {action}: {e}")
        raise


async def _list_tiles(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """List available service tiles from the catalog."""
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
        ) or 20
        
        provisionable = kwargs.get("provisionable", False)
        tenant_id = validate_optional_param(
            kwargs.get("tenant_id"),
            lambda x: validate_uuid(x, "Tenant ID"),
            "tenant_id"
        )
        
        service_type = validate_optional_param(
            kwargs.get("service_type"),
            lambda x: validate_string_param(x, "Service Type", min_length=1, max_length=100),
            "service_type"
        )
        
        # Prepare query parameters
        params = {"page": page, "size": size}
        if provisionable:
            params["provisionable"] = "true"
        if tenant_id:
            params["tenantId"] = tenant_id
        if service_type:
            params["serviceType"] = service_type
        
        # Make API request to tiles endpoint
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/tiles",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to list tiles: {response.status_code}",
                "details": response.text
            }
        
        tiles_data = response.json()
        
        return {
            "success": True,
            "tiles": tiles_data.get("content", []),
            "total_elements": tiles_data.get("totalElements", 0),
            "total_pages": tiles_data.get("totalPages", 0),
            "page": page,
            "size": size
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _search_tiles(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Advanced tile search with filtering."""
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
        ) or 20
        
        provisionable = kwargs.get("provisionable", False)
        tenant_id = validate_optional_param(
            kwargs.get("tenant_id"),
            lambda x: validate_uuid(x, "Tenant ID"),
            "tenant_id"
        )
        
        service_type = validate_optional_param(
            kwargs.get("service_type"),
            lambda x: validate_string_param(x, "Service Type", min_length=1, max_length=100),
            "service_type"
        )
        
        # Prepare query parameters for search
        params = {"page": page, "size": size}
        if provisionable:
            params["provisionable"] = "true"
        if tenant_id:
            params["tenantId"] = tenant_id
        if service_type:
            params["serviceType"] = service_type
        
        # Make API request to tiles endpoint with search parameters
        response = await auth.make_authenticated_request(
            "GET",
            "/v1/tiles",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to search tiles: {response.status_code}",
                "details": response.text
            }
        
        tiles_data = response.json()
        
        return {
            "success": True,
            "tiles": tiles_data.get("content", []),
            "total_elements": tiles_data.get("totalElements", 0),
            "total_pages": tiles_data.get("totalPages", 0),
            "page": page,
            "size": size,
            "search_filters": {
                "provisionable": provisionable,
                "tenant_id": tenant_id,
                "service_type": service_type
            }
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tile_details(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get detailed information about a specific tile."""
    try:
        # Validate parameters
        tile_id = validate_uuid(kwargs.get("tile_id"), "tile_id")
        provisionable = kwargs.get("provisionable", False)
        
        # Prepare query parameters
        params = {}
        if provisionable:
            params["provisionable"] = "true"
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tiles/{tile_id}",
            params=params
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tile details: {response.status_code}",
                "details": response.text
            }
        
        tile_data = response.json()
        
        return {
            "success": True,
            "tile": tile_data
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_tile_plans(auth: DPoDAuth, **kwargs) -> Dict[str, Any]:
    """Get available plans for a specific tile."""
    try:
        # Validate parameters
        tile_id = validate_uuid(kwargs.get("tile_id"), "tile_id")
        
        # Make API request
        response = await auth.make_authenticated_request(
            "GET",
            f"/v1/tiles/{tile_id}/plans"
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get tile plans: {response.status_code}",
                "details": response.text
            }
        
        plans_data = response.json()
        
        return {
            "success": True,
            "tile_id": tile_id,
            "plans": plans_data,
            "total_plans": len(plans_data) if isinstance(plans_data, list) else 1
        }
        
    except ValidationError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)} 