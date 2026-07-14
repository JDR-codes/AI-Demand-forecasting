# fastapi_app/services/connectors/api_connector.py
import requests
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def fetch_api(url: str, headers: Dict[str, str] = None, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Fetch data from an API endpoint.
    
    Args:
        url: The API endpoint URL
        headers: Optional headers for the request
        params: Optional query parameters
        
    Returns:
        List of dictionaries containing the response data
    """
    try:
        if headers is None:
            headers = {}
            
        # Add common headers
        headers.setdefault('Accept', 'application/json')
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # If the response is a dict, check for common data keys
            for key in ['data', 'results', 'items', 'records']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If no list found, return the dict as a single item list
            return [data]
        else:
            logger.warning(f"Unexpected response type: {type(data)}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching from API {url}: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Error parsing JSON from API {url}: {str(e)}")
        raise

def fetch_api_with_pagination(url: str, headers: Dict[str, str] = None, 
                               params: Dict[str, Any] = None, 
                               pagination_key: str = 'page') -> List[Dict[str, Any]]:
    """
    Fetch data from an API with pagination support.
    
    Args:
        url: The API endpoint URL
        headers: Optional headers
        params: Optional query parameters
        pagination_key: The parameter key for pagination
        
    Returns:
        Combined list of all paginated results
    """
    all_data = []
    page = 1
    
    while True:
        paginated_params = params.copy() if params else {}
        paginated_params[pagination_key] = page
        
        data = fetch_api(url, headers, paginated_params)
        
        if not data:
            break
            
        all_data.extend(data)
        
        # If the response has metadata, check if we've reached the last page
        # This is a simplified approach - actual implementation depends on API
        if len(data) < 100:  # Arbitrary threshold
            break
            
        page += 1
        
    return all_data