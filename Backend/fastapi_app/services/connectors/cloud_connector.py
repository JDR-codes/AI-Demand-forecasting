# fastapi_app/services/connectors/cloud_connector.py
"""
Cloud storage connector for S3/MinIO.
"""
import io
import pandas as pd
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def fetch_s3_data(
    bucket_name: str,
    prefix: str = "",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    endpoint_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch data from S3/MinIO and return as list of dictionaries.

    Supports:
    - CSV files
    - Excel files
    - JSON files

    Args:
        bucket_name: S3 bucket name
        prefix: Optional folder prefix
        access_key: AWS access key
        secret_key: AWS secret key
        endpoint_url: Optional custom endpoint (for MinIO)

    Returns:
        List of dictionaries containing the data
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.error("boto3 not installed. Please install: pip install boto3")
        return []

    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # List objects in bucket
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        all_data = []

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                if key.endswith('/'):
                    continue

                # Determine file type
                file_type = key.split('.')[-1].lower()

                try:
                    # Read file from S3
                    response = s3.get_object(Bucket=bucket_name, Key=key)
                    content = response['Body'].read()

                    if file_type == 'csv':
                        df = pd.read_csv(io.BytesIO(content))
                    elif file_type in ['xlsx', 'xls']:
                        df = pd.read_excel(io.BytesIO(content))
                    elif file_type == 'json':
                        df = pd.read_json(io.BytesIO(content))
                    else:
                        logger.warning(f"Skipping unsupported file type: {key}")
                        continue

                    # Convert to dict and add source info
                    records = df.to_dict('records')
                    for record in records:
                        record['_source_file'] = key
                        record['_source_bucket'] = bucket_name

                    all_data.extend(records)
                    logger.info(f"Loaded {len(records)} records from s3://{bucket_name}/{key}")

                except Exception as e:
                    logger.error(f"Error reading s3://{bucket_name}/{key}: {str(e)}")
                    continue

        logger.info(f"Total records loaded from S3: {len(all_data)}")
        return all_data

    except ClientError as e:
        logger.error(f"AWS/S3 error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching from S3: {str(e)}")
        return []