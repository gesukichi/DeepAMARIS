"""
System Settings Entity

軽量なシステム設定エンティティ。
既存の app.py の frontend_settings 機能を User Domain として再実装。

Design principles:
- Simple, practical implementation
- Backward compatibility with existing frontend_settings
- Safe handling of invalid/missing configuration data
- Immutable settings after creation
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass(frozen=True, eq=True)
class SystemSettings:
    """
    System Settings entity representing system configuration.
    
    Designed to handle:
    - Frontend UI configuration
    - Authentication and feedback settings
    - Environment-specific overrides
    - Safe data conversion and validation
    """
    
    # Authentication & Core Settings
    auth_enabled: bool = False
    feedback_enabled: bool = False
    sanitize_answer: bool = True
    oyd_enabled: Optional[str] = None
    
    # UI Settings
    ui_title: str = 'Contoso'
    ui_logo: Optional[str] = None
    ui_chat_logo: Optional[str] = None
    ui_chat_title: str = 'Start chatting'
    ui_chat_description: str = 'This chatbot is configured to answer your questions'
    ui_show_share_button: bool = True
    ui_show_chat_history_button: bool = False
    
    @classmethod
    def from_config_data(cls, config_data: Optional[Dict[str, Any]]) -> 'SystemSettings':
        """
        Create SystemSettings entity from configuration data.
        
        Args:
            config_data: Configuration data dictionary (can be None)
            
        Returns:
            SystemSettings entity with safe data conversion
            
        Design: Handles all edge cases gracefully:
        - None data
        - Missing fields
        - Invalid data types
        - Malformed nested structures
        """
        if config_data is None:
            config_data = {}
        
        if not isinstance(config_data, dict):
            config_data = {}
        
        # UI settings extraction with safe defaults
        ui_data = config_data.get('ui', {})
        if not isinstance(ui_data, dict):
            ui_data = {}
        
        # Safe extraction with type validation
        auth_enabled = cls._safe_bool_convert(config_data.get('auth_enabled'), False)
        feedback_enabled = cls._safe_bool_convert(config_data.get('feedback_enabled'), False)
        sanitize_answer = cls._safe_bool_convert(config_data.get('sanitize_answer'), True)
        
        # OYD (On Your Data) setting
        oyd_enabled = config_data.get('oyd_enabled')
        if oyd_enabled is not None and not isinstance(oyd_enabled, str):
            oyd_enabled = None
        
        # UI settings with safe extraction
        ui_title = cls._safe_string_convert(ui_data.get('title'), 'Contoso')
        ui_logo = cls._safe_string_convert(ui_data.get('logo'), None)
        ui_chat_logo = cls._safe_string_convert(ui_data.get('chat_logo'), None)
        ui_chat_title = cls._safe_string_convert(ui_data.get('chat_title'), 'Start chatting')
        ui_chat_description = cls._safe_string_convert(
            ui_data.get('chat_description'), 
            'This chatbot is configured to answer your questions'
        )
        ui_show_share_button = cls._safe_bool_convert(ui_data.get('show_share_button'), True)
        ui_show_chat_history_button = cls._safe_bool_convert(ui_data.get('show_chat_history_button'), False)
        
        return cls(
            auth_enabled=auth_enabled,
            feedback_enabled=feedback_enabled,
            sanitize_answer=sanitize_answer,
            oyd_enabled=oyd_enabled,
            ui_title=ui_title,
            ui_logo=ui_logo,
            ui_chat_logo=ui_chat_logo,
            ui_chat_title=ui_chat_title,
            ui_chat_description=ui_chat_description,
            ui_show_share_button=ui_show_share_button,
            ui_show_chat_history_button=ui_show_chat_history_button
        )
    
    def to_frontend_dict(self) -> Dict[str, Any]:
        """
        Convert to frontend-compatible dictionary format.
        
        Returns:
            Dict compatible with existing frontend_settings format
        """
        return {
            'auth_enabled': self.auth_enabled,
            'feedback_enabled': self.feedback_enabled,
            'ui': {
                'title': self.ui_title,
                'logo': self.ui_logo,
                'chat_logo': self.ui_chat_logo,
                'chat_title': self.ui_chat_title,
                'chat_description': self.ui_chat_description,
                'show_share_button': self.ui_show_share_button,
                'show_chat_history_button': self.ui_show_chat_history_button,
            },
            'sanitize_answer': self.sanitize_answer,
            'oyd_enabled': self.oyd_enabled,
        }
    
    @staticmethod
    def _safe_bool_convert(value: Any, default: bool) -> bool:
        """
        Safely convert value to boolean.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Boolean value or default
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower_value = value.lower()
            if lower_value in ('true', 'yes', '1', 'on'):
                return True
            elif lower_value in ('false', 'no', '0', 'off'):
                return False
            else:
                # 無効な文字列はデフォルト値を返す
                return default
        # その他のデータ型（数値など）はデフォルト値を返す
        return default
    
    @staticmethod
    def _safe_string_convert(value: Any, default: Optional[str]) -> Optional[str]:
        """
        Safely convert value to string.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            String value or default
        """
        if value is None:
            return default
        if isinstance(value, str):
            return value
        try:
            return str(value)
        except (ValueError, TypeError):
            return default
