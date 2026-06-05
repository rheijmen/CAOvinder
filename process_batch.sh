#!/bin/bash

# Process 4 more small CAO documents
echo "Processing batch of 4 CAO documents..."

# 1. Maja Stuwadoors (82K)
echo "1/4: Processing Maja Stuwadoors..."
python -m cao_engine extract-setu-pipeline \
  data/ocr/1022-maja-stuwadoors-cao-01-01-2022-tm-31-12-2023-v04042023.md \
  --cao "Maja Stuwadoors" || echo "Failed: Maja Stuwadoors"

# 2. Eurotank Amsterdam (102K)
echo "2/4: Processing Eurotank Amsterdam..."
python -m cao_engine extract-setu-pipeline \
  data/ocr/1033-eurotank-amsterdam-cao-01-01-2023-tm-31-12-2024-v07042023.md \
  --cao "Eurotank Amsterdam" || echo "Failed: Eurotank Amsterdam"

# 3. De Volksbank (107K)
echo "3/4: Processing De Volksbank..."
python -m cao_engine extract-setu-pipeline \
  data/ocr/1056-de-volksbank-cao-01-01-2025-31-12-2026-v-15052025.md \
  --cao "De Volksbank" || echo "Failed: De Volksbank"

# 4. Test Tiny (273 bytes - for quick test)
echo "4/4: Processing Test Tiny..."
python -m cao_engine extract-setu-pipeline \
  data/ocr/test_tiny.md \
  --cao "Test Tiny" || echo "Failed: Test Tiny"

echo "Batch processing complete!"
echo "Checking results..."
ls -lh data/setu/*.json | tail -5