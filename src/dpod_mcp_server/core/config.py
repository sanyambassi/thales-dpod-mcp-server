#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Core Configuration

Handles environment variables, configuration validation, and server settings.
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DPoDConfig:
    """Configuration management for Thales DPoD MCP Server."""
    
    def __init__(self):
        # Server Configuration
        self.server_name = os.getenv("MCP_SERVER_NAME", "Thales DPoD Server")
        self.server_version = os.getenv("MCP_SERVER_VERSION", "1.0.0")
        
        # Transport Configuration
        self.transport = os.getenv("TRANSPORT", "stdio").lower()
        self.http_host = os.getenv("HTTP_HOST", "localhost")
        self.http_port = int(os.getenv("HTTP_PORT", "8000"))
        
        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s")
        self.log_file = os.getenv("LOG_FILE")
        
        # Read-Only Mode
        self.read_only_mode = os.getenv("READ_ONLY_MODE", "false").lower() == "true"
        
        # DPoD API Configuration
        self.dpod_base_url = os.getenv("DPOD_BASE_URL", "https://thales.na.market.dpondemand.io")
        self.dpod_auth_url = os.getenv("DPOD_AUTH_URL", "https://access.dpondemand.io/oauth/v1/token")
        
        # OAuth Configuration
        self.client_id = os.getenv("DPOD_CLIENT_ID")
        self.client_secret = os.getenv("DPOD_CLIENT_SECRET")
        
        # OAuth Scopes (will be populated dynamically from token)
        self.oauth_scopes = []
        
        # MCP Protocol Configuration
        self.supported_mcp_versions = ["2025-06-18", "2025-03-26", "2024-11-05"]
        self.default_mcp_version = "2025-06-18"
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration settings."""
        # Validate transport mode
        if self.transport not in ["stdio", "streamable-http"]:
            raise ValueError(f"Invalid transport mode: {self.transport}. Must be 'stdio' or 'streamable-http'")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. Must be one of {valid_log_levels}")
        
        # Validate HTTP port
        if not (1 <= self.http_port <= 65535):
            raise ValueError(f"Invalid HTTP port: {self.http_port}. Must be between 1 and 65535")
        
        # Validate DPoD URLs
        if not self.dpod_base_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid DPoD base URL: {self.dpod_base_url}")
        if not self.dpod_auth_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid DPoD auth URL: {self.dpod_auth_url}")
        
        # Validate OAuth credentials for HTTP transport
        if self.transport == "streamable-http" and not self.is_oauth_configured():
            raise ValueError("DPOD_CLIENT_ID and DPOD_CLIENT_SECRET are required for HTTP transport")
        
        # For stdio, warn but don't fail during config validation
        if self.transport == "stdio" and not self.is_oauth_configured():
            # No warning - let the main error handling provide clean messages
            pass
    
    def is_oauth_configured(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self.client_id and self.client_secret)
    
    def get_oauth_config(self) -> Dict[str, str]:
        """Get OAuth configuration."""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "auth_url": self.dpod_auth_url
        }
    
    def get_current_scope(self) -> str:
        """Get the current OAuth scope being used."""
        return "auto_detected"
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information for logging and status."""
        return {
            "name": self.server_name,
            "version": self.server_version,
            "transport": self.transport,
            "http_host": self.http_host,
            "http_port": self.http_port,
            "log_level": self.log_level,
            "read_only_mode": self.read_only_mode,
            "oauth_configured": self.is_oauth_configured(),
            "dpod_base_url": self.dpod_base_url,
            "dpod_auth_url": self.dpod_auth_url,
            "supported_mcp_versions": self.supported_mcp_versions,
            "default_mcp_version": self.default_mcp_version
        } 