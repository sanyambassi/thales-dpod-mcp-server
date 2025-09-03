#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Dependency Injection Module

Provides module-level access to configuration and scope manager for tools.
"""

from typing import Optional
from .config import DPoDConfig
from .scope_manager import ScopeManager

_config: Optional[DPoDConfig] = None
_scope_manager: Optional[ScopeManager] = None

def set_dependencies(config: DPoDConfig, scope_manager: ScopeManager) -> None:
    """Set the dependencies for tools to access."""
    global _config, _scope_manager
    _config = config
    _scope_manager = scope_manager

def get_config() -> DPoDConfig:
    """Get the current configuration instance."""
    if _config is None:
        raise RuntimeError("Dependencies not set. Call set_dependencies() first.")
    return _config

def get_scope_manager() -> ScopeManager:
    """Get the current scope manager instance."""
    if _scope_manager is None:
        raise RuntimeError("Dependencies not set. Call set_dependencies() first.")
    return _scope_manager

def clear_dependencies() -> None:
    """Clear the stored dependencies."""
    global _config, _scope_manager
    _config = None
    _scope_manager = None 