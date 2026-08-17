# fastapi_app/services/inventory/export_service.py
"""
Inventory Export Service - Exports inventory report.
"""
from typing import Any
import io
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from fastapi_app.services.inventory.dashboard_service import InventoryDashboardService


class InventoryExportService:
    """Service for exporting inventory data."""
    
    @staticmethod
    def export_inventory_report(db: Session, format: str = "csv") -> StreamingResponse:
        """Export comprehensive inventory report."""
        data = InventoryDashboardService.get_dashboard_data(db)
        
        # Prepare data for export
        export_data = {
            "Health Cards": pd.DataFrame([data["health_cards"]]),
            "Reorder Points": pd.DataFrame(data["reorder_points"]),
            "Excess Inventory": pd.DataFrame(data["excess_inventory"]),
            "Slow Moving": pd.DataFrame(data["slow_moving_items"]),
            "Warehouse Distribution": pd.DataFrame(data["warehouse_distribution"]),
            "Inventory Value Distribution": pd.DataFrame(data["inventory_value_distribution"]),
            "Warehouse Summary": pd.DataFrame(data["warehouse_summary"]),
            "Transfer Recommendations": pd.DataFrame(data["transfer_recommendations"]),
        }
        
        if format == "csv":
            return InventoryExportService._export_csv(export_data, "inventory_report")
        elif format == "excel":
            return InventoryExportService._export_excel(export_data, "inventory_report")
        elif format == "pdf":
            return InventoryExportService._export_pdf(export_data, "inventory_report")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def _export_csv(data: dict, filename: str) -> StreamingResponse:
        """Export data as CSV."""
        output = io.StringIO()
        
        for sheet_name, df in data.items():
            output.write(f"=== {sheet_name.upper()} ===\n")
            df.to_csv(output, index=False)
            output.write("\n\n")
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    @staticmethod
    def _export_excel(data: dict, filename: str) -> StreamingResponse:
        """Export data as Excel."""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Summary sheet
            summary_data = {
                "Generated At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "Report Type": filename.replace("_", " ").title(),
                "Total Sheets": len(data),
            }
            pd.DataFrame([summary_data]).to_excel(writer, sheet_name="Summary", index=False)
            
            # Data sheets
            for sheet_name, df in data.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
    
    @staticmethod
    def _export_pdf(data: dict, filename: str) -> StreamingResponse:
        """Export data as PDF."""
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
        
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
        story.append(Spacer(1, 12))
        
        # Each sheet as a table
        for sheet_name, df in data.items():
            story.append(PageBreak())
            story.append(Paragraph(sheet_name, styles['Heading2']))
            story.append(Spacer(1, 6))
            
            if len(df) > 0:
                headers = df.columns.tolist()
                table_data = [headers]
                
                max_rows = 30
                for _, row in df.head(max_rows).iterrows():
                    table_data.append([str(v)[:40] for v in row.values])
                
                col_widths = [1.0*inch] * len(headers)
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
                    story.append(Spacer(1, 6))
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