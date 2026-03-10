#!/usr/bin/env python3
"""
Quick test: Does Mistral Hybrid Pipeline generate CLEAN SETU files?
Tests the FIXED hybrid_pipeline_mistral.py (without confidence scoring)
"""
import json
import os
from pathlib import Path

from cao_engine.extraction.hybrid_pipeline_mistral import HybridPipelineMistral
from cao_engine.config import get_settings

settings = get_settings()

# Test with Metalektro CAO (small file)
pdf_path = Path("data/raw/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.pdf")
cao_name = "Metalektro-TEST"

print(f"\n{'='*80}")
print(f"TESTING: Mistral Hybrid Pipeline (FIXED - no confidence scoring)")
print(f"PDF: {pdf_path.name}")
print(f"CAO: {cao_name}")
print(f"{'='*80}\n")

# Initialize pipeline
pipeline = HybridPipelineMistral(
    mistral_api_key=settings.mistral_api_key,
    mistral_model="mistral-large-latest"
)

print("✅ Pipeline initialized (hybrid_pipeline_mistral.py)")
print("   - Confidence scorer: REMOVED")
print("   - Exception detector: REMOVED")
print("   - Pipeline steps: 3 (table annotation, full extraction, merge)\n")

# Run extraction
print("Starting extraction...")
result = pipeline.extract(
    pdf_path=pdf_path,
    cao_name=cao_name
)

print(f"\n✅ Extraction complete!")
print(f"   - Elapsed: {result.elapsed_seconds:.1f}s")
print(f"   - Merge notes: {len(result.merge_notes)}")
print(f"   - Exceptions: {len(result.exceptions)} (should be 0 - reserved for future)")
print(f"   - Confidence summary: {len(result.confidence_summary)} (should be 0 - reserved for future)\n")

# Check for non-SETU fields
print("="*80)
print("CLEANLINESS CHECK: Looking for non-SETU fields in output")
print("="*80)

setu_json = json.dumps(result.setu_data, indent=2)

forbidden_fields = [
    "_confidence",
    "_extraction_metadata",
    "_compliance",
    "_hybrid_extraction",
    "_value_confidence",
    "_schemeAgencyId_confidence"
]

violations = []
for field in forbidden_fields:
    count = setu_json.count(f'"{field}"')
    if count > 0:
        violations.append(f"  ❌ Found '{field}' {count} times")

if violations:
    print("\n❌ FAILED: SETU document contains non-SETU fields:")
    for v in violations:
        print(v)
    print("\nThis means the pipeline is STILL adding metadata fields!")
    print("The SETU validator will reject this.\n")
else:
    print("\n✅ SUCCESS: SETU document is CLEAN")
    print("   - No _confidence fields")
    print("   - No _extraction_metadata fields")
    print("   - No _compliance fields")
    print("   - No _hybrid_extraction fields")
    print("\nThis document should pass the official SETU validator!\n")

# Show sample of output
print("="*80)
print("SAMPLE OUTPUT (first 500 chars)")
print("="*80)
print(setu_json[:500] + "...\n")

# Save to file
output_file = settings.setu_dir / f"{pdf_path.stem}-TEST-CLEAN.setu.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result.setu_data, f, indent=2, ensure_ascii=False)

print(f"✅ Saved to: {output_file}")
print(f"\nTo validate against official SETU schema, upload to:")
print(f"   https://validator.setu.nl/\n")
