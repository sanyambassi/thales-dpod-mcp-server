#!/usr/bin/env python3
"""
Thales DPoD MCP Server - Authentication Module

Handles OAuth 2.0 client credentials flow and token management with JWT validation.
"""

import asyncio
import time
import logging
import jwt
from typing import Optional, Dict, Any, List
import httpx
from .config import DPoDConfig

class DPoDAuth:
    """OAuth 2.0 authentication for Thales DPoD API with JWT validation."""
    
    def __init__(self, config: DPoDConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        self.token_payload: Optional[Dict[str, Any]] = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(__name__)
    
    async def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        try:
            # Check if we have a valid token
            if not force_refresh and self._is_token_valid():
                return self.access_token
            
            # Get new token
            await self._refresh_token()
            return self.access_token
            
        except Exception as e:
            self.logger.error(f"Failed to get access token: {e}")
            return None
    
    async def _refresh_token(self) -> None:
        """Refresh the OAuth access token using client credentials flow."""
        try:
            # Validate credentials before making request
            if not self.config.client_id or not self.config.client_secret:
                raise Exception("Missing OAuth credentials: DPOD_CLIENT_ID and DPOD_CLIENT_SECRET are required")
            
            if not self.config.client_id.strip() or not self.config.client_secret.strip():
                raise Exception("OAuth credentials cannot be empty or whitespace only")
            
            # Prepare OAuth request
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret
            }
            
            # Scope is now automatically detected from the OAuth token response
            # No need to specify scope in the request for client credentials flow
            
            # Make token request
            response = await self.http_client.post(
                self.config.dpod_auth_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_text = response.text if response.text else "No error details provided"
                raise Exception(f"Token refresh failed: HTTP {response.status_code} - {error_text}")
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            
            if not self.access_token:
                raise Exception("No access token in response")
            
            # Calculate expiration (default to 1 hour if not provided)
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = time.time() + expires_in
            
            # Clear cached payload since we have a new token
            self.token_payload = None
            
            self.logger.info("OAuth access token refreshed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh OAuth token: {e}")
            raise
    
    def _is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Add 5-minute buffer to avoid edge cases
        buffer_time = 300  # 5 minutes
        return time.time() < (self.token_expires_at - buffer_time)
    
    async def make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an authenticated HTTP request to the DPoD API."""
        # Ensure we have a valid token before making the request
        await self.ensure_valid_token()
        
        # Prepare headers
        request_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)
        
        # Make the request
        try:
            response = await self.http_client.request(
                method,
                f"{self.config.dpod_base_url}{endpoint}",
                params=params,
                json=json_data,
                headers=request_headers,
                **kwargs
            )
            
            # If we get a 401, try to refresh the token and retry once
            if response.status_code == 401:
                self.logger.warning("Token expired, attempting to refresh...")
                await self._refresh_token()
                
                # Update headers with new token
                request_headers["Authorization"] = f"Bearer {self.access_token}"
                
                # Retry the request
                response = await self.http_client.request(
                    method,
                    f"{self.config.dpod_base_url}{endpoint}",
                    params=params,
                    json=json_data,
                    headers=request_headers,
                    **kwargs
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            raise

    async def make_unauthenticated_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an unauthenticated HTTP request to the DPoD API.
        
        This method is used for public endpoints that don't require authentication,
        such as /service_categories and /service_types.
        """
        # Prepare headers (no Authorization header)
        request_headers = {
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)
        
        # Make the request
        try:
            response = await self.http_client.request(
                method,
                f"{self.config.dpod_base_url}{endpoint}",
                params=params,
                json=json_data,
                headers=request_headers,
                **kwargs
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Unauthenticated request failed: {e}")
            raise

    async def ensure_valid_token(self) -> None:
        """Ensure we have a valid token, refreshing if necessary."""
        if not self.access_token or self.is_token_expired():
            await self._refresh_token()

    def is_token_expired(self) -> bool:
        """Check if the current token is expired or will expire soon (within 5 minutes)."""
        if not self.access_token:
            return True
        
        try:
            # Decode the JWT without verification to check expiration
            decoded = jwt.decode(self.access_token, options={"verify_signature": False})
            exp = decoded.get('exp')
            
            if not exp:
                return True
            
            # Check if token expires within 5 minutes
            current_time = time.time()
            return exp <= (current_time + 300)  # 5 minutes buffer
            
        except Exception as e:
            self.logger.warning(f"Could not decode token to check expiration: {e}")
            return True

    async def validate_token_permissions(self, required_scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate that the current token has the required permissions.
        
        Args:
            required_scopes: List of required scopes (optional)
            
        Returns:
            Dict with validation results and token info
        """
        try:
            await self.ensure_valid_token()
            
            if not self.access_token:
                return {
                    "valid": False,
                    "error": "No access token available"
                }
            
            # Decode the JWT to check scopes
            decoded = jwt.decode(self.access_token, options={"verify_signature": False})
            
            # Check if token is expired
            current_time = time.time()
            exp = decoded.get('exp', 0)
            
            if exp <= current_time:
                return {
                    "valid": False,
                    "error": "Token has expired"
                }
            
            # Extract scopes from the 'scope' field
            scopes = decoded.get('scope', '')
            
            if isinstance(scopes, str):
                scopes = scopes.split() if scopes else []
            
            # Check required scopes if specified
            missing_scopes = []
            if required_scopes:
                for required_scope in required_scopes:
                    if required_scope not in scopes:
                        missing_scopes.append(required_scope)
            
            return {
                "valid": len(missing_scopes) == 0,
                "scopes": scopes,
                "missing_scopes": missing_scopes,
                "expires_at": exp,
                "user_id": decoded.get('sub'),
                "client_id": decoded.get('cid'),
                "authorities": decoded.get('authorities', [])
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Token validation failed: {str(e)}"
            }
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Alias for make_authenticated_request for compatibility."""
        return await self.make_authenticated_request(method, endpoint, **kwargs)
    
    async def check_connection(self) -> bool:
        """Check if authentication and API connection are working."""
        try:
            token = await self.get_access_token()
            return token is not None
        except Exception as e:
            self.logger.warning(f"Connection check failed: {e}")
            return False
    
    async def get_token(self) -> Dict[str, Any]:
        """Get token information for compatibility with system tools.
        
        Returns:
            Dict with token status and information
        """
        try:
            token = await self.get_access_token()
            if token:
                return {
                    "success": True,
                    "access_token": token,
                    "expires_at": self.token_expires_at
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get access token"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def introspect_token(self) -> Dict[str, Any]:
        """Introspect the current token for detailed information.
        
        Returns:
            Dict with token introspection results
        """
        try:
            if not self.access_token:
                return {
                    "success": False,
                    "error": "No access token available"
                }
            
            # Decode the JWT to get token information
            decoded = jwt.decode(self.access_token, options={"verify_signature": False})
            
            return {
                "success": True,
                "token_data": {
                    "active": not self.is_token_expired(),
                    "exp": decoded.get('exp'),
                    "scope": decoded.get('scope', ''),  # Keep scope as string, don't join
                    "client_id": decoded.get('cid'),
                    "iss": decoded.get('iss'),
                    "aud": decoded.get('aud'),
                    "cached": True  # Token is cached in memory
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, 'http_client') and self.http_client:
            await self.http_client.aclose()
    
    def __del__(self):
        """Cleanup on deletion."""
        # Note: __del__ cannot be async, so we just ensure the object is cleaned up
        # The HTTP client will be cleaned up by Python's garbage collector
        pass 