#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Main Entry Point

FastMCP-based server for DPoD management operations with scope-based access control.
"""

import asyncio
import argparse
import logging
import signal
import sys
import time
import warnings
from pathlib import Path

# Suppress all warnings to keep output clean
warnings.filterwarnings("ignore")

from fastmcp import FastMCP, Context

from src.dpod_mcp_server.core.config import DPoDConfig
from src.dpod_mcp_server.core.auth import DPoDAuth
from src.dpod_mcp_server.core.scope_manager import ScopeManager
from src.dpod_mcp_server.tools import get_sorted_tools
from src.dpod_mcp_server.prompts import (
    get_service_logs,
    create_hsm_service,
    create_ctaas_service,
    create_hsm_client
)
from src.dpod_mcp_server.resources import server_status, health_check


def setup_logging(config: DPoDConfig, transport_mode: str) -> logging.Logger:
    """Set up logging configuration."""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create tools subdirectory
    tools_logs_dir = logs_dir / "tools"
    tools_logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger first
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Configure handlers based on transport mode
    handlers = []
    
    # Always add file handler for server.log
    server_file_handler = logging.FileHandler(logs_dir / "server.log", mode='a')  # Changed from 'w' to 'a' for append
    server_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handlers.append(server_file_handler)
    
    # Only add stdout handler when NOT using stdio transport to avoid JSON protocol interference
    if transport_mode != "stdio":
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        handlers.append(stdout_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Create tool-specific loggers with friendly names
    tool_logger_configs = {
        "tenant": "tenant-management.log",
        "scopes": "scope-management.log", 
        "dpod_availability": "dpod-availability.log",
        "audit": "audit-logs.log",
        "report": "reports.log",
        "service": "service-management.log",
        "tiles": "service-catalog.log",
        "user": "user-management.log",
        "subscriber_group": "subscriber-group-management.log",
        "subscriptions": "subscription-management.log",
        "service_agreements": "service-agreement-management.log",
        "products": "product-management.log",
        "pricing": "pricing-management.log",
        "credentials": "credential-management.log"
    }
    
    for tool_name, log_filename in tool_logger_configs.items():
        tool_logger = logging.getLogger(f"dpod.tools.{tool_name}")
        tool_logger.setLevel(getattr(logging, config.log_level.upper()))
        
        # Clear any existing handlers to avoid duplicates
        tool_logger.handlers.clear()
        
        # Add file handler for each tool in the tools subdirectory
        tool_handler = logging.FileHandler(tools_logs_dir / log_filename, mode='a')  # Changed from 'w' to 'a' for append
        tool_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        tool_logger.addHandler(tool_handler)
        
        # Ensure the logger doesn't propagate to root logger to avoid duplicate messages
        tool_logger.propagate = False
    
    # Get the server logger and ensure it's properly configured
    server_logger = logging.getLogger("dpod.server")
    server_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    return server_logger


async def main():
    """Main server function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Thales DPoD (Data Protection on Demand) MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage:
  python main.py                                          # Start with stdio transport
  python main.py --transport streamable-http --port 8000  # Start streamable HTTP server on all interfaces
  python main.py --transport streamable-http --host 0.0.0.0 --port 8000  # Start HTTP server on all interfaces
  python main.py --transport streamable-http --host 192.168.1.100 --port 8000  # Start HTTP server on specific IP
  python main.py --read-only                              # Start in read-only mode
  python main.py --log-level DEBUG                        # Enable debug logging

