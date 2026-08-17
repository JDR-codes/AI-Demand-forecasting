# fastapi_app/schemas/data_source_schema.py
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime, date, time
from typing import Optional, List, Union, Literal
from enum import Enum


class DataSourceType(str, Enum):
    API = "API"
    DATABASE = "DATABASE"
    CLOUD_STORAGE = "CLOUD_STORAGE"
    LOCAL_FOLDER = "LOCAL_FOLDER"


class DataSourceProvider(str, Enum):
    # PURELY CONNECTION/PROVIDER TYPES
    SAP = "SAP"
    MYSQL = "MYSQL"
    POSTGRES = "POSTGRES"
    SQLITE = "SQLITE"
    S3 = "S3"
    MINIO = "MINIO"
    CUSTOM = "CUSTOM"


class DataCategory(str, Enum):
    SALES = "sales"
    INVENTORY = "inventory"
    SUPPLIER = "supplier"
    PRODUCTS = "products"


class DataSourceBase(BaseModel):
    name: str
    type: DataSourceType
    provider: Optional[DataSourceProvider] = None
    created_by: Optional[int] = None
    data_category: DataCategory = DataCategory.SALES
    base_url: Optional[str] = None
    connection_string: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    bucket_name: Optional[str] = None
    folder_path: Optional[str] = None
    table_name: Optional[str] = None
    sync_frequency: Optional[str] = "manual"
    is_enabled: Optional[bool] = True


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceLookup(BaseModel):
    id: int
    name: str
    type: DataSourceType
    data_category: DataCategory
    is_enabled: bool

    class Config:
        from_attributes = True


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[DataSourceType] = None
    provider: Optional[DataSourceProvider] = None
    data_category: Optional[DataCategory] = None
    base_url: Optional[str] = None
    connection_string: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    bucket_name: Optional[str] = None
    folder_path: Optional[str] = None
    table_name: Optional[str] = None
    status: Optional[str] = None
    health: Optional[str] = None
    sync_frequency: Optional[str] = None
    is_enabled: Optional[bool] = None


class DataSourceOut(DataSourceBase):
    id: int
    status: str
    health: str
    is_enabled: bool
    last_sync: Optional[datetime]
    created_at: datetime
    record_count: Optional[int] = 0
    health_score: Optional[float] = 100.0
    last_sync_duration: Optional[float] = None
    next_sync: Optional[datetime] = None
    last_error: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# SCHEDULE SCHEMAS
# ============================================================================

class CustomScheduleRun(BaseModel):
    date: date
    time: time


class MonthlyScheduleRun(BaseModel):
    day: Union[int, Literal["last"]]
    time: time

    @field_validator("day")
    @classmethod
    def validate_day(cls, value):
        if value == "last":
            return value
        if not 1 <= value <= 31:
            raise ValueError(
                "Monthly day must be between 1 and 31 or 'last'"
            )
        return value


class SyncScheduleCreate(BaseModel):
    scope: Literal["all", "specific"]

    data_source_ids: Optional[List[int]] = None

    schedule_type: Literal["custom", "recurring"]

    timezone: str

    frequency: Optional[
        Literal["daily", "weekly", "monthly"]
    ] = None

    run_method: Optional[
        Literal["fixed_time", "interval"]
    ] = None

    custom_runs: Optional[List[CustomScheduleRun]] = None

    run_times: Optional[List[time]] = None

    weekdays: Optional[
        List[
            Literal[
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
                "sat",
                "sun",
            ]
        ]
    ] = None

    interval_value: Optional[int] = None
    interval_unit: Optional[
        Literal["minutes", "hours"]
    ] = None

    window_start_time: Optional[time] = None
    window_end_time: Optional[time] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    monthly_runs: Optional[List[MonthlyScheduleRun]] = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.scope == "specific" and not self.data_source_ids:
            raise ValueError(
                "At least one data source is required for 'specific' scope"
            )

        if self.schedule_type == "custom":
            if not self.custom_runs:
                raise ValueError(
                    "At least one custom date and time is required for 'custom' schedule"
                )

        if self.schedule_type == "recurring":
            if not self.frequency:
                raise ValueError("Frequency is required for 'recurring' schedule")

            if self.frequency in ("daily", "weekly"):
                if not self.run_method:
                    raise ValueError("Run method is required for daily/weekly schedules")

                if self.run_method == "fixed_time":
                    if not self.run_times:
                        raise ValueError(
                            "At least one run time is required for fixed_time"
                        )

                if self.run_method == "interval":
                    if not self.interval_value or self.interval_value <= 0:
                        raise ValueError(
                            "Interval must be greater than zero"
                        )
                    if not self.interval_unit:
                        raise ValueError(
                            "Interval unit is required"
                        )
                    if not self.window_start_time:
                        raise ValueError(
                            "Window start time is required for interval"
                        )
                    if not self.window_end_time:
                        raise ValueError(
                            "Window end time is required for interval"
                        )
                    if self.window_end_time <= self.window_start_time:
                        raise ValueError(
                            "Window end must be after window start"
                        )

            if self.frequency == "weekly":
                if not self.weekdays:
                    raise ValueError(
                        "At least one weekday is required for weekly schedule"
                    )

            if self.frequency == "monthly":
                if not self.monthly_runs:
                    raise ValueError(
                        "At least one monthly run is required for monthly schedule"
                    )

        if (
            self.start_date
            and self.end_date
            and self.end_date < self.start_date
        ):
            raise ValueError(
                "End date cannot be before start date"
            )

        return self


class SyncScheduleUpdate(SyncScheduleCreate):
    pass


class SyncScheduleOut(SyncScheduleCreate):
    id: int
    is_active: bool  
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True     