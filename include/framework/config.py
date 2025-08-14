import os
import yaml
from typing import Dict, Any
from pathlib import Path

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class Config:
    """Configuration manager for the ETL pipeline"""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration manager
        
        Args:
            config_path (str, optional): Path to configuration file. Defaults to config/default.yaml
        """
        if config_path is None:
            config_path = os.path.join('config', 'default.yaml')
        
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file and resolve environment variables
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        if not os.path.exists(self.config_path):
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return self._resolve_env_vars(config)
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve environment variables in configuration
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            
        Returns:
            Dict[str, Any]: Configuration with resolved environment variables
        """
        resolved_config = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                resolved_config[key] = self._resolve_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                env_value = os.getenv(env_var)
                if env_value is None:
                    raise ConfigurationError(f"Environment variable not set: {env_var}")
                resolved_config[key] = env_value
            else:
                resolved_config[key] = value
        
        return resolved_config
    
    def _validate_config(self):
        """Validate required configuration parameters"""
        required_configs = {
            'openmrs': ['base_url', 'username', 'password'],
            'dhis2': ['base_url', 'api_token'],
            'spark': ['master']
        }
        
        for section, fields in required_configs.items():
            if section not in self.config:
                raise ConfigurationError(f"Missing configuration section: {section}")
            
            for field in fields:
                if field not in self.config[section]:
                    raise ConfigurationError(f"Missing configuration field: {section}.{field}")
    
    def get(self, section: str, key: str = None) -> Any:
        """Get configuration value
        
        Args:
            section (str): Configuration section
            key (str, optional): Configuration key. If None, returns entire section
            
        Returns:
            Any: Configuration value
        """
        if section not in self.config:
            raise ConfigurationError(f"Configuration section not found: {section}")
        
        if key is None:
            return self.config[section]
        
        if key not in self.config[section]:
            raise ConfigurationError(f"Configuration key not found: {section}.{key}")
        
        return self.config[section][key]
    
    @property
    def openmrs(self) -> Dict[str, Any]:
        """Get OpenMRS configuration
        
        Returns:
            Dict[str, Any]: OpenMRS configuration
        """
        return self.get('openmrs')
    
    @property
    def dhis2(self) -> Dict[str, Any]:
        """Get DHIS2 configuration
        
        Returns:
            Dict[str, Any]: DHIS2 configuration
        """
        return self.get('dhis2')
    
    @property
    def spark(self) -> Dict[str, Any]:
        """Get Spark configuration
        
        Returns:
            Dict[str, Any]: Spark configuration
        """
        return self.get('spark')
