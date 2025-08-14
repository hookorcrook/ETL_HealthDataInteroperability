from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests

class BaseLoader(ABC):
    """Base class for all data loaders"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timestamp = datetime.now().strftime("%Y%m%d")
        self.temp_path = config.get('temp_data', {}).get('base_path', './include/temp_data')
        self.batch_size = config.get('loader', {}).get('batch_size', 100)
        self.max_workers = config.get('loader', {}).get('max_workers', 5)
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()
        
        # Setup retry strategy
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        
        # Mount the retry adapter
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def get_input_path(self, prefix: str, suffix: str = 'transformed') -> str:
        """Get path for input data file"""
        return os.path.join(self.temp_path, f"{prefix}_{suffix}_{self.timestamp}.json")
    
    def load_data(self, input_path: str) -> Dict[str, Any]:
        """Load data from input file"""
        with open(input_path, 'r') as f:
            return json.load(f)
    
    def process_batch(self, batch: List[Any]) -> List[Dict[str, Any]]:
        """Process a batch of records
        
        Args:
            batch: List of records to process
            
        Returns:
            List[Dict[str, Any]]: List of results for each record
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.process_record, record) for record in batch]
            results = []
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing record: {str(e)}")
                    results.append({"status": "error", "error": str(e)})
            
        return results
    
    @abstractmethod
    def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single record
        
        Args:
            record: The record to process
            
        Returns:
            Dict[str, Any]: Result of processing the record
        """
        pass
    
    def validate_load(self, results: List[Dict[str, Any]]) -> bool:
        """Validate load results
        
        Args:
            results: Results from loading data
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        return all(result.get('status') == 'success' for result in results)
    
    def cleanup(self):
        """Cleanup any resources"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
