import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


def generate_invoice_pdf(invoice, user):
    """Build a professional PDF invoice and return it as raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle", parent=styles["Heading1"], fontSize=24, textColor=colors.HexColor("#1a1a2e")
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading3"], fontSize=11, textColor=colors.HexColor("#4a4a68")
    )
    normal = styles["Normal"]

    elements = []

    # Header: business info + invoice title/status
    header_data = [
        [
            Paragraph(f"<b>{user.name}</b><br/>{user.email}", normal),
            Paragraph(f"<para alignment='right'><b>INVOICE</b></para>", title_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.15 * inch))

    status_color = {
        "PAID": colors.HexColor("#1a7f37"),
        "OVERDUE": colors.HexColor("#c0392b"),
        "CANCELLED": colors.HexColor("#7f8c8d"),
        "SENT": colors.HexColor("#2563eb"),
        "DRAFT": colors.HexColor("#8a8a8a"),
    }.get(invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status), colors.black)

    status_value = invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status)

    meta_data = [
        ["Invoice Number:", invoice.invoice_number, "Status:", status_value],
        ["Issue Date:", invoice.issue_date.isoformat(), "Due Date:", invoice.due_date.isoformat()],
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.2 * inch, 1.0 * inch, 2.0 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (3, 0), (3, 0), status_color),
        ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.25 * inch))

    # Bill to
    elements.append(Paragraph("BILL TO", heading_style))
    customer = invoice.customer
    bill_to_lines = [f"<b>{customer.name}</b>"]
    if customer.email:
        bill_to_lines.append(customer.email)
    if customer.phone:
        bill_to_lines.append(customer.phone)
    if customer.address:
        bill_to_lines.append(customer.address.replace("\n", "<br/>"))
    elements.append(Paragraph("<br/>".join(bill_to_lines), normal))
    elements.append(Spacer(1, 0.3 * inch))

    # Items table
    item_rows = [["Description", "Qty", "Unit Price", "Total"]]
    for item in invoice.items:
        desc = item.name
        if item.description:
            desc += f"<br/><font size=8 color='#666666'>{item.description}</font>"
        item_rows.append([
            Paragraph(desc, normal),
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{item.line_total:.2f}",
        ])

    items_table = Table(item_rows, colWidths=[3.4 * inch, 0.8 * inch, 1.4 * inch, 1.4 * inch])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5fa")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Totals
    totals_data = [
        ["Subtotal:", f"{invoice.subtotal:.2f}"],
        ["Tax:", f"{invoice.tax:.2f}"],
        ["Total:", f"{invoice.total:.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[5.6 * inch, 1.4 * inch])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1a1a2e")),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
    ]))
    elements.append(totals_table)

    if invoice.notes:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("NOTES", heading_style))
        elements.append(Paragraph(invoice.notes.replace("\n", "<br/>"), normal))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
