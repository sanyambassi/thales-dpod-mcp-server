"""
Shared logging utilities for DPoD MCP Server tools.
"""
import logging
from pathlib import Path


def get_tool_logger(tool_name: str):
    """Get a tool logger, ensuring it's properly configured.
    
    Args:
        tool_name: The tool name (e.g., 'audit', 'service', 'pricing')
        
    Returns:
        A properly configured logger instance
    """
    logger = logging.getLogger(f"dpod.tools.{tool_name}")
    
    # Always ensure the logger is properly configured, even if it already has handlers
    # This is needed because the MCP server might not have set up the handlers properly
    # or there might be timing issues with the logging configuration
    if not logger.handlers or not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        try:
            from pathlib import Path
            logs_dir = Path("logs")
            tools_logs_dir = logs_dir / "tools"
            tools_logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Map tool names to log filenames (matching main.py configuration)
            log_filename_map = {
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
            
            log_filename = log_filename_map.get(tool_name, f"{tool_name}.log")
            
            # Add a basic file handler
            handler = logging.FileHandler(tools_logs_dir / log_filename, mode='a')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
            
            # Ensure the handler is flushed immediately
            handler.flush()
        except Exception:
            # If we can't configure it, just return the basic logger
            pass
    
    return logger