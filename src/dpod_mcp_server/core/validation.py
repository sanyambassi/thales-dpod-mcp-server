#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Validation Utilities

Parameter validation and sanitization functions.
"""

import re
import json
from typing import Any, Callable, Optional, Union
from uuid import UUID

class ValidationError(Exception):
    """Custom validation error."""
    pass

def validate_string_param(value: Any, param_name: str, min_length: int = 1, max_length: int = 1000) -> str:
    """Validate and return a string parameter."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    if len(value) < min_length:
        raise ValidationError(f"{param_name} must be at least {min_length} characters long")
    
    if len(value) > max_length:
        raise ValidationError(f"{param_name} must be no more than {max_length} characters long")
    
    return value.strip()

def validate_uuid(value: Any, param_name: str) -> str:
    """Validate and return a UUID parameter."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    # Check if the UUID appears to be truncated
    if len(value) < 36:  # Standard UUID length is 36 characters (32 hex + 4 hyphens)
        raise ValidationError(f"{param_name} appears to be truncated. Expected 36 characters, got {len(value)}. Full UUID: {value}")
    
    try:
        UUID(value)
        return value
    except ValueError:
        raise ValidationError(f"{param_name} must be a valid UUID. Received: {value}")


def validate_uuid_or_partial(value: Any, param_name: str) -> str:
    """Validate and return a UUID or partial UUID parameter.
    
    Allows partial UUIDs for search/filtering operations.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    value = value.strip()
    
    # Check if it's a complete UUID
    try:
        UUID(value)
        return value
    except ValueError:
        pass
    
    # Check if it's a partial UUID (at least 8 characters, hex only)
    if len(value) < 8:
        raise ValidationError(f"{param_name} must be at least 8 characters long for partial UUID")
    
    if not re.match(r'^[0-9a-fA-F-]+$', value):
        raise ValidationError(f"{param_name} must contain only hexadecimal characters and hyphens")
    
    return value


def validate_uuid_with_truncation_check(value: Any, param_name: str) -> str:
    """Validate UUID with special handling for truncated values.
    
    This function attempts to handle cases where UUIDs might be truncated
    due to MCP tool parameter length limitations.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    value = value.strip()
    
    # If it's exactly 36 characters, try to validate as a complete UUID
    if len(value) == 36:
        try:
            UUID(value)
            return value
        except ValueError:
            raise ValidationError(f"{param_name} is not a valid UUID: {value}")
    
    # If it's shorter than 36 characters, it might be truncated
    if len(value) < 36:
        # Try to find a matching service by searching with the partial UUID
        # This is a workaround for truncated UUIDs
        raise ValidationError(
            f"{param_name} appears to be truncated. Length: {len(value)}, Expected: 36. "
            f"Value: {value}. This may be due to MCP tool parameter length limitations. "
            f"Try using the service name instead or check the full UUID."
        )
    
    # If it's longer than 36 characters, it's invalid
    if len(value) > 36:
        raise ValidationError(f"{param_name} is too long. Expected 36 characters, got {len(value)}: {value}")
    
    # Should not reach here, but just in case
    raise ValidationError(f"{param_name} has unexpected length: {len(value)}")

def validate_enum_param(value: Any, valid_values: list, param_name: str) -> str:
    """Validate and return an enum parameter."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    if value not in valid_values:
        raise ValidationError(f"{param_name} must be one of: {', '.join(valid_values)}")
    
    return value

