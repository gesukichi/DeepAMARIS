"""
User Service

Lightweight user authentication and management service.
Integrates with existing backend/auth/auth_utils.py functionality.

Design principles:
- Practical implementation over complex architecture
- Backward compatibility with existing auth system
- Safe handling of invalid/missing authentication data
- Stateless and thread-safe operation
"""

from typing import Dict, Any, Optional, List
import os
from domain.user.models.user import User


class UserService:
    """
    User authentication and management service.
    
    Responsibilities:
    - Authenticate users from HTTP headers
    - Provide auth_me() endpoint compatibility
    - Integrate with existing auth_utils.py functionality
    - Handle development mode fallback
    
    Design: Stateless service that can safely handle any input
    """
    
    def authenticate_user_from_headers(self, headers: Optional[Any]) -> User:
        """
        Authenticate user from HTTP request headers.
        
        Args:
            headers: HTTP request headers (can be None, invalid type, etc.)
            
        Returns:
            User entity (authenticated or development mode)
            
        Design: Handles all edge cases gracefully:
        - None headers
        - Invalid header types
        - Missing authentication data
        - Development mode fallback
        """
        # Handle None or invalid header types
        if not self._is_valid_headers(headers):
            return self._get_development_mode_user()
        
        # Check for Azure App Service EasyAuth headers
        if self._has_production_auth_headers(headers):
            return self._create_user_from_production_headers(headers)
        else:
            return self._get_development_mode_user()
    
    def get_auth_me_response(self, headers: Optional[Any]) -> List[Dict[str, Any]]:
        """
        Get response for /.auth/me endpoint.
        
        Args:
            headers: HTTP request headers
            
        Returns:
            List format compatible with auth_me() endpoint
            
        Compatibility: Maintains exact compatibility with existing auth_me() function
        """
        user = self.authenticate_user_from_headers(headers)
        return user.to_auth_me_format()
    
    def _is_valid_headers(self, headers: Any) -> bool:
        """
        Check if headers parameter is valid.
        
        Args:
            headers: Headers to validate
            
        Returns:
            True if headers can be processed, False otherwise
            
        Edge cases: Handles None, non-dict types, etc.
        """
        if headers is None:
            return False
        
        # Must be dict-like (support .get() method)
        return hasattr(headers, 'get') or isinstance(headers, dict)
    
    def _has_production_auth_headers(self, headers: Dict[str, Any]) -> bool:
        """
        Check if headers contain Azure App Service EasyAuth data.
        
        Args:
            headers: HTTP headers dictionary
            
        Returns:
            True if production auth headers are present
            
        Logic: Presence of X-Ms-Client-Principal-Id indicates production auth
        """
        try:
            return 'X-Ms-Client-Principal-Id' in headers
        except (TypeError, AttributeError):
            return False
    
    def _create_user_from_production_headers(self, headers: Dict[str, Any]) -> User:
        """
        Create User entity from production authentication headers.
        
        Args:
            headers: HTTP headers with Azure EasyAuth data
            
        Returns:
            User entity with production authentication data
            
        Implementation: Maps Azure EasyAuth headers to User entity
        """
        auth_data = {
            'user_principal_id': self._safe_header_get(headers, 'X-Ms-Client-Principal-Id'),
            'user_name': self._safe_header_get(headers, 'X-Ms-Client-Principal-Name'),
            'auth_provider': self._safe_header_get(headers, 'X-Ms-Client-Principal-Idp'),
            'auth_token': self._safe_header_get(headers, 'X-Ms-Token-Aad-Id-Token'),
            'client_principal_b64': self._safe_header_get(headers, 'X-Ms-Client-Principal'),
            'aad_id_token': self._safe_header_get(headers, 'X-Ms-Token-Aad-Id-Token')
        }
        
        return User.from_auth_data(auth_data)
    
    def _get_development_mode_user(self) -> User:
        """
        Get user for development mode.
        
        Returns:
            User entity with development mode data
            
        Implementation: Uses sample_user data for development compatibility
        """
        try:
            # Import sample_user data (existing development mode support)
            from backend.auth import sample_user
            sample_data = sample_user.sample_user
            
            auth_data = {
                'user_principal_id': sample_data.get('X-Ms-Client-Principal-Id'),
                'user_name': sample_data.get('X-Ms-Client-Principal-Name'),
                'auth_provider': sample_data.get('X-Ms-Client-Principal-Idp'),
                'auth_token': sample_data.get('X-Ms-Token-Aad-Id-Token'),
                'client_principal_b64': sample_data.get('X-Ms-Client-Principal'),
                'aad_id_token': sample_data.get('X-Ms-Token-Aad-Id-Token')
            }
            
            return User.from_auth_data(auth_data)
            
        except (ImportError, AttributeError, KeyError):
            # Fallback if sample_user cannot be loaded
            fallback_data = {
                'user_principal_id': '00000000-0000-0000-0000-000000000000',
                'user_name': 'dev-user@localhost',
                'auth_provider': 'development',
                'auth_token': None
            }
            
            return User.from_auth_data(fallback_data)
    
    def _safe_header_get(self, headers: Dict[str, Any], key: str) -> Optional[str]:
        """
        Safely get header value.
        
        Args:
            headers: Headers dictionary
            key: Header key to retrieve
            
        Returns:
            Header value or None
            
        Safety: Handles any exception during header access
        """
        try:
            return headers.get(key)
        except (AttributeError, TypeError, KeyError):
            return None
    
    def is_development_mode(self) -> bool:
        """
        Check if running in development mode.
        
        Returns:
            bool: True if in development mode
            
        Note: Checks AUTH_REQUIRED environment variable.
        If AUTH_REQUIRED is 'false', it's development mode.
        """
        # Check environment variable
        auth_required = os.environ.get('AUTH_REQUIRED', 'true').lower()
        
        # Development mode when auth is not required
        return auth_required == 'false'
