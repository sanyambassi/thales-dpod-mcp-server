# DPoD MCP Server - Actionable Prompts

## Overview

The DPoD MCP Server now includes **3 actionable prompts** that AI assistants can use to immediately execute DPoD operations. These prompts are **not user guides** - they are **executable instructions** that tell AI assistants exactly what to do.

## Available Prompts

### 1. `get_service_logs` - Retrieve Service Audit Logs
Get comprehensive audit logs for a specific DPoD service within a date range with flexible filtering.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD or YYYY/MM/DD format
- `end_date` (required): End date in YYYY-MM-DD or YYYY/MM/DD format
- `service_name` (optional): Name of the service to get logs for
- `source` (optional): Source filter (e.g., "thales/cloudhsm/partitionID")
- `action_filter` (optional): Filter by specific actions
- `status_filter` (optional): Filter by status (e.g., "LUNA_RET_OK" for HSM, "success" for CTAAS)

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
- `os_type` (optional): Operating system type (linux or windows, defaults to linux)
- `download_path` (optional): Directory path where the client configuration file should be saved (defaults to system temp directory)