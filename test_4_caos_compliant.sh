#!/bin/bash
# Test 4 CAOs with SETU v2.0 compliant hybrid extraction pipeline
# Uses updated code with correct schemeAgencyId enum values

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Testing 4 CAOs with SETU v2.0 Compliant Hybrid Pipeline  ║"
echo "║  Updated: schemeAgencyId enums + role→roleCode fix        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Define test CAOs
declare -A CAOS
CAOS[nam]="data/raw/27-nam-de-nederlandse-aardolie-maatschappij-bv-cao-01-01-2025-31-03-2026-v01092025.pdf"
CAOS[metalektro]="data/raw/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.pdf"
CAOS[goederenvervoer]="data/raw/498-beroepsgoederenvervoer-over-de-weg-en-verhuur-van-mobiele-kranen-cao-01-01-2026-tm-31-12-2026-v10022026.pdf"
CAOS[metaal_techniek]="data/raw/527-metaal-en-techniek-goud-en-zilvernijverheid-cao-01-04-2024-tm-31-01-2026-v12122024.pdf"

declare -A NAMES
NAMES[nam]="NAM"
NAMES[metalektro]="Metalektro"
NAMES[goederenvervoer]="Beroepsgoederenvervoer"
NAMES[metaal_techniek]="Metaal en Techniek - Goud en Zilvernijverheid"

# Create logs directory
mkdir -p /tmp/cao_test_logs

# Function to run extraction for one CAO
run_extraction() {
    local key=$1
    local pdf="${CAOS[$key]}"
    local cao_name="${NAMES[$key]}"
    local log_file="/tmp/cao_test_logs/${key}.log"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📄 CAO: $cao_name"
    echo "📁 PDF: $pdf"
    echo "📝 Log: $log_file"
    echo ""

    # Check if command exists
    if ! python -m cao_engine --help | grep -q "extract-setu-mistral-hybrid"; then
        echo "⚠️  WARNING: extract-setu-mistral-hybrid command not found"
        echo "   Skipping $cao_name..."
        echo ""
        return 1
    fi

    # Run extraction
    echo "⏳ Starting extraction..."
    if python -m cao_engine extract-setu-mistral-hybrid "$pdf" --cao "$cao_name" > "$log_file" 2>&1; then
        echo "✅ Extraction completed successfully"
    else
        echo "❌ Extraction failed - check log for details"
        echo ""
        echo "Last 20 lines of log:"
        tail -20 "$log_file" | sed 's/^/   /'
        echo ""
        return 1
    fi

    # Find output file
    local basename=$(basename "$pdf" .pdf)
    local setu_file="data/setu/${basename}.setu.json"

    if [ -f "$setu_file" ]; then
        echo "📦 Output: $setu_file"

        # Check file size
        local size=$(wc -c < "$setu_file")
        echo "📊 Size: $size bytes"

        # Check for critical fields
        if grep -q '"schemeAgencyId": "Customer"' "$setu_file"; then
            echo "✅ documentId.schemeAgencyId = 'Customer'"
        else
            echo "⚠️  documentId.schemeAgencyId not 'Customer'"
        fi

        if grep -q '"schemeAgencyId": "KvK"' "$setu_file"; then
            echo "✅ legalId.schemeAgencyId = 'KvK'"
        else
            echo "⚠️  legalId.schemeAgencyId not 'KvK'"
        fi

        if grep -q '"roleCode"' "$setu_file"; then
            echo "✅ Uses 'roleCode' (not 'role')"
        else
            echo "ℹ️  No roleCode found (might be OK if no contacts)"
        fi

        # Count salary scales
        local scales=$(grep -c '"salaryScale"' "$setu_file" || echo "0")
        echo "📊 Salary scales found: $scales"

    else
        echo "❌ Output file not found: $setu_file"
        return 1
    fi

    echo ""
}

# Run all extractions
success_count=0
total_count=0

for key in nam metalektro goederenvervoer metaal_techniek; do
    total_count=$((total_count + 1))
    if run_extraction "$key"; then
        success_count=$((success_count + 1))
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Successful: $success_count / $total_count"
echo "📁 Logs in: /tmp/cao_test_logs/"
echo "📦 Output in: data/setu/"
echo ""

if [ $success_count -eq $total_count ]; then
    echo "🎉 ALL EXTRACTIONS SUCCESSFUL!"
    echo ""
    echo "Next step: Test with official SETU validator"
    echo "   → https://setu.semantic-treehouse.nl/validator/"
    exit 0
else
    echo "⚠️  Some extractions failed - check logs for details"
    exit 1
fi
