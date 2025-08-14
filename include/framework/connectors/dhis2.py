from typing import Any, Dict, List
import json
from airflow.hooks.base import BaseHook
from ..base.loader import BaseLoader

class DHIS2Loader(BaseLoader):
    """Loader for DHIS2 data"""
    
    def __init__(self, config: Dict[str, Any], entity_type: str = 'trackedEntityInstances'):
        super().__init__(config)
        self.conn = BaseHook.get_connection('dhis2_api')
        self.entity_type = entity_type
        self.api_config = config.get('dhis2', {}).get('api', {})
        
        # Setup headers
        self.headers = {
            "Authorization": f"ApiToken {self.conn.password}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add any additional headers from config
        self.headers.update(self.api_config.get('headers', {}))
    
    def build_url(self, endpoint: str) -> str:
        """Build API URL for the given endpoint"""
        if not endpoint:
            endpoint = self.api_config.get(f'{self.entity_type}_endpoint')
        if not endpoint:
            raise ValueError(f"No endpoint configured for entity type: {self.entity_type}")
        
        return f"{self.conn.host}{endpoint}"
    
    def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single record
        
        Args:
            record: The record to process
            
        Returns:
            Dict[str, Any]: Result of processing the record
        """
        try:
            url = self.build_url(self.api_config.get(f'{self.entity_type}_endpoint'))
            
            response = self.session.post(
                url,
                json=record,
                headers=self.headers
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "status": "success",
                "id": record.get('id'),
                "response": result
            }
            
        except Exception as e:
            self.logger.error(f"Error processing record {record.get('id')}: {str(e)}")
            return {
                "status": "error",
                "id": record.get('id'),
                "error": str(e)
            }
    
    def validate_load(self, results: List[Dict[str, Any]]) -> bool:
        """Validate load results
        
        Args:
            results: Results from loading data
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        success_count = sum(1 for r in results if r.get('status') == 'success')
        total_count = len(results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        # Log the results
        self.logger.info(f"Load Results: {success_count}/{total_count} successful ({success_rate:.2%})")
        
        # Log any errors
        for result in results:
            if result.get('status') == 'error':
                self.logger.error(f"Error loading record {result.get('id')}: {result.get('error')}")
        
        # Consider the load successful if success rate is above 95%
        threshold = self.config.get('loader', {}).get('success_threshold', 0.95)
        return success_rate >= threshold
