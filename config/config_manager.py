"""Configuration management for the Music ETL Pipeline"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager
        
        Args:
            config_path: Path to YAML config file. If None, uses default location.
        """
        load_dotenv()
        
        if config_path is None:
            config_path = Path(__file__).parent / "pipeline_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Override with environment variables where applicable
            self._apply_env_overrides(config)
            
            return config
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> None:
        """Apply environment variable overrides"""
        # Override with environment variables
        env_mappings = {
            'PIPELINE_LOG_LEVEL': ['logging', 'level'],
            'SPOTIFY_TIMEOUT': ['apis', 'spotify', 'timeout'],
            'YOUTUBE_TIMEOUT': ['apis', 'youtube', 'timeout'],
            'MAX_RECORDS_PER_RUN': ['data_quality', 'validation_rules', 'max_records_per_run'],
            'DAYS_BEHIND': ['ingestion', 'default_days_behind'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config, config_path, value)
    
    def _set_nested_value(self, config: Dict, path: List[str], value: str) -> None:
        """Set a nested configuration value"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Convert string values to appropriate types
        if value.isdigit():
            value = int(value)
        elif value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.replace('.', '').isdigit():
            value = float(value)
        
        current[path[-1]] = value
    
    def _validate_config(self) -> None:
        """Validate configuration completeness and correctness"""
        required_sections = ['pipeline', 'ingestion', 'music', 'data_quality', 'storage']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
    
    # Getter methods for easy access
    def get_approved_genres(self) -> List[str]:
        """Get list of approved music genres"""
        return self.config['music']['approved_genres']
    
    def get_genre_aliases(self) -> Dict[str, List[str]]:
        """Get genre aliases mapping"""
        return self.config['music'].get('genre_aliases', {})
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get data validation rules"""
        return self.config['data_quality']['validation_rules']
    
    def get_required_fields(self, data_type: str) -> List[str]:
        """Get required fields for a specific data type"""
        return self.config['data_quality']['required_fields'].get(data_type, [])
    
    def get_ingestion_config(self) -> Dict[str, Any]:
        """Get ingestion configuration"""
        return self.config['ingestion']
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.config['storage']
    
    def get_api_config(self, api_name: str) -> Dict[str, Any]:
        """Get API-specific configuration"""
        return self.config['apis'].get(api_name, {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config['logging']
    
    def get_days_behind(self) -> int:
        """Get default days behind for data ingestion"""
        return self.config['ingestion']['default_days_behind']
    
    def get_batch_size(self, service: str) -> int:
        """Get batch size for a specific service"""
        return self.config['ingestion'].get(f'{service}_batch_size', 50)
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """Update a configuration value at runtime"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def save_config(self, output_path: Optional[str] = None) -> None:
        """Save current configuration to file"""
        if output_path is None:
            output_path = self.config_path
        
        with open(output_path, 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False, indent=2)