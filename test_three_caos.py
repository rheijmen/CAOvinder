"""Test improved 4-layer system on 3 different CAOs."""

import json
from pathlib import Path
from cao_engine.compliance.layer1_fact_extractor import FactExtractor
from cao_engine.compliance.layer2_setu_transformer import SETUTransformer
from cao_engine.compliance.layer3_compliance_validator import ComplianceValidator
from cao_engine.compliance.layer4_remediation_engine import RemediationEngine
from datetime import datetime
import os

# Setup
api_key = os.environ["MISTRAL_API_KEY"]
fact_extractor = FactExtractor(api_key)
transformer = SETUTransformer()
validator = ComplianceValidator()
remediator = RemediationEngine()

# Test cases
test_cases = [
    {
        "name": "IKEA",
        "ocr_path": "data/ocr/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.md",
        "cao_name": "IKEA",
        "baseline_errors": 0  # IKEA already had 0 errors
    },
    {
        "name": "Metalektro",
        "ocr_path": "data/ocr/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.md",
        "cao_name": "Metalektro",
        "baseline_errors": None  # Unknown baseline
    },
    {
        "name": "Rabobank",
        "ocr_path": "data/ocr/1055-rabobank-cao-2024-2025-v01102024.md",
        "cao_name": "Rabobank",
        "baseline_errors": None  # Unknown baseline
    }
]

results = []

print("=" * 80)
print("4-LAYER SYSTEM TEST - 3 CAOs")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

for i, test in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST {i}/3: {test['name']} CAO")
    print(f"{'=' * 80}")

    ocr_path = Path(test['ocr_path'])

    # Check if facts already exist
    cao_filename = ocr_path.stem.replace('.md', '')
    facts_path = Path(f"data/setu_raw/facts/{cao_filename}.facts.json")

    start_time = datetime.now()

    # Layer 1: Extract facts (or load existing)
    if facts_path.exists():
        print(f"📂 Loading existing facts from {facts_path.name}")
        with open(facts_path) as f:
            facts = json.load(f)
    else:
        print(f"🔍 Layer 1: Extracting facts from {ocr_path.name}...")
        facts = fact_extractor.extract_from_file(ocr_path, test['cao_name'])
        # Save facts
        facts_path.parent.mkdir(exist_ok=True)
        with open(facts_path, 'w') as f:
            json.dump(facts, f, indent=2)
        print(f"   ✅ Facts saved to {facts_path.name}")

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
    print(f"     - Semantic: {initial_validation.semantic_errors}")

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
    output_path = Path(f"data/setu/{cao_filename}.4layer.setu.json")
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
        "baseline_errors": test['baseline_errors'],
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
    print(f"   Processing time: {duration:.1f}s")
    print(f"   Output saved: {output_path.name}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY - 4-LAYER SYSTEM TEST RESULTS")
print("=" * 80)

total_initial = sum(r['initial_errors'] for r in results)
total_final = sum(r['final_errors'] for r in results)
total_fixed = sum(r['fixed_errors'] for r in results)
avg_compliance = sum(r['compliance_score'] for r in results) / len(results)
avg_auto_repair = sum(r['auto_repair_rate'] for r in results) / len(results)
total_duration = sum(r['duration_seconds'] for r in results)

print(f"\nTotal CAOs tested: {len(results)}")
print(f"Total initial errors: {total_initial}")
print(f"Total final errors: {total_final}")
print(f"Total fixed errors: {total_fixed}")
print(f"Average compliance: {avg_compliance * 100:.1f}%")
print(f"Average auto-repair rate: {avg_auto_repair:.1f}%")
print(f"Total processing time: {total_duration:.1f}s")

print(f"\n{'CAO':<15} {'Initial':<10} {'Final':<10} {'Fixed':<10} {'Compliance':<12} {'Status'}")
print("-" * 80)
for r in results:
    print(f"{r['cao']:<15} {r['initial_errors']:<10} {r['final_errors']:<10} "
          f"{r['fixed_errors']:<10} {r['compliance_score']*100:>10.1f}%  {r['status']}")

# Save detailed results
report_path = Path("validation_reports/three_cao_test_results.json")
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
            "total_duration_seconds": total_duration
        },
        "results": results
    }, f, indent=2)

print(f"\n💾 Detailed report saved: {report_path}")
print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
