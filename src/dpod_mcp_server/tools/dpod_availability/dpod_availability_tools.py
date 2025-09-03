#!/usr/bin/env python3
"""
Platform Management Tools for DPoD MCP Server

Provides platform status and availability information.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastmcp import Context
from pydantic import Field

from ...core.validation import validate_string_param

async def check_dpod_availability(
    ctx: Context,
    action: str = Field(description="Operation to perform: check_dpod_status")
) -> Dict[str, Any]:
    """DPoD platform availability and comprehensive status operations.
    
    Fetches real-time information from the official DPoD status page including:
    - Overall platform status and uptime
    - Individual service statuses by region (EU, NA, LATAM)
    - 90-day uptime statistics for each service
    - Recent incidents and maintenance events
    - Regional availability breakdown
    
    Actions:
    - check_dpod_status: Comprehensive DPoD platform status check with uptime and incident data
    """
    # Get config from dependency injection
    from ...core.dependency_injection import get_config
    config = get_config()
    
    from ...core.logging_utils import get_tool_logger
    tool_logger = get_tool_logger("dpod_availability")
    tool_logger.info(f"Starting DPoD availability check: {action}")
    
    try:
        await ctx.info(f"Starting DPoD availability check: {action}")
        await ctx.report_progress(0, 100, f"Starting DPoD availability check: {action}")
        
        if action == "check_dpod_status":
            await ctx.report_progress(30, 100, "Checking DPoD platform status...")
            await ctx.info("Checking DPoD platform status...")
            
            result = await _get_dpod_status()
            
            await ctx.report_progress(90, 100, "DPoD status check completed")
            await ctx.info("DPoD status check completed")
            
        else:
            error_msg = f"Unknown action: {action}. Supported actions: check_dpod_status"
            await ctx.error(error_msg)
            raise ValueError(error_msg)
            
        await ctx.report_progress(100, 100, f"Completed DPoD availability check: {action}")
        await ctx.info(f"Completed DPoD availability check: {action}")
        tool_logger.info(f"Completed DPoD availability check: {action}")
        return result
        
    except Exception as e:
        error_msg = f"Error in DPoD availability check {action}: {str(e)}"
        tool_logger.error(error_msg)
        await ctx.error(error_msg)
        return {"success": False, "error": str(e)}


async def _get_dpod_status() -> Dict[str, Any]:
    """Get comprehensive DPoD service status from the official status page.
    
    Fetches real-time status information for all DPoD services including:
    - Overall platform status
    - Individual service statuses with regional breakdowns
    - 90-day uptime statistics for each service
    - Recent incidents and maintenance events
    - Service availability by region (EU, NA, LATAM)
    
    Returns:
        Comprehensive DPoD service status information including:
        - overall_status: Overall platform status
        - services: Individual service statuses with uptime
        - uptime_stats: 90-day uptime statistics
        - recent_incidents: Past incidents and maintenance
        - regional_status: Status breakdown by region
        - last_updated: When status was last checked
        - status_page_url: Link to official status page
    """
    try:
        import httpx
        import re
        from bs4 import BeautifulSoup
        
        # Get logger for this function
        from ...core.logging_utils import get_tool_logger
        tool_logger = get_tool_logger("dpod_availability")
        
        # DPoD Status page URL
        status_url = "https://status.dpondemand.io/"
        
        # Fetch the status page
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(status_url)
            
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to fetch status page: {response.status_code}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Log what we're working with
        tool_logger.debug(f"HTML content length: {len(response.text)}")
        tool_logger.debug(f"Found {len(soup.find_all('div'))} div elements")
        
        # Extract overall status dynamically from the page
        overall_status = "Unknown"
        
        # Look for status indicators in various places
        status_patterns = [
            r"All Systems Operational",
            r"Degraded Performance", 
            r"Partial Outage",
            r"Major Outage",
            r"Maintenance",
            r"Operational",
            r"Outage",
            r"Disruption"
        ]
        
        for pattern in status_patterns:
            status_elements = soup.find_all(string=re.compile(pattern, re.IGNORECASE))
            if status_elements:
                overall_status = status_elements[0].strip()
                tool_logger.debug(f"Found overall status: {overall_status}")
                break
        
        # If no status found in main content, look in JavaScript variables
        if overall_status == "Unknown":
            for script in script_tags:
                script_text = script.get_text()
                # Look for status variables or indicators
                status_match = re.search(r'status["\']?\s*[:=]\s*["\']([^"\']+)["\']', script_text, re.IGNORECASE)
                if status_match:
                    overall_status = status_match.group(1).strip()
                    tool_logger.debug(f"Found status in JavaScript: {overall_status}")
                    break
        
        # Extract uptime data from JavaScript variables
        uptime_summary = {}
        uptime_data = {}
        
        # Look for uptimeValues JavaScript variable (this is the correct one)
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_text = script.get_text()
            
            # Extract uptimeValues data - this contains the actual uptime percentages
            if 'uptimeValues' in script_text:
                # Find the uptimeValues array
                values_match = re.search(r'uptimeValues\s*=\s*\[(.*?)\];', script_text, re.DOTALL)
                if values_match:
                    values_text = values_match.group(1)
                    tool_logger.debug(f"Found uptimeValues data: {values_text[:200]}...")
                    
                    # Parse each component entry
                    component_entries = re.findall(r'\{[^}]+\}', values_text)
                    tool_logger.debug(f"Found {len(component_entries)} component entries in uptimeValues")
                    
                    for entry in component_entries:
                        # Extract component code and uptime values
                        code_match = re.search(r'"component":"([^"]+)"', entry)
                        ninety_match = re.search(r'"ninety":([\d.]+)', entry)
                        sixty_match = re.search(r'"sixty":([\d.]+)', entry)
                        thirty_match = re.search(r'"thirty":([\d.]+)', entry)
                        
                        if code_match:
                            component_code = code_match.group(1)
                            uptime_summary[component_code] = {
                                "90_day": float(ninety_match.group(1)) if ninety_match else None,
                                "60_day": float(sixty_match.group(1)) if sixty_match else None,
                                "30_day": float(thirty_match.group(1)) if thirty_match else None
                            }
                            tool_logger.debug(f"Added component {component_code} with uptime data")
            
            # Extract uptimeData for component names and incident information
            if 'uptimeData' in script_text:
                # Find the uptimeData object - use a more flexible approach
                # Look for the pattern: "component_code":{"component":{"code":"...","name":"..."}
                component_matches = re.findall(r'"([a-zA-Z0-9]+)":\{"component":\{"code":"([^"]+)","name":"([^"]+)"', script_text)
                for match in component_matches:
                    component_id, component_code, component_name = match
                    uptime_data[component_code] = {
                        "id": component_id,
                        "name": component_name
                    }
                    tool_logger.debug(f"Added component data for {component_code}: {component_name}")
        
        tool_logger.debug(f"Found {len(uptime_summary)} uptime summary entries")
        tool_logger.debug(f"Found {len(uptime_data)} component data entries")
        
        # Debug: Show what components we found
        for code, info in uptime_data.items():
            tool_logger.debug(f"Component: {code} -> {info.get('name', 'Unknown')}")
        
        # Extract service statuses with uptime
        services = {}
        uptime_stats = {}
        
        # Build services dynamically from uptime data - no hardcoded mappings
        for component_code, uptime_info in uptime_summary.items():
            # Get service name from uptimeData if available
            service_name = "Unknown Service"
            if component_code in uptime_data:
                service_name = uptime_data[component_code]["name"]
            else:
                # Fallback: create a more descriptive name from the component code
                # Try to extract meaningful information from the component code
                if len(component_code) >= 8:
                    # Use first 8 characters but make it more readable
                    readable_code = component_code[:8]
                    # Add some context based on the uptime value
                    if uptime_info["90_day"] and uptime_info["90_day"] >= 99.9:
                        service_name = f"High-Availability Service ({readable_code})"
                    elif uptime_info["90_day"] and uptime_info["90_day"] >= 99.0:
                        service_name = f"Reliable Service ({readable_code})"
                    else:
                        service_name = f"Service Component ({readable_code})"
                else:
                    service_name = f"Service {component_code}"
            
            # Extract region from service name dynamically
            region = None  # Don't default to Global
            
            # Look for region indicators in the service name
            if "(EU Region)" in service_name:
                region = "EU"
                service_name = service_name.replace(" (EU Region)", "")
            elif "(NA Region)" in service_name:
                region = "NA"
                service_name = service_name.replace(" (NA Region)", "")
            elif "(LATAM Region)" in service_name:
                region = "LATAM"
                service_name = service_name.replace(" (LATAM Region)", "")
            elif "EU" in service_name.upper():
                region = "EU"
            elif "NA" in service_name.upper():
                region = "NA"
            elif "LATAM" in service_name.upper():
                region = "LATAM"
            elif "GLOBAL" in service_name.upper():
                region = "Global"
            else:
                # If no region found, try to infer from component code patterns
                # Based on DPoD's actual service structure, we can make educated guesses
                if component_code in uptime_data:
                    # If we have component data, try to infer region from the component ID
                    component_id = uptime_data[component_code].get("id", "")
                    if component_id:
                        # DPoD typically uses patterns like "eu-", "na-", "latam-" in component IDs
                        if component_id.lower().startswith("eu-") or "eu" in component_id.lower():
                            region = "EU"
                        elif component_id.lower().startswith("na-") or "na" in component_id.lower():
                            region = "NA"
                        elif component_id.lower().startswith("latam-") or "latam" in component_id.lower():
                            region = "LATAM"
                        else:
                            # For services without explicit region info, check if they're platform-wide
                            if any(keyword in service_name.lower() for keyword in ["platform", "api", "hsm", "console"]):
                                region = "Global"  # Platform-wide services
                            else:
                                region = "Global"  # Default for global services
                    else:
                        region = "Global"  # Default for global services
                else:
                    # For services without uptimeData, assume they're global services
                    region = "Global"
            
            # Get uptime percentage (use 90-day if available, fallback to 60-day, then 30-day)
            uptime = "N/A"
            if uptime_info["90_day"] is not None:
                uptime = f"{uptime_info['90_day']:.2f}%"
            elif uptime_info["60_day"] is not None:
                uptime = f"{uptime_info['60_day']:.2f}%"
            elif uptime_info["30_day"] is not None:
                uptime = f"{uptime_info['30_day']:.2f}%"
            
            # Initialize service if not exists
            if service_name not in services:
                # Try to determine status from the data
                service_status = "Operational"  # Default fallback
                
                # Look for status information in the component data
                if component_code in uptime_data:
                    # Check if there are any outages or incidents for this component
                    # This would require parsing the uptimeData days array for outages
                    # For now, use default status
                    pass
                
                services[service_name] = {
                    "status": service_status,
                    "uptime": uptime,
                    "regions": {}
                }
            
            # Add regional information
            services[service_name]["regions"][region] = {
                "status": services[service_name]["status"],  # Use service status
                "uptime": uptime
            }
            
            # Store uptime stats
            if service_name not in uptime_stats:
                uptime_stats[service_name] = {}
            uptime_stats[service_name][region] = uptime
        
        # Add any additional services found in uptimeData that weren't in uptimeValues
        # This ensures we capture all services, not just those with uptime data
        for component_code, component_info in uptime_data.items():
            if component_code not in uptime_summary:
                service_name = component_info["name"]
                
                # Extract region from service name
                region = None  # Don't default to Global
                
                # Look for region indicators in the service name
                if "(EU Region)" in service_name:
                    region = "EU"
                    service_name = service_name.replace(" (EU Region)", "")
                elif "(NA Region)" in service_name:
                    region = "NA"
                    service_name = service_name.replace(" (NA Region)", "")
                elif "(LATAM Region)" in service_name:
                    region = "LATAM"
                    service_name = service_name.replace(" (LATAM Region)", "")
                elif "EU" in service_name.upper():
                    region = "EU"
                elif "NA" in service_name.upper():
                    region = "NA"
                elif "LATAM" in service_name.upper():
                    region = "LATAM"
                elif "GLOBAL" in service_name.upper():
                    region = "Global"
                else:
                    # If no region found, try to infer from component code patterns
                    # Based on DPoD's actual service structure, we can make educated guesses
                    if component_code in uptime_data:
                        # If we have component data, try to infer region from the component ID
                        component_id = uptime_data[component_code].get("id", "")
                        if component_id:
                            # DPoD typically uses patterns like "eu-", "na-", "latam-" in component IDs
                            if component_id.lower().startswith("eu-") or "eu" in component_id.lower():
                                region = "EU"
                            elif component_id.lower().startswith("na-") or "na" in component_id.lower():
                                region = "NA"
                            elif component_id.lower().startswith("latam-") or "latam" in component_id.lower():
                                region = "LATAM"
                            else:
                                region = "Global"  # Default for global services
                        else:
                            region = "Global"  # Default for global services
                    else:
                        # For services without uptimeData, assume they're global services
                        region = "Global"
                
                # Initialize service if not exists
                if service_name not in services:
                    # Try to determine status from the data
                    service_status = "Operational"  # Default fallback
                    
                    # Look for status information in the component data
                    if component_code in uptime_data:
                        # Check if there are any outages or incidents for this component
                        # This would require parsing the uptimeData days array for outages
                        # For now, use default status
                        pass
                    
                    services[service_name] = {
                        "status": service_status,
                        "uptime": "N/A",  # No uptime data available
                        "regions": {}
                    }
                
                # Add regional information
                services[service_name]["regions"][region] = {
                    "status": services[service_name]["status"],  # Use service status
                    "uptime": "N/A"
                }
                
                # Store uptime stats
                if service_name not in uptime_stats:
                    uptime_stats[service_name] = {}
                uptime_stats[service_name][region] = "N/A"
        
        # Extract recent incidents from uptimeData
        recent_incidents = []
        
        # Look for incident information in the uptimeData JavaScript variable
        for script in script_tags:
            script_text = script.get_text()
            if 'uptimeData' in script_text:
                # Find the uptimeData variable content - look for the entire object
                # Start from 'var uptimeData = {' and find the matching closing brace
                start_pos = script_text.find('var uptimeData = {')
                if start_pos != -1:
                    # Find the matching closing brace by counting braces
                    brace_count = 0
                    end_pos = start_pos + len('var uptimeData = {')
                    
                    for i in range(end_pos, len(script_text)):
                        if script_text[i] == '{':
                            brace_count += 1
                        elif script_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i
                                break
                    
                    if end_pos > start_pos:
                        uptime_data_text = script_text[start_pos + len('var uptimeData = {'):end_pos]
                        
                        # Look for incidents in the days arrays
                        # Pattern: "date":"2025-08-24","outages":{},"related_events":[{"name":"On-boarding Disruption","code":"8ccw26zsv1z9"}]
                        # Only match when related_events is not empty (not just [])
                        incident_matches = re.findall(r'"date":"([^"]+)","outages":\{[^}]*\},"related_events":\[([^\]]+)\]', uptime_data_text)
                        
                        for date_str, events_text in incident_matches:
                            # events_text will only contain non-empty arrays due to the regex pattern
                            if events_text and events_text != "[]":
                                # Parse the events
                                event_matches = re.findall(r'"name":"([^"]+)","code":"([^"]+)"', events_text)
                                for event_name, event_code in event_matches:
                                    if len(event_name) > 5:  # Avoid generic names
                                        # Parse the date
                                        try:
                                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                                            incident_date = date_obj.strftime("%b %d, %Y")
                                        except ValueError:
                                            incident_date = date_str
                                        
                                        incident_info = {
                                            "title": event_name,
                                            "status": "Resolved",  # Default status - could be enhanced to parse actual status
                                            "date": incident_date
                                        }
                                        
                                        # Only add if not already present
                                        if not any(inc["title"] == event_name for inc in recent_incidents):
                                            recent_incidents.append(incident_info)
                                            tool_logger.debug(f"Added incident: {event_name} on {incident_date}")
                                            if len(recent_incidents) >= 10:  # Limit to 10 incidents
                                                break
                            
                            if len(recent_incidents) >= 10:
                                break
                        
                        # If we found incidents, break out of the script loop
                        if recent_incidents:
                            break
        
        # If no incidents found from uptimeData, try alternative methods
        if not recent_incidents:
            # Look for incident information in the JavaScript
            for script in script_tags:
                script_text = script.get_text()
                if 'related_events' in script_text:
                    # Find incident entries with better date extraction
                    incident_matches = re.findall(r'"name":"([^"]+)","code":"([^"]+)","created_at":"([^"]+)"', script_text)
                    for incident_name, incident_code, created_at in incident_matches:
                        # Only add meaningful incidents (avoid generic names)
                        if len(incident_name) > 5 and incident_name not in [inc["title"] for inc in recent_incidents]:
                            # Parse the created_at timestamp
                            incident_date = "Unknown"
                            try:
                                # Handle different date formats
                                if created_at and created_at != "null":
                                    # Try to parse ISO format or other common formats
                                    if "T" in created_at:
                                        # ISO format: "2025-08-24T10:30:00Z"
                                        date_obj = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                                        incident_date = date_obj.strftime("%b %d, %Y")
                                    elif "-" in created_at:
                                        # Date format: "2025-08-24"
                                        date_obj = datetime.strptime(created_at, "%Y-%m-%d")
                                        incident_date = date_obj.strftime("%b %d, %Y")
                                    else:
                                        incident_date = created_at
                            except (ValueError, TypeError):
                                incident_date = created_at if created_at and created_at != "null" else "Unknown"
                            
                            incident_info = {
                                "title": incident_name,
                                "status": "Resolved",  # Default status - could be enhanced to parse actual status
                                "date": "Recent"  # Default date
                            }
                            recent_incidents.append(incident_info)
                            if len(recent_incidents) >= 10:  # Limit to 10 incidents
                                break
                    
                    # If no incidents found with created_at, try alternative patterns
                    if not recent_incidents:
                        # Look for incidents without timestamps
                        incident_matches = re.findall(r'"name":"([^"]+)","code":"([^"]+)"', script_text)
                        for incident_name, incident_code in incident_matches:
                            if len(incident_name) > 5 and incident_name not in [inc["title"] for inc in recent_incidents]:
                                incident_info = {
                                    "title": incident_name,
                                    "status": "Resolved",  # Default status
                                    "date": "Recent"  # Default date
                                }
                                recent_incidents.append(incident_info)
                                if len(recent_incidents) >= 10:
                                    break
        
        # Extract regional status summary dynamically from the actual data
        regional_status = {}
        
        # First, discover all regions from the actual service data
        discovered_regions = set()
        for service_name, service_info in services.items():
            for region in service_info["regions"].keys():
                discovered_regions.add(region)
        
        # Initialize regional status for discovered regions
        for region in discovered_regions:
            regional_status[region] = {"operational": 0, "total": 0}
        
        # Count operational services by region
        for service_name, service_info in services.items():
            for region, region_info in service_info["regions"].items():
                if region in regional_status:
                    regional_status[region]["total"] += 1
                    # Check for various operational statuses dynamically
                    if (region_info["status"].lower() in ["operational", "operational", "healthy", "normal"] or 
                        "outage" not in region_info["status"].lower() and 
                        "disruption" not in region_info["status"].lower()):
                        regional_status[region]["operational"] += 1
        
        # Calculate overall uptime
        total_uptime = 0
        uptime_count = 0
        for service_name, service_info in services.items():
            for region, region_info in service_info["regions"].items():
                if region_info["uptime"] != "N/A":
                    try:
                        uptime_value = float(region_info["uptime"].replace('%', ''))
                        total_uptime += uptime_value
                        uptime_count += 1
                    except ValueError:
                        pass
        
        overall_uptime = round(total_uptime / uptime_count, 2) if uptime_count > 0 else "N/A"
        
        return {
            "success": True,
            "overall_status": overall_status,
            "overall_uptime": f"{overall_uptime}%" if overall_uptime != "N/A" else "N/A",
            "services": services,
            "uptime_stats": uptime_stats,
            "regional_status": regional_status,
            "recent_incidents": recent_incidents,
            "status_page_url": status_url,
            "last_updated": datetime.now().isoformat(),
            "message": f"DPoD platform status: {overall_status} (Overall uptime: {overall_uptime}%)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to check DPoD status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        } 