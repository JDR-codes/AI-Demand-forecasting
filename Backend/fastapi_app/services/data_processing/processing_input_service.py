# fastapi_app/services/data_processing/processing_input_service.py
from typing import List
from sqlalchemy.orm import Session
from fastapi_app.models.data_source_model import DataSource
from fastapi_app.models.upload_model import Upload


class ProcessingInputService:

    @staticmethod
    def get_data_sources(
        db: Session,
        data_source_ids: List[int],
        category_mode: str,
        categories: List[str],
        current_user_id: int = None
    ) -> List[DataSource]:
        if not data_source_ids:
            return []
        query = db.query(DataSource).filter(
            DataSource.id.in_(data_source_ids)
        )
        if current_user_id is not None:
            query = query.filter(DataSource.created_by == current_user_id)
        if category_mode == "selected" and categories:
            query = query.filter(
                DataSource.data_category.in_(categories)
            )
        return query.all()

    @staticmethod
    def get_uploads(
        db: Session,
        upload_ids: List[int],
        category_mode: str,
        categories: List[str],
        current_user_id: int = None
    ) -> List[Upload]:
        if not upload_ids:
            return []
        query = db.query(Upload).filter(
            Upload.id.in_(upload_ids)
        )
        if current_user_id is not None:
            query = query.filter(Upload.uploaded_by == current_user_id)
        if category_mode == "selected" and categories:
            query = query.filter(
                Upload.data_category.in_(categories)
            )
        return query.all()


    @staticmethod
    def validate_ids(
        data_sources: List[DataSource],
        uploads: List[Upload],
        requested_source_ids: List[int],
        requested_upload_ids: List[int]
    ) -> None:
        found_sources = {source.id for source in data_sources}
        found_uploads = {upload.id for upload in uploads}

        missing_sources = set(requested_source_ids) - found_sources
        missing_uploads = set(requested_upload_ids) - found_uploads

        if missing_sources:
            raise ValueError(f"Invalid or category-mismatched data source IDs: {list(missing_sources)}")
        if missing_uploads:
            raise ValueError(f"Invalid or category-mismatched upload IDs: {list(missing_uploads)}")
