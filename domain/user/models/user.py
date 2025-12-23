"""
User Entity

Lightweight user model for authentication and basic user information management.
Designed for practical implementation, avoiding complex layered architecture.

Design principles:
- Simple, practical implementation
- Backward compatibility with auth_me() endpoint
- Safe handling of invalid/missing data
- Secure token handling
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class User:
    """
    User entity representing authenticated user information.
    
    Designed to handle:
    - Azure AD authentication data
    - Development mode compatibility  
    - Safe data conversion and validation
    - auth_me() endpoint compatibility
    """
    
    user_principal_id: Optional[str] = None
    user_name: Optional[str] = None
    auth_provider: Optional[str] = None
    auth_token: Optional[str] = None
    client_principal_b64: Optional[str] = None
    aad_id_token: Optional[str] = None
    
    @classmethod
    def from_auth_data(cls, auth_data: Optional[Dict[str, Any]]) -> 'User':
        """
        Create User entity from authentication data.
        
        Args:
            auth_data: Authentication data dictionary (can be None)
            
        Returns:
            User entity with safe data conversion
            
        Design: Handles all edge cases gracefully:
        - None data
        - Missing fields
        - Invalid data types
        - Empty strings
        """
        if auth_data is None:
            return cls()
        
        # Safe data conversion with type handling
        user_principal_id = cls._safe_string_conversion(auth_data.get('user_principal_id'))
        user_name = cls._safe_string_conversion(auth_data.get('user_name'))
        auth_provider = cls._safe_string_conversion(auth_data.get('auth_provider'))
        auth_token = cls._safe_string_conversion(auth_data.get('auth_token'))
        client_principal_b64 = cls._safe_string_conversion(auth_data.get('client_principal_b64'))
        aad_id_token = cls._safe_string_conversion(auth_data.get('aad_id_token'))
        
        return cls(
            user_principal_id=user_principal_id,
            user_name=user_name,
            auth_provider=auth_provider,
            auth_token=auth_token,
            client_principal_b64=client_principal_b64,
            aad_id_token=aad_id_token
        )
    
    @staticmethod
    def _safe_string_conversion(value: Any) -> Optional[str]:
        """
        Safely convert any value to string or None.
        
        Args:
            value: Any value to convert
            
        Returns:
            String representation or None
            
        Edge cases handled:
        - None -> None
        - Empty string -> None (treated as no data)
        - Numbers, lists, dicts -> string representation
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            return value if value.strip() else None
        
        # Convert other types to string representation
        try:
            str_value = str(value)
            return str_value if str_value.strip() else None
        except (TypeError, ValueError, UnicodeError):
            # Handle specific exceptions that might occur during string conversion
            return None
    
    @property
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        
        Returns:
            True if user has valid principal ID, False otherwise
            
        Logic: User is considered authenticated if they have a non-empty principal ID
        """
        return self.user_principal_id is not None and len(self.user_principal_id.strip()) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user to dictionary representation.
        
        Returns:
            Dictionary with user data (excluding sensitive tokens)
            
        Security: Excludes auth_token and other sensitive data
        """
        return {
            'user_principal_id': self.user_principal_id,
            'user_name': self.user_name,
            'auth_provider': self.auth_provider,
            'is_authenticated': self.is_authenticated
            # Note: auth_token and other sensitive data intentionally excluded
        }
    
    def to_auth_me_format(self) -> List[Dict[str, Any]]:
        """
        Convert user to auth_me() endpoint format.
        
        Returns:
            List format compatible with /.auth/me endpoint:
            - Empty list for unauthenticated users
            - Single-item list for authenticated users
            
        Compatibility: Maintains backward compatibility with existing auth_me() endpoint
        """
        if not self.is_authenticated:
            return []
        
        return [{
            'user_id': self.user_principal_id,
            'user_claims': []  # Empty claims list for development compatibility
        }]
    
    def __eq__(self, other) -> bool:
        """
        User equality comparison based on principal ID.
        
        Args:
            other: Another User instance
            
        Returns:
            True if both users have the same principal ID
        """
        if not isinstance(other, User):
            return False
        
        return self.user_principal_id == other.user_principal_id
    
    def __hash__(self) -> int:
        """
        Hash function for User entity.
        
        Returns:
            Hash based on principal ID
        """
        return hash(self.user_principal_id) if self.user_principal_id else hash(None)
    
    def __str__(self) -> str:
        """
        String representation of User.
        
        Returns:
            Human-readable string representation
        """
        if self.is_authenticated:
            return f"User(id={self.user_principal_id}, name={self.user_name})"
        else:
            return "User(unauthenticated)"
    
    def __repr__(self) -> str:
        """
        Developer representation of User.
        
        Returns:
            Detailed representation for debugging
        """
        return (f"User(user_principal_id={self.user_principal_id!r}, "
                f"user_name={self.user_name!r}, "
                f"auth_provider={self.auth_provider!r}, "
                f"is_authenticated={self.is_authenticated})")
