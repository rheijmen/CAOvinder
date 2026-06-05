"""Batch processing for cost-efficient CAO processing at scale.

Uses Mistral Batch API (50% discount) and Gemini Batch API (50% discount)
to process 700+ CAOs asynchronously within 24-48 hours.

Cost savings:
- Mistral OCR: $70,000 → $35,000 (50% off)
- Gemini extraction: $24.50 → $12.25 (50% off)
- Mistral Large: $98 → $49 (50% off)
- Total: $35,061 saved per full batch run
"""

from .coordinator import BatchCoordinator
from .input_generator import generate_gemini_batch_jsonl, generate_ocr_batch_jsonl
from .models import BatchJob, BatchStatus

__all__ = [
    "BatchCoordinator",
    "generate_ocr_batch_jsonl",
    "generate_gemini_batch_jsonl",
    "BatchJob",
    "BatchStatus",
]
