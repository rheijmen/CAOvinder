"""
Test SETU extraction using Mistral Document AI structured output.

This test combines markdown + HTML tables to create optimized input for Gemini.
"""

import json
from pathlib import Path

def combine_markdown_and_tables(docai_json_path: Path, docai_md_path: Path) -> str:
    """
    Combine Mistral Document AI markdown + HTML tables into LLM-optimized format.

    Strategy:
    1. Use markdown for main text flow
    2. Insert HTML tables at appropriate pages
    3. Keep headers/footers for context
    4. Result: Best of both worlds for LLM parsing
    """

    # Load JSON with tables
    with open(docai_json_path) as f:
        data = json.load(f)

    # Load markdown
    with open(docai_md_path) as f:
        markdown = f.read()

    # Build combined output
    combined_parts = []
    combined_parts.append("# CAO Document (Mistral Document AI Extraction)\n\n")
    combined_parts.append(f"**Model:** {data['model']}\n")
    combined_parts.append(f"**Pages:** {data['total_pages']}\n")
    combined_parts.append(f"**Tables:** {data['total_tables']}\n")
    combined_parts.append(f"**Hyperlinks:** {data['total_hyperlinks']}\n\n")
    combined_parts.append("---\n\n")

    # For each page with tables, insert table HTML
    pages_with_tables = {
        page['index']: page for page in data['pages']
        if page.get('tables')
    }

    if pages_with_tables:
        combined_parts.append("## SALARY TABLES (HTML Format for Accurate Extraction)\n\n")
        combined_parts.append("**IMPORTANT:** The following tables are in HTML format with proper structure. ")
        combined_parts.append("Use `<th>` tags for column headers and `<td>` tags for cell values.\n\n")

        for page_idx, page in pages_with_tables.items():
            combined_parts.append(f"### Page {page_idx + 1}\n\n")

            if page.get('header'):
                combined_parts.append(f"**Header:** {page['header']}\n\n")

            for table in page['tables']:
                combined_parts.append(f"**Table {table['id']}** (Format: {table['format']})\n\n")
                combined_parts.append(table['content'])
                combined_parts.append("\n\n")

            if page.get('footer'):
                combined_parts.append(f"**Footer:** {page['footer']}\n\n")

            combined_parts.append("---\n\n")

    # Add full markdown at the end for context
    combined_parts.append("## FULL TEXT CONTENT\n\n")
    combined_parts.append(markdown)

    return ''.join(combined_parts)


def main():
    """Test combining document AI output for SETU extraction."""

    # Paths
    docai_json = Path("data/ocr_mistral_ai/529-metaal-en-techniek-metaalbewerkingsbedrijf-cao-01-04-2024-tm-31-01-2026-v12122024.docai.json")
    docai_md = Path("data/ocr_mistral_ai/529-metaal-en-techniek-metaalbewerkingsbedrijf-cao-01-04-2024-tm-31-01-2026-v12122024.docai.md")
    output_path = Path("data/ocr_mistral_ai/529-metaal-en-techniek-metaalbewerkingsbedrijf-cao-01-04-2024-tm-31-01-2026-v12122024.combined.md")

    print("=" * 80)
    print("COMBINING MISTRAL DOCUMENT AI OUTPUT FOR SETU EXTRACTION")
    print("=" * 80)
    print()
    print(f"Input JSON:  {docai_json.name}")
    print(f"Input MD:    {docai_md.name}")
    print(f"Output:      {output_path.name}")
    print()

    # Combine
    combined = combine_markdown_and_tables(docai_json, docai_md)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined, encoding='utf-8')

    print(f"✅ Combined output saved: {output_path}")
    print(f"   Size: {len(combined):,} characters")
    print()

    # Show preview
    lines = combined.split('\n')
    print("📖 PREVIEW (first 50 lines):")
    print()
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3}: {line}")

    print()
    print("=" * 80)
    print("✅ READY FOR SETU EXTRACTION!")
    print("=" * 80)
    print()
    print("Next step: Run 3-LLM pipeline:")
    print()
    print(f"  python -m cao_engine extract-setu-pipeline \\")
    print(f"    {output_path} \\")
    print(f"    --cao 'CAO Metaal en Techniek'")
    print()


if __name__ == "__main__":
    main()
