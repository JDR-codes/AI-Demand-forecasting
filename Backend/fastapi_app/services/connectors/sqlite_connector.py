# fastapi_app/services/connectors/sqlite_connector.py
from sqlalchemy import create_engine
import pandas as pd
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def fetch_sqlite_table(connection_string: str, table_name: str, limit: int = None) -> List[Dict[str, Any]]:
    """
    Fetch data from a SQLite table.
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
        logger.error(f"Error fetching from SQLite table {table_name}: {str(e)}")
        raise