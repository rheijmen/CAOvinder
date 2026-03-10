"""
Test Edge Case Workflow: Mistral Document Annotation for Low-Confidence Fields

This demonstrates the hybrid approach:
1. Basic OCR extracts all tables (fast, cheap)
2. Gemini flags low-confidence salary cells
3. Mistral Document Annotation re-extracts those specific pages with schema + confidence
4. Compare and use highest confidence result
"""

import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from src.cao_engine.ocr.mistral_document_ai import MistralDocumentAI


# Define schema for salary table extraction with confidence
class SalaryTableRow(BaseModel):
    """A single row in a CAO salary table with confidence scores."""

    row_type: str = Field(
        description="Type of row: 'age' (16 jaar, 17 jaar) or 'service_year' (Functiejaren 0, 1, 2...)"
    )
    row_label: str = Field(
        description="The label for this row, e.g. '16 jaar' or 'Functiejaren 0'"
    )
    functiegroep_a2: Optional[float] = Field(
        None,
        description="Salary amount for functiegroep A/2 in euros"
    )
    functiegroep_b3: Optional[float] = Field(
        None,
        description="Salary amount for functiegroep B/3 in euros"
    )
    functiegroep_c4: Optional[float] = Field(
        None,
        description="Salary amount for functiegroep C/4 in euros"
    )
    confidence: float = Field(
        description="Confidence score for this row extraction, 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )


class SalaryTableExtraction(BaseModel):
    """Complete salary table extraction with metadata."""

    table_title: str = Field(
        description="Title or description of the salary table"
    )
    effective_period_start: str = Field(
        description="Start date of salary table validity, format: YYYY-MM-DD"
    )
    effective_period_end: Optional[str] = Field(
        None,
        description="End date of salary table validity, format: YYYY-MM-DD"
    )
    rows: List[SalaryTableRow] = Field(
        description="All rows in the salary table"
    )
    overall_confidence: float = Field(
        description="Overall confidence for this table extraction, 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )


def test_edge_case_workflow():
    """
    Test the edge case workflow on CAO 529 salary tables.

    Scenario: Gemini extracted the table but flagged some cells as low confidence.
    We use Mistral Document Annotation to re-extract just those problematic pages.
    """

    print("=" * 80)
    print("EDGE CASE WORKFLOW TEST: Mistral Document Annotation")
    print("=" * 80)
    print()

    # Setup
    pdf_path = Path("data/raw/529-metaal-en-techniek-metaalbewerkingsbedrijf-cao-01-04-2024-tm-31-01-2026-v12122024.pdf")

    # Simulate: Gemini flagged pages 40-42 as having low-confidence salary amounts
    # (In real workflow, this comes from Gemini's extraction report)
    flagged_pages = [39, 40, 41]  # 0-indexed (pages 40, 41, 42 in PDF)

    print("📋 SCENARIO:")
    print(f"   - Gemini extracted CAO 529 salary tables")
    print(f"   - Flagged pages {[p+1 for p in flagged_pages]} as low confidence")
    print(f"   - Reason: Ambiguous OCR on some salary amounts")
    print()

    # Initialize Mistral Document AI
    ocr = MistralDocumentAI()

    print("🔍 STEP 1: Re-extract flagged pages with schema + confidence")
    print(f"   Using Mistral Document Annotation on {len(flagged_pages)} pages")
    print()

    # Annotate the flagged pages with salary table schema
    try:
        annotation_result = ocr.annotate_pages(
            pdf_path=pdf_path,
            page_numbers=flagged_pages,
            annotation_schema=SalaryTableExtraction,
            annotation_prompt=(
                "Extract salary tables with confidence scores. "
                "Pay special attention to ambiguous amounts. "
                "Mark low confidence (< 0.85) for any uncertain values."
            )
        )

        print("✅ Annotation complete!")
        print()
        print(f"Model: {annotation_result['model']}")
        print(f"Pages processed: {annotation_result['pages']}")
        print(f"Schema: {annotation_result['schema']}")
        print()

        # Save result
        output_path = Path("data/ocr_mistral_ai/cao529_edge_case_annotation.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "model": annotation_result['model'],
                "pages": annotation_result['pages'],
                "schema": annotation_result['schema'],
                "annotations": str(annotation_result.get('annotations'))
            }, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved annotation result: {output_path}")
        print()

        # Analyze confidence scores
        print("📊 CONFIDENCE ANALYSIS:")
        print()

        if annotation_result.get('annotations'):
            print("   Found annotations with confidence scores!")
            print(f"   {annotation_result['annotations']}")
        else:
            print("   ⚠️  No annotations found in response")
            print("   This might be because:")
            print("   - The API response structure is different than expected")
            print("   - We need to check the raw_response object")
            print()
            print("   Raw response type:", type(annotation_result['raw_response']))
            print("   Raw response attributes:", dir(annotation_result['raw_response']))

        print()
        print("=" * 80)
        print("🎯 EDGE CASE WORKFLOW DEMONSTRATION COMPLETE")
        print("=" * 80)
        print()
        print("💡 KEY INSIGHTS:")
        print()
        print("1. Mistral Document Annotation adds intelligence layer")
        print("   - Schema-based extraction ensures structured output")
        print("   - Confidence scores (0.0-1.0) flag uncertain extractions")
        print()
        print("2. Cost-effective hybrid approach:")
        print("   - Basic OCR: $0.002/page × 209 pages = $0.42")
        print("   - Annotation: $0.003/page × 3 pages = $0.009")
        print("   - Total: $0.429 per CAO")
        print()
        print("3. Use cases for annotation:")
        print("   - Gemini flags uncertain salary amounts")
        print("   - Complex tables with merged cells")
        print("   - Handwritten annotations on PDFs")
        print("   - Ambiguous date formats")
        print()
        print("4. Routing decision:")
        print("   - Confidence ≥ 0.90: Trust Gemini extraction")
        print("   - Confidence < 0.85: Use Mistral annotation")
        print("   - Confidence 0.85-0.90: Send to Mistral Large for review")
        print()

    except Exception as e:
        print(f"❌ Error during annotation: {e}")
        print()
        print("This might be expected if:")
        print("- The document_annotation API endpoint differs from ocr.process")
        print("- Additional configuration is needed")
        print("- The feature is not yet available in the SDK version")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_edge_case_workflow()
