"""Analyze the current validation errors in detail."""

import json
from pathlib import Path
from cao_engine.compliance.layer1_fact_extractor import FactExtractor
from cao_engine.compliance.layer2_setu_transformer import SETUTransformer
from cao_engine.compliance.layer3_compliance_validator import ComplianceValidator
from cao_engine.compliance.layer4_remediation_engine import RemediationEngine
from collections import Counter
import os

# Setup
api_key = os.environ["MISTRAL_API_KEY"]
transformer = SETUTransformer()
validator = ComplianceValidator()
remediator = RemediationEngine()

# Load existing facts
facts_path = Path("data/setu_raw/facts/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.facts.json")
with open(facts_path) as f:
    facts = json.load(f)

# Transform and remediate
setu_data = transformer.transform(facts)
initial_validation = validator.validate(setu_data)
remediation_result = remediator.remediate(setu_data, initial_validation)
final_validation = validator.validate(remediation_result.compliant_data)

print("📊 ERROR ANALYSIS")
print(f"\nTotal errors: {final_validation.total_errors}")
print(f"  - Critical: {final_validation.critical_errors}")
print(f"  - Fixable: {final_validation.fixable_errors}")
print(f"  - Semantic: {final_validation.semantic_errors}")

# Group errors by type
errors_by_validator = Counter()
errors_by_path = Counter()

for error in final_validation.errors:
    errors_by_validator[error["validator"]] += 1
    path = error["path"]
    # Get the root path (first part)
    root = path.split("/")[1] if "/" in path else path
    errors_by_path[root] += 1

print("\n🔍 ERRORS BY VALIDATOR:")
for validator_type, count in errors_by_validator.most_common():
    print(f"  {validator_type}: {count}")

print("\n🗂️  ERRORS BY ROOT PATH:")
for path, count in errors_by_path.most_common():
    print(f"  /{path}: {count}")

# Show first 10 actual errors
print("\n📋 FIRST 10 ERRORS:")
for i, error in enumerate(final_validation.errors[:10], 1):
    print(f"\n{i}. {error['validator']} at /{error['path']}")
    print(f"   {error['message']}")
    print(f"   Category: {error['category']}")

# Save detailed error report
output = {
    "total_errors": final_validation.total_errors,
    "errors_by_validator": dict(errors_by_validator),
    "errors_by_path": dict(errors_by_path),
    "all_errors": final_validation.errors
}

report_path = Path("validation_reports/current_errors_detailed.json")
report_path.parent.mkdir(exist_ok=True)
with open(report_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Detailed report saved: {report_path}")
