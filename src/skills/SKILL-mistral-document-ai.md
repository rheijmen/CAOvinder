# SKILL: Mistral Document AI

> Use this skill whenever a task involves reading, extracting, structuring, or processing documents or images using Mistral's Document AI stack.  
> Covers: OCR, Annotations (bbox + document), Document Q&A, and Batch OCR.

---

## What This Skill Is

Mistral Document AI is an enterprise-grade document processing API built on the model `mistral-ocr-latest`. It goes beyond plain text extraction — it understands document structure, extracts images and tables, returns results in markdown, and can annotate or structure the output into any JSON schema you define.

Entry point in the SDK: `client.ocr.process()`  
API endpoint: `https://api.mistral.ai/v1/ocr`

---

## Three Services Available

### 1. OCR Processor
Basic document-to-text conversion with structure preservation.

### 2. Annotations
Structured data extraction on top of OCR. Returns JSON matching your schema.

### 3. Document Q&A
Combine OCR output with Mistral LLMs for question-answering over document content.

---

## Service 1: OCR Processor

### What It Does
- Extracts text while preserving document hierarchy (headers, paragraphs, lists, tables)
- Returns output in markdown format
- Extracts image bounding boxes (bboxes)
- Returns hyperlinks when present
- Handles multi-column layouts and complex mixed content

### Supported Input Formats

**Images:** PNG, JPEG/JPG, AVIF, and more  
**Documents:** PDF, PPTX, DOCX, and more

Input can be provided as:
- A public URL (`document_url` or `image_url`)
- A base64-encoded file
- An uploaded file via Mistral Cloud

### Key Parameters

| Parameter | Values | Default | Notes |
|-----------|--------|---------|-------|
| `model` | `"mistral-ocr-latest"` | required | Always use this model |
| `document` | dict with `type` + URL/data | required | `document_url` or `image_url` |
| `table_format` | `null`, `"markdown"`, `"html"` | `null` | `null` = inline in markdown; others = separate field |
| `extract_header` | `True` / `False` | `False` | Puts header in separate `header` field |
| `extract_footer` | `True` / `False` | `False` | Puts footer in separate `footer` field |
| `include_image_base64` | `True` / `False` | `False` | Returns extracted images as base64 |

> Note: `table_format`, `extract_header`, and `extract_footer` require OCR model version 2512 or newer.

### Response Structure

```json
{
  "pages": [
    {
      "index": int,
      "markdown": "str — main text output",
      "images": [],
      "tables": [],
      "hyperlinks": [],
      "header": "str or null",
      "footer": "str or null",
      "dimensions": {}
    }
  ],
  "model": "str",
  "document_annotation": null,
  "usage_info": {}
}
```

When images or tables are extracted, they are replaced with placeholders in the markdown:
- `![img-0.jpeg](img-0.jpeg)` → map via `images[]`
- `[tbl-3.html](tbl-3.html)` → map via `tables[]`

### Minimal Code Example (PDF via URL)

```python
import os
from mistralai import Mistral

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": "https://example.com/document.pdf"
    },
    table_format="html",
    extract_header=True,
    extract_footer=True,
    include_image_base64=True
)

# Access text from first page
print(response.pages[0].markdown)
```

### Minimal Code Example (Image via URL)

```python
response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "image_url",
        "image_url": "https://example.com/receipt.png"
    },
    include_image_base64=True
)
```

---

## Service 2: Annotations

### What It Does
Extracts structured, schema-defined data from documents on top of OCR. Two modes:

**`bbox_annotation`**: Annotates individual bounding boxes (charts, figures, signatures, etc.) using a vision LLM. Every detected bbox gets its own structured JSON output per your schema.

**`document_annotation`**: Annotates the entire document. OCR markdown output + up to 8 image bboxes are sent to a vision LLM together with your schema. Returns one structured JSON for the whole document.

You can use either one or both simultaneously.

### How the Annotation Schema Works

Define a Pydantic model (Python), Zod schema (TypeScript), or raw JSON Schema (curl). Nested objects, arrays, and enums are all supported. Add `Field(..., description="...")` to guide the model on how to fill each field.

```python
from pydantic import BaseModel, Field

class InvoiceData(BaseModel):
    vendor_name: str = Field(..., description="Name of the vendor or supplier")
    invoice_number: str = Field(..., description="The invoice or reference number")
    total_amount: float = Field(..., description="Total amount due including taxes")
    invoice_date: str = Field(..., description="Date of the invoice in ISO format")
```

### BBox Annotation Example

```python
from mistralai import Mistral, DocumentURLChunk
from mistralai.extra import response_format_from_pydantic_model
from pydantic import BaseModel, Field

class ImageCaption(BaseModel):
    image_type: str = Field(..., description="Type of image, e.g. chart, diagram, photo")
    short_description: str = Field(..., description="One-sentence description in English")
    summary: str = Field(..., description="Full summary of what the image contains")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

response = client.ocr.process(
    model="mistral-ocr-latest",
    document=DocumentURLChunk(document_url="https://arxiv.org/pdf/2410.07073"),
    bbox_annotation_format=response_format_from_pydantic_model(ImageCaption),
    include_image_base64=True
)
```

