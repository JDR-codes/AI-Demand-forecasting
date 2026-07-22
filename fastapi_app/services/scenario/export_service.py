# fastapi_app/services/scenario/export_service.py
"""
Export Service - Handles exporting scenario data to various formats.
"""
from typing import Dict, Any, Optional
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
        data = ScenarioService.export_scenario(db, scenario_id, "csv")
        if "error" in data:
            raise ValueError(data["error"])
        
        output = io.StringIO()
        
        # Write metrics
        output.write("=== METRICS ===\n")
        pd.DataFrame([data["metrics"]]).to_csv(output, index=False)
        output.write("\n\n")
        
        # Write forecast
        output.write("=== FORECAST ===\n")
        forecast_df = pd.DataFrame({
            "label": data["forecast"]["labels"],
            "baseline": data["forecast"]["baseline"],
            "simulation": data["forecast"]["simulation"],
            "difference": data["forecast"]["difference"] if data["forecast"].get("difference") else []
        })
        forecast_df.to_csv(output, index=False)
        output.write("\n\n")
        
        # Write inventory
        output.write("=== INVENTORY ===\n")
        inventory_df = pd.DataFrame({
            "label": data["inventory"]["labels"],
            "baseline": data["inventory"]["baseline"],
            "simulation": data["inventory"]["simulation"]
        })
        inventory_df.to_csv(output, index=False)
        output.write("\n\n")
        
        # Write parameters
        output.write("=== PARAMETERS ===\n")
        pd.DataFrame([data["scenario"]["parameters"]]).to_csv(output, index=False)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.csv"}
        )
    
    @staticmethod
    def export_excel(db: Session, scenario_id: int) -> StreamingResponse:
        """Export scenario to Excel."""
        data = ScenarioService.export_scenario(db, scenario_id, "excel")
        if "error" in data:
            raise ValueError(data["error"])
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Summary sheet
            summary_data = {
                "Scenario Name": [data["scenario"]["name"]],
                "Description": [data["scenario"]["description"] or ""],
                "Created At": [data["scenario"].get("created_at")],
                "Status": [data["scenario"].get("status", "completed")]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
            
            # Metrics sheet
            pd.DataFrame([data["metrics"]]).to_excel(writer, sheet_name="Metrics", index=False)
            
            # Parameters sheet
            pd.DataFrame([data["scenario"]["parameters"]]).to_excel(writer, sheet_name="Parameters", index=False)
            
            # Forecast sheet
            forecast_df = pd.DataFrame({
                "Date": data["forecast"]["labels"],
                "Baseline Demand": data["forecast"]["baseline"],
                "Simulated Demand": data["forecast"]["simulation"],
                "Difference": data["forecast"]["difference"] if data["forecast"].get("difference") else []
            })
            forecast_df.to_excel(writer, sheet_name="Forecast", index=False)
            
            # Inventory sheet
            inventory_df = pd.DataFrame({
                "Date": data["inventory"]["labels"],
                "Baseline Inventory": data["inventory"]["baseline"],
                "Simulated Inventory": data["inventory"]["simulation"]
            })
            inventory_df.to_excel(writer, sheet_name="Inventory", index=False)
            
            # Recommendations sheet
            if data.get("recommendations"):
                pd.DataFrame(data["recommendations"]).to_excel(writer, sheet_name="Recommendations", index=False)
            
            # Stockout SKUs sheet
            if data.get("stockout_skus"):
                pd.DataFrame(data["stockout_skus"]).to_excel(writer, sheet_name="Stockout Risk", index=False)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.xlsx"}
        )
    
    @staticmethod
    def export_pdf(db: Session, scenario_id: int) -> StreamingResponse:
        """Export scenario to PDF."""
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.lineplots import LinePlot
        from reportlab.graphics.charts.legends import Legend
        import io
        
        data = ScenarioService.export_scenario(db, scenario_id, "pdf")
        if "error" in data:
            raise ValueError(data["error"])
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30
        )
        story.append(Paragraph(f"Scenario Report: {data['scenario']['name']}", title_style))
        story.append(Spacer(1, 12))
        
        # Description
        if data['scenario'].get('description'):
            story.append(Paragraph(data['scenario']['description'], styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Parameters
        story.append(Paragraph("Parameters", styles['Heading2']))
        param_data = [["Parameter", "Value"]]
        for k, v in data['scenario']['parameters'].items():
            param_data.append([k.replace('_', ' ').title(), str(v)])
        param_table = Table(param_data, colWidths=[2*inch, 2*inch])
        param_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(param_table)
        story.append(Spacer(1, 12))
        
        # Metrics
        story.append(Paragraph("Key Metrics", styles['Heading2']))
        metric_data = [["Metric", "Value"]]
        for k, v in data['metrics'].items():
            metric_data.append([k.replace('_', ' ').title(), f"{v:.2f}%" if isinstance(v, float) else str(v)])
        metric_table = Table(metric_data, colWidths=[2*inch, 2*inch])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metric_table)
        story.append(PageBreak())
        
        # Forecast Chart (text representation)
        story.append(Paragraph("Forecast Data", styles['Heading2']))
        forecast_data = [["Date", "Baseline", "Simulation", "Difference"]]
        for i, label in enumerate(data['forecast']['labels'][:20]):  # Limit to 20 rows
            row = [
                label,
                f"{data['forecast']['baseline'][i]:.2f}" if i < len(data['forecast']['baseline']) else "",
                f"{data['forecast']['simulation'][i]:.2f}" if i < len(data['forecast']['simulation']) else "",
                f"{data['forecast']['difference'][i]:.2f}" if data['forecast'].get('difference') and i < len(data['forecast']['difference']) else ""
            ]
            forecast_data.append(row)
        
        forecast_table = Table(forecast_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
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
        story.append(Spacer(1, 12))
        
        # Inventory Data
        story.append(Paragraph("Inventory Data", styles['Heading2']))
        inventory_data = [["Date", "Baseline", "Simulation"]]
        for i, label in enumerate(data['inventory']['labels'][:20]):
            row = [
                label,
                f"{data['inventory']['baseline'][i]:.2f}" if i < len(data['inventory']['baseline']) else "",
                f"{data['inventory']['simulation'][i]:.2f}" if i < len(data['inventory']['simulation']) else ""
            ]
            inventory_data.append(row)
        
        inventory_table = Table(inventory_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        inventory_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(inventory_table)
        
        # Recommendations
        if data.get('recommendations'):
            story.append(PageBreak())
            story.append(Paragraph("Recommendations", styles['Heading2']))
            rec_data = [["SKU", "Type", "Priority", "Action", "Quantity"]]
            for rec in data['recommendations'][:10]:
                rec_data.append([
                    rec.get('sku', ''),
                    rec.get('recommendation_type', ''),
                    rec.get('priority', ''),
                    rec.get('suggested_action', '')[:50] + "...",
                    str(rec.get('quantity', 0))
                ])
            rec_table = Table(rec_data, colWidths=[1*inch, 1*inch, 1*inch, 2*inch, 1*inch])
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(rec_table)
        
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.pdf"}
        )