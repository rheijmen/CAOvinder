"""
Extract the actual SETU v2.0 JSON Schema from the Excel specification.
This will help us understand the exact structure the validator expects.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd


class SETUSchemaExtractor:
    """Extract SETU v2.0 schema from Excel specification."""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.df = None

    def load_excel(self):
        """Load the Excel file with correct header row."""
        # Based on our exploration, header row 0 has the column names we need
        self.df = pd.read_excel(
            self.excel_path,
            sheet_name='InquiryPayEquity',
            header=0
        )
        print(f"Loaded {len(self.df)} rows from Excel")
        print(f"Columns: {list(self.df.columns)}")

    def find_enum_values(self, element_name: str) -> list[str] | None:
        """Find enumeration values for a specific element."""
        # Look for rows containing the element name
        matching_rows = self.df[
            self.df['Element name'].str.contains(element_name, case=False, na=False)
        ]

        for _, row in matching_rows.iterrows():
            # Check if there's an enumeration or specific values mentioned
            definition = str(row.get('Definition', ''))
            if 'must be' in definition.lower() or 'allowed values' in definition.lower():
                print(f"  Found constraint for {element_name}: {definition}")

    def analyze_structure(self):
        """Analyze the structure to understand field names and requirements."""

        print("\n=== Analyzing schemeAgencyId ===")
        scheme_rows = self.df[
            self.df['Element name'].str.contains('schemeAgencyId', case=False, na=False)
        ]
        for _, row in scheme_rows.iterrows():
            print(f"Element: {row['Element name']}")
            print(f"  Type: {row['Type']}")
            print(f"  Base: {row['Base datatype']}")
            print(f"  Mult: {row['Mult']}")
            print(f"  Path: {row['Path']}")
            print(f"  Definition: {row.get('Definition', '')[:200]}")

        print("\n=== Analyzing positionProfile ===")
        # Look for position-related elements
        pos_rows = self.df[
            self.df['Path'].str.contains('positionProfile', case=False, na=False) |
            self.df['Element name'].str.contains('position', case=False, na=False)
        ]

        # Group by path depth to understand structure
        position_fields = {}
        for _, row in pos_rows.iterrows():
            path = row['Path']
            element = row['Element name']
            mult = row['Mult']

            if 'positionProfile' in path:
                depth = path.count('/')
                if depth == 2:  # Direct children of positionProfile
                    position_fields[element] = {
                        'mult': mult,
                        'type': row['Type'],
                        'base': row['Base datatype']
                    }

        print("Position Profile Fields:")
        for field, info in position_fields.items():
            print(f"  - {field}: {info}")

        print("\n=== Analyzing remuneration/workDuration ===")
        work_rows = self.df[
            self.df['Path'].str.contains('workDuration', case=False, na=False)
        ]
        for _, row in work_rows.head(10).iterrows():
            print(f"Path: {row['Path']}")
            print(f"  Element: {row['Element name']}")
            print(f"  Type: {row['Type']}")
            print(f"  Base: {row['Base datatype']}")
            print(f"  Mult: {row['Mult']}")

        print("\n=== Analyzing salaryScale structure ===")
        scale_rows = self.df[
            self.df['Path'].str.contains('salaryScale', case=False, na=False)
        ]

        scale_fields = {}
        for _, row in scale_rows.iterrows():
            path = row['Path']
            element = row['Element name']

            if 'salaryScale' in path:
                # Count path segments after salaryScale
                path_parts = path.split('/')
                if 'salaryScale' in path_parts:
                    idx = path_parts.index('salaryScale')
                    if idx + 1 < len(path_parts):
                        next_element = path_parts[idx + 1]
                        if next_element not in scale_fields:
                            scale_fields[next_element] = {
                                'mult': row['Mult'],
                                'type': row['Type'],
                                'base': row['Base datatype']
                            }

        print("Salary Scale Fields:")
        for field, info in scale_fields.items():
            print(f"  - {field}: {info}")

        print("\n=== Looking for baseDefinition structure ===")
        base_rows = self.df[
            self.df['Element name'].str.contains('baseDefinition', case=False, na=False) |
            self.df['Path'].str.contains('baseDefinition', case=False, na=False)
        ]

        if len(base_rows) > 0:
            print("BaseDefinition found:")
            for _, row in base_rows.head(10).iterrows():
                print(f"  Path: {row['Path']}")
                print(f"    Element: {row['Element name']}, Mult: {row['Mult']}")
        else:
            print("BaseDefinition NOT found in Excel - might not be in this version!")

    def extract_full_schema(self) -> dict[str, Any]:
        """Extract complete schema structure from Excel."""

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": []
        }

        # Group rows by top-level path
        top_level_elements = self.df[
            self.df['Path'].str.count('/') == 1
        ]

        for _, row in top_level_elements.iterrows():
            element_name = row['Element name']
            mult = row['Mult']
            element_type = row['Type']
            base_type = row['Base datatype']

            # Parse multiplicity to determine if required
            if mult.startswith('1..'):
                schema['required'].append(element_name)

            # Determine JSON type from base datatype
            json_type = self._map_to_json_type(base_type, element_type)

            schema['properties'][element_name] = {
                'type': json_type
            }

            print(f"Added {element_name}: type={json_type}, required={mult.startswith('1..')}")

        return schema

    def _map_to_json_type(self, base_type, element_type):
        """Map SETU types to JSON Schema types."""
        if pd.isna(base_type):
            if pd.notna(element_type):
                # Complex type - likely an object
                return 'object'
            return 'string'

        base_type = str(base_type).lower()

        if 'string' in base_type or 'text' in base_type:
            return 'string'
        elif 'number' in base_type or 'decimal' in base_type:
            return 'number'
        elif 'integer' in base_type:
            return 'integer'
        elif 'boolean' in base_type or 'indicator' in base_type:
            return 'boolean'
        elif 'date' in base_type:
            return 'string'
        elif 'array' in base_type:
            return 'array'
        else:
            return 'object'


def main():
    excel_path = '/Users/macbookpro/DEV/202602_CAOvinder/data/setu_input/SETU Inquiry Pay Equity v2.0 - InquiryPayEquity (4).xlsx'

    extractor = SETUSchemaExtractor(excel_path)
    extractor.load_excel()
    extractor.analyze_structure()

    # Extract schema
    print("\n=== Extracting Schema ===")
    schema = extractor.extract_full_schema()

    # Save schema
    output_path = Path('data/setu/extracted_schema_from_excel.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Schema extracted to {output_path}")


if __name__ == "__main__":
    main()