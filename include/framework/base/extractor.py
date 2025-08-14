from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import os

class BaseExtractor(ABC):
    """Base class for all data extractors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timestamp = datetime.now().strftime("%Y%m%d")
        self.temp_path = config.get('temp_data', {}).get('base_path', './include/temp_data')
        
    def get_output_path(self, prefix: str, suffix: str = 'raw') -> str:
        """Generate output path for extracted data"""
        os.makedirs(self.temp_path, exist_ok=True)
        return os.path.join(self.temp_path, f"{prefix}_{suffix}_{self.timestamp}.json")
    
    @abstractmethod
    def extract(self) -> str:
        """Extract data from source system
        
        Returns:
            str: Path to the extracted data file
        """
        pass
    
    def validate_extraction(self, data: Any) -> bool:
        """Validate extracted data
        
        Args:
            data: The extracted data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        return True
    
    def cleanup(self):
        """Cleanup any resources used during extraction"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
