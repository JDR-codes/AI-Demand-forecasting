# fastapi_app/services/inventory/dashboard_cache_service.py
"""
Dashboard Cache Service - Caches inventory dashboard data.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from fastapi_app.services.inventory.dashboard_service import InventoryDashboardService

logger = logging.getLogger(__name__)


class DashboardCacheService:
    """Service for caching inventory dashboard data."""
    
    _cache: Optional[Dict[str, Any]] = None
    _cache_time: Optional[datetime] = None
    _cache_ttl_minutes: int = 15
    
    @classmethod
    def get_dashboard_data(cls, db) -> Dict[str, Any]:
        """
        Get dashboard data from cache or generate fresh.
        """
        # Check if cache is valid
        if cls._cache and cls._cache_time:
            age = datetime.utcnow() - cls._cache_time
            if age.total_seconds() < cls._cache_ttl_minutes * 60:
                logger.info("Returning cached dashboard data")
                return cls._cache
        
        # Generate fresh data
        logger.info("Generating fresh dashboard data")
        try:
            data = InventoryDashboardService.get_dashboard_data(db)
            cls._cache = data
            cls._cache_time = datetime.utcnow()
            return data
        except Exception as e:
            logger.error(f"Failed to generate dashboard data: {str(e)}")
            if cls._cache:
                logger.warning("Returning stale cache due to error")
                return cls._cache
            raise
    
    @classmethod
    def invalidate_cache(cls):
        """Invalidate the dashboard cache."""
        cls._cache = None
        cls._cache_time = None
        logger.info("Dashboard cache invalidated")
    
    @classmethod
    def set_ttl(cls, minutes: int):
        """Set cache TTL in minutes."""
        cls._cache_ttl_minutes = minutes
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        """Get cache information."""
        return {
            "cached": cls._cache is not None,
            "cache_time": cls._cache_time.isoformat() if cls._cache_time else None,
            "cache_age_seconds": (datetime.utcnow() - cls._cache_time).total_seconds() if cls._cache_time else None,
            "ttl_minutes": cls._cache_ttl_minutes,
            "is_valid": cls._cache is not None and cls._cache_time and (datetime.utcnow() - cls._cache_time).total_seconds() < cls._cache_ttl_minutes * 60
        }