"""Test improved 4-layer system on Metalektro CAO using existing Gemini extraction."""

import json
from pathlib import Path
from cao_engine.compliance.layer2_setu_transformer import SETUTransformer
from cao_engine.compliance.layer3_compliance_validator import ComplianceValidator
from cao_engine.compliance.layer4_remediation_engine import RemediationEngine
from datetime import datetime

print("=" * 80)
print("METALEKTRO CAO - 4-LAYER SYSTEM TEST")
print("=" * 80)

# Use existing Gemini extraction as facts
gemini_path = Path("data/setu_raw/gemini/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini.json")

print(f"📂 Using existing Gemini extraction: {gemini_path.name}\n")

with open(gemini_path) as f:
    facts = json.load(f)

print(f"Facts loaded: {len(facts)} top-level keys")
print(f"Keys: {list(facts.keys())}\n")

# Setup
transformer = SETUTransformer()
validator = ComplianceValidator()
remediator = RemediationEngine()

start_time = datetime.now()

# Layer 2: Transform
print("📐 Layer 2: Transforming to SETU...")
setu_data = transformer.transform(facts)
print(f"✅ SETU created: {len(setu_data)} root fields")
print(f"Remuneration entries: {len(setu_data.get('remuneration', []))}\n")

# Layer 3: Validate
print("✅ Layer 3: Validating...")
initial_validation = validator.validate(setu_data)
print(f"Initial errors: {initial_validation.total_errors}")
print(f"  Critical: {initial_validation.critical_errors}")
print(f"  Fixable: {initial_validation.fixable_errors}\n")

# Layer 4: Remediate
print("🔧 Layer 4: Remediating...")
remediation_result = remediator.remediate(setu_data, initial_validation)
print(f"Fixed: {remediation_result.fixed_errors}")
print(f"Remaining: {remediation_result.remaining_errors}")
print(f"Auto-repair: {remediation_result.success_rate:.1f}%\n")

# Final validation
final_validation = validator.validate(remediation_result.compliant_data)
print(f"🎯 Final: {final_validation.total_errors} errors, {final_validation.compliance_score*100:.1f}% compliant\n")

# Status
if final_validation.total_errors == 0:
    print("🎉 ✅ PERFECT - Zero errors!")
elif final_validation.total_errors < 5:
    print(f"🎯 ✅ SUCCESS - {final_validation.total_errors} errors (target <5)")
else:
    print(f"⚠️  {final_validation.total_errors} errors (target <5)")

# Save
output_path = Path("data/setu/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.4layer.setu.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(remediation_result.compliant_data, f, indent=2)

print(f"\n💾 Output: {output_path.name}")
print(f"⏱️  Time: {(datetime.now() - start_time).total_seconds():.1f}s")
