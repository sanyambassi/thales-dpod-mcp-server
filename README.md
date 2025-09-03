# Thales DPoD MCP Server

A comprehensive FastMCP-based server for Thales DPoD (Data Protection on Demand) management operations with scope-based access control and actionable AI prompts.

## Features

- **Scope-Based Access Control**: Automatic detection and enforcement of DPoD API scopes
- **FastMCP Compliance**: Full MCP/FastMCP protocol support
- **Transport Modes**: stdio and streamable-http transport support
- **Action-Level Filtering**: Granular permission control based on detected scopes
- **OAuth 2.0 Authentication**: Secure client credentials flow
- **Comprehensive Logging**: Structured logging with file and console output
- **Actionable AI Prompts**: Ready-to-use prompts for immediate DPoD operations
- **Service Management**: Full lifecycle management of DPoD services
- **Audit Logging**: Comprehensive audit log operations and analysis
- **Tenant Management**: Multi-tenant operations and configuration
- **System Monitoring**: Health checks and system status
- **Reporting**: Service analytics and compliance reporting
- **Smart Identifiers**: Service management by name or UUID

## Architecture

```
src/dpod_mcp_server/
├── core/                   # Core functionality
│   ├── auth.py            # Authentication and API client
│   ├── config.py          # Configuration management
│   ├── scope_manager.py   # Scope-based access control
│   ├── scope_wrapper.py   # Scope validation wrapper
│   ├── validation.py      # Parameter validation
│   └── dependency_injection.py # Dependency injection
├── tools/                  # MCP tool implementations
│   ├── services/          # Service management tools
│   ├── audit/             # Audit log tools
│   ├── tiles/             # Service catalog tools
│   ├── tenants/           # Tenant management tools
│   ├── users/             # User management tools
│   ├── scopes/            # Scope management tools
│   ├── dpod_availability/ # DPoD platform status
│   └── reports/           # Reporting tools
├── prompts/                # AI assistant prompts
│   └── service_prompts.py # Actionable service prompts
└── resources/              # Static resources
    └── server_resources.py # Server status and health
```

## Quick Start

### Prerequisites

- Python 3.11 or higher
- UV package manager (recommended) or pip
- Thales DPoD account with API access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sanyambassi/thales-dpod-mcp-server.git
   cd thales-dpod-mcp-server
   ```

2. **Set up environment**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your DPoD credentials
   nano .env  # or use your preferred editor
   ```

3. **Install dependencies**

   **Using UV (Recommended):**
   ```bash
   # Install UV if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install dependencies
   uv sync
   ```

   **Using pip:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**

   **Using UV:**
   ```bash
   # stdio transport (default)
   uv run python main.py
   
   # HTTP transport on default port 8000, binding to all interfaces
   uv run python main.py --transport streamable-http --port 8000
   
   # HTTP transport on specific port, binding to all interfaces
   uv run python main.py --transport streamable-http --host 0.0.0.0 --port 8000
   
   # HTTP transport on specific IP address and port
   uv run python main.py --transport streamable-http --host 192.168.1.100 --port 8000
   
   # HTTP transport on localhost only
   uv run python main.py --transport streamable-http --host 127.0.0.1 --port 8000
   ```

   **Using pip:**
   ```bash
   # stdio transport (default)
   python main.py
   
   # HTTP transport on default port 8000, binding to all interfaces
   python main.py --transport streamable-http --port 8000
   
   # HTTP transport on specific port, binding to all interfaces
   python main.py --transport streamable-http --host 0.0.0.0 --port 8000
   
   # HTTP transport on specific IP address and port
   python main.py --transport streamable-http --host 192.168.1.100 --port 8000
   
   # HTTP transport on localhost only
   python main.py --transport streamable-http --host 127.0.0.1 --port 8000
   ```

## Configuration

### Environment Variables

Required environment variables in `.env`:

- `DPOD_CLIENT_ID`: Your DPoD OAuth client ID
- `DPOD_CLIENT_SECRET`: Your DPoD OAuth client secret
- `DPOD_BASE_URL`: DPoD API base URL for your region
- `DPOD_AUTH_URL`: OAuth token endpoint

Optional environment variables:

- `DPOD_OAUTH_SCOPE`: OAuth scope (defaults to tenant API access)
- `DPOD_READ_ONLY_MODE`: Enable read-only mode (default: false)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, default: INFO)

### Configuration File

Create a `.env` file in the project root:

```env
# Required DPoD Configuration
DPOD_CLIENT_ID=your_client_id
DPOD_CLIENT_SECRET=your_client_secret
DPOD_BASE_URL=https://thales.na.market.dpondemand.io
DPOD_AUTH_URL=https://access.dpondemand.io/oauth/v1/token

# Optional Configuration
DPOD_OAUTH_SCOPE=tenant
DPOD_READ_ONLY_MODE=false
LOG_LEVEL=INFO
```

