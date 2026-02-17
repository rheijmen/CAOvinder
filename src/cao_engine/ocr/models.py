"""Local models mirroring Mistral OCR API response structure."""

from pydantic import BaseModel, Field


class OCRPageDimensions(BaseModel):
    dpi: int
    height: int
    width: int


class OCRPage(BaseModel):
    index: int
    markdown: str
    dimensions: OCRPageDimensions | None = None
    header: str | None = None
    footer: str | None = None


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
        """Combine all pages into a single markdown document."""
        parts = []
        for page in self.pages:
            parts.append(f"<!-- Page {page.index} -->")
            if page.header:
                parts.append(f"> Header: {page.header}")
            parts.append(page.markdown)
            if page.footer:
                parts.append(f"> Footer: {page.footer}")
        return "\n\n---\n\n".join(parts)

    @property
    def total_pages(self) -> int:
        return self.usage_info.pages_processed
