#fastapi_app/services/data_integration/test_connection_service.py
"""
Test Connection Service - Tests connections to various data sources.
"""
import time
import requests
import os
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from fastapi_app.models.data_source_model import DataSource, DataSourceType
from fastapi_app.models.connection_history_model import ConnectionHistory
import logging

logger = logging.getLogger(__name__)


class TestConnectionService:
    """Service for testing data source connections."""
    
    @staticmethod
    def test_connection(ds: DataSource) -> Dict[str, Any]:
        """Test connection based on data source type."""
        start_time = time.time()
        
        try:
            if ds.type == DataSourceType.API:
                result = TestConnectionService._test_api(ds)
            elif ds.type == DataSourceType.DATABASE:
                result = TestConnectionService._test_database(ds)
            elif ds.type == DataSourceType.CLOUD_STORAGE:
                result = TestConnectionService._test_cloud_storage(ds)
            elif ds.type == DataSourceType.LOCAL_FOLDER:
                result = TestConnectionService._test_folder(ds)
            else:
                result = {"success": False, "message": f"Unsupported type: {ds.type}"}
        except Exception as e:
            logger.error(f"Connection test failed for {ds.id}: {str(e)}")
            result = {"success": False, "message": str(e)}
        
        response_time = time.time() - start_time
        result["response_time"] = round(response_time, 3)
        
        return result
    
    @staticmethod
    def test_connection_with_history(db: Session, ds: DataSource) -> Dict[str, Any]:
        """Test connection and record history."""
        started_at = datetime.utcnow()
        
        history = ConnectionHistory(
            datasource_id=ds.id,
            status="running",
            started_at=started_at
        )
        db.add(history)
        db.commit()
        
        try:
            result = TestConnectionService.test_connection(ds)
            
            history.status = "success" if result.get("success") else "failed"
            history.response_time = result.get("response_time")
            history.completed_at = datetime.utcnow()
            if not result.get("success"):
                history.error_message = result.get("message")
            
            db.commit()
            return result
        except Exception as e:
            history.status = "failed"
            history.error_message = str(e)
            history.completed_at = datetime.utcnow()
            db.commit()
            return {"success": False, "message": str(e), "response_time": 0}
    
    @staticmethod
    def _test_api(ds: DataSource) -> Dict[str, Any]:
        """Test API connection."""
        if not ds.base_url:
            return {"success": False, "message": "No base_url configured"}
        
        headers = {}
        if ds.api_key:
            headers['Authorization'] = f'Bearer {ds.api_key}'
        if ds.username and ds.password:
            import base64
            auth = base64.b64encode(f"{ds.username}:{ds.password}".encode()).decode()
            headers['Authorization'] = f'Basic {auth}'
        
        try:
            response = requests.get(ds.base_url, headers=headers, timeout=10)
            if response.status_code < 400:
                return {"success": True, "message": f"Connected (Status: {response.status_code})"}
            else:
                return {"success": False, "message": f"Error {response.status_code}: {response.text[:100]}"}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Connection timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "Connection refused"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _test_database(ds: DataSource) -> Dict[str, Any]:
        """Test database connection."""
        if not ds.connection_string:
            return {"success": False, "message": "No connection_string configured"}
        
        try:
            if "mysql" in ds.connection_string:
                return TestConnectionService._test_mysql(ds.connection_string)
            elif "postgres" in ds.connection_string or "postgresql" in ds.connection_string:
                return TestConnectionService._test_postgres(ds.connection_string)
            elif "sqlite" in ds.connection_string:
                return TestConnectionService._test_sqlite(ds.connection_string)
            else:
                return {"success": False, "message": "Unsupported database type"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _test_mysql(connection_string: str) -> Dict[str, Any]:
        """Test MySQL connection."""
        import re
        from urllib.parse import unquote
        pattern = r'mysql(?:\+pymysql)?://([^:]+):([^@]+)@([^:]+):?(\d+)?/(.+)'
        match = re.match(pattern, connection_string)
        if not match:
            return {"success": False, "message": "Invalid MySQL connection string"}
        
        username, password, host, port, database = match.groups()
        username = unquote(username)
        password = unquote(password)
        port = int(port) if port else 3306
        
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=host, port=port, user=username,
                password=password, database=database,
                connection_timeout=5
            )
            conn.close()
            return {"success": True, "message": f"Connected to MySQL database '{database}'"}
        except ImportError:
            return {"success": False, "message": "mysql-connector-python not installed"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _test_postgres(connection_string: str) -> Dict[str, Any]:
        """Test PostgreSQL connection."""
        try:
            # Clean connection string if it has driver prefix
            conn_str = connection_string
            if "postgresql+psycopg2://" in conn_str:
                conn_str = conn_str.replace("postgresql+psycopg2://", "postgresql://")
            elif "postgres+psycopg2://" in conn_str:
                conn_str = conn_str.replace("postgres+psycopg2://", "postgresql://")
                
            import psycopg2
            conn = psycopg2.connect(conn_str)
            conn.close()
            return {"success": True, "message": "Connected to PostgreSQL"}
        except ImportError:
            return {"success": False, "message": "psycopg2 not installed"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _test_sqlite(connection_string: str) -> Dict[str, Any]:
        """Test SQLite connection."""
        import sqlite3
        try:
            path = connection_string.replace("sqlite:///", "")
            conn = sqlite3.connect(path, timeout=5)
            conn.close()
            return {"success": True, "message": "Connected to SQLite"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _test_cloud_storage(ds: DataSource) -> Dict[str, Any]:
        """Test cloud storage (S3/MinIO) connection."""
        if ds.provider == "S3" or ds.provider == "MINIO":
            return TestConnectionService._test_s3(ds)
        return {"success": False, "message": f"Unsupported cloud provider: {ds.provider}"}
    
    @staticmethod
    def _test_s3(ds: DataSource) -> Dict[str, Any]:
        """Test S3/MinIO connection."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            endpoint_url = ds.base_url if ds.base_url else None
            s3 = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=ds.username,
                aws_secret_access_key=ds.password
            )
            if ds.bucket_name:
                s3.head_bucket(Bucket=ds.bucket_name)
                return {"success": True, "message": f"Connected to bucket '{ds.bucket_name}'"}
            else:
                s3.list_buckets()
                return {"success": True, "message": "Connected to S3"}
        except ImportError:
            return {"success": False, "message": "boto3 not installed"}
        except ClientError as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _test_folder(ds: DataSource) -> Dict[str, Any]:
        """Test folder/local connection."""
        if not ds.folder_path:
            return {"success": False, "message": "No folder_path configured"}
        
        if not os.path.exists(ds.folder_path):
            return {"success": False, "message": f"Path '{ds.folder_path}' does not exist"}
        
        if os.path.isdir(ds.folder_path):
            files = os.listdir(ds.folder_path)
            return {"success": True, "message": f"Connected to folder '{ds.folder_path}' ({len(files)} files)"}
        elif os.path.isfile(ds.folder_path):
            size = os.path.getsize(ds.folder_path)
            return {"success": True, "message": f"Connected to file '{ds.folder_path}' ({size} bytes)"}
        else:
            return {"success": False, "message": "Path exists but is not a file or directory"}