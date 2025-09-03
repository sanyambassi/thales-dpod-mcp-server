"""
Server Resources for DPoD MCP Server

Provides server status and health check resources with dynamic capability discovery.
"""

import time
from fastmcp import Context


async def server_status(ctx: Context) -> str:
    """Current server status and health information with dynamic capability discovery."""
    try:
        # Check authentication
        auth_healthy = False
        try:
            auth = ctx.get("auth")
            if auth:
                token = await auth.get_access_token()
                auth_healthy = bool(token)
        except Exception:
            pass
        
        # Dynamic discovery of server capabilities
        try:
            mcp = ctx.get("mcp")
            if mcp:
                tools = await mcp.get_tools()
                prompts = await mcp.get_prompts()
                resources = await mcp.get_resources()
            else:
                tools = []
                prompts = []
                resources = []
        except Exception:
            # Fallback if discovery fails
            tools = []
            prompts = []
            resources = []
        
        status = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "server_name": "Thales DPoD MCP Server",
            "version": "2.0.0",
            "authentication": "healthy" if auth_healthy else "degraded",
            "capabilities": {
                "tools": len(tools),
                "prompts": len(prompts),
                "resources": len(resources)
            }
        }
        
        return f"""# Thales DPoD Server Status

**Status**: {'Healthy' if auth_healthy else 'Degraded'}
**Timestamp**: {status['timestamp']}
**Version**: {status['version']}

## Capabilities
- **Tools**: {status['capabilities']['tools']} Management Tools
- **Prompts**: {status['capabilities']['prompts']} Interactive Guides
- **Resources**: {status['capabilities']['resources']} Status & Configuration

## Authentication
- **Status**: {status['authentication']}
- **OAuth**: {'Active' if auth_healthy else 'Failed'}

## Available Tools
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools[:5]])}{'...' if len(tools) > 5 else ''}

## Available Prompts
{chr(10).join([f"- {prompt.name}: {prompt.description}" for prompt in prompts[:3]])}{'...' if len(prompts) > 3 else ''}
"""
        
    except Exception as e:
        return f"# Server Status Error\n\n**Error**: {str(e)}\n\nPlease check server logs for details."


async def health_check(ctx: Context) -> str:
    """Health check for monitoring and load balancers with dynamic capability discovery."""
    try:
        # Check authentication status
        auth_status = False
        try:
            auth = ctx.get("auth")
            if auth:
                token = await auth.get_access_token()
                auth_status = bool(token)
        except Exception:
            auth_status = False
        
        # Dynamic discovery of server capabilities
        try:
            mcp = ctx.get("mcp")
            if mcp:
                tools = await mcp.get_tools()
                prompts = await mcp.get_prompts()
                resources = await mcp.get_resources()
            else:
                tools = []
                prompts = []
                resources = []
        except Exception:
            # Fallback if discovery fails
            tools = []
            prompts = []
            resources = []
        
        health_data = {
            "status": "healthy" if auth_status else "degraded",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "version": "2.0.0",
            "authentication": "healthy" if auth_status else "failed",
            "capabilities": {
                "tools": len(tools),
                "prompts": len(prompts),
                "resources": len(resources)
            }
        }
        
        return f"""# Health Check

**Overall Status**: {'Healthy' if auth_status else 'Degraded'}
**Timestamp**: {health_data['timestamp']}
**Version**: {health_data['version']}

## Component Health
- **Authentication**: {health_data['authentication']}
- **Tools Registry**: Active ({health_data['capabilities']['tools']} tools)
- **Prompts Registry**: Active ({health_data['capabilities']['prompts']} prompts)
- **Resources Registry**: Active ({health_data['capabilities']['resources']} resources)

## Capability Summary
- **Management Tools**: {health_data['capabilities']['tools']}
- **Interactive Guides**: {health_data['capabilities']['prompts']}
- **Status Resources**: {health_data['capabilities']['resources']}

## Recommendations
{'Server is operating normally' if auth_status else 'Check authentication configuration and credentials'}
"""
        
    except Exception as e:
        return f"# Health Check Error\n\n**Error**: {str(e)}\n\n**Status**: unhealthy\n**Recommendation**: Check server logs and configuration" 