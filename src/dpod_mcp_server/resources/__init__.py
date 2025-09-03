"""
DPoD MCP Server Resources Module

This module contains status and configuration resources.
"""

from .server_resources import server_status, health_check

__all__ = [
    "server_status",
    "health_check"
] 