Note: --host and --port are only applicable with --transport streamable-http
        """
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host IP address to bind to for HTTP transport (default: 0.0.0.0 for all interfaces, only applicable with --transport streamable-http)"
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Enable read-only mode"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = DPoDConfig()
    config.log_level = args.log_level
    config.read_only_mode = args.read_only
    
    # Set up logging first
    logger = setup_logging(config, args.transport)
    
    # Early configuration validation for OAuth credentials
    if not config.is_oauth_configured():
        # For stdio, print to stdout before exiting
        if args.transport == "stdio":
            print("DPoD Credentials not configured.")
            print("Please set DPOD_CLIENT_ID and DPOD_CLIENT_SECRET in .env file or environment variables.")
            print("Server startup aborted.")
        else:
            # For HTTP mode, print clean error message
            print("DPoD Credentials not configured.")
            print("Please set DPOD_CLIENT_ID and DPOD_CLIENT_SECRET in .env file or environment variables.")
            print("Server startup aborted.")
        
        sys.exit(1)
    
    # Configuration loaded
    logger.info(f"Configuration: {config.dpod_base_url}, Read-only: {config.read_only_mode}")
    logger.info(f"Scope management: Always enabled (automatic)")
    
    # Log transport information correctly
    if args.transport == "stdio":
        logger.info(f"Transport mode: {args.transport} (no port needed)")
    else:
        logger.info(f"Transport mode: {args.transport}, Host: {args.host}, Port: {args.port}")
    
    # Log OAuth configuration status
    if config.is_oauth_configured():
        logger.info("OAuth credentials: Configured [OK]")
    else:
        logger.error("OAuth credentials: Not configured [MISSING]")
        logger.error("Server will fail at startup without valid credentials")
    
    # Initialize authentication
    auth = DPoDAuth(config)
    
    # Initialize scope management (always enabled)
    logger.info("Initializing scope management...")
    scope_manager = ScopeManager(config, auth)
    
    # Set up module-level access for tools
    import src.dpod_mcp_server.core.dependency_injection as di
    di.set_dependencies(config, scope_manager)
    
    # Get sorted tools for consistent alphabetical registration
    sorted_tools = get_sorted_tools()
    
    # Detect scopes at startup
    logger.info("Authenticating and detecting API scopes...")
    
    try:
        scope_result = await scope_manager.detect_scopes()
        
        if not scope_result.get("success"):
            # For stdio, print to stdout before exiting
            if args.transport == "stdio":
                print("DPoD Authentication failed.")
                print("Please check your credentials and network connectivity.")
                print("Server startup aborted.")
            else:
                # For HTTP mode, print clean error message
                print("DPoD Authentication failed.")
                print("Please check your credentials and network connectivity.")
                print("Server startup aborted.")
            
            sys.exit(1)
            
    except Exception as e:
        # For stdio, print to stdout before exiting
        if args.transport == "stdio":
            print("DPoD Authentication failed.")
            print("Please check your credentials and network connectivity.")
            print("Server startup aborted.")
        else:
            # For HTTP mode, print clean error message
            print("DPoD Authentication failed.")
            print("Please check your credentials and network connectivity.")
            print("Server startup aborted.")
        
        sys.exit(1)
    
    detected_scopes = scope_result.get("detected_scopes", [])
    primary_scope = scope_result.get("primary_scope")
    allowed_tools = scope_result.get("allowed_tools", [])
    
    logger.info(f"Authentication successful")
    logger.info(f"Detected API scopes: {detected_scopes}")
    logger.info(f"Primary scope: {primary_scope}")
    logger.info(f"Tools will be filtered at action level based on scope permissions")
    
    # Log detailed tool permissions
    logger.info("Tool permissions summary (action-level filtering):")
    permissions_summary = scope_manager.get_tool_permissions_summary()
    for tool_name, perms in permissions_summary.items():
        scopes = perms.get("scopes", [])
        actions = perms.get("actions", {})
        total_actions = sum(len(acts) for acts in actions.values())
        logger.info(f"  - {tool_name}: {len(scopes)} scope(s), {total_actions} total actions")
        # Log specific actions for each scope
        for scope, scope_actions in actions.items():
            logger.info(f"    - {scope}: {', '.join(scope_actions[:5])}{'...' if len(scope_actions) > 5 else ''}")
    
    # Create MCP server
    mcp = FastMCP("dpod-server")
    
    # Register all tools with scope validation wrapper and dependency injection
    logger.info("Registering all tools with scope validation:")
    registered_count = 0
    for tool_name, tool_func in sorted_tools.items():
        try:
            # Apply scope validation wrapper
            from src.dpod_mcp_server.core.scope_wrapper import scope_validate
            wrapped_tool = scope_validate(scope_manager, tool_name=tool_name)(tool_func)
            
            mcp.tool(tags={"management"})(wrapped_tool)
            logger.info(f"  + Registered: {tool_name} (with scope validation)")
            registered_count += 1
        except Exception as e:
            logger.error(f"  ! Failed to register {tool_name}: {e}")
    
    logger.info(f"Successfully registered {registered_count} tools with scope validation")
    
    # Register prompts
    mcp.prompt()(get_service_logs)
    mcp.prompt()(create_hsm_service)
    mcp.prompt()(create_ctaas_service)
    mcp.prompt()(create_hsm_client)
    
    # Register resources
    mcp.resource("dpod://server/status")(server_status)
    mcp.resource("dpod://server/health")(health_check)
    
    # Only register HTTP endpoints when using HTTP transport
    if args.transport == "streamable-http":
        @mcp.custom_route("/health", methods=["GET"])
        async def http_health_check(request):
            """HTTP health check endpoint for monitoring tools."""
            try:
                # Get basic server info
                health_data = {
                    "status": "healthy",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "server": {
                        "name": "Thales DPoD (Data Protection on Demand) MCP Server",
                        "version": "2.0.0",
                        "transport": args.transport,
                        "host": args.host if args.transport == "streamable-http" else None,
                        "port": args.port if args.transport == "streamable-http" else None
                    },
                    "tools": {
                        "count": len(sorted_tools),
                        "available": list(sorted_tools.keys())
                    },
                    "configuration": {
                        "read_only_mode": config.read_only_mode,
                        "dpod_base_url": config.dpod_base_url
                    }
                }
                
                # Add scope information if available
                scope_summary = scope_manager.get_scope_summary()
                health_data["scopes"] = {
                    "detected": scope_summary.get("detected_scopes", []),
                    "primary": scope_summary.get("primary_scope"),
                    "filtering_mode": "action_level",
                    "total_tools": len(sorted_tools),
                    "scope_restricted_tools": scope_summary.get("allowed_tools", [])
                }
                
                # Return JSON response for Starlette
                from starlette.responses import JSONResponse
                return JSONResponse(health_data)
                
            except Exception as e:
                error_data = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
                }
                from starlette.responses import JSONResponse
                return JSONResponse(error_data, status_code=500)
        
        @mcp.custom_route("/tools", methods=["GET"])
        async def http_tools_list(request):
            """HTTP tools endpoint for quick tool discovery."""
            try:
                tools_info = []
                for tool_name, tool_func in sorted_tools.items():
                    # All tools are registered but actions are filtered at runtime
                    available = True  # Tool is always available
                    
                    # Get tool description if available
                    description = "DPoD management tool"
                    if hasattr(tool_func, '__doc__') and tool_func.__doc__:
                        doc_lines = tool_func.__doc__.strip().split('\n')
                        if doc_lines:
                            description = doc_lines[0]
                    
                    # Get allowed actions for current scope
                    allowed_actions = scope_manager.get_allowed_actions(tool_name)
                    
                    tools_info.append({
                        "name": tool_name,
                        "description": description,
                        "type": "management_tool",
                        "available": available,
                        "allowed_actions": allowed_actions if available else []
                    })
                
                tools_data = {
                    "server": "Thales DPoD MCP Server",
                    "transport": args.transport,
                    "host": args.host if args.transport == "streamable-http" else None,
                    "port": args.port if args.transport == "streamable-http" else None,
                    "total_tools": len(tools_info),
                    "filtering_mode": "action_level",
                    "tools": tools_info,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
                }
                
                # Add scope information if available
                scope_summary = scope_manager.get_scope_summary()
                tools_data["scopes"] = {
                    "detected": scope_summary.get("detected_scopes", []),
                    "primary": scope_summary.get("primary_scope"),
                    "note": "All tools are registered but actions are filtered based on detected scopes"
                }
                
                from starlette.responses import JSONResponse
                return JSONResponse(tools_data)
                
            except Exception as e:
                error_data = {
                    "error": str(e),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
                }
                from starlette.responses import JSONResponse
                return JSONResponse(error_data, status_code=500)
        
        logger.info("HTTP endpoints registered: /health and /tools")
    
    # Handle shutdown signals
    import signal
    
    shutdown_requested = False
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        nonlocal shutdown_requested
        logger.info("Graceful shutdown initiated")
        shutdown_requested = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.transport == "stdio":
            logger.info("Starting stdio transport")
            logger.info("Press Ctrl+C for graceful shutdown")
            await mcp.run_stdio_async()
        elif args.transport == "streamable-http":
            logger.info(f"Starting streamable HTTP transport on {args.host}:{args.port}")
            logger.info("Press Ctrl+C for graceful shutdown")
            
            # Show binding information
            if args.host == "0.0.0.0":
                logger.info(f"Server binding to all interfaces on port {args.port}")
                logger.info(f"External access: http://localhost:{args.port}/mcp")
                logger.info(f"Network access: http://[your-ip]:{args.port}/mcp")
            else:
                logger.info(f"Server binding to {args.host}:{args.port}")
                logger.info(f"Access URL: http://{args.host}:{args.port}/mcp")
            
            # Start HTTP server
            server_task = asyncio.create_task(
                mcp.run_http_async(host=args.host, port=args.port)
            )
            
            try:
                # Wait for shutdown signal or server completion
                while not shutdown_requested and not server_task.done():
                    await asyncio.sleep(0.1)
                
                if shutdown_requested:
                    logger.info("Shutdown requested, stopping HTTP server...")
                    server_task.cancel()
                    try:
                        await server_task
                    except asyncio.CancelledError:
                        pass
                    logger.info("HTTP server stopped gracefully")
                else:
                    logger.info("HTTP server completed normally")
                    
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received during HTTP server operation")
                shutdown_requested = True
                logger.info("Stopping HTTP server...")
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
                logger.info("HTTP server stopped due to keyboard interrupt")
        else:
            logger.error(f"Unknown transport mode: {args.transport}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down gracefully...")
        shutdown_requested = True
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        # Clean up resources
        logger.info("Cleaning up resources...")
        
        # Close scope manager auth instance
        if 'scope_manager' in locals() and hasattr(scope_manager, 'auth'):
            try:
                await scope_manager.auth.close()
                logger.info("Scope manager auth closed")
            except Exception as e:
                logger.warning(f"Error closing scope manager auth: {e}")
        
        # Close direct auth instance if it exists
        if 'auth' in locals():
            try:
                await auth.close()
                logger.info("Direct auth instance closed")
            except Exception as e:
                logger.warning(f"Error closing auth: {e}")
        
        # Ensure all log messages are flushed to files
        try:
            # Flush all handlers
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                if hasattr(handler, 'close'):
                    handler.close()
            
            # Also flush tool-specific loggers
            for tool_name in ["tenant", "scopes", "dpod_availability", "audit", "report", "service", "tiles"]:
                tool_logger = logging.getLogger(f"dpod.tools.{tool_name}")
                for handler in tool_logger.handlers:
                    if hasattr(handler, 'flush'):
                        handler.flush()
                    if hasattr(handler, 'close'):
                        handler.close()
                        
        except Exception as e:
            logger.warning(f"Error during logging cleanup: {e}")
        
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        basic_logger = logging.getLogger("dpod.startup")
        
        import tracemalloc
        tracemalloc.start()
        
        asyncio.run(main())
    except KeyboardInterrupt:
        basic_logger.info("Server stopped by user")
    except Exception as e:
        basic_logger.error(f"Fatal error: {e}")
        sys.exit(1)