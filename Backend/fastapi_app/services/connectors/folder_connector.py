# fastapi_app/services/connectors/folder_connector.py
import pandas as pd
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def fetch_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Read CSV file and return data as list of dictionaries.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries representing the CSV data
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
            
        if not file_path.lower().endswith('.csv'):
            raise ValueError(f"File must be a CSV: {file_path}")
            
        df = pd.read_csv(file_path)
        
        # Convert to list of dictionaries
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {str(e)}")
        raise

def fetch_all_csvs_in_folder(folder_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Read all CSV files in a folder.
    
    Args:
        folder_path: Path to the folder containing CSV files
        
    Returns:
        Dictionary mapping filename to data
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
        
    result = {}
    
    for file in os.listdir(folder_path):
        if file.lower().endswith('.csv'):
            file_path = os.path.join(folder_path, file)
            try:
                data = fetch_csv(file_path)
                result[file] = data
            except Exception as e:
                logger.error(f"Error reading {file}: {str(e)}")
                result[file] = []
                
    return result