# fastapi_app/models/connection_history_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class ConnectionHistory(Base):
    """History of connection tests."""
    __tablename__ = "connection_history"
    
    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    status = Column(String(50), nullable=False)  # success, failed, running
    response_time = Column(Float, nullable=True)  # seconds
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    datasource = relationship("DataSource", back_populates="connection_history")
    
    __table_args__ = (
        Index('idx_connection_history_datasource', 'datasource_id'),
        Index('idx_connection_history_status', 'status'),
        Index('idx_connection_history_started_at', 'started_at'),
    )
    
    def __repr__(self):
        return f"<ConnectionHistory(id={self.id}, datasource_id={self.datasource_id}, status={self.status})>"