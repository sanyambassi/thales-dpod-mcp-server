# Thales DPoD MCP Server

A comprehensive FastMCP-based server for Thales DPoD (Data Protection on Demand) management operations with scope-based access control and actionable AI prompts.

## 🎥 See It In Action

**▶️ [Watch the Demo Video](https://www.youtube.com/watch?v=X5VOalQvQQw)** - Discover how AI-powered automation revolutionizes your DPoD workflows!

---

## Quick Install (Cursor AI)
**Click Below**

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=thales-dpod-stdio-na&config=eyJjb21tYW5kIjoicHl0aG9uIG1haW4ucHkgLS10cmFuc3BvcnQgc3RkaW8iLCJlbnYiOnsiRFBPRF9DTElFTlRfSUQiOiJ5b3VyX2NsaWVudF9pZF9oZXJlIiwiRFBPRF9DTElFTlRfU0VDUkVUIjoieW91cl9jbGllbnRfc2VjcmV0X2hlcmUiLCJEUE9EX0JBU0VfVVJMIjoiaHR0cHM6Ly90aGFsZXMubmEubWFya2V0LmRwb25kZW1hbmQuaW8iLCJEUE9EX0FVVEhfVVJMIjoiaHR0cHM6Ly9hY2Nlc3MuZHBvbmRlbWFuZC5pby9vYXV0aC92MS90b2tlbiIsIkxPR19MRVZFTCI6IklORk8ifX0%3D)


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
- **Tenant Management**: Tenant related operations for api_spadmin scope
- **System Monitoring**: Health checks and system status

## Architecture

```
src/dpod_mcp_server/
├── core/                   # Core functionality
│   ├── auth.py            # Authentication and API client
│   ├── config.py          # Configuration management
│   ├── scope_manager.py   # Scope-based access control
│   ├── scope_wrapper.py   # Scope validation wrapper
│   ├── validation.py      # Parameter validation
│   ├── dependency_injection.py # Dependency injection
│   └── logging_utils.py   # Logging utilities
├── tools/                  # MCP tool implementations
│   ├── services/          # Service management tools
│   ├── audit/             # Audit log tools
│   ├── tiles/             # Service catalog tools
│   ├── tenants/           # Tenant management tools
│   ├── users/             # User management tools
│   ├── scopes/            # Scope management tools
│   ├── dpod_availability/ # DPoD platform status
│   ├── reports/           # Reporting tools
│   ├── credentials/       # Credential management tools
│   ├── products/          # Product catalog tools
│   ├── pricing/           # Pricing management tools
│   ├── service_agreements/ # Service agreement tools
│   ├── subscriber_groups/ # Subscriber group tools
│   ├── subscriptions/     # Subscription management tools
│   └── authentication/    # Authentication tools
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

   # Windows
   copy .env.example .env
   
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
   
   # HTTP transport
   uv run python main.py --transport streamable-http --port 8000
   ```

   **Using pip:**
   ```bash
   # stdio transport (default)
   python main.py
   
   # HTTP transport
   python main.py --transport streamable-http --port 8000
   ```

## Configuration

### Environment Variables

Required environment variables in `.env`:

- `DPOD_CLIENT_ID`: Your DPoD OAuth client ID
- `DPOD_CLIENT_SECRET`: Your DPoD OAuth client secret
- `DPOD_BASE_URL`: DPoD API base URL for your region
- `DPOD_AUTH_URL`: OAuth token endpoint

Optional environment variables:

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
DPOD_READ_ONLY_MODE=false
LOG_LEVEL=INFO
```

### Regional Configuration

The server supports different DPoD regions. Update the URLs accordingly:

- **North America**: `https://thales.na.market.dpondemand.io`
- **Europe**: `https://thales.eu.market.dpondemand.io`

## Usage

### Scope-Based Access Control

The server **automatically** implements **scope-based access control** based on DPoD API scopes:

- **`dpod.tenant.api_spadmin`**: Full API access (Service Provider Administrator)
- **`dpod.tenant.api_appowner`**: Limited API access (Application Owner)  
- **`dpod.tenant.api_service`**: Service-specific API access

**Features:**
- **Automatic Startup Authentication**: Server automatically authenticates at startup and detects available scopes
- **Action-Level Control**: Individual actions within tools are restricted based on scope
- **Multiple Scope Support**: Union of permissions when multiple API scopes are detected
- **Mandatory Scope Detection**: Server cannot start without valid API scopes

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

## Available Tools

The server provides **14 comprehensive tools** for DPoD management operations:

