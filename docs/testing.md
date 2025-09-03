# Manual Testing Guide

This guide provides step-by-step instructions for manually testing the Thales DPoD MCP Server using JSON-RPC protocol over stdio transport.

## Prerequisites

1. **Server Setup**: Ensure the DPoD MCP server is properly configured with valid credentials
2. **Environment**: Have a terminal/command prompt ready for JSON-RPC communication
3. **DPoD Access**: Valid DPoD account with appropriate API scopes

## Testing Setup

### 1. Start the Server

Start the server in stdio mode for testing:

```bash
# Using UV (recommended)
uv run python main.py --transport stdio --log-level DEBUG

# Using pip
python main.py --transport stdio --log-level DEBUG
```

The server will wait for JSON-RPC messages on stdin and respond on stdout.

## JSON-RPC Testing Steps

### Step 1: Protocol Initialization

Send the initialization request to establish the MCP protocol connection:

```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "id": 1,
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "Test Client", "version": "1.0.0"}
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "tools": {},
      "prompts": {},
      "resources": {}
    },
    "serverInfo": {
      "name": "thales-dpod-mcp-server",
      "version": "1.0.0"
    }
  }
}
```

### Step 2: Send Initialized Notification

After successful initialization, send the initialized notification:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized",
  "params": {}
}
```

**Expected Response:** No response (notification only)

### Step 3: List Available Tools

Request a list of all available tools:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 3
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "tools": [
      {
        "name": "manage_services",
        "description": "Manage DPoD services lifecycle",
        "inputSchema": {
          "type": "object",
          "properties": {
            "action": {"type": "string", "enum": ["list", "get", "create", "update", "delete"]},
            "service_name": {"type": "string"},
            "service_type": {"type": "string"},
            "service_plan": {"type": "string"},
            "device_type": {"type": "string"},
            "description": {"type": "string"}
          },
          "required": ["action"]
        }
      },
      {
        "name": "manage_tiles",
        "description": "Manage service catalog and discovery",
        "inputSchema": {
          "type": "object",
          "properties": {
            "action": {"type": "string", "enum": ["list", "get"]},
            "tile_id": {"type": "string"}
          },
          "required": ["action"]
        }
      },
      {
        "name": "check_dpod_availability",
        "description": "Check DPoD platform status and incidents",
        "inputSchema": {
          "type": "object",
          "properties": {
            "action": {"type": "string", "enum": ["check_dpod_status"]}
          },
          "required": ["action"]
        }
      }
    ]
  }
}
```

### Step 4: List Available Prompts

Request a list of all available prompts:

```json
{
  "jsonrpc": "2.0",
  "method": "prompts/list",
  "id": 4
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "prompts": [
      {
        "name": "get_service_logs",
        "description": "Retrieve comprehensive audit logs for a specific DPoD service",
        "arguments": [
          {
            "name": "service_name",
            "description": "Name of the service to get logs for",
            "required": true
          },
          {
            "name": "start_date",
            "description": "Start date for logs in RFC 3339 format (YYYY-MM-DDTHH:MM:SSZ)",
            "required": true
          },
          {
            "name": "end_date",
            "description": "End date for logs in RFC 3339 format (YYYY-MM-DDTHH:MM:SSZ)",
            "required": true
          }
        ]
      },
      {
        "name": "create_hsm_service",
        "description": "Create a new Hardware Security Module (HSM) service",
        "arguments": [
          {
            "name": "service_type",
            "description": "Type of HSM service",
            "required": true
          },
          {
            "name": "service_name",
            "description": "Name for the service (4-45 characters)",
            "required": true
          },
          {
            "name": "service_plan",
            "description": "Service plan",
            "required": true
          },
          {
            "name": "device_type",
            "description": "Device type (optional)",
            "required": false
          },
          {
            "name": "description",
            "description": "Service description (optional)",
            "required": false
          }
        ]
      },
      {
        "name": "create_ctaas_service",
        "description": "Create a new CipherTrust Data Security Platform as a Service (CTAAS)",
        "arguments": [
          {
            "name": "cluster",
            "description": "Cluster for the CTAAS service deployment",
            "required": true
          },
          {
            "name": "service_name",
            "description": "Name for the service (4-45 characters)",
            "required": true
          },
          {
            "name": "initial_admin_password",
            "description": "Initial admin password for the CTAAS service",
            "required": true
          },
          {
            "name": "description",
            "description": "Service description (optional)",
            "required": false
          }
        ]
      },
      {
        "name": "create_hsm_client",
        "description": "Create an HSM service client and download the configuration file",
        "arguments": [
          {
            "name": "service_name",
            "description": "Name of the HSM service to bind the client to",
            "required": true
          },
          {
            "name": "client_name",
            "description": "Name for the client (1-64 characters)",
            "required": true
          },
          {
            "name": "os_type",
            "description": "Operating system type (linux or windows)",
            "required": false
          },
          {
            "name": "download_path",
            "description": "Directory path where the client configuration file should be saved",
            "required": false
          }
        ]
      }
    ]
  }
}
```

