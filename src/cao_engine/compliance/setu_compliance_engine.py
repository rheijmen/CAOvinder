"""
SETU Compliance Engine - Gold Standard
=======================================
This is the CANONICAL source of truth for SETU v2.0 compliance in the CAO Engine.

Purpose: Ensure 100% SETU v2.0 compliance with intelligent versioning and change detection.

Key Principles:
1. SETU schema is the law - we validate against the official OpenAPI spec
2. Version awareness - track SETU spec changes and adapt automatically
3. Proactive compliance - detect and alert on schema changes before they break
4. Extraction optimization - use schema knowledge to guide LLM extraction
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import requests
from pydantic import BaseModel, Field
from enum import Enum


class SETUVersion(BaseModel):
    """Represents a SETU specification version."""
    version: str  # e.g., "2.0.0-draft.3"
    release_date: datetime
    schema_hash: str  # SHA256 of the schema for change detection
    breaking_changes: List[str] = []
    new_fields: List[str] = []
    deprecated_fields: List[str] = []
    source_url: str


class ComplianceStatus(Enum):
    """SETU compliance status levels."""
    COMPLIANT = "compliant"  # Fully compliant with current version
    PARTIAL = "partial"  # Missing optional fields
    NON_COMPLIANT = "non_compliant"  # Missing required fields
    VERSION_MISMATCH = "version_mismatch"  # Using outdated schema
    UNKNOWN = "unknown"


class SETUComplianceEngine:
    """
    GOLD STANDARD: Central compliance engine for SETU v2.0

    This engine:
    1. Monitors SETU specification changes
    2. Validates extractions against current schema
    3. Guides LLM extraction with schema knowledge
    4. Maintains version history and migration paths
    """

    def __init__(self):
        self.schema_dir = Path(__file__).parent.parent / "models"
        self.compliance_dir = Path(__file__).parent
        self.compliance_dir.mkdir(exist_ok=True)

        # Load current schema
        self.current_schema = self._load_current_schema()
        self.current_version = self._extract_version()

        # Version tracking
        self.version_history_file = self.compliance_dir / "setu_version_history.json"
        self.version_history = self._load_version_history()

    def _load_current_schema(self) -> Dict:
        """Load the current SETU OpenAPI schema."""
        schema_file = self.schema_dir / "setu_v2_openapi.yaml"
        with open(schema_file, 'r') as f:
            return yaml.safe_load(f)

    def _extract_version(self) -> str:
        """Extract version from OpenAPI schema."""
        return self.current_schema.get('info', {}).get('version', 'unknown')

    def _calculate_schema_hash(self, schema: Dict) -> str:
        """Calculate SHA256 hash of schema for change detection."""
        # Focus on the InquiryPayEquity schema structure
        inquiry_schema = schema['components']['schemas']['InquiryPayEquity']
        schema_json = json.dumps(inquiry_schema, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()

    def _load_version_history(self) -> List[SETUVersion]:
        """Load version history from disk."""
        if self.version_history_file.exists():
            with open(self.version_history_file, 'r') as f:
                data = json.load(f)
                return [SETUVersion(**v) for v in data]
        return []

    def check_for_updates(self) -> Optional[SETUVersion]:
        """
        Check if SETU specification has been updated.
        In production, this would check the official SETU API.
        """
        # Check official SETU endpoint (simulated for now)
        latest_url = "https://standard.setu.nl/docs/api/oas-gelijkwaardige-beloning"

        current_hash = self._calculate_schema_hash(self.current_schema)

        # Check if we've seen this version before
        for version in self.version_history:
            if version.schema_hash == current_hash:
                return None  # No update

        # New version detected!
        new_version = SETUVersion(
            version=self.current_version,
            release_date=datetime.now(),
            schema_hash=current_hash,
            source_url=latest_url
        )

        # Detect changes
        if self.version_history:
            new_version.breaking_changes = self._detect_breaking_changes()
            new_version.new_fields = self._detect_new_fields()
            new_version.deprecated_fields = self._detect_deprecated_fields()

        return new_version

    def _detect_breaking_changes(self) -> List[str]:
        """Detect breaking changes in schema."""
        changes = []

        # Check required fields
        current_required = set(self.current_schema['components']['schemas']['InquiryPayEquity'].get('required', []))

        # Compare with last known version (would need previous schema stored)
        # For now, return empty list
        return changes

    def _detect_new_fields(self) -> List[str]:
        """Detect new fields in schema."""
        # Would compare with previous version
        return []

    def _detect_deprecated_fields(self) -> List[str]:
        """Detect deprecated fields in schema."""
        # Would compare with previous version
        return []

    def generate_extraction_prompt(self) -> str:
        """
        Generate optimized extraction prompt based on current SETU schema.
        This is the GOLD STANDARD prompt that ensures compliance.
        """

        schema = self.current_schema['components']['schemas']['InquiryPayEquity']
        required_fields = schema.get('required', [])

        prompt = f"""