### Regional Configuration

The server supports different DPoD regions. Update the URLs accordingly:

- **North America**: `https://thales.na.market.dpondemand.io`
- **Europe**: `https://thales.eu.market.dpondemand.io`
- **Asia Pacific**: `https://thales.ap.market.dpondemand.io`

## Usage

### Starting the Server

```bash
# Standard mode with automatic scope management
python main.py

# Read-only mode
python main.py --read-only

# Custom port
python main.py --port 8080

# Debug logging
python main.py --log-level DEBUG

# HTTP transport with custom host and port
python main.py --transport streamable-http --host 127.0.0.1 --port 8080
```

### Scope-Based Access Control

The server **automatically** implements **scope-based access control** based on DPoD API scopes:

- **`dpod.tenant.api_spadmin`**: Full API access (Service Provider Administrator)
- **`dpod.tenant.api_appowner`**: Limited API access (Application Owner)  
- **`dpod.tenant.api_service`**: Service-specific API access

**Features:**
- **Automatic Startup Authentication**: Server automatically authenticates at startup and detects available scopes
- **Automatic Tool Filtering**: Only tools supported by the detected scope(s) are registered
- **Action-Level Control**: Individual actions within tools are restricted based on scope
- **Multiple Scope Support**: Union of permissions when multiple API scopes are detected
- **Mandatory Scope Detection**: Server cannot start without valid API scopes

**Scope Detection:**
- Server automatically authenticates with DPoD at startup
- Extracts API scopes from OAuth token
- Determines primary scope (highest privilege)
- Builds tool permission matrix
- Logs detailed scope information

**Note**: Scope management is **automatic and mandatory** - no configuration required. The server will automatically adapt to different user credentials and provide appropriate access levels.

### Transport Modes

- **stdio**: Standard input/output for MCP clients
- **streamable-http**: HTTP server with MCP over HTTP

### Command-Line Options

The server supports the following command-line arguments:

- `--transport`: Transport mode (`stdio` or `streamable-http`, default: `stdio`)
- `--port`: Port for HTTP transport (default: 8000, only applicable with `--transport streamable-http`)
- `--host`: Host IP address to bind to (default: `0.0.0.0` for all interfaces, only applicable with `--transport streamable-http`)
- `--read-only`: Enable read-only mode
- `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, default: `INFO`)

**Note**: `--host` and `--port` arguments are only applicable when using `--transport streamable-http`. They have no effect with stdio transport.

### Host Binding Examples

- `--host 0.0.0.0`: Bind to all network interfaces (default, allows external access)
- `--host 127.0.0.1`: Bind to localhost only (restricts to local access)
- `--host 192.168.1.100`: Bind to specific network interface IP

## Available Tools

### Service Management
- `manage_services`: Full service lifecycle management
- `manage_tiles`: Service catalog and discovery

### Audit and Compliance
- `manage_audit_logs`: Audit log export and analysis
- `manage_reports`: Compliance and usage reporting

### System Operations
- `manage_system`: Health checks and system status
- `manage_tenants`: Tenant management operations
- `check_dpod_availability`: DPoD platform status and incident monitoring

### User and Scope Management
- `manage_users`: User management operations
- `manage_scopes`: Scope management and validation

**Note**: Tool availability depends on the detected API scope(s). Tools not supported by the current scope are not registered.

## Actionable AI Prompts

The server includes **3 actionable prompts** that AI assistants can use to immediately execute DPoD operations:

### 1. `get_service_logs` - Retrieve Service Audit Logs
Get comprehensive audit logs for a specific DPoD service within a date range.

**Parameters:**
- `service_name` (required): Name of the service to get logs for
- `start_date` (required): Start date for logs in RFC 3339 format (YYYY-MM-DDTHH:MM:SSZ)
- `end_date` (required): End date for logs in RFC 3339 format (YYYY-MM-DDTHH:MM:SSZ)

### 2. `create_hsm_service` - Provision HSM Service
Create a new Hardware Security Module (HSM) service with comprehensive configuration.

**Parameters:**
- `service_type` (required): Type of HSM service (key_vault, hsm_key_export, ms_sql_server, etc.)
- `service_name` (required): Name for the service (4-45 characters)
- `service_plan` (required): Service plan (single_hsm, dual_hsm, multi_hsm, trial, standard)
- `device_type` (optional): Device type (cryptovisor or cryptovisor_fips, defaults to cryptovisor_fips)
- `description` (optional): Service description

### 3. `create_ctaas_service` - Provision CTAAS Service
Create a new CipherTrust Data Security Platform as a Service (CTAAS) in a specific cluster.

**Parameters:**
- `cluster` (required): Cluster for the CTAAS service deployment (gcp-europe-west3, gcp-us-east1)
- `service_name` (required): Name for the service (4-45 characters)
- `initial_admin_password` (required): Initial admin password for the CTAAS service (minimum 8 characters)
- `service_plan` (optional): Service plan (defaults to "Tenant")
- `description` (optional): Service description

### 4. `create_hsm_client` - Create and Download HSM Service Client
Create an HSM service client and download the configuration file to a specified location.

**Parameters:**
- `service_name` (required): Name of the HSM service to bind the client to
- `client_name` (required): Name for the client (1-64 characters, must be unique for the service)
- `download_path` (optional): Directory path where the client configuration file should be saved (defaults to system temp directory)
- `os_type` (optional): Operating system type (linux or windows, defaults to linux)

For detailed information about these prompts, see [docs/PROMPTS.md](docs/PROMPTS.md).

## MCP Client Integration

The server implements the MCP protocol and can be used with any MCP-compatible client.

**Scope Information:**
- HTTP endpoints (`/health`, `/tools`) include scope information
- Tool availability is clearly indicated
- Allowed actions per tool are listed
- Scope detection results are logged at startup

## Development

### Project Structure

The server is organized into logical modules:

- **Core**: Authentication, configuration, validation, and scope management
- **Tools**: MCP tool implementations
- **Prompts**: AI assistant guidance
- **Resources**: Static configuration and templates

### Adding New Tools

1. Create a new tool file in the appropriate directory
2. Implement the tool function with proper validation
3. Add scope permissions to `ScopeManager.tool_scope_mappings`
4. Register the tool in the main server
5. Add documentation and examples

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function parameters
- Include comprehensive docstrings
- Implement proper error handling

## Security

### Authentication
- OAuth 2.0 client credentials flow
- Automatic token refresh
- Scope-based permission validation

### Read-Only Mode
- Protects against destructive operations
- Can be combined with scope management

### Scope Management
- **API-Level Access Control**: Tools and actions restricted based on OAuth scopes
- **Startup Validation**: Scope detection and validation at server startup
- **Tool Registration**: Only supported tools are registered with MCP
- **Action Filtering**: Individual actions within tools are scope-restricted
- **Multiple Scope Support**: Union of permissions across all detected scopes

**Scope Hierarchy:**
1. `dpod.tenant.api_spadmin` - Full administrative access
2. `dpod.tenant.api_appowner` - Application owner access
3. `dpod.tenant.api_service` - Service-specific access

**Security Benefits:**
- **Principle of Least Privilege**: Users only see tools they can actually use
- **Scope Isolation**: Service-level scopes cannot access tenant-wide operations
- **Automatic Enforcement**: No manual permission checking required in tools
- **Audit Trail**: All scope decisions are logged at startup

## Troubleshooting

### Common Issues

#### 1. **Server Fails Silently or Exits Immediately**

**Symptoms:**
- Server starts but exits without error message
- No clear indication of what went wrong
- Process terminates immediately

**Common Causes:**
- Missing or empty `.env` file
- Missing DPoD credentials (`DPOD_CLIENT_ID`, `DPOD_CLIENT_SECRET`)
- Invalid DPoD API endpoints
- Network connectivity issues

**Solutions:**
```bash
# 1. Check if .env file exists and has content
ls -la .env
cat .env

# 2. Copy and configure the example file
cp .env.example .env
# Edit .env with your actual DPoD credentials

# 3. Verify required variables are set
grep -E "DPOD_CLIENT_ID|DPOD_CLIENT_SECRET" .env

# 4. Test with verbose logging
python main.py --transport stdio --log-level DEBUG
```

#### 2. **Authentication Errors**

**Symptoms:**
- "Scope detection failed" errors
- "OAuth token refresh failed" messages
- "Server cannot start without valid API scopes"

**Solutions:**
- Verify your DPoD credentials are correct
- Check that your DPoD account has the required API scopes
- Ensure network access to DPoD endpoints
- Verify your DPoD subscription is active

#### 3. **Transport Mode Issues**

**Symptoms:**
- "Invalid transport mode" errors
- Port binding failures
- Host binding issues

**Solutions:**
- Use `--transport stdio` for local development
- Use `--transport streamable-http` for network access
- Ensure ports are not already in use
- Check firewall settings for external access

### Getting Help

If you continue to experience issues:

1. **Check the logs:** Look in `logs/server.log` and `logs/tools/` for detailed error messages
2. **Enable debug logging:** Use `--log-level DEBUG` for verbose output
3. **Verify configuration:** Ensure all required environment variables are set
4. **Test connectivity:** Verify network access to DPoD endpoints

## License

See [LICENSE](LICENSE) for license information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Documentation

Additional documentation is available in the `docs/` folder:

- **[docs/PROMPTS.md](docs/prompts.md)** - Detailed guide to actionable AI prompts
- **[docs/testing.md](docs/testing.md)** - Manual JSON-RPC testing guide

## Support

For support and questions:
- Check the [troubleshooting section](#troubleshooting)
- Review the logs in the `logs/` directory
- Open an issue on GitHub

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.