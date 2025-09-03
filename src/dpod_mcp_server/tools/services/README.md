# DPoD Service Management Tools

## ⚠️ CRITICAL DISTINCTION FOR AI ASSISTANTS ⚠️

DPoD has **TWO DIFFERENT CONCEPTS** that AI assistants must understand:

### 1. **Service Catalog (Tiles)** - Available Service Types
- **Tool**: `manage_tiles`
- **API Endpoint**: `GET /v1/tiles`
- **Purpose**: Lists available service types that can be provisioned
- **Use Case**: When user wants to see what services are available to create
- **Returns**: Service types like "Luna Cloud HSM", "CipherTrust Data Security Platform", etc.

### 2. **Service Instances** - Provisioned/Deployed Services
- **Tool**: `manage_services`
- **API Endpoint**: `GET /v1/service_instances`
- **Purpose**: Lists actual deployed services that are running
- **Use Case**: When user wants to see what services they currently have deployed
- **Returns**: Actual service instances with names, status, configuration, etc.

## 🎯 When to Use Each Tool

### Use `manage_tiles` when:
- User asks: "What services are available?"
- User asks: "Show me the service catalog"
- User asks: "What can I create?"
- User asks: "List available service types"
- User wants to browse available services before creating

### Use `manage_services` when:
- User asks: "What services do I have?"
- User asks: "Show me my deployed services"
- User asks: "List my running services"
- User wants to manage existing services (update, delete, etc.)
- User wants to see service status and configuration

## 🔍 Example Scenarios

### Scenario 1: User wants to see available services
```
User: "Show me what services I can create"
AI Response: Use manage_tiles with action="list_tiles"
```

### Scenario 2: User wants to see their deployed services
```
User: "What services do I currently have running?"
AI Response: Use manage_services with action="list_services"
```

### Scenario 3: User wants to create a new service
```
User: "I want to create a new HSM service"
AI Response: 
1. First use manage_tiles to see available HSM services
2. Then use manage_services with action="create_service_instance"
```

## 📋 Tool Actions Summary

### manage_tiles (Service Catalog)
- `list_tiles` - Browse available service types
- `search_tiles` - Find specific service types
- `get_tile_details` - Get detailed info about a service type
- `get_tile_plans` - Get pricing/plans for a service type

### manage_services (Service Instances)
- `list_services` - List deployed services
- `get_service_instance` - Get details of a specific service
- `create_service_instance` - Create a new service

- `delete_service_instance` - Delete a service
- `bind_client` - Connect a client to a service

## 🚨 Common Mistakes to Avoid

1. **Don't use `manage_services` to browse available service types**
2. **Don't use `manage_tiles` to manage deployed services**
3. **Always check the user's intent first** - are they asking about available services or existing services?
4. **For service creation, always start with `manage_tiles` to show options**

## 💡 Best Practices

1. **Ask clarifying questions** if the user's intent is unclear
2. **Use the right tool for the right purpose**
3. **Explain the difference** to users if they seem confused
4. **Guide users through the workflow** step by step
5. **Always verify** you're using the correct tool before proceeding 