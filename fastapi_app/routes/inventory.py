from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user, get_db
from fastapi_app.models.auth_model import User
from fastapi_app.services.inventory.inventory_service import InventoryService
from fastapi_app.schemas.inventory_schema import (
    InventoryHealthResponse,
    SafetyStockResponse,
    ReorderPointResponse,
    TransferOptimizationResponse,
    ExcessStockResponse,
)


router = APIRouter(prefix="/api/inventory", tags=["Inventory Optimization"])

@router.post("/seed-sample-data")
def seed_sample_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seed database with sample inventory data for testing and demonstration.
    
    This endpoint creates:
    - 3 sample SKUs with different product categories
    - 9 warehouse inventory records across 3 warehouses and 2 regions
    
    Use this to populate sample data for testing the inventory optimization endpoints.
    """
    try:
        InventoryService.seed_sample_inventory(db)
        return {
            "message": "Sample inventory data seeded successfully",
            "skus_created": 3,
            "warehouse_records_created": 9,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding data: {str(e)}")

@router.get("/health", response_model=InventoryHealthResponse)
def get_inventory_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get overall inventory health dashboard.
    
    Returns:
    - health_score: 0-100 score of overall inventory health
    - status: healthy, at_risk, or critical
    - total_skus: Total number of SKUs in inventory
    - at_risk_skus: Number of SKUs with inventory imbalance
    - critical_skus: Number of SKUs at critical risk
    - metrics: Detailed health metrics
    """
    try:
        health_report = InventoryService.get_inventory_health(db)
        return health_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving inventory health: {str(e)}")


@router.get("/safety-stock", response_model=SafetyStockResponse)
def get_safety_stock(
    service_level: float = 95,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get safety stock recommendations for all SKUs.
    
    Parameters:
    - service_level: Service level percentage (90, 95, 97, 99, 99.9). Default: 95
    
    Returns:
    - data: List of safety stock details per warehouse
    - summary: Overall summary metrics
    
    Functionality:
    - Calculates safety stock based on demand volatility and lead time
    - Compares current vs recommended levels
    - Identifies under/over stock situations
    """
    try:
        if service_level not in [90, 95, 97, 99, 99.9]:
            raise HTTPException(
                status_code=400,
                detail="Service level must be one of: 90, 95, 97, 99, 99.9",
            )
        
        safety_stock_report = InventoryService.get_safety_stock_report(db, service_level)
        return safety_stock_report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving safety stock: {str(e)}")


@router.get("/reorder-points", response_model=ReorderPointResponse)
def get_reorder_points(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get reorder point recommendations for all SKUs.
    
    Returns:
    - data: List of reorder point details per warehouse
    - total_urgent_reorders: Count of SKUs needing immediate reorder
    - total_planned_reorders: Count of SKUs needing planned reorder
    
    Functionality:
    - Calculates reorder points based on demand and lead time
    - Determines optimal order quantities (EOQ)
    - Identifies urgent reorder needs
    - Forecasts stockout risks
    """
    try:
        reorder_report = InventoryService.get_reorder_points_report(db)
        return reorder_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reorder points: {str(e)}")


@router.get("/transfers", response_model=TransferOptimizationResponse)
def get_transfer_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get optimal inventory transfer recommendations between warehouses.
    
    Returns:
    - transfers: List of recommended transfers with ROI analysis
    - total_transfers_recommended: Total number of recommended transfers
    - total_potential_savings: Total cost savings from transfers
    
    Functionality:
    - Identifies excess and shortage across warehouses
    - Calculates transfer costs based on distance
    - Determines cost savings and ROI
    - Recommends transfer timing and quantities
    - Optimizes network-wide inventory balance
    """
    try:
        transfer_report = InventoryService.get_transfer_recommendations(db)
        return transfer_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving transfer recommendations: {str(e)}")


@router.get("/excess-stock", response_model=ExcessStockResponse)
def get_excess_stock(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get excess and slow-moving inventory analysis.
    
    Returns:
    - excess_items: List of items with excess inventory
    - total_excess_quantity: Total excess units across all warehouses
    - total_carrying_cost: Total annual carrying costs for excess stock
    - total_potential_savings: Total savings from liquidating excess
    
    Functionality:
    - Identifies overstocked items
    - Calculates days inventory on hand (DIOH)
    - Determines excess levels (critical, high, medium, low)
    - Recommends actions: discount, transfer, clearance, or donation
    - Calculates carrying costs and storage risk scores
    - Estimates liquidation values
    """
    try:
        excess_report = InventoryService.get_excess_stock_report(db)
        return excess_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving excess stock: {str(e)}")



