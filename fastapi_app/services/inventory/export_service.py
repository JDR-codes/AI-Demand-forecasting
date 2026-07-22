# fastapi_app/services/inventory/export_service.py
"""
Inventory Export Service - Exports inventory reports to various formats.
"""
from typing import Dict, Any, List, Optional
import io
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from fastapi.responses import StreamingResponse

from fastapi_app.models.inventory_model import (
    WarehouseInventory,
    InventorySKU,
    InventoryTransfer,
    ReorderPoint,
    SafetyStockCalculation,
    ExcessStock,
    SlowMovingInventory,
)
from fastapi_app.services.inventory.inventory_service import InventoryService


class InventoryExportService:
    """Service for exporting inventory data."""
    
    @staticmethod
    def export_inventory_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export comprehensive inventory report."""
        data = InventoryExportService._get_inventory_report_data(db)
        
        if format == "csv":
            return InventoryExportService._export_csv(data, "inventory_report")
        elif format == "excel":
            return InventoryExportService._export_excel(data, "inventory_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(data, "inventory_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_warehouse_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export warehouse report."""
        data = InventoryExportService._get_warehouse_report_data(db)
        
        if format == "csv":
            return InventoryExportService._export_csv(data, "warehouse_report")
        elif format == "excel":
            return InventoryExportService._export_excel(data, "warehouse_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(data, "warehouse_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_transfer_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export transfer report."""
        data = InventoryExportService._get_transfer_report_data(db)
        
        if format == "csv":
            return InventoryExportService._export_csv(data, "transfer_report")
        elif format == "excel":
            return InventoryExportService._export_excel(data, "transfer_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(data, "transfer_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_safety_stock_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export safety stock report."""
        data = InventoryService.get_safety_stock_report(db, 95)
        
        df = pd.DataFrame([{
            "SKU": d.sku,
            "Warehouse": d.warehouse,
            "Region": d.region,
            "Current Safety Stock": d.current_safety_stock,
            "Recommended Safety Stock": d.recommended_safety_stock,
            "Variance (%)": d.variance_percentage,
            "Lead Time (days)": d.lead_time_days,
            "Demand Std Dev": d.demand_std_dev,
            "Service Level": d.service_level,
            "Status": d.status,
        } for d in data.data])
        
        if format == "csv":
            return InventoryExportService._export_csv(df, "safety_stock_report")
        elif format == "excel":
            return InventoryExportService._export_excel(df, "safety_stock_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(df, "safety_stock_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_reorder_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export reorder report."""
        data = InventoryService.get_reorder_points_report(db)
        
        df = pd.DataFrame([{
            "SKU": d.sku,
            "Product": d.product_name or d.sku,
            "Warehouse": d.warehouse,
            "Current Stock": d.current_stock,
            "Reorder Point": d.reorder_point,
            "Safety Stock": d.safety_stock,
            "EOQ": d.economic_order_quantity,
            "Avg Daily Demand": d.avg_daily_demand,
            "Lead Time (days)": d.lead_time_days,
            "Days Until Stockout": d.days_until_stockout,
            "Status": d.reorder_status,
        } for d in data.data])
        
        if format == "csv":
            return InventoryExportService._export_csv(df, "reorder_report")
        elif format == "excel":
            return InventoryExportService._export_excel(df, "reorder_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(df, "reorder_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_excess_stock_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export excess stock report."""
        data = InventoryService.get_excess_stock_report(db)
        
        df = pd.DataFrame([{
            "SKU": e.sku,
            "Warehouse": e.warehouse,
            "Region": e.region,
            "Current Stock": e.current_stock,
            "Forecasted Demand (30 days)": e.forecasted_demand_30days,
            "Days Inventory On Hand": e.days_inventory_on_hand,
            "Excess Quantity": e.excess_quantity,
            "Carrying Cost (Yearly)": e.carrying_cost_per_unit_yearly,
            "Total Carrying Cost": e.total_carrying_cost,
            "Excess Level": e.excess_level,
            "Recommended Action": e.action_recommended,
            "Liquidation Value": e.estimated_liquidation_value,
            "Potential Savings": e.potential_savings,
            "Storage Risk Score": e.storage_risk_score,
        } for e in data.excess_items])
        
        if format == "csv":
            return InventoryExportService._export_csv(df, "excess_stock_report")
        elif format == "excel":
            return InventoryExportService._export_excel(df, "excess_stock_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(df, "excess_stock_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_slow_moving_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export slow moving inventory report."""
        items = InventoryService.get_slow_moving_items(db)
        
        df = pd.DataFrame([{
            "SKU": i.sku,
            "Product": i.product_name,
            "Warehouse": i.warehouse,
            "Region": i.region,
            "Current Stock": i.current_stock,
            "Turnover Ratio": i.turnover_ratio,
            "Days in Stock": i.days_in_stock,
            "Status": i.status,
            "Recommended Action": i.action,
            "Last Sale Date": i.last_sale_date,
        } for i in items])
        
        if format == "csv":
            return InventoryExportService._export_csv(df, "slow_moving_report")
        elif format == "excel":
            return InventoryExportService._export_excel(df, "slow_moving_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(df, "slow_moving_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # ============ Private Methods ============
    
    @staticmethod
    def _get_inventory_report_data(db: Session) -> pd.DataFrame:
        """Get inventory report data."""
        inventory = db.query(WarehouseInventory).options(
            joinedload(WarehouseInventory.inventory_sku)
        ).all()
        
        data = []
        for item in inventory:
            sku = item.inventory_sku
            data.append({
                "SKU": item.sku,
                "Product": sku.description if sku else item.sku,
                "Category": sku.category if sku else "Unknown",
                "Warehouse": item.warehouse,
                "Region": item.region,
                "Current Stock": item.current_stock,
                "Safety Stock": item.safety_stock or 0,
                "Reorder Point": item.reorder_point or 0,
                "Unit Cost": sku.unit_cost if sku else 0,
                "Inventory Value": item.inventory_value or 0,
                "Lead Time (days)": sku.lead_time_days if sku else 0,
                "Last Reorder Date": item.last_reorder_date,
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def _get_warehouse_report_data(db: Session) -> pd.DataFrame:
        """Get warehouse report data."""
        from sqlalchemy import func
        
        warehouses = db.query(
            WarehouseInventory.warehouse,
            WarehouseInventory.region,
            func.sum(WarehouseInventory.current_stock).label('total_units'),
            func.sum(WarehouseInventory.inventory_value).label('total_value'),
            func.count(WarehouseInventory.id).label('item_count'),
        ).group_by(WarehouseInventory.warehouse, WarehouseInventory.region).all()
        
        data = []
        for w in warehouses:
            data.append({
                "Warehouse": w.warehouse,
                "Region": w.region,
                "Total Units": w.total_units,
                "Inventory Value": w.total_value,
                "Item Count": w.item_count,
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def _get_transfer_report_data(db: Session) -> pd.DataFrame:
        """Get transfer report data."""
        transfers = db.query(InventoryTransfer).all()
        
        data = []
        for t in transfers:
            data.append({
                "Transfer Number": t.transfer_number,
                "SKU": t.sku,
                "From": t.from_warehouse,
                "To": t.to_warehouse,
                "Quantity": t.transfer_quantity,
                "Status": t.status,
                "Priority": t.priority,
                "Cost": t.transfer_cost,
                "Savings": t.potential_cost_savings,
                "ROI (%)": t.roi_percentage,
                "Created At": t.created_at,
                "Completed At": t.completed_at,
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def _export_csv(data: Any, filename: str) -> StreamingResponse:
        """Export data as CSV."""
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)
        
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    @staticmethod
    def _export_excel(data: Any, filename: str) -> StreamingResponse:
        """Export data as Excel."""
        if isinstance(data, pd.DataFrame):
            df = data
            dfs = {"Sheet1": df}
        else:
            dfs = data
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if isinstance(dfs, dict):
                for sheet_name, df in dfs.items():
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            else:
                dfs.to_excel(writer, sheet_name="Report", index=False)
            
            # Add summary sheet if it's a dict
            if isinstance(dfs, dict) and len(dfs) > 1:
                summary_data = {
                    "Report Type": filename.replace("_", " ").title(),
                    "Generated At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "Total Sheets": len(dfs),
                }
                pd.DataFrame([summary_data]).to_excel(writer, sheet_name="Summary", index=False)
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
    
    @staticmethod
    def _export_pdf(data: Any, filename: str) -> StreamingResponse:
        """Export data as PDF."""
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20
        )
        story.append(Paragraph(f"{filename.replace('_', ' ').title()}", title_style))
        story.append(Spacer(1, 12))
        
        # Generated info
        story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"Total Records: {len(df)}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Table
        if len(df) > 0:
            # Prepare table data
            headers = df.columns.tolist()
            table_data = [headers]
            
            # Limit rows for PDF (max 50 rows per page)
            max_rows = 50
            for _, row in df.head(max_rows).iterrows():
                table_data.append([str(v)[:50] for v in row.values])
            
            # Create table
            col_widths = [1.2*inch] * len(headers)
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            story.append(table)
            
            if len(df) > max_rows:
                story.append(Spacer(1, 12))
                story.append(Paragraph(f"Showing first {max_rows} of {len(df)} records", styles['Normal']))
        else:
            story.append(Paragraph("No data available", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )