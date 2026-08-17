# fastapi_app/services/connectors/mysql_connector.py
from sqlalchemy import create_engine, text
import pandas as pd
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def fetch_mysql_table(connection_string: str, table_name: str, limit: int = None) -> List[Dict[str, Any]]:
    """
    Fetch data from a MySQL table.
    
    Args:
        connection_string: MySQL connection string
        table_name: Name of the table to query
        limit: Optional limit on number of rows
        
    Returns:
        List of dictionaries representing the table data
    """
    try:
        engine = create_engine(connection_string)
        
        query = f"SELECT * FROM {table_name}"
        if limit:
            query = f"{query} LIMIT {limit}"
            
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
            
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Error fetching from MySQL table {table_name}: {str(e)}")
        raise

def fetch_mysql_custom_query(connection_string: str, query: str) -> List[Dict[str, Any]]:
    """
    Execute a custom MySQL query.
    
    Args:
        connection_string: MySQL connection string
        query: SQL query to execute
        
    Returns:
        List of dictionaries representing the query results
    """
    try:
        engine = create_engine(connection_string)
        
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
            
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Error executing MySQL query: {str(e)}")
        raise