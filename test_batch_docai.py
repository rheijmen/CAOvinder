"""
Batch test Mistral Document AI on 4 CAOs.

Tests:
1. CAO 1004 - Achmea (0 errors baseline)
2. CAO 315 - Metalektro (1 error baseline)
3. CAO 1049 - IKEA
4. CAO 1055 - Rabobank
"""

import json
from pathlib import Path
from typing import Dict, List
from src.cao_engine.ocr.mistral_document_ai import MistralDocumentAI
import time


def process_cao(pdf_path: Path, cao_name: str) -> Dict:
    """Process a single CAO with Mistral Document AI."""

    print(f"\n{'='*80}")
    print(f"Processing: {cao_name}")
    print(f"PDF: {pdf_path.name}")
    print(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"{'='*80}\n")

    ocr = MistralDocumentAI()

    start_time = time.time()

    try:
        result = ocr.process_pdf(
            pdf_path=pdf_path,
            table_format="html",
            extract_header=True,
            extract_footer=True,
            include_image_base64=False
        )

        elapsed = time.time() - start_time

        # Save outputs
        output_dir = Path("data/ocr_mistral_ai")
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = pdf_path.stem
        json_output = output_dir / f"{base_name}.docai.json"
        md_output = output_dir / f"{base_name}.docai.md"
        tables_output = output_dir / f"{base_name}.tables.json"

        ocr.save_extraction(result, json_output, include_images=False)
        ocr.save_markdown(result, md_output)

        # Save tables separately
        tables_data = []
        for page in result.pages:
            for table in page.tables:
                tables_data.append({
                    "page": page.index + 1,
                    "table_id": table.id,
                    "format": table.format,
                    "content": table.content
                })

        with open(tables_output, 'w', encoding='utf-8') as f:
            json.dump(tables_data, f, indent=2, ensure_ascii=False)

        print(f"✅ SUCCESS: {cao_name}")
        print(f"   Time: {elapsed:.1f}s")
        print(f"   Pages: {result.total_pages}")
        print(f"   Tables: {result.total_tables}")
        print(f"   Images: {result.total_images}")
        print(f"   Hyperlinks: {result.total_hyperlinks}")
        print(f"   Output: {json_output.name}")

        return {
            "cao": cao_name,
            "pdf": pdf_path.name,
            "status": "success",
            "elapsed": elapsed,
            "pages": result.total_pages,
            "tables": result.total_tables,
            "images": result.total_images,
            "hyperlinks": result.total_hyperlinks,
            "json_size_kb": json_output.stat().st_size / 1024,
            "md_size_kb": md_output.stat().st_size / 1024,
            "tables_size_kb": tables_output.stat().st_size / 1024
        }

    except Exception as e:
        print(f"❌ FAILED: {cao_name}")
        print(f"   Error: {e}")

        return {
            "cao": cao_name,
            "pdf": pdf_path.name,
            "status": "failed",
            "error": str(e)
        }


def main():
    """Process 4 CAOs in batch."""

    print("="*80)
    print("BATCH MISTRAL DOCUMENT AI TEST - 4 CAOS")
    print("="*80)

    # Define CAOs to test
    caos = [
        {
            "name": "Achmea",
            "pdf": "data/raw/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.pdf",
            "baseline": "0 errors"
        },
        {
            "name": "Metalektro",
            "pdf": "data/raw/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.pdf",
            "baseline": "1 error"
        },
        {
            "name": "IKEA",
            "pdf": "data/raw/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.pdf",
            "baseline": "unknown"
        },
        {
            "name": "Rabobank",
            "pdf": "data/raw/1055-rabobank-cao-2024-2025-v01102024.pdf",
            "baseline": "unknown"
        }
    ]

    results: List[Dict] = []

    for cao in caos:
        pdf_path = Path(cao["pdf"])

        if not pdf_path.exists():
            print(f"\n⚠️  SKIP: {cao['name']} - PDF not found: {pdf_path}")
            results.append({
                "cao": cao["name"],
                "status": "skipped",
                "reason": "PDF not found"
            })
            continue

        result = process_cao(pdf_path, cao["name"])
        result["baseline"] = cao["baseline"]
        results.append(result)

        # Small delay between CAOs
        time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("BATCH PROCESSING COMPLETE")
    print("="*80)
    print()

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")

    print(f"📊 SUMMARY:")
    print(f"   Total: {len(results)}")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print()

    if success_count > 0:
        print("📈 STATISTICS:")
        print()

        total_pages = sum(r.get("pages", 0) for r in results if r["status"] == "success")
        total_tables = sum(r.get("tables", 0) for r in results if r["status"] == "success")
        total_time = sum(r.get("elapsed", 0) for r in results if r["status"] == "success")

        print(f"   Total pages: {total_pages}")
        print(f"   Total tables: {total_tables}")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   Avg time per CAO: {total_time / success_count:.1f}s")
        print(f"   Avg pages per CAO: {total_pages / success_count:.0f}")
        print(f"   Avg tables per CAO: {total_tables / success_count:.0f}")
        print()

        print("📋 DETAILED RESULTS:")
        print()

        for result in results:
            if result["status"] == "success":
                print(f"   {result['cao']}:")
                print(f"      Pages: {result['pages']}")
                print(f"      Tables: {result['tables']}")
                print(f"      Time: {result['elapsed']:.1f}s")
                print(f"      Baseline: {result['baseline']}")
                print()

    # Save results
    results_path = Path("data/ocr_mistral_ai/batch_results.json")
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved: {results_path}")
    print()
    print("="*80)
    print("✅ NEXT STEP: Compare OCR quality with old approach")
    print("="*80)


if __name__ == "__main__":
    main()
