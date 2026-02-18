#!/usr/bin/env python3
"""Batch OCR processing for 10 CAO files."""

import sys
import time
from pathlib import Path
from datetime import datetime

# List of 10 CAO PDFs to process
cao_files = [
    "1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.pdf",
    # Skip 1006 - already processed
    "1014-rotterdam-shortsea-terminals-rst-cao-1-1-2022-tm-31-12-2025-v03062024.pdf",
    "1021-nederlandse-spoorwegen-cao-01-01-2024-tm-28-02-2025-v02022026.pdf",
    "1022-maja-stuwadoors-cao-01-01-2022-tm-31-12-2023-v04042023.pdf",
    "1033-eurotank-amsterdam-cao-01-01-2023-tm-31-12-2024-v07042023.pdf",
    "1036-ing-bank-cao-01-01-2025-tm-31-12-2026-v17112025.pdf",
    "1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.pdf",
    "1055-rabobank-cao-2024-2025-v01102024.pdf",
    "1056-de-volksbank-cao-01-01-2025-31-12-2026-v-15052025.pdf",
    "1063-lidl-cao-01-01-2024-tm-31-12-2025-v01032024.pdf",  # Extra one
]

def process_batch():
    """Process CAO files in batch."""
    data_dir = Path("data/raw")
    ocr_dir = Path("data/ocr")

    print(f"Starting batch OCR processing at {datetime.now()}")
    print(f"Processing {len(cao_files)} CAO files")
    print("=" * 80)

    successful = []
    failed = []

    for i, filename in enumerate(cao_files, 1):
        pdf_path = data_dir / filename

        # Check if already processed
        output_md = ocr_dir / f"{pdf_path.stem}.md"
        if output_md.exists():
            print(f"[{i}/{len(cao_files)}] ⏭️  SKIPPED: {filename} (already processed)")
            continue

        if not pdf_path.exists():
            print(f"[{i}/{len(cao_files)}] ❌ NOT FOUND: {filename}")
            failed.append(filename)
            continue

        print(f"[{i}/{len(cao_files)}] 🔄 Processing: {filename}")
        start_time = time.time()

        # Run OCR using subprocess
        import subprocess
        try:
            result = subprocess.run(
                ["python", "-m", "cao_engine", "process-single", str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout per file
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                print(f"    ✅ Success in {elapsed:.1f}s")
                successful.append(filename)
            else:
                print(f"    ❌ Failed: {result.stderr[:200]}")
                failed.append(filename)

        except subprocess.TimeoutExpired:
            print(f"    ⏱️  Timeout after 60s")
            failed.append(filename)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            failed.append(filename)

        # Small delay between files to avoid rate limiting
        time.sleep(2)

    print("\n" + "=" * 80)
    print(f"Batch processing complete at {datetime.now()}")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")

    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  - {f}")

    return len(successful), len(failed)

if __name__ == "__main__":
    successes, failures = process_batch()
    sys.exit(0 if failures == 0 else 1)