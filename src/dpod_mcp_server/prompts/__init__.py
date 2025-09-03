"""
DPoD MCP Server Prompts Module

Provides actionable prompt templates for AI assistants to use DPoD tools.
"""

from .service_prompts import (
    get_service_logs,
    create_hsm_service,
    create_ctaas_service,
    create_hsm_client
)

__all__ = [
    "get_service_logs",
    "create_hsm_service", 
    "create_ctaas_service",
    "create_hsm_client"
] 