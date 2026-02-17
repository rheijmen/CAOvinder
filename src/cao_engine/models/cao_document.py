"""Top-level CAO document model aggregating all sub-schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from .arbeidsvoorwaarden import ArbeidsVoorwaarden
from .cao_metadata import CAOMetadata
from .inlenersbeloning import InlenersbeloningElementen
from .loongebouw import Loongebouw
from .momenten import Moment


class ProcessingInfo(BaseModel):
    """Metadata about when and how the document was processed."""

    ocr_model: str
    ocr_timestamp: datetime
    extraction_timestamp: datetime | None = None
    extraction_model: str | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    pages_processed: int = 0
    source_file: str


class CAODocument(BaseModel):
    """Complete structured representation of a CAO.

    Aggregates all extracted data: metadata, wage structure, employment conditions,
    inlenersbeloning elements, and all identified moments.
    """

    metadata: CAOMetadata
    loongebouw: Loongebouw | None = None
    arbeidsvoorwaarden: ArbeidsVoorwaarden | None = None
    inlenersbeloning: InlenersbeloningElementen | None = None
    momenten: list[Moment] = Field(
        default_factory=list,
        description="All extracted moments (ground truth for notifications)",
    )
    processing: ProcessingInfo
    raw_markdown: str | None = Field(None, description="Full OCR markdown for reference")
    schema_version: str = Field("1.0.0", description="Schema version")
