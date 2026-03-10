"""Fix final Achmea validation issues"""
import json

with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.setu-VALID.setu.json', 'r') as f:
    data = json.load(f)

# Fix baseDefinition - remove additional properties
if "baseDefinition" in data:
    for base in data["baseDefinition"]:
        # Only keep the 5 allowed fields
        allowed = ["baseType", "remunerationIndicator", "holidayAllowanceIndicator",
                   "paidLeaveDayIndicator", "allAllowancesIndicator"]
        keys_to_remove = [k for k in base.keys() if k not in allowed]
        for k in keys_to_remove:
            del base[k]

# Fix holidayAllowance - must be array, not object
if "holidayAllowance" in data and isinstance(data["holidayAllowance"], dict):
    # Convert to array with single item
    data["holidayAllowance"] = [data["holidayAllowance"]]

# Fix pension - must be array, not object
if "pension" in data and isinstance(data["pension"], dict):
    # Convert to array with single item
    data["pension"] = [data["pension"]]

with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1004-achmea-FINAL-VALID.setu.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Fixed Achmea CAO - saved to 1004-achmea-FINAL-VALID.setu.json")
