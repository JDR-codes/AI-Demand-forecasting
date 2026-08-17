#fastapi_app/models/recommendation_history_model.py
"""
Recommendation History Model - Tracks execution history.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from fastapi_app.db.session import Base
from sqlalchemy.orm import relationship


class RecommendationHistory(Base):
    """History of recommendation actions."""
    __tablename__ = "recommendation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendation_results.id", ondelete="CASCADE"), nullable=False)
    
    # Action types
    action = Column(String(50), nullable=False)  # generated, executed, ignored, deleted
    
    # Status before/after
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    
    # User
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Details
    reason = Column(Text, nullable=True)
    
    # Timestamp
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    recommendation = relationship("RecommendationResult", foreign_keys=[recommendation_id])
    performer = relationship("User", foreign_keys=[performed_by])
    
    __table_args__ = (
        Index('idx_rec_history_recommendation_id', 'recommendation_id'),
        Index('idx_rec_history_action', 'action'),
        Index('idx_rec_history_performed_at', 'performed_at'),
        Index('idx_rec_history_performed_by', 'performed_by'),
    )
    
    def __repr__(self):
        return f"<RecommendationHistory(id={self.id}, recommendation_id={self.recommendation_id}, action={self.action})>"