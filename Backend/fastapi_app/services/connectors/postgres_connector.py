# fastapi_app/services/connectors/postgres_connector.py
"""
PostgreSQL connector for fetching data.
"""
import pandas as pd
from sqlalchemy import create_engine, text
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def fetch_postgres_table(
    connection_string: str,
    table_name: str,
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch data from a PostgreSQL table and return as list of dictionaries.

    Args:
        connection_string: PostgreSQL connection string
        table_name: Name of the table to query
        query: Optional custom SQL query (overrides table_name)

    Returns:
        List of dictionaries containing the data
    """
    engine = None
    try:
        engine = create_engine(connection_string)

        if query:
            df = pd.read_sql_query(query, engine)
        else:
            df = pd.read_sql_table(table_name, engine)

        # Convert to dict records
        records = df.to_dict('records')

        logger.info(f"Fetched {len(records)} records from PostgreSQL table '{table_name}'")
        return records

    except Exception as e:
        logger.error(f"Error fetching from PostgreSQL: {str(e)}")
        raise

    finally:
        if engine:
            engine.dispose()