def validate_integer_param(value: Any, param_name: str, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    """Validate and return an integer parameter."""
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{param_name} must be an integer")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(f"{param_name} must be at least {min_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"{param_name} must be no more than {max_value}")
    
    return int_value

def validate_boolean_param(value: Any, param_name: str) -> bool:
    """Validate and return a boolean parameter."""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        if value.lower() in ['true', '1', 'yes', 'on']:
            return True
        elif value.lower() in ['false', '0', 'no', 'off']:
            return False
    
    if isinstance(value, int):
        if value == 1:
            return True
        elif value == 0:
            return False
    
    raise ValidationError(f"{param_name} must be a boolean value")

def validate_optional_param(value: Any, validator: Callable, param_name: str) -> Optional[Any]:
    """Validate an optional parameter using the provided validator."""
    if value is None:
        return None
    
    try:
        return validator(value)
    except Exception as e:
        raise ValidationError(f"Invalid {param_name}: {e}")

def validate_json_data(value: Any, param_name: str) -> dict:
    """Validate and return JSON data."""
    if isinstance(value, dict):
        return value
    
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError(f"{param_name} must be valid JSON")
    
    raise ValidationError(f"{param_name} must be a dictionary or valid JSON string")

def sanitize_json_data(data: dict) -> dict:
    """Sanitize JSON data by removing None values and empty strings."""
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if value is not None and value != "":
            if isinstance(value, dict):
                sanitized[key] = sanitize_json_data(value)
            elif isinstance(value, list):
                sanitized[key] = [sanitize_json_data(item) if isinstance(item, dict) else item for item in value if item is not None and item != ""]
            else:
                sanitized[key] = value
    
    return sanitized

def validate_date_format(value: Any, param_name: str) -> str:
    """Validate date format (YYYY-MM-DD)."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, value):
        raise ValidationError(f"{param_name} must be in YYYY-MM-DD format")
    
    return value

def validate_email(value: Any, param_name: str) -> str:
    """Validate email format."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValidationError(f"{param_name} must be a valid email address")
    
    return value.lower()

def validate_url(value: Any, param_name: str) -> str:
    """Validate URL format."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(url_pattern, value):
        raise ValidationError(f"{param_name} must be a valid URL")
    
    return value

def validate_phone_number(value: Any, param_name: str) -> str:
    """Validate phone number format."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', value)
    
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError(f"{param_name} must be a valid phone number (10-15 digits)")
    
    return digits_only

def validate_strong_password(value: Any, param_name: str, min_length: int = 8) -> str:
    """Validate password strength."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    if len(value) < min_length:
        raise ValidationError(f"{param_name} must be at least {min_length} characters long")
    
    # Check for at least one uppercase letter, one lowercase letter, and one digit
    if not re.search(r'[A-Z]', value):
        raise ValidationError(f"{param_name} must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', value):
        raise ValidationError(f"{param_name} must contain at least one lowercase letter")
    
    if not re.search(r'\d', value):
        raise ValidationError(f"{param_name} must contain at least one digit")
    
    return value

def validate_file_extension(value: Any, param_name: str, allowed_extensions: list) -> str:
    """Validate file extension."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    if not value.lower().endswith(tuple(ext.lower() for ext in allowed_extensions)):
        raise ValidationError(f"{param_name} must have one of these extensions: {', '.join(allowed_extensions)}")
    
    return value


def validate_create_params(value: Any, param_name: str = "createParams", service_type: Optional[str] = None) -> dict:
    """Validate createParams for service instance creation.
    
    FastMCP automatically handles type conversion from JSON to Python objects,
    so we handle both dict and JSON string inputs for compatibility.
    
    Args:
        value: The createParams value to validate (dict or JSON string)
        param_name: Name of the parameter for error messages
        service_type: Optional service type to validate specific parameters
        
    Returns:
        Validated createParams dictionary
        
    Raises:
        ValidationError: If createParams is invalid
    """
    # Handle FastMCP automatic type conversion
    if isinstance(value, str):
        try:
            import json
            value = json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError(
                f"{param_name} must be a valid JSON object or dictionary. Example: {{'deviceType': 'cryptovisor'}}"
            )
    
    if not isinstance(value, dict):
        raise ValidationError(
            f"{param_name} must be a dictionary/object. Example: {{'deviceType': 'cryptovisor'}}"
        )
    
    # Allow empty configuration - defaults will be applied later
    if not value:
        # Return empty dict - service creation logic will add defaults
        return {}
    
    # Validate that all keys are strings
    for key in value.keys():
        if not isinstance(key, str):
            raise ValidationError(f"{param_name} keys must be strings, found: {type(key).__name__}")
        
        if not key.strip():
            raise ValidationError(f"{param_name} keys cannot be empty strings")
    
    # Validate that values are not None (empty strings are allowed)
    for key, val in value.items():
        if val is None:
            raise ValidationError(f"{param_name}.{key} cannot be None")
    
    # Service-specific validations
    if service_type == "key_vault" or service_type == "hsm":
        # Luna Cloud HSM validation - deviceType should be in createParams
        if "deviceType" in value and value["deviceType"] not in ["cryptovisor", "cryptovisor_fips"]:
            raise ValidationError(
                f"Invalid deviceType in {param_name}. Must be 'cryptovisor' or 'cryptovisor_fips'"
            )
    elif service_type == "ctaas":
        # CTAAS validation - cluster and initial_admin_password are REQUIRED
        if "cluster" not in value:
            raise ValidationError(
                f"cluster is REQUIRED for CTAAS services in {param_name}. Must be one of: gcp-us-east1, gcp-europe-west3"
            )
        
        if "initial_admin_password" not in value:
            raise ValidationError(
                f"initial_admin_password is REQUIRED for CTAAS services in {param_name}. Must be a string with at least 8 characters"
            )
        
        # Validate cluster value
        valid_clusters = ["gcp-us-east1", "gcp-europe-west3"]
        if value["cluster"] not in valid_clusters:
            raise ValidationError(
                f"Invalid cluster in {param_name}. Must be one of: {', '.join(valid_clusters)}"
            )
        
        # Validate password value
        password = value["initial_admin_password"]
        if not isinstance(password, str) or len(password) < 8:
            raise ValidationError(
                f"Invalid initial_admin_password in {param_name}. Must be a string with at least 8 characters"
            )
        
        # Validate tenant_rot_anchor if provided (optional - only validate if user specifies it)
        if "tenant_rot_anchor" in value:
            valid_anchors = ["softkek", "hsmod"]
            if value["tenant_rot_anchor"] not in valid_anchors:
                raise ValidationError(
                    f"Invalid tenant_rot_anchor in {param_name}. Must be one of: {', '.join(valid_anchors)}"
                )
    
    return value


def validate_service_plan(value: Any, param_name: str = "servicePlan", service_type: str = None) -> str:
    """Validate service plan for service instance creation.
    
    Args:
        value: The service plan to validate
        param_name: Name of the parameter for error messages
        service_type: Service type to validate plan compatibility
        
    Returns:
        Validated service plan string
        
    Raises:
        ValidationError: If service plan is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    plan = value.strip()
    
    if len(plan) < 1:
        raise ValidationError(f"{param_name} cannot be empty")
    
    if len(plan) > 255:
        raise ValidationError(f"{param_name} must be no more than 255 characters long")
    
    # Service-specific plan validation
    if service_type == "key_vault" or service_type == "hsm":
        # Luna Cloud HSM common plans
        valid_luna_plans = ["single_hsm", "dual_hsm", "multi_hsm", "trial"]
        if plan not in valid_luna_plans:
            raise ValidationError(
                f"Invalid {param_name} for Luna Cloud HSM: '{plan}'. "
                f"Common plans: {', '.join(valid_luna_plans)}"
            )
    elif service_type == "ctaas":
        # CTAAS common plans
        valid_ctaas_plans = ["Tenant"]
        if plan not in valid_ctaas_plans:
            raise ValidationError(
                f"Invalid {param_name} for CTAAS: '{plan}'. "
                f"Common plans: {', '.join(valid_ctaas_plans)}"
            )
    
    return plan


def validate_service_name(value: Any, param_name: str = "name") -> str:
    """Validate service name for service instance creation.
    
    Args:
        value: The service name to validate
        param_name: Name of the parameter for error messages
        
    Returns:
        Validated service name string
        
    Raises:
        ValidationError: If service name is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    name = value.strip()
    
    if len(name) < 4:
        raise ValidationError(f"{param_name} must be at least 4 characters long")
    
    if len(name) > 45:
        raise ValidationError(f"{param_name} must be no more than 45 characters long")
    
    # Validate name format (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValidationError(f"{param_name} can only contain letters, numbers, hyphens, and underscores")
    
    # Cannot start or end with hyphen
    if name.startswith('-') or name.endswith('-'):
        raise ValidationError(f"{param_name} cannot start or end with a hyphen")
    
    return name

def validate_hex_color(value: Any, param_name: str) -> str:
    """Validate hex color format."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    if not re.match(hex_pattern, value):
        raise ValidationError(f"{param_name} must be a valid hex color (e.g., #FF0000 or #F00)")
    
    return value.upper()

def validate_ip_address(value: Any, param_name: str) -> str:
    """Validate IP address format."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, value):
        parts = value.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                raise ValidationError(f"{param_name} must be a valid IPv4 address")
        return value
    
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    if re.match(ipv6_pattern, value):
        return value
    
    raise ValidationError(f"{param_name} must be a valid IP address")

def validate_mac_address(value: Any, param_name: str) -> str:
    """Validate MAC address format."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    if not re.match(mac_pattern, value):
        raise ValidationError(f"{param_name} must be a valid MAC address (e.g., 00:1B:44:11:3A:B7)")
    
    return value.upper()

def validate_credit_card(value: Any, param_name: str) -> str:
    """Validate credit card number using Luhn algorithm."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    # Remove spaces and dashes
    clean_number = re.sub(r'[\s-]', '', value)
    
    if not clean_number.isdigit():
        raise ValidationError(f"{param_name} must contain only digits")
    
    if len(clean_number) < 13 or len(clean_number) > 19:
        raise ValidationError(f"{param_name} must be 13-19 digits long")
    
    # Luhn algorithm
    digits = [int(d) for d in clean_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    
    if checksum % 10 != 0:
        raise ValidationError(f"{param_name} is not a valid credit card number")
    
    return clean_number

def validate_postal_code(value: Any, param_name: str, country: str = "US") -> str:
    """Validate postal code format for different countries."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    patterns = {
        "US": r'^\d{5}(-\d{4})?$',  # 12345 or 12345-6789
        "CA": r'^[A-Za-z]\d[A-Za-z] \d[A-Za-z]\d$',  # A1A 1A1
        "UK": r'^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$',  # SW1A 1AA
        "DE": r'^\d{5}$',  # 12345
        "FR": r'^\d{5}$',  # 12345
        "JP": r'^\d{3}-\d{4}$',  # 123-4567
    }
    
    pattern = patterns.get(country.upper(), patterns["US"])
    if not re.match(pattern, value):
        raise ValidationError(f"{param_name} must be a valid {country} postal code")
    
    return value.upper()

def validate_currency_code(value: Any, param_name: str) -> str:
    """Validate ISO 4217 currency code."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    currency_pattern = r'^[A-Z]{3}$'
    if not re.match(currency_pattern, value):
        raise ValidationError(f"{param_name} must be a valid 3-letter currency code (e.g., USD, EUR)")
    
    return value

def validate_language_code(value: Any, param_name: str) -> str:
    """Validate ISO 639-1 language code."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    language_pattern = r'^[a-z]{2}$'
    if not re.match(language_pattern, value):
        raise ValidationError(f"{param_name} must be a valid 2-letter language code (e.g., en, es, fr)")
    
    return value.lower()

def validate_timezone(value: Any, param_name: str) -> str:
    """Validate IANA timezone identifier."""
    if not isinstance(value, str):
        raise ValidationError(f"{param_name} must be a string")
    
    timezone_pattern = r'^[A-Za-z_]+/[A-Za-z_]+$'
    if not re.match(timezone_pattern, value):
        raise ValidationError(f"{param_name} must be a valid timezone (e.g., America/New_York, Europe/London)")
    
    return value

def validate_json_schema(value: Any, schema: dict) -> dict:
    """Validate JSON data against a schema."""
    if not isinstance(value, dict):
        raise ValidationError("Value must be a dictionary")
    
    # Basic schema validation (simplified)
    for field, rules in schema.items():
        if rules.get("required", False) and field not in value:
            raise ValidationError(f"Required field '{field}' is missing")
        
        if field in value:
            field_value = value[field]
            field_type = rules.get("type")
            
            if field_type == "string" and not isinstance(field_value, str):
                raise ValidationError(f"Field '{field}' must be a string")
            elif field_type == "integer" and not isinstance(field_value, int):
                raise ValidationError(f"Field '{field}' must be an integer")
            elif field_type == "boolean" and not isinstance(field_value, bool):
                raise ValidationError(f"Field '{field}' must be a boolean")
            elif field_type == "array" and not isinstance(field_value, list):
                raise ValidationError(f"Field '{field}' must be an array")
            elif field_type == "object" and not isinstance(field_value, dict):
                raise ValidationError(f"Field '{field}' must be an object")
    
    return value 