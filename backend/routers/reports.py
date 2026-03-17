"""
PatientPath AI - Management Reports Router
==========================================
PDF report generation for hospital management summaries.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from services.patient_service import PatientService
from services.zone_service import ZoneService
from services.analytics_service import AnalyticsService
from auth import require_role
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


def _escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(title: str, sections: list) -> io.BytesIO:
    """
    Build a professional A4 PDF from a list of sections.
    Each section is a dict: {"heading": str, "rows": [str, ...]}
    No external libraries required.
    """
    page_w, page_h = 595.28, 841.89
    parts = []

    # --- Header background ---
    parts.append("0.055 0.290 0.482 rg")
    parts.append(f"0 {page_h - 80:.2f} {page_w:.2f} 80 re f")

    # Header title
    parts.append("1 1 1 rg")
    parts.append("BT /F2 18 Tf")
    parts.append(f"{page_w / 2 - 170:.2f} {page_h - 38:.2f} Td")
    parts.append(f"({_escape('PatientPath AI Eye Care Hospital')}) Tj ET")

    parts.append("BT /F1 10 Tf")
    parts.append(f"{page_w / 2 - 130:.2f} {page_h - 58:.2f} Td")
    parts.append(f"({_escape('Smart Healthcare  |  AI-Powered Patient Flow Management')}) Tj ET")

    # Accent line
    parts.append("0.055 0.647 0.910 RG 2 w")
    parts.append(f"30 {page_h - 90:.2f} m {page_w - 30:.2f} {page_h - 90:.2f} l S")

    y = page_h - 115

    # Report title + timestamp
    parts.append("0.102 0.102 0.180 rg BT /F2 14 Tf")
    parts.append(f"30 {y:.2f} Td ({_escape(title)}) Tj ET")
    y -= 18
    parts.append("0.392 0.455 0.545 rg BT /F1 9 Tf")
    parts.append(f"30 {y:.2f} Td ({_escape('Generated: ' + datetime.now().strftime('%d %B %Y  %H:%M'))}) Tj ET")
    y -= 6

    # Separator
    parts.append("0.796 0.835 0.878 RG 0.5 w")
    parts.append(f"30 {y:.2f} m {page_w - 30:.2f} {y:.2f} l S")
    y -= 20

    for section in sections:
        heading = section.get("heading", "")
        rows = section.get("rows", [])

        # Section heading bar
        parts.append("0.941 0.976 1.000 rg")
        parts.append(f"30 {y - 16:.2f} {page_w - 60:.2f} 20 re f")
        parts.append("0.055 0.290 0.482 rg BT /F2 11 Tf")
        parts.append(f"36 {y - 11:.2f} Td ({_escape(heading)}) Tj ET")
        y -= 28

        parts.append("0.102 0.102 0.180 rg")
        for row in rows:
            # Wrap at 95 chars
            words = str(row).split()
            lines, cur = [], ""
            for w in words:
                if cur and len(cur) + 1 + len(w) > 95:
                    lines.append(cur)
                    cur = w
                else:
                    cur = f"{cur} {w}".strip()
            if cur:
                lines.append(cur)

            for line in lines:
                parts.append(f"BT /F1 10 Tf {42:.2f} {y:.2f} Td ({_escape(line)}) Tj ET")
                y -= 14
                if y < 60:  # near bottom of page — stop adding content
                    break
            if y < 60:
                break
        y -= 10
        if y < 60:
            break

    # Footer
    parts.append("0.945 0.961 0.976 rg")
    parts.append(f"0 0 {page_w:.2f} 30 re f")
    parts.append("0.392 0.455 0.545 rg BT /F1 7 Tf")
    parts.append(f"{page_w / 2 - 170:.2f} 11 Td")
    parts.append("(This is a computer-generated management report from PatientPath AI Eye Care Hospital.) Tj ET")

    stream_content = "\n".join(parts)
    stream_bytes = stream_content.encode("latin-1")

    objects = []

    def add_obj(content):
        objects.append(content)
        return len(objects)

    add_obj("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
    add_obj("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj")
    add_obj(
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        f"/MediaBox [0 0 {page_w:.2f} {page_h:.2f}] "
        f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj"
    )
    add_obj(
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n"
        + stream_content
        + "\nendstream\nendobj"
    )
    add_obj(
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        "/Encoding /WinAnsiEncoding >>\nendobj"
    )
    add_obj(
        "6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        "/Encoding /WinAnsiEncoding >>\nendobj"
    )

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(buf.tell())
        buf.write(obj.encode("latin-1"))
        buf.write(b"\n")

    xref_offset = buf.tell()
    buf.write(b"xref\n")
    buf.write(f"0 {len(objects) + 1}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for off in offsets:
        buf.write(f"{off:010d} 00000 n \n".encode())

    buf.write(b"trailer\n")
    buf.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    buf.write(b"startxref\n")
    buf.write(f"{xref_offset}\n".encode())
    buf.write(b"%%EOF\n")
    buf.seek(0)
    return buf


@router.get(
    "/management-summary",
    summary="Management Summary Report",
    description="Download a PDF management summary with hospital load, zone occupancy, AI predictions, active alerts, and staff status.",
)
def management_summary_pdf(
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("admin", "staff")),
):
    """
    Generate and download a PDF management summary report.

    Returns:
        PDF file download
    """
    sections = []

    # --- Section 1: Hospital Load Overview ---
    try:
        active_count = PatientService.count_active(db)
        zone_svc = ZoneService(db)
        zones = zone_svc.get_all()
        total_cap = sum(z.capacity_limit for z in zones if z.capacity_limit)
        occupancy_pct = round(active_count / total_cap * 100, 1) if total_cap else 0

        sections.append({
            "heading": "Hospital Load Overview",
            "rows": [
                f"Report Date/Time     : {datetime.now().strftime('%d %B %Y, %H:%M')}",
                f"Active Patients      : {active_count}",
                f"Total Zone Capacity  : {total_cap}",
                f"Overall Occupancy    : {occupancy_pct}%",
            ],
        })
    except Exception as e:
        logger.warning("Hospital load section failed: %s", e)
        sections.append({"heading": "Hospital Load Overview", "rows": ["Data unavailable."]})

    # --- Section 2: Zone-by-Zone Occupancy ---
    try:
        zone_svc = ZoneService(db)
        zones = zone_svc.get_all()
        VALID = ["registration", "vision_lab", "dilation_hall", "diagnostics",
                 "consultation", "pharmacy", "billing_insurance"]
        zone_rows = []
        for z in zones:
            if z.zone_name not in VALID:
                continue
            cap = z.capacity_limit or 1
            pct = round(z.current_occupancy / cap * 100, 1)
            status = "OK" if pct < 80 else ("WARNING" if pct < 100 else "FULL")
            label = z.zone_name.replace("_", " ").title()
            zone_rows.append(
                f"{label:<30} Occupancy: {z.current_occupancy}/{cap}  ({pct}%)  [{status}]"
            )
        sections.append({"heading": "Zone-by-Zone Occupancy", "rows": zone_rows or ["No zone data available."]})
    except Exception as e:
        logger.warning("Zone occupancy section failed: %s", e)
        sections.append({"heading": "Zone-by-Zone Occupancy", "rows": ["Data unavailable."]})

    # --- Section 3: AI Predictions Summary ---
    try:
        from services.prediction_service import PredictionService
        pred_rows = []

        try:
            arr = PredictionService.predict_arrival_rate()
            pred_rows.append(
                f"Predicted Arrival Rate   : {arr.get('predicted_arrival_rate', 'N/A')} patients/hr"
                + (f"  (95% CI: {arr.get('lower_bound','?')} – {arr.get('upper_bound','?')})" if 'lower_bound' in arr else "")
            )
        except Exception:
            pred_rows.append("Predicted Arrival Rate   : Model unavailable")

        try:
            ext = PredictionService.predict_exit_rate()
            pred_rows.append(
                f"Predicted Exit Rate      : {ext.get('predicted_exit_rate', 'N/A')} patients/hr"
                + (f"  (95% CI: {ext.get('lower_bound','?')} – {ext.get('upper_bound','?')})" if 'lower_bound' in ext else "")
            )
        except Exception:
            pred_rows.append("Predicted Exit Rate      : Model unavailable")

        try:
            bn = PredictionService.predict_bottleneck()
            bottlenecks = [
                p["department"].replace("_", " ").title()
                for p in bn.get("predictions", [])
                if p.get("risk_level") == "HIGH"
            ]
            pred_rows.append(
                f"High-Risk Bottlenecks    : {', '.join(bottlenecks) if bottlenecks else 'None detected'}"
            )
        except Exception:
            pred_rows.append("Bottleneck Analysis      : Model unavailable")

        sections.append({"heading": "AI Predictions Summary", "rows": pred_rows})
    except Exception as e:
        logger.warning("Predictions section failed: %s", e)
        sections.append({"heading": "AI Predictions Summary", "rows": ["Prediction service unavailable."]})

    # --- Section 4: Active Alerts ---
    try:
        from models.alert import Alert
        from sqlalchemy import desc
        alerts = (
            db.query(Alert)
            .filter(Alert.resolved == False)
            .order_by(desc(Alert.created_at))
            .limit(10)
            .all()
        )
        if alerts:
            alert_rows = []
            for a in alerts:
                ts = a.created_at.strftime("%d %b %H:%M") if a.created_at else "N/A"
                zone = (a.zone_name or "").replace("_", " ").title()
                alert_rows.append(f"[{a.severity.upper() if a.severity else 'INFO'}]  {zone:<25}  {a.message or ''}  ({ts})")
        else:
            alert_rows = ["No active alerts."]
        sections.append({"heading": "Active Alerts (Top 10)", "rows": alert_rows})
    except Exception as e:
        logger.warning("Alerts section failed: %s", e)
        sections.append({"heading": "Active Alerts", "rows": ["Alert data unavailable."]})

    # --- Section 5: Staff Allocation Status ---
    try:
        from services.staff_allocation_service import StaffAllocationService
        staff_svc = StaffAllocationService(db)
        staff_rows = []
        DEPTS = ["registration", "vision_lab", "dilation_hall", "diagnostics",
                 "consultation", "pharmacy", "billing_insurance"]
        for dept in DEPTS:
            count = StaffAllocationService.get_current_staff().get(dept, 0)
            label = dept.replace("_", " ").title()
            staff_rows.append(f"{label:<30} Staff on duty: {count}")
        sections.append({"heading": "Staff Allocation Status", "rows": staff_rows})
    except Exception as e:
        logger.warning("Staff section failed: %s", e)
        sections.append({"heading": "Staff Allocation Status", "rows": ["Staff data unavailable."]})

    pdf_buf = _build_pdf("Management Summary Report", sections)
    filename = f"management_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
