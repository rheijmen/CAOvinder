"""Quick test of improved transformer with flexible field mapping."""

import json
from pathlib import Path
from cao_engine.compliance.layer1_fact_extractor import FactExtractor
from cao_engine.compliance.layer2_setu_transformer import SETUTransformer
from cao_engine.compliance.layer3_compliance_validator import ComplianceValidator
from cao_engine.compliance.layer4_remediation_engine import RemediationEngine
import os

# Setup
api_key = os.environ["MISTRAL_API_KEY"]
fact_extractor = FactExtractor(api_key)
transformer = SETUTransformer()
validator = ComplianceValidator()
remediator = RemediationEngine()

# Load existing facts (to skip slow extraction)
facts_path = Path("data/setu_raw/facts/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.facts.json")
with open(facts_path) as f:
    facts = json.load(f)

print("🔍 Testing improved transformer...")
print(f"Facts loaded: {len(facts)} top-level keys")
print(f"Has 'salary_information': {'salary_information' in facts}")

if "salary_information" in facts:
    print(f"  - salary_information keys: {list(facts['salary_information'].keys())}")

# Layer 2: Transform to SETU
print("\n📐 Layer 2: Transforming facts to SETU...")
setu_data = transformer.transform(facts)

# Check what remuneration looks like
print(f"\nRemuneration created: {len(setu_data.get('remuneration', []))} entries")
for i, rem in enumerate(setu_data.get('remuneration', [])):
    print(f"  Remuneration {i+1}: {rem.get('name')}")
    if 'salaryScale' in rem:
        print(f"    - Has salaryScale: {len(rem['salaryScale'])} scales")
        for scale in rem['salaryScale']:
            print(f"      - {scale.get('name')}: min={scale.get('minValue')}, max={scale.get('maxValue')}")

# Layer 3: Validate compliance
print("\n✅ Layer 3: Validating compliance...")
initial_validation = validator.validate(setu_data)
print(f"Initial errors: {initial_validation.total_errors}")
print(f"  - Critical: {initial_validation.critical_errors}")
print(f"  - Fixable: {initial_validation.fixable_errors}")
print(f"  - Semantic: {initial_validation.semantic_errors}")

# Layer 4: Remediate issues
print("\n🔧 Layer 4: Applying remediation...")
remediation_result = remediator.remediate(setu_data, initial_validation)
print(f"Fixed errors: {remediation_result.fixed_errors}")
print(f"Remaining errors: {remediation_result.remaining_errors}")
print(f"Fixes applied: {len(remediation_result.fixes_applied)}")

# Final validation
print("\n🎯 Final validation...")
final_validation = validator.validate(remediation_result.compliant_data)
print(f"Final errors: {final_validation.total_errors}")
print(f"  - Critical: {final_validation.critical_errors}")
print(f"  - Fixable: {final_validation.fixable_errors}")
print(f"  - Semantic: {final_validation.semantic_errors}")

# Compare to baseline
baseline = 171
improvement = baseline - final_validation.total_errors
print(f"\n📊 RESULTS:")
print(f"Baseline errors (old approach): {baseline}")
print(f"Current errors (4-layer system): {final_validation.total_errors}")
print(f"Improvement: {improvement} errors fixed ({improvement/baseline*100:.1f}%)")

if final_validation.total_errors < 5:
    print("\n✅ SUCCESS: Met target of <5 errors!")
elif final_validation.total_errors < 10:
    print(f"\n⚠️  CLOSE: {final_validation.total_errors} errors (target <5)")
else:
    print(f"\n❌ NEEDS WORK: {final_validation.total_errors} errors (target <5)")