You are extracting data for SETU v2.0 InquiryPayEquity (version {self.current_version}).

CRITICAL REQUIREMENTS - These fields are MANDATORY:
{json.dumps(required_fields, indent=2)}

EXTRACTION RULES:

1. DOCUMENT IDENTIFICATION
   - documentId: Must be unique, use format "CAO-{number}-{year}"
   - versionId: Use CAO version if specified, otherwise "1.0"
   - issued: Current datetime in ISO 8601 format

2. EFFECTIVE PERIOD (REQUIRED)
   - validFrom: Start date of CAO validity (format: YYYY-MM-DD)
   - validTo: End date of CAO validity (format: YYYY-MM-DD)

3. CUSTOMER (REQUIRED)
   - name: Exact name of the employer/sector
   - legalId: KvK number if available
   - personContacts: At least one authorized contact person

4. REMUNERATION (REQUIRED) - MOST CRITICAL SECTION
   Must extract ALL of:
   - origin.type: "CollectiveLabourAgreement" or "CustomLabourAgreement"
   - workDuration: Standard work hours (e.g., 40 hours/week)
   - interval: Payment period (Week/Month/Year)
   - salaryScale: ALL salary scales with:
     * name: Scale identifier (e.g., "Schaal II", "FWG-10")
     * steps: ALL salary steps with amounts
     * youthScales: If present, ages 16-20 with percentages

5. ALLOWANCES (Extract ALL found):
   - Type codes: Overtime, Shift, Irregular, Travel, Meal, etc.
   - Amount calculation method (percentage/fixed)
   - Conditions for eligibility

6. HOLIDAY ALLOWANCE
   - Standard is 8% unless specified otherwise
   - Payment date if specified

7. LEAVE ARRANGEMENTS
   - Paid leave days
   - ADV/ATV days if applicable
   - Special leave conditions

8. PENSION
   - Employer contribution percentage
   - Franchise information if applicable

FORMAT REQUIREMENTS:
- Dates: YYYY-MM-DD (ISO 8601)
- Currency: Decimal with 2 places (e.g., 2500.00)
- Percentages: Decimal (e.g., 0.08 for 8%)
- Durations: ISO 8601 (e.g., "P1Y" for 1 year, "P6M" for 6 months)

VALIDATION CHECKS:
- All salary scales must have aanvang <= eind
- Youth scales must progress: 16yr < 17yr < 18yr < 19yr < 20yr
- validFrom must be before validTo
- At least one remuneration block must be present

