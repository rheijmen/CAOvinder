"""Local models mirroring Mistral OCR API response structure."""

from pydantic import BaseModel, Field


class OCRPageDimensions(BaseModel):
    dpi: int
    height: int
    width: int


class OCRTable(BaseModel):
    """Table extracted from a page."""
    id: str
    content: str  # Markdown formatted table content
    format: str = "markdown"


class OCRPage(BaseModel):
    index: int
    markdown: str
    dimensions: OCRPageDimensions | None = None
    header: str | None = None
    footer: str | None = None
    tables: list[OCRTable] = Field(default_factory=list)


class OCRUsageInfo(BaseModel):
    pages_processed: int
    doc_size_bytes: int | None = None


class OCRResult(BaseModel):
    """Local representation of a Mistral OCR API response."""

    model: str
    pages: list[OCRPage] = Field(default_factory=list)
    usage_info: OCRUsageInfo
    document_annotation: str | None = None
    source_file: str

    @property
    def full_markdown(self) -> str:
        """Combine all pages into a single markdown document with tables inline."""
        parts = []
        for page in self.pages:
            parts.append(f"<!-- Page {page.index} -->")
            if page.header:
                parts.append(f"> Header: {page.header}")

            # Replace table references with actual table content
            markdown = page.markdown
            for table in page.tables:
                # Replace [tbl-X.md](tbl-X.md) with the actual table content
                markdown = markdown.replace(f"[{table.id}]({table.id})", f"\n{table.content}\n")

            parts.append(markdown)

            if page.footer:
                parts.append(f"> Footer: {page.footer}")
        return "\n\n---\n\n".join(parts)

    @property
    def total_pages(self) -> int:
        return self.usage_info.pages_processed