### Step 5: Test Service Management - List Services

Test the service management tool by listing all services:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 5,
  "params": {
    "name": "manage_services",
    "arguments": {
      "action": "list_services"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Service List:\n- Service 1: HSMaaS_001 (key_vault, single_hsm, Active)\n- Service 2: CTAAS_EU_001 (ctaas, standard, Active)\n- Service 3: Backup_HSM_001 (luna_hsm_backup, dual_hsm, Active)"
      }
    ]
  }
}
```

### Step 6: Test Service Catalog - List Available Service Types

Test the service catalog tool to see available service types and pricing:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 6,
  "params": {
    "name": "manage_tiles",
    "arguments": {
      "action": "list"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Available Service Types:\n\nHSM Services:\n- key_vault: Basic Cloud HSM service\n- hsm_key_export: HSM with private key export capability\n- ms_sql_server: SQL Server cryptographic operations\n- java_code_sign: Java code signing key protection\n- ms_authenticode: Microsoft Authenticode certificate security\n- ms_adcs: Microsoft Root CA key security\n- pki_private_key_protection: PKI trust hierarchy protection\n- digital_signing: Software/firmware signing\n- oracle_tde_database: Oracle database encryption key protection\n- hyperledger: Blockchain transaction security\n- luna_dke: Microsoft Double Key Encryption endpoint\n- cyberark_digital_vault: CyberArk encryption key security\n- luna_hsm_backup: On-premises Luna HSM backup/restore\n\nCipherTrust Data Security Platform:\n- ctaas: Core data security platform\n\npayShield Cloud Services:\n- payshield_na: North America hosted HSM service\n- payshield_eu: Europe hosted HSM service\n- p2pe: Point-to-point encryption services\n\nPartner Services:\n- codesign-secure: Certificate management (Encryption Consulting)\n- kt_ses: Secure email signing/encryption (KeyTalk)\n- kt_pki: PKI lifecycle management (KeyTalk)\n- garasign: Key/certificate management (Garantir)\n- pkiaas: Customizable PKI solution (Encryption Consulting)\n- suredrop: Secure file sharing and collaboration (Thales)\n- a24_hsm: Managed HSM services (A24)\n- ascertia_pki: Digital signing and PKI (Ascertia)\n- codesign: Code signing solution (Encryption Consulting)\n- pk_sign_cloud: Cloud-based digital signing (PrimeKey)\n- kf_command: Enterprise digital identity (Keyfactor)\n- pk_sign_sw: On-premises digital signing (PrimeKey)\n- ven_platform: Machine identity automation (Venafi)\n- signpath: Policy-driven automation (SignPath)\n\nPricing Information (US Region):\n- Single HSM: $0.50/hour\n- Dual HSM: $0.90/hour\n- Multi HSM: $1.50/hour\n- Trial: $0.10/hour (limited to 30 days)\n- Standard: $0.75/hour"
      }
    ]
  }
}
```

### Step 7: Test DPoD Platform Status