### Service Management
- `manage_services`: Full service lifecycle management (create, read, update, delete, client binding)
- `manage_tiles`: Service catalog and discovery (browse available service types)

### Audit and Compliance
- `manage_audit_logs`: Audit log export, download, and analysis with flexible filtering
- `manage_reports`: Compliance and usage reporting

### System Operations
- `manage_tenants`: Tenant management operations
- `check_dpod_availability`: DPoD platform status and incident monitoring
- `manage_credentials`: Credential management operations

### User and Access Management
- `manage_users`: User management operations
- `manage_scopes`: Scope management and validation
- `manage_subscriber_groups`: Subscriber group management
- `manage_subscriptions`: Subscription management

### Product and Pricing
- `manage_products`: Product catalog and service plans
- `manage_pricing`: Pricing information and calculations
- `manage_service_agreements`: Service agreement management

## Actionable AI Prompts

The server includes **4 actionable prompts** that AI assistants can use to immediately execute DPoD operations:

For detailed information about these prompts, see [prompts](docs/prompts.md).

## Example Prompts for AI Assistants

Here are example prompts you can send to AI assistants/chatbots to demonstrate the DPoD MCP Server capabilities:

### Service Management Examples

**Create an HSM Service:**
```
"Create a new HSM key vault service named 'MySecureVault' with a single HSM plan and cryptovisor_fips device type."
```

**List All Services:**
```
"Show me all the DPoD services currently deployed in my account."
```

**Get Service Details:**
```
"Get detailed information about the service named 'MySecureVault' including its status and configuration."
```

**Create HSM Client:**
```
"Create a linux client named 'webapp-client' for the HSM service 'MySecureVault' and download the configuration file."
```

### Audit and Compliance Examples

**Get Service Logs:**
```
"Get audit logs for the service 'MySecureVault' from January 1, 2025 to January 31, 2025."
```

**Get All Service Logs:**
```
"Show me all audit logs from March 1, 2025 to March 15, 2025 for all services."
```

**Get Filtered Logs:**
```
"Get audit logs for all CDSP services from last week, filtering for successful operations only."
```

**Export Audit Logs:**
```
"Export audit logs for HSM service 'MySecureVault' from the past 30 days and download them."
```

### Service Catalog and Discovery Examples

**Browse Available Services:**
```
"Show me all available HSM service types I can deploy."
```

**Get Service Plans:**
```
"What service plans are available for the key_vault HSM service type?"
```

**Get Service Details:**
```
"Show me detailed information about the ctaas service type including pricing and requirements."
```

### System Monitoring Examples

**Check Platform Status:**
```
"Is the DPoD platform currently operational? Are there any incidents or maintenance windows?"
```

**Check Service State**
```
"Check the Status of all my deployed services."
```

**Delete Service:**
```
"Delete the test HSM service named 'TestVault'."
```

**Create CTAAS Service:**
```
"Create a new CTAAS service named 'CDSPaaS_service' in the gcp-europe-west3 cluster with initial admin password 'SecurePass@123'."
```

### Multi-Step Workflow Examples

**Complete HSM Setup:**
```
"1. Create an HSM key vault service named 'ProductionVault' with single HSM plan
2. Wait for it to be provisioned
3. Create a windows client named 'app-server' for this service
4. Download the client configuration file
5. Show me the final service status"
```

**Service Discovery and Planning:**
```
"1. Show me all available HSM service types
2. Get pricing information for single_hsm and dual_hsm plans for US."
```

**DPoD Service availability:**
```
"Is there a platform outage? Check the DPoD availability status and any active incidents."
```

## MCP Client Integration

The server can be used with any MCP-compatible client. For information about how to configure MCP clients like Claude Desktop, Cursor AI and Google gemini, see [config](config/README.md).

## Development

### Project Structure

The server is organized into logical modules:

- **Core**: Authentication, configuration, validation, and scope management
- **Tools**: MCP tool implementations
- **Prompts**: MCP prompts

## Security

### Authentication
- OAuth 2.0 client credentials flow
- Automatic token refresh
- Scope-based permission validation

### Read-Only Mode
- Protects against destructive operations
- Can be combined with scope management

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Documentation

Additional documentation is available in the `docs/` folder:

- **[Prompts](docs/prompts.md)** - Detailed guide to actionable AI prompts
- **[Testing](docs/testing.md)** - Manual JSON-RPC testing guide

## Support

For support and questions:
- Check the [troubleshooting section](#troubleshooting)
- Review the logs in the `logs/` directory
- Open an issue on GitHub

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.