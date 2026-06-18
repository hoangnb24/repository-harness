from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PDF_BACKEND = "vsf_profiler.simple_pdf"
PDF_GENERATOR = "vsf_profiler.pdf_export.write_simple_pdf_report"
PAGE_WIDTH = 612
PAGE_HEIGHT = 792
PAGE_MARGIN = 54
FONT_SIZE = 10
LINE_HEIGHT = 12
MAX_LINE_CHARS = 92
LINES_PER_PAGE = 56


@dataclass(frozen=True)
class PdfExportResult:
    path: Path
    backend: str
    generator: str
    created_at: str
    source_path: Path


def write_simple_pdf_report(
    *,
    source_markdown_path: Path,
    output_pdf_path: Path,
    created_at: str | None = None,
) -> PdfExportResult:
    if not source_markdown_path.is_file():
        raise ValueError(f"Markdown report does not exist: {source_markdown_path}")
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    created_at_value = created_at or _iso_now()
    source_text = source_markdown_path.read_text(encoding="utf-8", errors="replace")
    lines = _markdown_to_pdf_lines(source_text)
    output_pdf_path.write_bytes(_build_pdf(lines))
    return PdfExportResult(
        path=output_pdf_path,
        backend=PDF_BACKEND,
        generator=PDF_GENERATOR,
        created_at=created_at_value,
        source_path=source_markdown_path,
    )


def _markdown_to_pdf_lines(source_text: str) -> list[str]:
    lines: list[str] = ["VSF Data Profiler Analysis Report", ""]
    for raw_line in source_text.splitlines():
        normalized = _normalize_markdown_line(raw_line)
        if not normalized:
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            normalized,
            width=MAX_LINE_CHARS,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        lines.extend(wrapped or [""])
    return lines or ["VSF Data Profiler Analysis Report"]


def _normalize_markdown_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("#"):
        return stripped.lstrip("#").strip()
    return stripped


def _build_pdf(lines: list[str]) -> bytes:
    pages = _chunk_lines(lines, LINES_PER_PAGE)
    objects: dict[int, bytes] = {}
    page_object_numbers: list[int] = []

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    next_object_number = 4
    for page_lines in pages:
        page_object_number = next_object_number
        content_object_number = next_object_number + 1
        next_object_number += 2
        page_object_numbers.append(page_object_number)
        content = _page_content(page_lines)
        objects[page_object_number] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_number} 0 R >>"
        ).encode("ascii")
        objects[content_object_number] = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"endstream"
        )

    kids = " ".join(f"{object_number} 0 R" for object_number in page_object_numbers)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode(
        "ascii"
    )

    max_object_number = max(objects)
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (max_object_number + 1)
    for object_number in range(1, max_object_number + 1):
        offsets[object_number] = len(pdf)
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_number])
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {max_object_number + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for object_number in range(1, max_object_number + 1):
        pdf.extend(f"{offsets[object_number]:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {max_object_number + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _page_content(lines: list[str]) -> bytes:
    y_start = PAGE_HEIGHT - PAGE_MARGIN
    commands = [
        "BT",
        f"/F1 {FONT_SIZE} Tf",
        f"{PAGE_MARGIN} {y_start} Td",
        f"{LINE_HEIGHT} TL",
    ]
    for line in lines:
        commands.append(f"({_escape_pdf_text(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return ("\n".join(commands) + "\n").encode("latin-1", errors="replace")


def _escape_pdf_text(value: str) -> str:
    safe = value.encode("latin-1", errors="replace").decode("latin-1")
    safe = safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return "".join(char if char >= " " or char == "\t" else " " for char in safe)


def _chunk_lines(lines: list[str], chunk_size: int) -> list[list[str]]:
    chunks = [lines[index : index + chunk_size] for index in range(0, len(lines), chunk_size)]
    return chunks or [["VSF Data Profiler Analysis Report"]]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
