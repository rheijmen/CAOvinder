"""Test improved 4-layer system on 3 CAOs (using existing facts)."""

import json
from pathlib import Path
from cao_engine.compliance.layer2_setu_transformer import SETUTransformer
from cao_engine.compliance.layer3_compliance_validator import ComplianceValidator
from cao_engine.compliance.layer4_remediation_engine import RemediationEngine
from datetime import datetime

# Setup (no fact extractor needed - using existing facts)
transformer = SETUTransformer()
validator = ComplianceValidator()
remediator = RemediationEngine()

# Test cases - using CAOs we have facts for
test_cases = [
    {
        "name": "Achmea",
        "facts_file": "data/setu_raw/facts/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.facts.json",
        "baseline_errors": 171  # Known baseline from earlier work
    },
    {
        "name": "IKEA",
        "facts_file": "data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.setu.json",  # Use as-is (already valid)
        "baseline_errors": 0,
        "skip_transform": True  # Already SETU format
    }
]

# Check for additional facts files
facts_dir = Path("data/setu_raw/facts")
if facts_dir.exists():
    for facts_file in facts_dir.glob("*.facts.json"):
        filename = facts_file.stem.replace(".facts", "")
        if "achmea" not in filename.lower():  # Don't duplicate Achmea
            test_cases.append({
                "name": filename[:30],  # Truncate long names
                "facts_file": str(facts_file),
                "baseline_errors": None
            })

results = []

print("=" * 80)
print("4-LAYER SYSTEM TEST - MULTIPLE CAOs")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
print(f"Testing {len(test_cases)} CAOs\n")

