#!/bin/bash
# Test 4 CAOs with SETU v2.0 compliant hybrid extraction pipeline
# Simple version compatible with all bash shells

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Testing 4 CAOs with SETU v2.0 Compliant Hybrid Pipeline  ║"
echo "║  Updated: schemeAgencyId enums + role→roleCode fix        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Create logs directory
mkdir -p /tmp/cao_test_logs

# Function to run one CAO extraction
test_cao() {
    local name="$1"
    local pdf="$2"
    local log="/tmp/cao_test_logs/${name}.log"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📄 CAO: $name"
    echo "📁 PDF: $pdf"
    echo ""

    # Run extraction
    echo "⏳ Starting extraction (this may take 2-5 minutes)..."
    if python -m cao_engine extract-setu-mistral-hybrid "$pdf" --cao "$name" > "$log" 2>&1; then
        echo "✅ Extraction completed"

        # Find output
        local basename=$(basename "$pdf" .pdf)
        local setu="data/setu/${basename}.setu.json"

        if [ -f "$setu" ]; then
            echo "📦 Output: $setu"
            echo "📊 Size: $(wc -c < "$setu") bytes"

            # Check compliance
            grep -q '"schemeAgencyId": "Customer"' "$setu" && echo "✅ documentId.schemeAgencyId = 'Customer'" ||  echo "⚠️  documentId.schemeAgencyId not 'Customer'"
            grep -q '"schemeAgencyId": "KvK"' "$setu" && echo "✅ legalId.schemeAgencyId = 'KvK'" || echo "⚠️  legalId.schemeAgencyId not 'KvK'"
            grep -q '"roleCode"' "$setu" && echo "✅ Uses 'roleCode'" || echo "ℹ️  No roleCode"
            echo "📊 Salary scales: $(grep -c '"salaryScale"' "$setu" || echo "0")"
        else
            echo "❌ Output file not found"
            return 1
        fi
    else
        echo "❌ Extraction failed"
        echo "Last 15 lines of log:"
        tail -15 "$log" | sed 's/^/   /'
        return 1
    fi

    echo ""
}

# Test each CAO
success=0
total=0

# 1. NAM
total=$((total + 1))
test_cao "NAM" "data/raw/27-nam-de-nederlandse-aardolie-maatschappij-bv-cao-01-01-2025-31-03-2026-v01092025.pdf" && success=$((success + 1))

# 2. Metalektro
total=$((total + 1))
test_cao "Metalektro" "data/raw/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.pdf" && success=$((success + 1))

# 3. Beroepsgoederenvervoer
total=$((total + 1))
test_cao "Beroepsgoederenvervoer" "data/raw/498-beroepsgoederenvervoer-over-de-weg-en-verhuur-van-mobiele-kranen-cao-01-01-2026-tm-31-12-2026-v10022026.pdf" && success=$((success + 1))

# 4. Metaal en Techniek
total=$((total + 1))
test_cao "Metaal en Techniek - Goud/Zilver" "data/raw/527-metaal-en-techniek-goud-en-zilvernijverheid-cao-01-04-2024-tm-31-01-2026-v12122024.pdf" && success=$((success + 1))

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Successful: $success / $total"
echo "📁 Logs: /tmp/cao_test_logs/"
echo "📦 Output: data/setu/"
echo ""

if [ $success -eq $total ]; then
    echo "🎉 ALL EXTRACTIONS SUCCESSFUL!"
    echo ""
    echo "Next step: Test outputs with official SETU validator"
    echo "   → https://setu.semantic-treehouse.nl/validator/"
else
    echo "⚠️  Some extractions failed - check logs"
fi
