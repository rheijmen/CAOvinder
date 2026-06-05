"""Test improved 4-layer system on Metalektro CAO."""

import json
from pathlib import Path
from cao_engine.compliance.layer1_fact_extractor import FactExtractor
from cao_engine.compliance.layer2_setu_transformer import SETUTransformer
from cao_engine.compliance.layer3_compliance_validator import ComplianceValidator
from cao_engine.compliance.layer4_remediation_engine import RemediationEngine
from datetime import datetime
import os

print("=" * 80)
print("METALEKTRO CAO - 4-LAYER SYSTEM TEST")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Setup
api_key = os.environ["MISTRAL_API_KEY"]
fact_extractor = FactExtractor(api_key)
transformer = SETUTransformer()
validator = ComplianceValidator()
remediator = RemediationEngine()

# Test case
ocr_path = Path("data/ocr/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.md")
cao_name = "Metalektro"
cao_id = "315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024"

# Check OCR file
if not ocr_path.exists():
    print(f"❌ ERROR: OCR file not found: {ocr_path}")
    exit(1)

# Read OCR file
with open(ocr_path) as f:
    ocr_text = f.read()

print(f"📄 OCR file: {ocr_path.name}")
print(f"   Size: {len(ocr_text):,} characters")

# Check if facts already exist
facts_path = Path(f"data/setu_raw/facts/{cao_id}.facts.json")

start_time = datetime.now()

# Layer 1: Extract facts (or load existing)
if facts_path.exists():
    print(f"\n📂 Loading existing facts from {facts_path.name}")
    with open(facts_path) as f:
        facts = json.load(f)
    print(f"   ✅ Facts loaded: {len(facts)} top-level keys")
else:
    print(f"\n🔍 Layer 1: Extracting facts with Mistral Large...")
    print(f"   This may take 2-3 minutes...")
    facts = fact_extractor.extract_from_file(ocr_path, cao_name)

    # Save facts
    facts_path.parent.mkdir(exist_ok=True)
    with open(facts_path, 'w') as f:
        json.dump(facts, f, indent=2)
    print(f"   ✅ Facts saved: {facts_path.name}")
    print(f"   Facts extracted: {len(facts)} top-level keys")

# Show fact structure
print(f"\n📊 Fact structure:")
for key in facts.keys():
    if isinstance(facts[key], dict):
        print(f"   - {key}: {len(facts[key])} fields")
    elif isinstance(facts[key], list):
        print(f"   - {key}: {len(facts[key])} items")
    else:
        print(f"   - {key}: {type(facts[key]).__name__}")

# Layer 2: Transform to SETU
print(f"\n📐 Layer 2: Transforming facts to SETU...")
setu_data = transformer.transform(facts)
print(f"   ✅ SETU structure created")
print(f"   Root fields: {list(setu_data.keys())}")
print(f"   Remuneration entries: {len(setu_data.get('remuneration', []))}")

# Show remuneration summary
if setu_data.get('remuneration'):
    print(f"\n   Salary scales found:")
    for i, rem in enumerate(setu_data['remuneration'][:5], 1):  # Show first 5
        scale_name = rem.get('salaryScale', [{}])[0].get('name', 'Unknown')
        print(f"   {i}. {scale_name}")
    if len(setu_data['remuneration']) > 5:
        print(f"   ... and {len(setu_data['remuneration']) - 5} more")

# Layer 3: Validate compliance
print(f"\n✅ Layer 3: Validating compliance...")
initial_validation = validator.validate(setu_data)
print(f"   Initial errors: {initial_validation.total_errors}")
print(f"     - Critical: {initial_validation.critical_errors}")
print(f"     - Fixable: {initial_validation.fixable_errors}")
print(f"     - Semantic: {initial_validation.semantic_errors}")

# Show first few errors
if initial_validation.total_errors > 0:
    print(f"\n   First 5 errors:")
    for i, error in enumerate(initial_validation.errors[:5], 1):
        print(f"   {i}. {error['validator']} at /{error['path']}")
        print(f"      {error['message']}")

# Layer 4: Remediate issues
print(f"\n🔧 Layer 4: Applying remediation...")
remediation_result = remediator.remediate(setu_data, initial_validation)
print(f"   Fixed: {remediation_result.fixed_errors} errors")
print(f"   Remaining: {remediation_result.remaining_errors} errors")
print(f"   Auto-repair rate: {remediation_result.success_rate:.1f}%")

if remediation_result.fixes_applied:
    print(f"\n   Fixes applied:")
    for fix in remediation_result.fixes_applied[:5]:  # Show first 5
        print(f"   - {fix}")

# Final validation
print(f"\n🎯 Final validation...")
final_validation = validator.validate(remediation_result.compliant_data)
print(f"   Final errors: {final_validation.total_errors}")
print(f"   Compliance score: {final_validation.compliance_score * 100:.1f}%")

# Show remaining errors if any
if final_validation.total_errors > 0:
    print(f"\n   Remaining errors:")
    for i, error in enumerate(final_validation.errors[:10], 1):
        print(f"   {i}. {error['validator']} at /{error['path']}")
        print(f"      {error['message']}")
        print(f"      Category: {error['category']}")

end_time = datetime.now()
duration = (end_time - start_time).total_seconds()

# Save compliant data
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

print(f"\n{'=' * 80}")
print(f"RESULT: {emoji} {status}")
print(f"{'=' * 80}")
print(f"Final errors: {final_validation.total_errors}")
print(f"Compliance: {final_validation.compliance_score * 100:.1f}%")
print(f"Auto-repair: {remediation_result.success_rate:.1f}%")
print(f"Processing time: {duration:.1f}s")
print(f"Output: {output_path.name}")

# Save test report
report = {
    "cao": cao_name,
    "cao_id": cao_id,
    "test_date": datetime.now().isoformat(),
    "duration_seconds": duration,
    "fact_keys": list(facts.keys()),
    "remuneration_count": len(setu_data.get('remuneration', [])),
    "initial_errors": initial_validation.total_errors,
    "final_errors": final_validation.total_errors,
    "fixed_errors": remediation_result.fixed_errors,
    "compliance_score": final_validation.compliance_score,
    "auto_repair_rate": remediation_result.success_rate,
    "status": status,
    "output_file": str(output_path)
}

report_path = Path("validation_reports/metalektro_test_report.json")
report_path.parent.mkdir(exist_ok=True)
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n💾 Test report saved: {report_path}")
print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
