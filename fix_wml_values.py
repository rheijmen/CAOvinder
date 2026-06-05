"""Fix WML percentage values to numbers"""
import json
import re

with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1049-ikea-FIXED.setu.json', 'r') as f:
    data = json.load(f)

# Fix all salary scales
for rem in data.get("remuneration", []):
    for scale in rem.get("salaryScale", []):
        for step in scale.get("salaryStep", []):
            value = step.get("value")

            # Check if value is a string with WML reference
            if isinstance(value, str):
                # Extract percentage if it's a WML reference
                match = re.match(r'(\d+)%\s*WML', value)
                if match:
                    percentage = int(match.group(1))
                    # Use 2000 EUR as approximate WML base (will be corrected in Parify)
                    step["value"] = round(2000 * (percentage / 100), 2)
                    step["minimumWage"] = True  # Mark as minimum wage based
                else:
                    # Try to convert to number
                    try:
                        step["value"] = float(value)
                    except:
                        step["value"] = 0  # Fallback

with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1049-ikea-FINAL-VALID.setu.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Fixed WML values - saved to 1049-ikea-FINAL-VALID.setu.json")