### Document Annotation Example

```python
from pydantic import BaseModel, Field

class ContractSummary(BaseModel):
    parties: list[str] = Field(..., description="Names of all parties in the contract")
    effective_date: str = Field(..., description="Contract start date")
    key_clauses: list[str] = Field(..., description="Most important clauses or obligations")

response = client.ocr.process(
    model="mistral-ocr-latest",
    document=DocumentURLChunk(document_url="https://example.com/contract.pdf"),
    document_annotation_format=response_format_from_pydantic_model(ContractSummary),
    document_annotation_prompt="Focus on legal obligations and payment terms."
)

# Access structured result
print(response.document_annotation)
```

### Common Use Cases for Annotations

- Invoice processing (vendor, amount, date extraction)
- Receipt capture (merchant name, line items, totals)
- Contract clause extraction
- Form parsing and classification
- Chart-to-table conversion
- Signature detection
- Medical record structuring

---

## Service 3: Document Q&A

Combine OCR with Mistral chat models to ask questions over document content. The OCR output is passed into a Mistral LLM context window for Q&A, summarization, or analysis.

Use case: "What is the total on this invoice?", "Summarize the key risks in this contract", etc.

> See: `https://docs.mistral.ai/capabilities/document_ai/document_qna`

---

## OCR at Scale: Batch Inference

For processing large volumes of documents, use Mistral's Batch API. Benefits:
- 50% cost reduction vs. direct OCR API
- Parallel processing of hundreds/thousands of images or PDFs
- Supports all annotations features

### How Batch OCR Works

1. Prepare a JSONL batch file with all OCR requests
2. Upload batch file via `client.files.upload()`
3. Create batch job via `client.batch.jobs.create()` with `endpoint="/v1/ocr"`
4. Poll job status; download output when complete

```python
# Create batch job
created_job = client.batch.jobs.create(
    input_files=[batch_data.id],
    model="mistral-ocr-latest",
    endpoint="/v1/ocr",
    metadata={"job_type": "document_processing"}
)

# Poll until done, then retrieve results
```

Output is a JSONL file with one OCR result per line, same structure as the synchronous API.

---

## Capabilities Summary Table

| Capability | Supported |
|---|---|
| PDF extraction | Yes |
| Image extraction (PNG, JPG, AVIF...) | Yes |
| PPTX, DOCX extraction | Yes |
| Scanned/handwritten documents | Yes |
| Table extraction (markdown or HTML) | Yes |
| Image bbox extraction | Yes |
| Header/footer separation | Yes |
| Hyperlink detection | Yes |
| Multi-column layout handling | Yes |
| Structured JSON output (Annotations) | Yes |
| Per-image annotation (bbox) | Yes |
| Whole-document annotation | Yes |
| Batch processing (cost -50%) | Yes |
| Document Q&A with LLM | Yes |
| Multilingual support | Yes |

---

## Practical Patterns

### Pattern 1: Extract + Structure in One Call
Use `document_annotation` with a Pydantic schema to go from raw PDF to structured JSON in a single API call. No separate LLM call needed.

### Pattern 2: Image Understanding from PDFs
Use `bbox_annotation` to automatically describe, caption, or classify every chart/figure/image in a PDF. Useful for financial reports, scientific papers, medical records.

### Pattern 3: Large Dataset Processing
Use Batch Inference with a JSONL input file. Process 100–10,000+ documents overnight at half the API cost. Results arrive as a JSONL output file.

### Pattern 4: Form/Invoice Automation Pipeline
1. Receive document (email attachment, upload, etc.)
2. Call `client.ocr.process()` with `document_annotation_format` set to your invoice schema
3. Receive structured JSON → insert into database or accounting system
4. No manual data entry

---

## Limits & Constraints

- `table_format`, `extract_header`, `extract_footer` require OCR model version 2512+
- `document_annotation` sends max 8 image bboxes to the LLM (per call)
- Input URLs must be publicly accessible (not behind auth)
- Base64 encoding works for private files
- See official FAQ for rate limits: `https://docs.mistral.ai/capabilities/document_ai/basic_ocr#faq`

---

## Reference Links

- Overview: https://docs.mistral.ai/capabilities/document_ai
- OCR Processor: https://docs.mistral.ai/capabilities/document_ai/basic_ocr
- Annotations: https://docs.mistral.ai/capabilities/document_ai/annotations
- Document Q&A: https://docs.mistral.ai/capabilities/document_ai/document_qna
- API reference: https://docs.mistral.ai/api/endpoint/ocr
- Cookbook – Data Extraction: https://colab.research.google.com/github/mistralai/cookbook/blob/main/mistral/ocr/data_extraction.ipynb
- Cookbook – Batch OCR: https://colab.research.google.com/github/mistralai/cookbook/blob/main/mistral/ocr/batch_ocr.ipynb
- AI Studio Playground: https://console.mistral.ai/build/document-ai/ocr-playground
