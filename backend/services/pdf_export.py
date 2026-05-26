import io
import logging
import re
from html import unescape
from typing import Any

logger = logging.getLogger('ats_resume_scorer')


def _strip_html(html: str) -> str:
    text = re.sub(r'<\s*br\s*/?\s*>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</\s*(p|div|h[1-6]|li|tr)\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def _pdf_escape(text: str) -> str:
    return (
        text.replace('\\', '\\\\')
        .replace('(', '\\(')
        .replace(')', '\\)')
        .encode('latin-1', errors='replace')
        .decode('latin-1')
    )


def _wrap_text(text: str, width: int = 92) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        words = raw_line.split()
        if not words:
            lines.append('')
            continue

        current = words[0]
        for word in words[1:]:
            if len(current) + len(word) + 1 > width:
                lines.append(current)
                current = word
            else:
                current += ' ' + word
        lines.append(current)
    return lines


def _build_simple_pdf(sections: dict[str, str]) -> bytes:
    page_streams: list[str] = []

    for title, html in sections.items():
        lines = [title.replace('_', ' ').title(), '']
        lines.extend(_wrap_text(_strip_html(html)))

        for start in range(0, len(lines), 48):
            page_lines = lines[start:start + 48]
            content = ['BT', '/F1 10 Tf', '50 790 Td', '14 TL']
            for line in page_lines:
                content.append(f'({_pdf_escape(line)}) Tj')
                content.append('T*')
            content.append('ET')
            page_streams.append('\n'.join(content))

    objects: list[bytes] = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'',  # Filled after page objects are known.
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]

    page_object_ids: list[int] = []
    for stream in page_streams:
        stream_bytes = stream.encode('latin-1', errors='replace')
        content_id = len(objects) + 1
        page_id = len(objects) + 2
        objects.append(
            b'<< /Length ' + str(len(stream_bytes)).encode('ascii') +
            b' >>\nstream\n' + stream_bytes + b'\nendstream'
        )
        objects.append(
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Resources << /Font << /F1 3 0 R >> >> /Contents ' +
            str(content_id).encode('ascii') + b' 0 R >>'
        )
        page_object_ids.append(page_id)

    kids = b' '.join(f'{page_id} 0 R'.encode('ascii') for page_id in page_object_ids)
    objects[1] = (
        b'<< /Type /Pages /Kids [' + kids + b'] /Count ' +
        str(len(page_object_ids)).encode('ascii') + b' >>'
    )

    pdf = io.BytesIO()
    pdf.write(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f'{index} 0 obj\n'.encode('ascii'))
        pdf.write(obj)
        pdf.write(b'\nendobj\n')

    xref_offset = pdf.tell()
    pdf.write(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    pdf.write(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.write(f'{offset:010d} 00000 n \n'.encode('ascii'))
    pdf.write(
        b'trailer\n<< /Size ' + str(len(objects) + 1).encode('ascii') +
        b' /Root 1 0 R >>\nstartxref\n' +
        str(xref_offset).encode('ascii') + b'\n%%EOF\n'
    )
    return pdf.getvalue()


def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:
    try:
        from weasyprint import HTML

        documents = []
        for _name, html_str in html_docs.items():
            documents.append(HTML(string=html_str).render())

        first_doc = documents[0]
        for other_doc in documents[1:]:
            first_doc.pages.extend(other_doc.pages)

        return first_doc.write_pdf()
    except Exception as exc:
        logger.warning(
            'WeasyPrint PDF generation failed; using simple PDF fallback: %s',
            exc,
        )
        return _build_simple_pdf(html_docs)


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    if hasattr(value, '__dict__'):
        return value.__dict__
    return {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _severity_color(severity: str):
    from reportlab.lib import colors

    severity = (severity or '').lower()
    if severity == 'high':
        return colors.HexColor('#dc2626')
    if severity in ('moderate', 'medium'):
        return colors.HexColor('#d97706')
    return colors.HexColor('#2563eb')


def generate_analysis_pdf(analysis_data: dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title='ATS Resume Report',
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=27,
        textColor=colors.HexColor('#111827'),
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='Muted',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#6b7280'),
    ))
    styles.add(ParagraphStyle(
        name='Section',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#111827'),
        spaceBefore=14,
        spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name='CardTitle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#111827'),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='Small',
        parent=styles['BodyText'],
        fontSize=8.7,
        leading=11.5,
        textColor=colors.HexColor('#374151'),
    ))

    def para(text: Any, style='Small') -> Paragraph:
        value = str(text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return Paragraph(value, styles[style])

    def bullet_items(items: list[Any], limit: int = 6) -> list[Paragraph]:
        output = []
        for item in items[:limit]:
            output.append(para(f'- {item}', 'Small'))
        return output

    story = [
        Paragraph('ATS Resume Report', styles['ReportTitle']),
        Paragraph('Generated by AI Resume ATS Analyzer', styles['Muted']),
        Spacer(1, 14),
    ]

    score = float(analysis_data.get('ATS_score') or analysis_data.get('ats_score') or 0)
    score_color = '#16a34a' if score >= 80 else '#d97706' if score >= 60 else '#dc2626'
    interpretation = analysis_data.get('interpretation') or 'Resume analysis summary'

    summary_table = Table(
        [[
            Paragraph(
                f'<font size="30" color="{score_color}"><b>{score:.0f}</b></font>'
                '<font size="13" color="#6b7280"> / 100</font><br/>'
                '<font size="8" color="#6b7280">ATS SCORE</font>',
                styles['BodyText'],
            ),
            para(interpretation, 'Small'),
        ]],
        colWidths=[1.55 * inch, 5.35 * inch],
    )
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(summary_table)

    component_scores = _as_dict(analysis_data.get('component_scores'))
    max_scores = {
        'formatting': 20,
        'keywords': 25,
        'content': 25,
        'skill_validation': 15,
        'ats_compatibility': 15,
    }
    rows = [[para('Component', 'CardTitle'), para('Score', 'CardTitle'), para('Percent', 'CardTitle')]]
    for key, max_score in max_scores.items():
        value = float(component_scores.get(key, 0) or 0)
        label = key.replace('_', ' ').title()
        rows.append([para(label), para(f'{value:g} / {max_score}'), para(f'{round(value / max_score * 100)}%')])
    table = Table(rows, colWidths=[3.4 * inch, 1.45 * inch, 1.55 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef2ff')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#d1d5db')),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.extend([Paragraph('Score Breakdown', styles['Section']), table])

    jd = _as_dict(analysis_data.get('jd_match_analysis') or analysis_data.get('jd_comparison'))
    if jd:
        jd_rows = [
            [para('JD Match', 'CardTitle'), para(f"{jd.get('match_percentage', 0)}%")],
            [para('Semantic Similarity', 'CardTitle'), para(jd.get('semantic_similarity', 0))],
            [para('Matched Keywords', 'CardTitle'), para(', '.join(_as_list(jd.get('matched_keywords'))[:14]) or 'None')],
            [para('Missing Keywords', 'CardTitle'), para(', '.join(_as_list(jd.get('missing_keywords'))[:14]) or 'None')],
        ]
        jd_table = Table(jd_rows, colWidths=[1.8 * inch, 4.6 * inch])
        jd_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#d1d5db')),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f9fafb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.extend([Paragraph('Job Description Match', styles['Section']), jd_table])

    svd = _as_dict(analysis_data.get('skill_validation_details'))
    if svd:
        story.append(Paragraph('Skill Validation', styles['Section']))
        story.append(para(
            f"{svd.get('validated_count', 0)} of {svd.get('total', 0)} skills validated "
            f"({svd.get('validation_pct', 0)}%)."
        ))
        unvalidated = _as_list(svd.get('unvalidated'))
        if unvalidated:
            story.append(Spacer(1, 4))
            story.append(para('Unvalidated skills: ' + ', '.join(unvalidated[:20])))

    feedback = [_as_dict(item) for item in _as_list(analysis_data.get('detailed_feedback'))]
    if feedback:
        story.append(Paragraph('Priority Fixes', styles['Section']))
        for index, item in enumerate(feedback[:10], start=1):
            sev = item.get('severity_level', 'Info')
            header = Table(
                [[
                    para(f"{index}. {item.get('issue_title', 'Issue')}", 'CardTitle'),
                    Paragraph(
                        f'<font color="{_severity_color(sev).hexval()}"><b>{sev}</b></font>',
                        styles['Small'],
                    ),
                ]],
                colWidths=[5.35 * inch, 1.05 * inch],
            )
            header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            block = [
                header,
                Spacer(1, 4),
                para(item.get('explanation')),
                Spacer(1, 3),
                para('<b>How to fix:</b> ' + str(item.get('how_to_fix', ''))),
                Spacer(1, 3),
                *bullet_items(_as_list(item.get('action_items')), 5),
                Spacer(1, 9),
            ]
            story.append(KeepTogether(block))

    doc.build(story)
    return buffer.getvalue()
