# fastapi_app/services/scenario/export_service.py
"""
Export Service - Exports scenario data to CSV, Excel, and PDF.
"""
from typing import Dict, Any
import io
import pandas as pd
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from fastapi_app.services.scenario.scenario_service import ScenarioService


class ExportService:
    """Service for exporting scenario data."""
    
    @staticmethod
    def export_csv(db: Session, scenario_id: int) -> StreamingResponse:
        """Export scenario to CSV."""
        data = ScenarioService.get_dashboard(db, scenario_id)
        if not data:
            raise ValueError("Scenario not found or no results")
        
        output = io.StringIO()
        
        # Metrics
        output.write("=== METRICS ===\n")
        summary = data.get("summary_cards", {})
        pd.DataFrame([summary]).to_csv(output, index=False)
        output.write("\n\n")
        
        # Forecast
        output.write("=== FORECAST ===\n")
        forecast = data.get("forecast", {})
        forecast_df = pd.DataFrame({
            "Date": forecast.get("labels", []),
            "Baseline": forecast.get("baseline", []),
            "Simulation": forecast.get("simulation", [])
        })
        forecast_df.to_csv(output, index=False)
        output.write("\n\n")
        
        # Inventory
        output.write("=== INVENTORY ===\n")
        inventory = data.get("inventory", {})
        inventory_df = pd.DataFrame({
            "Date": inventory.get("labels", []),
            "Baseline": inventory.get("baseline", []),
            "Simulation": inventory.get("simulation", [])
        })
        inventory_df.to_csv(output, index=False)
        output.write("\n\n")
        
        # Stockouts
        stockouts = data.get("stockouts", [])
        if stockouts:
            output.write("=== STOCKOUT RISK ===\n")
            pd.DataFrame(stockouts).to_csv(output, index=False)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.csv"}
        )
    
    @staticmethod
    def export_excel(db: Session, scenario_id: int) -> StreamingResponse:
        """Export scenario to Excel."""
        data = ScenarioService.get_dashboard(db, scenario_id)
        if not data:
            raise ValueError("Scenario not found or no results")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Metrics
            summary = data.get("summary_cards", {})
            pd.DataFrame([summary]).to_excel(writer, sheet_name="Metrics", index=False)
            
            # Forecast
            forecast = data.get("forecast", {})
            forecast_df = pd.DataFrame({
                "Date": forecast.get("labels", []),
                "Baseline": forecast.get("baseline", []),
                "Simulation": forecast.get("simulation", [])
            })
            forecast_df.to_excel(writer, sheet_name="Forecast", index=False)
            
            # Inventory
            inventory = data.get("inventory", {})
            inventory_df = pd.DataFrame({
                "Date": inventory.get("labels", []),
                "Baseline": inventory.get("baseline", []),
                "Simulation": inventory.get("simulation", [])
            })
            inventory_df.to_excel(writer, sheet_name="Inventory", index=False)
            
            # Stockouts
            stockouts = data.get("stockouts", [])
            if stockouts:
                pd.DataFrame(stockouts).to_excel(writer, sheet_name="Stockout Risk", index=False)
            
            # Recommendations
            recommendations = data.get("recommendations", [])
            if recommendations:
                pd.DataFrame([r.dict() for r in recommendations]).to_excel(writer, sheet_name="Recommendations", index=False)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.xlsx"}
        )
    
    @staticmethod
    def export_pdf(db: Session, scenario_id: int) -> StreamingResponse:
        """Export scenario to PDF."""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
        
        data = ScenarioService.get_dashboard(db, scenario_id)
        if not data:
            raise ValueError("Scenario not found or no results")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=24, spaceAfter=30)
        scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
        story.append(Paragraph(f"Scenario Report: {scenario.name if scenario else 'Unknown'}", title_style))
        story.append(Spacer(1, 12))
        
        # Metrics
        story.append(Paragraph("Key Metrics", styles['Heading2']))
        summary = data.get("summary_cards", {})
        metric_data = [["Metric", "Value"]]
        for k, v in summary.items():
            if v is not None:
                metric_data.append([k.replace('_', ' ').title(), f"{v:.2f}" if isinstance(v, float) else str(v)])
        
        metric_table = Table(metric_data, colWidths=[2*inch, 2*inch])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metric_table)
        story.append(PageBreak())
        
        # Forecast
        story.append(Paragraph("Forecast Data", styles['Heading2']))
        forecast = data.get("forecast", {})
        forecast_data = [["Date", "Baseline", "Simulation"]]
        labels = forecast.get("labels", [])[:20]
        baseline = forecast.get("baseline", [])[:20]
        simulation = forecast.get("simulation", [])[:20]
        
        for i in range(len(labels)):
            forecast_data.append([
                labels[i] if i < len(labels) else "",
                f"{baseline[i]:.2f}" if i < len(baseline) else "",
                f"{simulation[i]:.2f}" if i < len(simulation) else ""
            ])
        
        forecast_table = Table(forecast_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        forecast_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(forecast_table)
        
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.pdf"}
        )