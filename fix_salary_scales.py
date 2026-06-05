"""Quick fix for salary scales in IKEA JSON"""
import json

# Read the file
with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1049-ikea-final-compliant.setu.json', 'r') as f:
    data = json.load(f)

# Fix all salary scales
for rem in data.get("remuneration", []):
    for scale in rem.get("salaryScale", []):
        # Remove youthScale if present
        if "youthScale" in scale:
            del scale["youthScale"]
        
        # Fix salaryStep
        if "salaryStep" in scale:
            fixed_steps = []
            for step in scale["salaryStep"]:
                clean_step = {
                    "name": str(step.get("zone", step.get("name", len(fixed_steps) + 1))),
                    "value": step.get("amount", step.get("value", 0))
                }
                # Only include optional fields if they exist
                if "minimumWage" in step:
                    clean_step["minimumWage"] = step["minimumWage"]
                if "conditions" in step:
                    clean_step["conditions"] = step["conditions"]
                
                fixed_steps.append(clean_step)
            
            scale["salaryStep"] = fixed_steps

# Save
with open('/Users/macbookpro/DEV/202602_CAOvinder/data/setu/1049-ikea-FIXED.setu.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Fixed salary scales - saved to 1049-ikea-FIXED.setu.json")
