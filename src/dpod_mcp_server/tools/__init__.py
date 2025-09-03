"""
DPoD Management Tools Module

This module provides tools for DPoD management operations.
"""

from .tenants.tenant_tools import manage_tenants
from .scopes.scope_tools import manage_scopes
from .dpod_availability.dpod_availability_tools import check_dpod_availability
from .audit.audit_tools import manage_audit_logs
from .reports.report_tools import manage_reports
from .tiles.tile_tools import manage_tiles
from .services.service_tools import manage_services
from .users.user_tools import manage_users
from .subscriber_groups.subscriber_group_tools import manage_subscriber_groups
from .credentials.credential_tools import manage_credentials
from .products.product_tools import manage_products
from .service_agreements.service_agreement_tools import manage_service_agreements
from .subscriptions.subscription_tools import manage_subscriptions
from .pricing.pricing_tools import manage_pricing

# Sort tools alphabetically for consistent export order
def get_sorted_tools():
    """Return tools sorted alphabetically by name."""
    tools = {
        "manage_audit_logs": manage_audit_logs,
        "check_dpod_availability": check_dpod_availability,
        "manage_credentials": manage_credentials,
        "manage_pricing": manage_pricing,
        "manage_products": manage_products,
        "manage_reports": manage_reports,
        "manage_service_agreements": manage_service_agreements,
        "manage_services": manage_services,
        "manage_scopes": manage_scopes,
        "manage_subscriber_groups": manage_subscriber_groups,
        "manage_subscriptions": manage_subscriptions,
        "manage_tenants": manage_tenants,
        "manage_tiles": manage_tiles,
        "manage_users": manage_users
    }
    return dict(sorted(tools.items()))

# Export tools in alphabetical order
__all__ = sorted([
    "manage_tenants",
    "manage_scopes",
    "check_dpod_availability",
    "manage_audit_logs",
    "manage_reports",
    "manage_services",
    "manage_tiles",
    "manage_users",
    "manage_subscriber_groups",
    "manage_credentials",
    "manage_products",
    "manage_service_agreements",
    "manage_subscriptions",
    "manage_pricing"
]) 