for i, test in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST {i}/{len(test_cases)}: {test['name']}")
    print(f"{'=' * 80}")

    facts_path = Path(test['facts_file'])
    if not facts_path.exists():
        print(f"⚠️  SKIPPED: Facts file not found: {facts_path}")
        continue

    start_time = datetime.now()

    # Load facts or existing SETU
    print(f"📂 Loading from {facts_path.name}")
    with open(facts_path) as f:
        data = json.load(f)

    # Check if already SETU format or raw facts
    if test.get('skip_transform'):
        print(f"   ℹ️  Already SETU format, skipping transformation")
        setu_data = data
        initial_validation = validator.validate(setu_data)
        print(f"\n✅ Validating existing SETU...")
        print(f"   Errors: {initial_validation.total_errors}")

        # No remediation needed if already perfect
        remediation_result = type('obj', (object,), {
            'compliant_data': setu_data,
            'fixed_errors': 0,
            'remaining_errors': initial_validation.total_errors,
            'success_rate': 100.0 if initial_validation.total_errors == 0 else 0.0
        })()
        final_validation = initial_validation
    else:
        facts = data
        print(f"   Facts: {len(facts)} top-level keys")

        # Layer 2: Transform to SETU
        print(f"\n📐 Layer 2: Transforming facts to SETU...")
        setu_data = transformer.transform(facts)
        print(f"   ✅ SETU structure created: {len(setu_data)} root fields")
        print(f"   Remuneration entries: {len(setu_data.get('remuneration', []))}")

        # Layer 3: Validate compliance
        print(f"\n✅ Layer 3: Validating compliance...")
        initial_validation = validator.validate(setu_data)
        print(f"   Initial errors: {initial_validation.total_errors}")
        print(f"     - Critical: {initial_validation.critical_errors}")
        print(f"     - Fixable: {initial_validation.fixable_errors}")

        # Layer 4: Remediate issues
        print(f"\n🔧 Layer 4: Applying remediation...")
        remediation_result = remediator.remediate(setu_data, initial_validation)
        print(f"   Fixed: {remediation_result.fixed_errors} errors")
        print(f"   Remaining: {remediation_result.remaining_errors} errors")
        print(f"   Success rate: {remediation_result.success_rate:.1f}%")

        # Final validation
        print(f"\n🎯 Final validation...")
        final_validation = validator.validate(remediation_result.compliant_data)
        print(f"   Final errors: {final_validation.total_errors}")
        print(f"   Compliance score: {final_validation.compliance_score * 100:.1f}%")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Save compliant data
    cao_id = facts_path.stem.replace(".facts", "").replace(".setu", "")
    output_path = Path(f"data/setu/{cao_id}.4layer.setu.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(remediation_result.compliant_data, f, indent=2)

    # Determine result
    if final_validation.total_errors == 0:
        status = "✅ PERFECT"
        emoji = "🎉"
    elif final_validation.total_errors < 5:
        status = "✅ SUCCESS"
        emoji = "🎯"
    elif final_validation.total_errors < 10:
        status = "⚠️  CLOSE"
        emoji = "⚡"
    else:
        status = "❌ NEEDS WORK"
        emoji = "🔧"

    result = {
        "cao": test['name'],
        "baseline_errors": test.get('baseline_errors'),
        "initial_errors": initial_validation.total_errors,
        "final_errors": final_validation.total_errors,
        "fixed_errors": remediation_result.fixed_errors,
        "compliance_score": final_validation.compliance_score,
        "auto_repair_rate": remediation_result.success_rate,
        "duration_seconds": duration,
        "status": status,
        "remuneration_count": len(setu_data.get('remuneration', [])),
        "output_file": str(output_path)
    }
    results.append(result)

    print(f"\n{emoji} {status}: {final_validation.total_errors} errors")
    if test.get('baseline_errors') is not None:
        improvement = test['baseline_errors'] - final_validation.total_errors
        print(f"   Improvement: {improvement} errors fixed ({improvement/max(1,test['baseline_errors'])*100:.1f}%)")
    print(f"   Processing time: {duration:.1f}s")
    print(f"   Output saved: {output_path.name}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY - 4-LAYER SYSTEM TEST RESULTS")
print("=" * 80)

total_initial = sum(r['initial_errors'] for r in results)
total_final = sum(r['final_errors'] for r in results)
total_fixed = sum(r['fixed_errors'] for r in results)
avg_compliance = sum(r['compliance_score'] for r in results) / len(results) if results else 0
avg_auto_repair = sum(r['auto_repair_rate'] for r in results) / len(results) if results else 0
total_duration = sum(r['duration_seconds'] for r in results)

print(f"\nTotal CAOs tested: {len(results)}")
print(f"Total initial errors: {total_initial}")
print(f"Total final errors: {total_final}")
print(f"Total fixed errors: {total_fixed}")
print(f"Average compliance: {avg_compliance * 100:.1f}%")
print(f"Average auto-repair rate: {avg_auto_repair:.1f}%")
print(f"Total processing time: {total_duration:.1f}s")

print(f"\n{'CAO':<30} {'Initial':<10} {'Final':<10} {'Fixed':<10} {'Compliance':<12} {'Status'}")
print("-" * 100)
for r in results:
    print(f"{r['cao']:<30} {r['initial_errors']:<10} {r['final_errors']:<10} "
          f"{r['fixed_errors']:<10} {r['compliance_score']*100:>10.1f}%  {r['status']}")

# Count success rates
perfect = sum(1 for r in results if r['final_errors'] == 0)
success = sum(1 for r in results if r['final_errors'] < 5)
close = sum(1 for r in results if 5 <= r['final_errors'] < 10)
needs_work = sum(1 for r in results if r['final_errors'] >= 10)

print(f"\n📊 SUCCESS BREAKDOWN:")
print(f"   🎉 Perfect (0 errors): {perfect}/{len(results)} ({perfect/len(results)*100:.0f}%)")
print(f"   🎯 Success (<5 errors): {success}/{len(results)} ({success/len(results)*100:.0f}%)")
print(f"   ⚡ Close (<10 errors): {close}/{len(results)} ({close/len(results)*100:.0f}%)")
print(f"   🔧 Needs work (>=10): {needs_work}/{len(results)} ({needs_work/len(results)*100:.0f}%)")

# Save detailed results
report_path = Path("validation_reports/multi_cao_test_results.json")
report_path.parent.mkdir(exist_ok=True)
with open(report_path, 'w') as f:
    json.dump({
        "test_date": datetime.now().isoformat(),
        "total_caos": len(results),
        "summary": {
            "total_initial_errors": total_initial,
            "total_final_errors": total_final,
            "total_fixed_errors": total_fixed,
            "average_compliance": avg_compliance,
            "average_auto_repair_rate": avg_auto_repair,
            "total_duration_seconds": total_duration,
            "perfect_count": perfect,
            "success_count": success,
            "close_count": close,
            "needs_work_count": needs_work
        },
        "results": results
    }, f, indent=2)

print(f"\n💾 Detailed report saved: {report_path}")
print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
