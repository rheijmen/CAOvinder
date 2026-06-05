"""Fix Achmea holidayAllowance and pension to proper SETU v2.0 structure"""
import json

with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1004-achmea-FINAL-VALID.setu.json', 'r') as f:
    data = json.load(f)

# Fix holidayAllowance - must have proper structure
if "holidayAllowance" in data and isinstance(data["holidayAllowance"], list):
    fixed_holiday = []
    for item in data["holidayAllowance"]:
        # REQUIRED: origin
        # OPTIONAL: id, name, effectivePeriod, line, payDate
        # NOT ALLOWED: percentage, description (custom fields)

        clean = {
            "origin": item.get("origin", {"type": "CollectiveLabourAgreement"})
        }

        # Add optional fields if they exist and are valid
        if "name" in item:
            clean["name"] = item["name"]
        elif "description" in item:
            # Use description as name if no name field
            clean["name"] = item["description"]

        if "effectivePeriod" in item:
            clean["effectivePeriod"] = item["effectivePeriod"]

        if "line" in item:
            clean["line"] = item["line"]

        if "payDate" in item:
            clean["payDate"] = item["payDate"]

        fixed_holiday.append(clean)

    data["holidayAllowance"] = fixed_holiday

# Fix pension - must have proper structure
if "pension" in data and isinstance(data["pension"], list):
    fixed_pension = []
    for item in data["pension"]:
        # REQUIRED: origin (only field required!)
        # OPTIONAL: effectivePeriod, line, franchise
        # NOT ALLOWED: employerContributionPercentage, pensionFundName, employeeContributionPercentage, description

        clean = {
            "origin": item.get("origin", {"type": "CollectiveLabourAgreement"})
        }

        # Add optional fields if valid
        if "effectivePeriod" in item:
            clean["effectivePeriod"] = item["effectivePeriod"]

        if "line" in item:
            clean["line"] = item["line"]

        if "franchise" in item:
            clean["franchise"] = item["franchise"]

        fixed_pension.append(clean)

    data["pension"] = fixed_pension

with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1004-achmea-FINAL-VALID-v2.setu.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Fixed Achmea arrays - saved to 1004-achmea-FINAL-VALID-v2.setu.json")
print("   - holidayAllowance: added required 'origin' field")
print("   - pension: added required 'origin' field, removed custom fields")
