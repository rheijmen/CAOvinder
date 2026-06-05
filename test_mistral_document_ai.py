"""
Test Mistral Document AI on CAO 529
====================================
Compare new OCR approach vs old approach.
"""

from pathlib import Path
from cao_engine.ocr.mistral_document_ai import MistralDocumentAI
import json

print("=" * 80)
print("MISTRAL DOCUMENT AI - CAO 529 TEST")
print("=" * 80)

# Setup
pdf_path = Path("data/raw/529-metaal-en-techniek-metaalbewerkingsbedrijf-cao-01-04-2024-tm-31-01-2026-v12122024.pdf")
output_dir = Path("data/ocr_mistral_ai")
output_dir.mkdir(exist_ok=True)

print(f"\nPDF: {pdf_path.name}")
print(f"Size: {round(pdf_path.stat().st_size / 1024 / 1024, 2)} MB")

# Initialize Mistral Document AI
print("\n🚀 Initializing Mistral Document AI...")
ocr = MistralDocumentAI()

# Process PDF
print("\n📄 Processing PDF with Mistral OCR API...")
print("   This will extract:")
print("   - Text with structure (headers, paragraphs, lists)")
print("   - Tables in HTML format (critical for salary scales!)")
print("   - Images with bounding boxes")
print("   - Hyperlinks")
print("   - Headers and footers separately")
print()

result = ocr.process_pdf(
    pdf_path=pdf_path,
    table_format="html",  # Use HTML for best table structure
    extract_header=True,
    extract_footer=True,
    include_image_base64=False  # Don't need images for now
)

# Display results
print("\n✅ EXTRACTION COMPLETE!")
print("=" * 80)
print(f"Model: {result.model}")
print(f"Total pages: {result.total_pages}")
print(f"Total tables: {result.total_tables} 📊")
print(f"Total images: {result.total_images} 🖼️")
print(f"Total hyperlinks: {result.total_hyperlinks} 🔗")

# Show first page preview
if result.pages:
    page = result.pages[0]
    print(f"\n📖 FIRST PAGE PREVIEW:")
    print(f"   Header: {page.header[:100] if page.header else 'None'}...")
    print(f"   Content preview: {page.markdown[:200]}...")
    print(f"   Footer: {page.footer[:100] if page.footer else 'None'}...")
    print(f"   Tables on this page: {len(page.tables)}")
    print(f"   Images on this page: {len(page.images)}")

# Show table extraction quality
if result.total_tables > 0:
    print(f"\n📊 TABLE EXTRACTION QUALITY:")
    table_count = 0
    for page in result.pages:
        for table in page.tables:
            table_count += 1
            print(f"\n   Table {table_count} (Page {page.index + 1}, ID: {table.id}):")
            print(f"   Format: {table.format}")
            # Show first 300 chars of table HTML
            preview = table.content[:300] if len(table.content) > 300 else table.content
            print(f"   Content preview:\n   {preview}...")
            if table_count >= 3:  # Show max 3 tables
                break
        if table_count >= 3:
            break

# Save outputs
print(f"\n💾 SAVING OUTPUTS...")

# Save full JSON
json_output = output_dir / f"{pdf_path.stem}.docai.json"
ocr.save_extraction(result, json_output, include_images=False)
print(f"   ✅ JSON saved: {json_output.name} ({round(json_output.stat().st_size / 1024, 2)} KB)")

# Save markdown
md_output = output_dir / f"{pdf_path.stem}.docai.md"
ocr.save_markdown(result, md_output)
print(f"   ✅ Markdown saved: {md_output.name} ({round(md_output.stat().st_size / 1024, 2)} KB)")

# Save tables separately for analysis
if result.total_tables > 0:
    tables_output = output_dir / f"{pdf_path.stem}.tables.json"
    tables_data = []
    for page in result.pages:
        for table in page.tables:
            tables_data.append({
                "page": page.index + 1,
                "table_id": table.id,
                "format": table.format,
                "content": table.content
            })

    with open(tables_output, 'w') as f:
        json.dump(tables_data, f, indent=2)
    print(f"   ✅ Tables saved: {tables_output.name} ({round(tables_output.stat().st_size / 1024, 2)} KB)")

# Compare with old OCR
old_ocr_path = Path(f"data/ocr/{pdf_path.stem}.md")
if old_ocr_path.exists():
    print(f"\n📊 COMPARISON WITH OLD OCR:")
    old_size = old_ocr_path.stat().st_size
    new_size = md_output.stat().st_size
    print(f"   Old OCR markdown: {round(old_size / 1024, 2)} KB")
    print(f"   New OCR markdown: {round(new_size / 1024, 2)} KB")
    print(f"   Size difference: {round((new_size - old_size) / 1024, 2)} KB")

    # Count tables in old OCR (rough estimate)
    with open(old_ocr_path) as f:
        old_content = f.read()
        old_table_markers = old_content.count("|")  # Rough estimate

    print(f"\n   Old OCR table markers (|): {old_table_markers}")
    print(f"   New OCR structured tables: {result.total_tables}")
    print(f"   Improvement: Structured HTML tables instead of markdown")
else:
    print(f"\n⚠️  Old OCR not found at: {old_ocr_path}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
print(f"\nNext step: Compare table extraction quality in:")
print(f"  - {tables_output.name}")
print(f"  - vs old OCR markdown tables")
print(f"\nThen run 4-layer SETU compliance test with new OCR output.")
