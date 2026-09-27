"""
Minimal dependency-free PDF 1.4 writer for incident exports.

No third-party PDF library is installed (and none may be added), so this
module hand-builds a valid single- or multi-page PDF using the built-in
Helvetica base fonts:

- title + reference number, status/severity/department/ward, description,
  timestamps, SLA deadline and the public timeline entries;
- text is escaped for PDF string syntax (backslashes + parentheses) and
  wrapped at ~90 characters per line;
- the xref table is computed from the actual byte offsets, so the output
  opens in any PDF reader.
"""

from __future__ import annotations

PAGE_WIDTH = 612  # US Letter, points
PAGE_HEIGHT = 792
MARGIN = 54
LINE_HEIGHT = 13
TITLE_SIZE = 15
BODY_SIZE = 10
WRAP_COLUMNS = 90
LINES_PER_PAGE = (PAGE_HEIGHT - 2 * MARGIN) // LINE_HEIGHT

FONT_BODY = "F1"
FONT_BOLD = "F2"

# (font, size, text) — one entry per rendered line.
Line = tuple[str, int, str]


def _escape(text: str) -> str:
    """Escape a PDF literal string (only backslash and parentheses are special)."""
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(text: str, width: int = WRAP_COLUMNS) -> list[str]:
    """Wrap one paragraph at `width` characters; blank paragraphs stay blank."""
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            if len(current) + 1 + len(word) <= width:
                current = f"{current} {word}"
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _format_dt(value) -> str:
    return f"{value:%Y-%m-%d %H:%M} UTC" if value else ""


def _incident_lines(incident, *, show_actor_names: bool = False) -> list[Line]:
    """Flatten the incident report into wrapped (font, size, text) lines."""
    lines: list[Line] = [
        (FONT_BOLD, TITLE_SIZE, "SafeCity Incident Report"),
        (FONT_BOLD, BODY_SIZE + 1, incident.reference_number),
        (FONT_BODY, BODY_SIZE, ""),
        (FONT_BOLD, BODY_SIZE, "Details"),
    ]

    fields = [
        ("Title", incident.title),
        ("Status", incident.get_status_display()),
        ("Severity", incident.get_severity_display()),
        ("Department", incident.department.name if incident.department else "—"),
        ("Ward", incident.ward.name if incident.ward else "—"),
    ]
    for label, value in fields:
        for i, wrapped in enumerate(_wrap(f"{label}: {value}")):
            lines.append((FONT_BOLD if i == 0 else FONT_BODY, BODY_SIZE, wrapped))

    lines.append((FONT_BODY, BODY_SIZE, ""))
    lines.append((FONT_BOLD, BODY_SIZE, "Description"))
    lines.extend((FONT_BODY, BODY_SIZE, line) for line in _wrap(incident.description))

    lines.append((FONT_BODY, BODY_SIZE, ""))
    lines.append((FONT_BOLD, BODY_SIZE, "Timestamps"))
    timestamps = [
        ("Created", incident.created_at),
        ("Submitted", incident.submitted_at),
        ("Verified", incident.verified_at),
        ("Assigned", incident.assigned_at),
        ("Resolved", incident.resolved_at),
        ("Closed", incident.closed_at),
    ]
    for label, value in timestamps:
        if value:
            lines.append((FONT_BODY, BODY_SIZE, f"{label}: {_format_dt(value)}"))
    lines.append(
        (
            FONT_BODY,
            BODY_SIZE,
            f"SLA deadline: {_format_dt(incident.sla_deadline) or 'Not set'}"
            + (" (breached)" if incident.sla_breached else ""),
        )
    )

    lines.append((FONT_BODY, BODY_SIZE, ""))
    lines.append((FONT_BOLD, BODY_SIZE, "Timeline"))
    timeline = incident.status_history.filter(is_public=True).order_by("created_at")
    if not timeline:
        lines.append((FONT_BODY, BODY_SIZE, "No public timeline entries."))
    for entry in timeline:
        if show_actor_names:
            actor = entry.actor.full_name if entry.actor else "System"
        else:
            actor = "SafeCity"
        text = f"{entry.created_at:%Y-%m-%d %H:%M}  {entry.to_status}  —  {actor}"
        if entry.note:
            text += f" — {entry.note}"
        lines.extend((FONT_BODY, BODY_SIZE, line) for line in _wrap(text))

    return lines


def _content_stream(page_lines: list[Line]) -> bytes:
    """Render one page's lines as a PDF content stream (latin-1 safe)."""
    commands = []
    for index, (font, size, text) in enumerate(page_lines):
        y = PAGE_HEIGHT - MARGIN - LINE_HEIGHT * (index + 1)
        commands.append(
            f"BT\n/{font} {size} Tf\n1 0 0 1 {MARGIN} {y} Tm\n"
            f"({_escape(text)}) Tj\nET"
        )
    return "\n".join(commands).encode("latin-1", "replace")


def build_incident_pdf(incident, *, show_actor_names: bool = False) -> bytes:
    """Build a valid PDF 1.4 document (bytes) for one incident."""
    lines = _incident_lines(incident, show_actor_names=show_actor_names)
    pages = [
        lines[start : start + LINES_PER_PAGE]
        for start in range(0, len(lines), LINES_PER_PAGE)
    ] or [[]]

    objects: dict[int, bytes] = {}
    page_numbers = [5 + 2 * i for i in range(len(pages))]
    kids = " ".join(f"{num} 0 R" for num in page_numbers)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii")
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
    for index, page_lines in enumerate(pages):
        content_number = 6 + 2 * index
        objects[5 + 2 * index] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /{FONT_BODY} 3 0 R /{FONT_BOLD} 4 0 R >> >> "
            f"/Contents {content_number} 0 R >>"
        ).encode("ascii")
        stream = _content_stream(page_lines)
        objects[content_number] = (
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out.extend(f"{number} 0 obj\n".encode("ascii"))
        out.extend(objects[number])
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    count = max(objects) + 1
    out.extend(f"xref\n0 {count}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for number in range(1, count):
        out.extend(f"{offsets[number]:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode(
            "ascii"
        )
    )
    return bytes(out)