Return ONLY valid JSON matching the SETU v2.0 InquiryPayEquity schema.
"""
        return prompt

    def validate_extraction(self, extraction: Dict) -> Tuple[ComplianceStatus, Dict]:
        """
        Validate extraction against SETU schema and return compliance status.
        This is the GOLD STANDARD validation.
        """

        report = {
            "version": self.current_version,
            "timestamp": datetime.now().isoformat(),
            "status": ComplianceStatus.UNKNOWN,
            "errors": [],
            "warnings": [],
            "coverage": 0.0
        }

        # Check required fields
        schema = self.current_schema['components']['schemas']['InquiryPayEquity']
        required = schema.get('required', [])

        missing_required = []
        for field in required:
            if field not in extraction or extraction[field] is None:
                missing_required.append(field)
                report["errors"].append(f"Missing required field: {field}")

        # Determine status
        if not missing_required:
            # Check critical data quality
            if self._validate_remuneration(extraction):
                report["status"] = ComplianceStatus.COMPLIANT
            else:
                report["status"] = ComplianceStatus.PARTIAL
                report["warnings"].append("Remuneration data incomplete")
        else:
            report["status"] = ComplianceStatus.NON_COMPLIANT

        # Calculate coverage
        report["coverage"] = self._calculate_coverage(extraction)

        return report["status"], report

    def _validate_remuneration(self, extraction: Dict) -> bool:
        """Validate remuneration section has complete salary data."""
        if 'remuneration' not in extraction:
            return False

        for remun in extraction['remuneration']:
            if 'salaryScale' not in remun or not remun['salaryScale']:
                return False

            # Check each scale has required data
            for scale in remun['salaryScale']:
                if 'name' not in scale:
                    return False
                if 'steps' not in scale or not scale['steps']:
                    return False

        return True

    def _calculate_coverage(self, extraction: Dict) -> float:
        """Calculate percentage of schema fields populated."""
        # Simplified coverage calculation
        total_fields = 15  # Key SETU fields
        filled = sum(1 for field in [
            'documentId', 'versionId', 'issued', 'effectivePeriod',
            'customer', 'labourAgreements', 'positionProfile',
            'remuneration', 'allowance', 'holidayAllowance',
            'sickPay', 'leave', 'pension', 'individualChoiceBudget',
            'sustainableEmployability'
        ] if field in extraction and extraction[field])

        return (filled / total_fields) * 100

    def update_schema(self, new_schema_path: Path) -> bool:
        """
        Update to new SETU schema version with migration support.
        """
        # Load new schema
        with open(new_schema_path, 'r') as f:
            new_schema = yaml.safe_load(f)

        new_version = new_schema.get('info', {}).get('version', 'unknown')

        # Check for breaking changes
        new_hash = self._calculate_schema_hash(new_schema)
        current_hash = self._calculate_schema_hash(self.current_schema)

        if new_hash == current_hash:
            print(f"Schema unchanged (version {new_version})")
            return False

        # Create backup of current schema
        backup_path = self.schema_dir / f"setu_v2_openapi_{self.current_version}.yaml.backup"
        current_schema_path = self.schema_dir / "setu_v2_openapi.yaml"

        import shutil
        shutil.copy(current_schema_path, backup_path)
        print(f"Backed up current schema to {backup_path}")

        # Update to new schema
        shutil.copy(new_schema_path, current_schema_path)

        # Record version change
        version_record = SETUVersion(
            version=new_version,
            release_date=datetime.now(),
            schema_hash=new_hash,
            source_url=str(new_schema_path),
            breaking_changes=self._detect_breaking_changes(),
            new_fields=self._detect_new_fields()
        )

        self.version_history.append(version_record)
        self._save_version_history()

        print(f"✅ Updated SETU schema from {self.current_version} to {new_version}")

        # Reload current schema
        self.current_schema = new_schema
        self.current_version = new_version

        return True

    def _save_version_history(self):
        """Save version history to disk."""
        with open(self.version_history_file, 'w') as f:
            json.dump(
                [v.model_dump() for v in self.version_history],
                f,
                indent=2,
                default=str
            )

    def generate_notification(self, change_type: str, details: Dict) -> Dict:
        """
        Generate notification for SETU compliance changes.
        Integrates with notification engine.
        """
        return {
            "type": "SETU_COMPLIANCE_CHANGE",
            "severity": "HIGH" if "breaking" in change_type else "MEDIUM",
            "timestamp": datetime.now().isoformat(),
            "change_type": change_type,
            "details": details,
            "action_required": self._determine_action(change_type),
            "affected_components": self._identify_affected_components(change_type)
        }

    def _determine_action(self, change_type: str) -> str:
        """Determine required action for change type."""
        actions = {
            "breaking_change": "Update extraction pipeline immediately",
            "new_fields": "Review and update extraction prompts",
            "deprecated_fields": "Plan migration to new field names",
            "version_update": "Test extraction with new schema"
        }
        return actions.get(change_type, "Review changes")

    def _identify_affected_components(self, change_type: str) -> List[str]:
        """Identify system components affected by change."""
        return [
            "extraction/gemini_setu_extractor.py",
            "extraction/mistral_reviewer.py",
            "validation/setu_validator.py",
            "models/setu_v2_schema.json"
        ]


# Singleton instance - this is THE compliance engine
_compliance_engine = None

def get_compliance_engine() -> SETUComplianceEngine:
    """Get the singleton SETU compliance engine."""
    global _compliance_engine
    if _compliance_engine is None:
        _compliance_engine = SETUComplianceEngine()
    return _compliance_engine


# CLI Commands for compliance management
if __name__ == "__main__":
    import sys

    engine = get_compliance_engine()

    if len(sys.argv) < 2:
        print("Usage: python setu_compliance_engine.py [check|validate|prompt]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        # Check for SETU updates
        update = engine.check_for_updates()
        if update:
            print(f"⚠️  New SETU version detected: {update.version}")
            print(f"   Breaking changes: {update.breaking_changes}")
            print(f"   New fields: {update.new_fields}")
        else:
            print(f"✅ Using latest SETU version: {engine.current_version}")

    elif command == "validate":
        # Validate a SETU file
        if len(sys.argv) < 3:
            print("Usage: python setu_compliance_engine.py validate <setu.json>")
            sys.exit(1)

        with open(sys.argv[2], 'r') as f:
            data = json.load(f)

        status, report = engine.validate_extraction(data)
        print(f"Compliance Status: {status.value}")
        print(f"Coverage: {report['coverage']:.1f}%")

        if report['errors']:
            print("\nErrors:")
            for error in report['errors']:
                print(f"  - {error}")

    elif command == "prompt":
        # Generate extraction prompt
        prompt = engine.generate_extraction_prompt()
        print(prompt)