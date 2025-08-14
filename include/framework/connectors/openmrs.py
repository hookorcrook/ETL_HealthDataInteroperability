from typing import Any, Dict, Optional
import requests
from airflow.hooks.base import BaseHook
from ..base.extractor import BaseExtractor

class OpenMRSExtractor(BaseExtractor):
    """Extractor for OpenMRS data"""
    
    def __init__(self, config: Dict[str, Any], entity_type: str = 'person'):
        super().__init__(config)
        self.conn = BaseHook.get_connection('openmrs_api')
        self.entity_type = entity_type
        self.api_config = config.get('openmrs', {}).get('api', {})
    
    def build_url(self) -> str:
        """Build API URL based on entity type"""
        endpoint = self.api_config.get(f'{self.entity_type}_endpoint')
        if not endpoint:
            raise ValueError(f"No endpoint configured for entity type: {self.entity_type}")
        
        return f"{self.conn.host}{endpoint}"
    
    def get_params(self) -> Dict[str, str]:
        """Get query parameters"""
        return self.api_config.get('default_params', {'v': 'full'})
    
    def extract(self) -> str:
        """Extract data from OpenMRS
        
        Returns:
            str: Path to extracted data file
        """
        self.logger.info(f"Extracting {self.entity_type} data from OpenMRS")
        
        url = self.build_url()
        params = self.get_params()
        auth = (self.conn.login, self.conn.password)
        
        try:
            response = requests.get(url, auth=auth, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not self.validate_extraction(data):
                raise ValueError("Data validation failed")
            
            output_path = self.get_output_path(self.entity_type)
            with open(output_path, 'w') as f:
                f.write(response.text)
            
            self.logger.info(f"Successfully extracted data to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error extracting data: {str(e)}")
            raise
    
    def validate_extraction(self, data: Dict[str, Any]) -> bool:
        """Validate extracted data
        
        Args:
            data: The extracted data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        if not isinstance(data, dict):
            self.logger.error("Extracted data is not a dictionary")
            return False
        
        if 'results' not in data:
            self.logger.error("No 'results' key in extracted data")
            return False
        
        if not isinstance(data['results'], list):
            self.logger.error("'results' is not a list")
            return False
        
        return True
