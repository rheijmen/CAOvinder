#!/bin/bash
# Run all 4 CAO's through the FIXED Mistral hybrid pipeline

echo "🚀 Starting batch extraction of 4 CAOs with FIXED schema conversion..."
echo ""

# Run all 4 in parallel
python -m cao_engine extract-setu-mistral-hybrid \
  data/raw/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.pdf \
  --cao "Achmea" > /tmp/fixed_achmea.log 2>&1 &
PID1=$!
echo "  [1/4] Achmea started (PID: $PID1)"

python -m cao_engine extract-setu-mistral-hybrid \
  data/raw/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.pdf \
  --cao "IKEA" > /tmp/fixed_ikea.log 2>&1 &
PID2=$!
echo "  [2/4] IKEA started (PID: $PID2)"

python -m cao_engine extract-setu-mistral-hybrid \
  data/raw/1055-rabobank-cao-2024-2025-v01102024.pdf \
  --cao "Rabobank" > /tmp/fixed_rabobank.log 2>&1 &
PID3=$!
echo "  [3/4] Rabobank started (PID: $PID3)"

python -m cao_engine extract-setu-mistral-hybrid \
  data/raw/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.pdf \
  --cao "Metalektro" > /tmp/fixed_metalektro.log 2>&1 &
PID4=$!
echo "  [4/4] Metalektro started (PID: $PID4)"

echo ""
echo "✅ All 4 extractions running in parallel!"
echo "PIDs: $PID1, $PID2, $PID3, $PID4"
echo ""
echo "Monitor progress:"
echo "  tail -f /tmp/fixed_*.log"
echo ""
echo "Wait for completion (approx 2 minutes)..."

# Wait for all to complete
wait $PID1 $PID2 $PID3 $PID4

echo ""
echo "=== EXTRACTION COMPLETE ==="
echo ""
echo "Check results:"
ls -lh data/setu/*.setu.json | grep -E "(achmea|ikea|rabobank|metalektro)" -i | tail -4
echo ""
echo "Run analysis:"
echo "  python analyze_hybrid_results.py"
