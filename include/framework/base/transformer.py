from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pyspark.sql import SparkSession
import logging
from datetime import datetime
import os

class BaseTransformer(ABC):
    """Base class for all data transformers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timestamp = datetime.now().strftime("%Y%m%d")
        self.temp_path = config.get('temp_data', {}).get('base_path', './include/temp_data')
        self._spark = None
        
    @property
    def spark(self) -> SparkSession:
        """Get or create Spark session"""
        if self._spark is None:
            spark_config = self.config.get('spark', {})
            builder = (SparkSession.builder
                      .appName(spark_config.get('app_name', 'DataTransformer'))
                      .master(spark_config.get('master', 'local[*]')))
            
            # Add custom Spark configurations
            for key, value in spark_config.get('config', {}).items():
                builder = builder.config(key, value)
            
            self._spark = builder.getOrCreate()
            
        return self._spark
    
    def get_input_path(self, prefix: str, suffix: str = 'raw') -> str:
        """Get path for input data file"""
        return os.path.join(self.temp_path, f"{prefix}_{suffix}_{self.timestamp}.json")
    
    def get_output_path(self, prefix: str, suffix: str = 'transformed') -> str:
        """Get path for output data file"""
        os.makedirs(self.temp_path, exist_ok=True)
        return os.path.join(self.temp_path, f"{prefix}_{suffix}_{self.timestamp}.json")
    
    @abstractmethod
    def transform(self, input_path: str) -> str:
        """Transform data from input file
        
        Args:
            input_path: Path to input data file
            
        Returns:
            str: Path to the transformed data file
        """
        pass
    
    def validate_transformation(self, df: Any) -> bool:
        """Validate transformed data
        
        Args:
            df: The transformed data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        return True
    
    def cleanup(self):
        """Cleanup Spark session and any other resources"""
        if self._spark:
            self._spark.stop()
            self._spark = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
