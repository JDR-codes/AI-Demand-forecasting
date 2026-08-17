# fastapi_app/services/data_processing/input_loader_service.py
import pandas as pd
from typing import Optional
from fastapi_app.models.upload_model import Upload
from fastapi_app.models.data_source_model import DataSource


class ProcessingInputLoader:

    @staticmethod
    def load_upload(upload: Upload) -> pd.DataFrame:
        path = upload.file_path
        filename = upload.filename.lower()

        if filename.endswith(".csv"):
            return pd.read_csv(path)

        if filename.endswith((".xlsx", ".xls")):
            return pd.read_excel(path)

        if filename.endswith(".json"):
            return pd.read_json(path)

        raise ValueError(f"Unsupported file format: {upload.filename}")

    @staticmethod
    def load_data_source(source: DataSource) -> pd.DataFrame:
        from fastapi_app.services.data_integration.data_source_service import fetch_data_from_source
        
        data = fetch_data_from_source(source)
        if not data:
            # Return an empty DataFrame with expected categories columns if no data is found
            return pd.DataFrame()
            
        return pd.DataFrame(data)
