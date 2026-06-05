"""
Extract complete SETU v2.0 JSON Schema from OpenAPI YAML specification.
This will give us the EXACT schema that the validator uses.
"""

import json
from pathlib import Path
from typing import Any

import yaml


def extract_schema_from_openapi(openapi_file: Path, output_file: Path):
    """Extract the InquiryPayEquity schema from OpenAPI spec."""

    print(f"📖 Reading OpenAPI spec from {openapi_file}")
    with open(openapi_file, encoding='utf-8') as f:
        openapi_spec = yaml.safe_load(f)

    # Extract the schemas section
    if 'components' not in openapi_spec or 'schemas' not in openapi_spec['components']:
        raise ValueError("No schemas found in OpenAPI spec")

    schemas = openapi_spec['components']['schemas']

    print(f"✅ Found {len(schemas)} schema definitions")

    # The main schema is InquiryPayEquity
    if 'InquiryPayEquity' not in schemas:
        raise ValueError("InquiryPayEquity schema not found")

    inquiry_schema = schemas['InquiryPayEquity']

    # Create a complete schema with all referenced definitions
    complete_schema = {
        "$schema": inquiry_schema.get('$schema', 'http://json-schema.org/draft-07/schema#'),
        "$id": inquiry_schema.get('$id', 'https://ontology.setu.nl/inquiry-pay-equity/InquiryPayEquity'),
        "title": inquiry_schema.get('title', 'SETU Inquiry Pay Equity v2.0'),
        "description": inquiry_schema.get('description', 'SETU Inquiry Pay Equity v2.0 schema'),
        "type": "object",
        "required": inquiry_schema.get('required', []),
        "additionalProperties": inquiry_schema.get('additionalProperties', False),
        "properties": inquiry_schema.get('properties', {}),
        "$defs": {}
    }

    # Add all schemas as definitions
    for schema_name, schema_def in schemas.items():
        complete_schema['$defs'][schema_name] = schema_def

    # Save the complete schema
    print(f"💾 Saving complete schema to {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_schema, f, indent=2, ensure_ascii=False)

    print("✅ Schema extracted successfully")
    print(f"   - Required fields: {complete_schema['required']}")
    print(f"   - Total properties: {len(complete_schema['properties'])}")
    print(f"   - Definitions: {len(complete_schema['$defs'])}")

    return complete_schema


def analyze_key_structures(schema: dict[str, Any]):
    """Analyze key structures from the schema."""

    print("\n=== KEY SCHEMA DETAILS ===\n")

    # 1. schemeAgencyId enum values
    print("1. SchemeAgencyId Enum Values:")
    if 'SchemeAgencyIdType' in schema['$defs']:
        enum_values = schema['$defs']['SchemeAgencyIdType'].get('enum', [])
        print(f"   {enum_values}")

    if 'LegalSchemeAgencyIdType' in schema['$defs']:
        legal_enum = schema['$defs']['LegalSchemeAgencyIdType']
        if 'properties' in legal_enum and 'schemeAgencyId' in legal_enum['properties']:
            legal_values = legal_enum['properties']['schemeAgencyId'].get('enum', [])
            print(f"   Legal ID: {legal_values}")

    # 2. positionProfile structure
    print("\n2. PositionProfile Fields:")
    if 'PositionProfile' in schema['$defs']:
        pos_schema = schema['$defs']['PositionProfile']
        print(f"   Required: {pos_schema.get('required', [])}")
        print(f"   Properties: {list(pos_schema.get('properties', {}).keys())}")
        print(f"   Additional properties: {pos_schema.get('additionalProperties', True)}")

    # 3. remuneration structure
    print("\n3. Remuneration Structure:")
    if 'remuneration' in schema['properties']:
        rem_schema = schema['properties']['remuneration']
        if 'items' in rem_schema:
            rem_item = rem_schema['items']
            print(f"   Required: {rem_item.get('required', [])}")
            print(f"   Properties: {list(rem_item.get('properties', {}).keys())}")
            print(f"   Additional properties: {rem_item.get('additionalProperties', True)}")

    # 4. salaryScale structure
    print("\n4. SalaryScale Structure:")
    rem_items = schema['properties'].get('remuneration', {}).get('items', {})
    if 'properties' in rem_items and 'salaryScale' in rem_items['properties']:
        scale_schema = rem_items['properties']['salaryScale']
        if 'items' in scale_schema:
            scale_item = scale_schema['items']
            print(f"   Properties: {list(scale_item.get('properties', {}).keys())}")
            print(f"   Additional properties: {scale_item.get('additionalProperties', True)}")

    # 5. baseDefinition structure
    print("\n5. BaseDefinition Structure:")
    if 'baseDefinition' in schema['properties']:
        base_schema = schema['properties']['baseDefinition']
        if 'items' in base_schema:
            base_item = base_schema['items']
            print(f"   Properties: {list(base_item.get('properties', {}).keys())}")
            print(f"   Additional properties: {base_item.get('additionalProperties', True)}")


if __name__ == "__main__":
    openapi_path = Path("/Users/macbookpro/DEV/202602_CAOvinder/data/setu_input/gelijkwaardige-beloning-api.yaml")
    output_path = Path("/Users/macbookpro/DEV/202602_CAOvinder/data/setu/setu_v2_official_from_openapi.json")

    schema = extract_schema_from_openapi(openapi_path, output_path)
    analyze_key_structures(schema)
