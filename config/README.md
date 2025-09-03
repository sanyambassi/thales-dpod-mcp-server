# MCP Server Configuration

This directory contains configuration files for the Thales DPoD MCP Server.

## Configuration Files

- `mcp-config.json` - Standard Python configuration
- `mcp-config-uv.json` - UV package manager configuration

## Transport Types

### STDIO Transport
For STDIO transport, the MCP client will start the server process directly using the `command` and `args` specified in the config.

### HTTP Transport
For HTTP transport, you need to:

1. **Start the server manually first:**
   ```bash
   # Using standard Python
   python main.py --transport streamable-http --host 0.0.0.0 --port 8000
   
   # Using UV
   uv run python main.py --transport streamable-http --host 0.0.0.0 --port 8000
   ```

2. **Configure environment variables:**
   ```bash
   export DPOD_CLIENT_ID="your_client_id_here"
   export DPOD_CLIENT_SECRET="your_client_secret_here"
   export DPOD_BASE_URL="https://thales.na.market.dpondemand.io"
   export DPOD_AUTH_URL="https://access.dpondemand.io/oauth/v1/token"
   export LOG_LEVEL="INFO"
   ```

3. **Use the HTTP configuration:**
   The config file will contain only the URL to connect to the running server:
   ```json
   "thales-dpod-http-cloud": {
     "url": "http://localhost:8000/mcp"
   }
   ```

## Environment Variables

Set these environment variables before starting the server:

- `DPOD_CLIENT_ID` - Your DPoD OAuth client ID
- `DPOD_CLIENT_SECRET` - Your DPoD OAuth client secret
- `DPOD_BASE_URL` - DPoD API base URL for your region
- `DPOD_AUTH_URL` - OAuth token endpoint
- `DPOD_OAUTH_SCOPE` - OAuth scope (optional, defaults to tenant)
- `DPOD_READ_ONLY_MODE` - Enable read-only mode (optional, defaults to false)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Usage Examples

### Cloud Configuration (North America)
```bash
export DPOD_CLIENT_ID="your_na_client_id"
export DPOD_CLIENT_SECRET="your_na_client_secret"
export DPOD_BASE_URL="https://thales.na.market.dpondemand.io"
export DPOD_AUTH_URL="https://access.dpondemand.io/oauth/v1/token"
export LOG_LEVEL="INFO"
python main.py --transport streamable-http --port 8000
```

### Cloud Configuration (Europe)
```bash
export DPOD_CLIENT_ID="your_eu_client_id"
export DPOD_CLIENT_SECRET="your_eu_client_secret"
export DPOD_BASE_URL="https://thales.eu.market.dpondemand.io"
export DPOD_AUTH_URL="https://access.dpondemand.io/oauth/v1/token"
export LOG_LEVEL="INFO"
python main.py --transport streamable-http --port 8000
```

### Read-Only Mode
```bash
export DPOD_CLIENT_ID="your_client_id"
export DPOD_CLIENT_SECRET="your_client_secret"
export DPOD_BASE_URL="https://thales.na.market.dpondemand.io"
export DPOD_AUTH_URL="https://access.dpondemand.io/oauth/v1/token"
export DPOD_READ_ONLY_MODE="true"
export LOG_LEVEL="INFO"
python main.py --transport streamable-http --port 8000
```

## Regional Endpoints

The DPoD platform supports multiple regions. Update the `DPOD_BASE_URL` accordingly:

- **North America**: `https://thales.na.market.dpondemand.io`
- **Europe**: `https://thales.eu.market.dpondemand.io`

## Security Notes

- Never commit your actual credentials to version control
- Use environment variables or secure configuration management
- Consider using read-only mode for production monitoring
- Ensure your DPoD account has appropriate API scopes for your use case

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify your DPoD credentials are correct
   - Check that your account has the required API scopes
   - Ensure network access to DPoD endpoints

2. **Connection Issues**
   - Verify the correct regional endpoint URL
   - Check firewall settings
   - Ensure the server is running before connecting

3. **Scope Issues**
   - The server automatically detects available scopes
   - Some tools may not be available depending on your account permissions
   - Check the server logs for scope detection results