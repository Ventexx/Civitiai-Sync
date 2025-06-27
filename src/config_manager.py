"""
Configuration management for Civitai Sync
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration for Civitai Sync"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize ConfigManager
        
        Args:
            config_dir: Optional custom config directory
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Use user's home directory for config
            self.config_dir = Path.home() / '.civitai-sync'
        
        self.config_file = self.config_dir / 'config.json'
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create config directory: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_file.exists():
            return {}
        
        try:
            with self.config_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with self.config_file.open('w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def save_api_key(self, api_key: str) -> bool:
        """
        Save API key to config
        
        Args:
            api_key: Civitai API key
            
        Returns:
            True if successful
        """
        config = self._load_config()
        config['api_key'] = api_key
        
        if self._save_config(config):
            logger.info("API key saved successfully")
            return True
        
        return False
    
    def get_api_key(self) -> Optional[str]:
        """
        Get API key from config
        
        Returns:
            API key if found, None otherwise
        """
        config = self._load_config()
        return config.get('api_key')
    
    def remove_api_key(self) -> bool:
        """
        Remove API key from config
        
        Returns:
            True if successful
        """
        config = self._load_config()
        if 'api_key' in config:
            del config['api_key']
            return self._save_config(config)
        return True
    
    def get_config_path(self) -> Path:
        """Get path to config file"""
        return self.config_file
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration setting
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        config = self._load_config()
        return config.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a configuration setting
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful
        """
        config = self._load_config()
        config[key] = value
        return self._save_config(config)