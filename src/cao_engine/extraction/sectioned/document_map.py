"""Build a structural map of an OCR'd CAO: ordered sections + their tables.

Deterministic and pure (no network, no LLM). Consumes an OCRResult and produces
a DocumentMap whose section bodies, concatenated, reproduce the document text.
Headers/footers and page markers are intentionally excluded as boilerplate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from cao_engine.ocr.models import OCRResult

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class MappedTable:
    id: str
    content: str
    page_index: int


@dataclass
class MappedSection:
    index: int
    heading: str | None  # None = preamble / front-matter (text before the first heading)
    level: int           # 0 for preamble, else 1-6
    page_start: int
    page_end: int
    body: str = ""
    tables: list[MappedTable] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Heading + body as markdown (used to assemble routed slices)."""
        head = f"{'#' * self.level} {self.heading}\n" if self.heading else ""
        return f"{head}{self.body}".strip()


@dataclass
class DocumentMap:
    sections: list[MappedSection]

    def all_tables(self) -> list[MappedTable]:
        return [t for s in self.sections for t in s.tables]

    def full_markdown(self) -> str:
        return "\n\n".join(s.text for s in self.sections if s.text)


def build_document_map(ocr_result: OCRResult) -> DocumentMap:
    sections: list[MappedSection] = []
    current: MappedSection | None = None

    def _open(heading: str | None, level: int, page_index: int) -> MappedSection:
        section = MappedSection(
            index=len(sections), heading=heading, level=level,
            page_start=page_index, page_end=page_index,
        )
        sections.append(section)
        return section

    for page in ocr_result.pages:
        tables_by_id = {t.id: t for t in page.tables}
        seen_ids: set[str] = set()
        for raw_line in page.markdown.splitlines():
            match = _HEADING_RE.match(raw_line.strip())
            if match:
                current = _open(match.group(2).strip(), len(match.group(1)), page.index)
                continue
            if current is None:
                current = _open(None, 0, page.index)  # preamble
            current.page_end = page.index
            line = raw_line
            for tid, table in tables_by_id.items():
                placeholder = f"[{tid}]({tid})"
                if placeholder in line:
                    line = line.replace(placeholder, f"\n{table.content}\n")
                    current.tables.append(
                        MappedTable(id=tid, content=table.content, page_index=page.index)
                    )
                    seen_ids.add(tid)
            current.body += line + "\n"
        # defensive: tables whose placeholder never appeared in the markdown
        for tid, table in tables_by_id.items():
            if tid in seen_ids:
                continue
            if current is None:
                current = _open(None, 0, page.index)
            current.page_end = page.index
            current.body += f"\n{table.content}\n"
            current.tables.append(
                MappedTable(id=tid, content=table.content, page_index=page.index)
            )

    return DocumentMap(sections=sections)
