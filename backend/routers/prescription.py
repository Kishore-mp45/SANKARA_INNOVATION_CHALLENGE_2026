"""
Prescription Router
===================
Endpoints for creating, listing, and downloading prescriptions as PDF.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models.prescription import Prescription
from services.activity_service import ActivityService
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import io

router = APIRouter(tags=["Prescription"])


class SavePrescriptionRequest(BaseModel):
    doctor_id: str = Field(..., max_length=100)
    patient_id: str = Field(..., max_length=100)
    diagnosis: str = Field(..., min_length=1)
    prescription: str = Field(..., min_length=1)
    next_visit: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("/doctor/save-prescription", summary="Save a prescription")
def save_prescription(body: SavePrescriptionRequest, db: Session = Depends(get_db)):
    # Always use server local time for consistent display
    ts = datetime.now()

    rx = Prescription(
        doctor_id=body.doctor_id,
        patient_id=body.patient_id,
        diagnosis=body.diagnosis,
        prescription=body.prescription,
        next_visit=body.next_visit,
        created_at=ts,
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)

    # Activity log
    ActivityService.add_log(
        action=f"Prescription created for Patient {body.patient_id}",
        details=f"Diagnosis: {body.diagnosis} — by Doctor {body.doctor_id}",
        severity="info",
        role="doctor",
        user_id=body.doctor_id,
    )

    return {
        "success": True,
        "message": "Prescription saved successfully",
        "prescription": rx.to_dict(),
    }


@router.get("/patient/prescriptions/{patient_id}", summary="Get prescriptions for a patient")
def get_patient_prescriptions(
    patient_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Prescription)
        .filter(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"prescriptions": [r.to_dict() for r in rows]}


@router.get("/prescription/download/{prescription_id}", summary="Download prescription as PDF")
def download_prescription_pdf(prescription_id: int, view: bool = False, db: Session = Depends(get_db)):
    rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    pdf_buffer = _generate_prescription_pdf(rx)

    disposition = "inline" if view else "attachment"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"{disposition}; filename=prescription_{rx.id}.pdf"
        },
    )


def _generate_prescription_pdf(rx: Prescription) -> io.BytesIO:
    """
    Generate a professional prescription PDF using raw PDF format.
    No external libraries required (no reportlab).
    """
    date_str = rx.created_at.strftime("%d %B %Y, %H:%M") if rx.created_at else "N/A"
    doctor_name = f"Dr. {rx.doctor_id}"
    patient_id = str(rx.patient_id)
    diagnosis = str(rx.diagnosis or "N/A")
    prescription = str(rx.prescription or "N/A")
    next_visit = str(rx.next_visit) if rx.next_visit else None

    # Wrap long text into lines (~80 chars per line)
    def wrap_text(text, max_chars=80):
        words = text.split()
        lines = []
        current = ""
        for w in words:
            if current and len(current) + 1 + len(w) > max_chars:
                lines.append(current)
                current = w
            else:
                current = f"{current} {w}".strip()
        if current:
            lines.append(current)
        return lines if lines else [""]

    def escape_pdf(text):
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Build the text stream content (PDF page content stream)
    # Page size: A4 = 595.28 x 841.89 points
    page_w, page_h = 595.28, 841.89

    stream_parts = []

    # --- Header background (dark blue rectangle) ---
    stream_parts.append("0.055 0.290 0.482 rg")  # #0e4a7b fill
    stream_parts.append(f"0 {page_h - 80:.2f} {page_w:.2f} 80 re f")

    # --- Header text ---
    stream_parts.append("1 1 1 rg")  # white
    stream_parts.append("BT")
    stream_parts.append("/F2 20 Tf")
    stream_parts.append(f"{page_w/2 - 180:.2f} {page_h - 40:.2f} Td")
    stream_parts.append("(PatientPath AI Eye Care Hospital) Tj")
    stream_parts.append("ET")

    stream_parts.append("BT")
    stream_parts.append("/F1 10 Tf")
    stream_parts.append(f"{page_w/2 - 150:.2f} {page_h - 58:.2f} Td")
    stream_parts.append("(Smart Healthcare  |  AI-Powered Patient Flow Management) Tj")
    stream_parts.append("ET")

    # --- Accent line ---
    stream_parts.append("0.055 0.647 0.910 RG")  # #0ea5e9 stroke
    stream_parts.append("2 w")
    stream_parts.append(f"30 {page_h - 90:.2f} m {page_w - 30:.2f} {page_h - 90:.2f} l S")

    y = page_h - 120

    # --- Title ---
    stream_parts.append("0.102 0.102 0.180 rg")  # #1a1a2e
    stream_parts.append("BT")
    stream_parts.append("/F2 16 Tf")
    stream_parts.append(f"30 {y:.2f} Td")
    stream_parts.append("(Medical Prescription) Tj")
    stream_parts.append("ET")
    y -= 10

    # Line separator
    stream_parts.append("0.886 0.910 0.878 RG")
    stream_parts.append("0.5 w")
    stream_parts.append(f"30 {y:.2f} m {page_w - 30:.2f} {y:.2f} l S")
    y -= 25

    # --- Date & Prescription ID ---
    stream_parts.append("0.392 0.455 0.545 rg")  # #64748b
    stream_parts.append("BT")
    stream_parts.append("/F1 10 Tf")
    stream_parts.append(f"30 {y:.2f} Td")
    stream_parts.append(f"(Date: {escape_pdf(date_str)}) Tj")
    stream_parts.append("ET")

    stream_parts.append("BT")
    stream_parts.append("/F1 10 Tf")
    stream_parts.append(f"300 {y:.2f} Td")
    stream_parts.append(f"(Prescription ID: RX-{rx.id}) Tj")
    stream_parts.append("ET")
    y -= 30

    # --- Doctor info box ---
    stream_parts.append("0.941 0.976 1.000 rg")  # #f0f9ff
    box_w = (page_w - 80) / 2
    stream_parts.append(f"30 {y - 45:.2f} {box_w:.2f} 50 re f")

    stream_parts.append("0.392 0.455 0.545 rg")
    stream_parts.append("BT")
    stream_parts.append("/F1 9 Tf")
    stream_parts.append(f"40 {y - 8:.2f} Td")
    stream_parts.append("(DOCTOR) Tj")
    stream_parts.append("ET")

    stream_parts.append("0.102 0.102 0.180 rg")
    stream_parts.append("BT")
    stream_parts.append("/F2 12 Tf")
    stream_parts.append(f"40 {y - 28:.2f} Td")
    stream_parts.append(f"({escape_pdf(doctor_name)}) Tj")
    stream_parts.append("ET")

    # --- Patient info box ---
    px = 30 + box_w + 20
    stream_parts.append("0.941 0.992 0.957 rg")  # #f0fdf4
    stream_parts.append(f"{px:.2f} {y - 45:.2f} {box_w:.2f} 50 re f")

    stream_parts.append("0.392 0.455 0.545 rg")
    stream_parts.append("BT")
    stream_parts.append("/F1 9 Tf")
    stream_parts.append(f"{px + 10:.2f} {y - 8:.2f} Td")
    stream_parts.append("(PATIENT ID) Tj")
    stream_parts.append("ET")

    stream_parts.append("0.102 0.102 0.180 rg")
    stream_parts.append("BT")
    stream_parts.append("/F2 12 Tf")
    stream_parts.append(f"{px + 10:.2f} {y - 28:.2f} Td")
    stream_parts.append(f"({escape_pdf(patient_id)}) Tj")
    stream_parts.append("ET")
    y -= 75

    # --- Diagnosis Section ---
    stream_parts.append("0.055 0.290 0.482 rg")  # primary
    stream_parts.append("BT")
    stream_parts.append("/F2 11 Tf")
    stream_parts.append(f"30 {y:.2f} Td")
    stream_parts.append("(Diagnosis) Tj")
    stream_parts.append("ET")
    y -= 5

    stream_parts.append("0.055 0.647 0.910 RG")
    stream_parts.append("1 w")
    stream_parts.append(f"30 {y:.2f} m 120 {y:.2f} l S")
    y -= 18

    stream_parts.append("0.102 0.102 0.180 rg")
    for line in wrap_text(diagnosis):
        stream_parts.append("BT")
        stream_parts.append("/F1 11 Tf")
        stream_parts.append(f"30 {y:.2f} Td")
        stream_parts.append(f"({escape_pdf(line)}) Tj")
        stream_parts.append("ET")
        y -= 16
    y -= 15

    # --- Prescription Section ---
    stream_parts.append("0.055 0.290 0.482 rg")
    stream_parts.append("BT")
    stream_parts.append("/F2 11 Tf")
    stream_parts.append(f"30 {y:.2f} Td")
    stream_parts.append("(Prescription) Tj")
    stream_parts.append("ET")
    y -= 5

    stream_parts.append("0.055 0.647 0.910 RG")
    stream_parts.append("1 w")
    stream_parts.append(f"30 {y:.2f} m 140 {y:.2f} l S")
    y -= 18

    stream_parts.append("0.102 0.102 0.180 rg")
    for line in wrap_text(prescription):
        stream_parts.append("BT")
        stream_parts.append("/F1 11 Tf")
        stream_parts.append(f"30 {y:.2f} Td")
        stream_parts.append(f"({escape_pdf(line)}) Tj")
        stream_parts.append("ET")
        y -= 16
    y -= 15

    # --- Next Visit ---
    if next_visit:
        stream_parts.append("1.000 0.984 0.922 rg")  # #fffbeb
        stream_parts.append(f"30 {y - 30:.2f} {page_w - 60:.2f} 35 re f")
        stream_parts.append("0.706 0.325 0.035 rg")  # #b45309
        stream_parts.append("BT")
        stream_parts.append("/F2 10 Tf")
        stream_parts.append(f"42 {y - 15:.2f} Td")
        stream_parts.append(f"(Next Visit:  {escape_pdf(next_visit)}) Tj")
        stream_parts.append("ET")
        y -= 55

    # --- Signature line ---
    y -= 20
    stream_parts.append("0.796 0.835 0.878 RG")  # #cbd5e1
    stream_parts.append("0.5 w")
    stream_parts.append(f"350 {y:.2f} m {page_w - 30:.2f} {y:.2f} l S")

    stream_parts.append("0.392 0.455 0.545 rg")
    stream_parts.append("BT")
    stream_parts.append("/F1 9 Tf")
    mid_sig = (350 + page_w - 30) / 2 - 30
    stream_parts.append(f"{mid_sig:.2f} {y - 14:.2f} Td")
    stream_parts.append("(Doctor's Signature) Tj")
    stream_parts.append("ET")

    # --- Footer background ---
    stream_parts.append("0.945 0.961 0.976 rg")  # #f1f5f9
    stream_parts.append(f"0 0 {page_w:.2f} 35 re f")
    stream_parts.append("0.392 0.455 0.545 rg")
    stream_parts.append("BT")
    stream_parts.append("/F1 7 Tf")
    stream_parts.append(f"{page_w/2 - 170:.2f} 14 Td")
    stream_parts.append("(This is a computer-generated prescription from PatientPath AI Eye Care Hospital.) Tj")
    stream_parts.append("ET")

    stream_content = "\n".join(stream_parts)
    stream_bytes = stream_content.encode("latin-1")

    # Build raw PDF
    objects = []
    offsets = []

    def add_obj(content):
        obj_num = len(objects) + 1
        objects.append(content)
        return obj_num

    # Object 1: Catalog
    add_obj("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
    # Object 2: Pages
    add_obj("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj")
    # Object 3: Page
    add_obj(
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        f"/MediaBox [0 0 {page_w:.2f} {page_h:.2f}] "
        f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj"
    )
    # Object 4: Content stream
    add_obj(
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n"
        + stream_content
        + "\nendstream\nendobj"
    )
    # Object 5: Font (Helvetica)
    add_obj(
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        "/Encoding /WinAnsiEncoding >>\nendobj"
    )
    # Object 6: Font (Helvetica-Bold)
    add_obj(
        "6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        "/Encoding /WinAnsiEncoding >>\nendobj"
    )

    # Assemble PDF
    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")

    for i, obj in enumerate(objects):
        offsets.append(buf.tell())
        buf.write(obj.encode("latin-1"))
        buf.write(b"\n")

    # Cross-reference table
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