Test the DPoD availability check:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 7,
  "params": {
    "name": "check_dpod_availability",
    "arguments": {
      "action": "check_dpod_status"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "DPoD Platform Status:\n\nOverall Status: Operational\nUptime: 99.9%\nLast Updated: 2025-01-09T10:30:00Z\n\nRegional Status:\n- North America: Operational\n- Europe: Operational\n- Asia Pacific: Operational\n\nRecent Incidents:\n- No incidents reported in the last 30 days\n\nService Health:\n- HSM Services: Operational\n- CTAAS Services: Operational\n- Partner Services: Operational"
      }
    ]
  }
}
```

### Step 8: Test Service Creation (Optional - Requires Write Permissions)

Test creating a new service (only if you have write permissions):

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 8,
  "params": {
    "name": "manage_services",
    "arguments": {
      "action": "create",
      "service_type": "key_vault",
      "service_name": "Test-HSM-001",
      "service_plan": "single_hsm",
      "device_type": "cryptovisor_fips",
      "description": "Test HSM service for manual testing"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Service Creation Initiated:\n\nService Name: Test-HSM-001\nService Type: key_vault\nService Plan: single_hsm\nDevice Type: cryptovisor_fips\nStatus: Provisioning\n\nService will be available in approximately 5-10 minutes.\nYou can check the status using the 'get' action with service name 'Test-HSM-001'."
      }
    ]
  }
}
```

### Step 9: Test HSM Client Creation (Optional - Requires Write Permissions)

Test creating an HSM client and downloading the configuration file:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 9,
  "params": {
    "name": "manage_services",
    "arguments": {
      "action": "bind_client",
      "service_id": "Test-HSM-001",
      "client_name": "TestClient",
      "os_type": "linux",
      "download_path": "/tmp/hsm_clients"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Client 'TestClient' bound successfully to service abc123-def456-ghi789\n\nFile saved to: /tmp/hsm_clients/client_config_TestClient_linux.tar.gz\nDownload path used: /tmp/hsm_clients\n\nNote: The client configuration file contains certificates and connection details needed to connect to the HSM service."
      }
    ]
  }
}
```

## Testing Tips

### 1. **Error Handling**
If you encounter errors, check the server logs for detailed information:
- Look for authentication errors
- Verify scope permissions
- Check network connectivity

### 2. **Scope-Based Testing**
The available tools depend on your DPoD API scopes:
- `dpod.tenant.api_spadmin`: Full access to all tools
- `dpod.tenant.api_appowner`: Limited access to service management
- `dpod.tenant.api_service`: Service-specific access only

### 3. **Read-Only Mode**
If testing in read-only mode, creation and modification operations will be blocked:
```bash
python main.py --transport stdio --read-only
```

### 4. **Debug Mode**
Enable debug logging for detailed information:
```bash
python main.py --transport stdio --log-level DEBUG
```

## Common Issues and Solutions

### 1. **Authentication Errors**
- Verify your DPoD credentials in the `.env` file
- Check that your account has the required API scopes
- Ensure network access to DPoD endpoints

### 2. **Tool Not Available**
- Check your API scopes - some tools require specific permissions
- Verify the tool is registered in the server startup logs
- Ensure you're using the correct tool name

### 3. **Invalid Parameters**
- Check the tool's input schema for required parameters
- Verify parameter types and formats
- Use the tools/list response to understand expected parameters

### 4. **Connection Issues**
- Ensure the server is running in stdio mode
- Check that JSON-RPC messages are properly formatted
- Verify the protocol version matches the server expectations

## Automated Testing

For automated testing, you can create scripts that send these JSON-RPC messages programmatically:

```python
import json
import subprocess
import sys

def send_jsonrpc_message(message):
    """Send a JSON-RPC message to the server"""
    process = subprocess.Popen(
        ['python', 'main.py', '--transport', 'stdio'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=json.dumps(message) + '\n')
    return json.loads(stdout.strip())

# Example usage
init_message = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1,
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "Test Client", "version": "1.0.0"}
    }
}

response = send_jsonrpc_message(init_message)
print("Server response:", response)
```

This testing guide provides comprehensive coverage of the DPoD MCP server functionality and helps ensure proper operation before deployment.