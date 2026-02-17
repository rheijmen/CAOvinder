"""Cross-Reference Validator for SETU ↔ Statutory data.

Implements 7 validation rules from LLM Field Mapping instructions:
1. WML floor check
2. Pension franchise consistency
3. Fiscal cap check
4. Holiday allowance minimum (8%)
5. Vacation days minimum
6. Regulatory impact flagging
7. SV-premie cost recalculation triggers

CRITICAL: Never modifies either document. Flags mismatches at read time only.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level of validation issue."""

    INFO = "info"  # Informational, no action needed
    WARNING = "warning"  # Should be reviewed but may be intentional
    ERROR = "error"  # Likely compliance issue
    CRITICAL = "critical"  # Definite compliance violation


@dataclass
class ValidationIssue:
    """A single validation issue found during cross-reference check."""

    rule: str  # Which validation rule (e.g. "WML_FLOOR_CHECK")
    severity: ValidationSeverity
    description: str
    setu_field: str | None = None  # Field path in SETU document
    statutory_field: str | None = None  # Field path in statutory document
    setu_value: str | None = None
    statutory_value: str | None = None
    recommendation: str | None = None


@dataclass
class ValidationReport:
    """Complete validation report for a SETU ↔ Statutory pair."""

    setu_document_id: str
    statutory_period: str
    validation_date: date
    issues: list[ValidationIssue]

    @property
    def has_errors(self) -> bool:
        """True if any ERROR or CRITICAL issues found."""
        return any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in self.issues)

    @property
    def error_count(self) -> int:
        """Count of ERROR and CRITICAL issues."""
        return sum(1 for i in self.issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL))

    @property
    def warning_count(self) -> int:
        """Count of WARNING issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)


class CrossReferenceValidator:
    """Validates SETU documents against Statutory References.

    All validation happens at READ TIME. Never modifies either document.
    """

    def validate(self, setu_data: dict, statutory_data: dict) -> ValidationReport:
        """Run all 7 validation rules on SETU ↔ Statutory pair.

        Args:
            setu_data: SETU InquiryPayEquity document
            statutory_data: Statutory References document

        Returns:
            ValidationReport with all issues found
        """
        setu_id = setu_data.get("documentId", {}).get("value", "unknown")
        stat_period_from = statutory_data.get("effectivePeriod", {}).get("validFrom", "unknown")
        stat_period_to = statutory_data.get("effectivePeriod", {}).get("validTo", "unknown")
        stat_period = f"{stat_period_from} to {stat_period_to}"

        logger.info("Starting cross-reference validation", setu_id=setu_id, statutory_period=stat_period)

        issues: list[ValidationIssue] = []

        # Rule 1: WML floor check
        issues.extend(self._check_wml_floor(setu_data, statutory_data))

        # Rule 2: Pension franchise consistency
        issues.extend(self._check_pension_franchise(setu_data, statutory_data))

        # Rule 3: Fiscal cap check
        issues.extend(self._check_fiscal_caps(setu_data, statutory_data))

        # Rule 4: Holiday allowance minimum (8%)
        issues.extend(self._check_holiday_allowance_minimum(setu_data))

        # Rule 5: Vacation days minimum
        issues.extend(self._check_vacation_days_minimum(setu_data))

        # Rule 6: Regulatory impact flagging
        issues.extend(self._check_regulatory_impact(setu_data, statutory_data))

        # Rule 7: SV-premie cost recalculation triggers (informational)
        issues.extend(self._check_sv_premie_changes(statutory_data))

        report = ValidationReport(
            setu_document_id=setu_id,
            statutory_period=stat_period,
            validation_date=date.today(),
            issues=issues,
        )

        logger.info(
            "Validation complete",
            setu_id=setu_id,
            total_issues=len(issues),
            errors=report.error_count,
            warnings=report.warning_count,
        )

        return report

    def _check_wml_floor(self, setu_data: dict, statutory_data: dict) -> list[ValidationIssue]:
        """Rule 1: Every SETU salaryStep with minimumWage=true must be >= statutory WML."""
        issues = []

        # Get statutory WML rates
        wml_versions = statutory_data.get("minimumWage", [])
        if not wml_versions:
            return issues  # No WML data to compare

        # Get latest WML adult rate (age 21+)
        latest_wml = wml_versions[-1] if wml_versions else None
        if not latest_wml:
            return issues

        adult_rate = None
        for rate in latest_wml.get("hourlyRates", []):
            if rate.get("ageFrom") == 21 and rate.get("ageTo") is None:
                adult_rate = rate.get("hourlyRate")
                break

        if not adult_rate:
            return issues

        # Check all salary steps in SETU remuneration
        for idx, rem in enumerate(setu_data.get("remuneration", [])):
            for scale_idx, scale in enumerate(rem.get("salaryScale", [])):
                scale_name = scale.get("name", f"Scale {scale_idx}")
                for step in scale.get("salaryStep", []):
                    if step.get("minimumWage") is True:
                        step_value = step.get("value")
                        if step_value and step_value < adult_rate:
                            issues.append(
                                ValidationIssue(
                                    rule="WML_FLOOR_CHECK",
                                    severity=ValidationSeverity.CRITICAL,
                                    description=f"Salary step below statutory minimum wage",
                                    setu_field=f"remuneration[{idx}].salaryScale[{scale_idx}].salaryStep (minimumWage=true)",
                                    statutory_field="minimumWage[latest].hourlyRates (age 21+)",
                                    setu_value=f"€{step_value:.2f}/hour",
                                    statutory_value=f"€{adult_rate:.2f}/hour (WML)",
                                    recommendation=f"Increase salary step in {scale_name} to at least €{adult_rate:.2f}/hour",
                                )
                            )

        return issues

    def _check_pension_franchise(self, setu_data: dict, statutory_data: dict) -> list[ValidationIssue]:
        """Rule 2: SETU pension.franchise should align with statutory pensionParameters.franchiseAmount."""
        issues = []

        # Get statutory pension franchise
        pension_params = statutory_data.get("pensionParameters", [])
        if not pension_params:
            return issues

        statutory_franchise = pension_params[-1].get("franchiseAmount") if pension_params else None
        if not statutory_franchise:
            return issues

        # Check SETU pension franchises
        for idx, pension in enumerate(setu_data.get("pension", [])):
            franchise_desc = pension.get("franchise", {}).get("description")
            if franchise_desc:
                # This is a text description - flag for manual review
                issues.append(
                    ValidationIssue(
                        rule="PENSION_FRANCHISE_CONSISTENCY",
                        severity=ValidationSeverity.WARNING,
                        description="Pension franchise should be verified against statutory amount",
                        setu_field=f"pension[{idx}].franchise.description",
                        statutory_field="pensionParameters[latest].franchiseAmount",
                        setu_value=franchise_desc,
                        statutory_value=f"€{statutory_franchise:,.2f}",
                        recommendation="Verify that pension franchise aligns with statutory requirement",
                    )
                )

        return issues

    def _check_fiscal_caps(self, setu_data: dict, statutory_data: dict) -> list[ValidationIssue]:
        """Rule 3: SETU allowances (reiskosten/thuiswerk) compared against statutory fiscalLimits."""
        issues = []

        # Get fiscal limits
        fiscal_versions = statutory_data.get("fiscalLimits", [])
        if not fiscal_versions:
            return issues

        latest_limits = fiscal_versions[-1] if fiscal_versions else None
        if not latest_limits:
            return issues

        # Build fiscal limit lookup
        limit_map = {}
        for limit in latest_limits.get("limits", []):
            code = limit.get("code")
            value = limit.get("value")
            unit = limit.get("unitCode")
            if code and value:
                limit_map[code] = (value, unit)

        # Check travel allowances
        reiskosten_limit = limit_map.get("REISKOSTEN_KM")
        if reiskosten_limit:
            limit_value, limit_unit = reiskosten_limit
            for idx, allowance in enumerate(setu_data.get("allowance", [])):
                type_code = allowance.get("typeCode", "").lower()
                if "reiskosten" in type_code or "km" in type_code:
                    for line in allowance.get("line", []):
                        amount_value = line.get("amount", {}).get("value")
                        if amount_value and amount_value > limit_value:
                            issues.append(
                                ValidationIssue(
                                    rule="FISCAL_CAP_CHECK",
                                    severity=ValidationSeverity.WARNING,
                                    description="Travel allowance exceeds tax-free limit (excess is taxable)",
                                    setu_field=f"allowance[{idx}] (reiskosten)",
                                    statutory_field="fiscalLimits (REISKOSTEN_KM)",
                                    setu_value=f"€{amount_value}/{limit_unit}",
                                    statutory_value=f"€{limit_value}/{limit_unit} (tax-free max)",
                                    recommendation=f"Excess above €{limit_value}/{limit_unit} is taxable income",
                                )
                            )

        return issues

    def _check_holiday_allowance_minimum(self, setu_data: dict) -> list[ValidationIssue]:
        """Rule 4: SETU holidayAllowance percentage must be >= 8% (statutory minimum)."""
        issues = []

        STATUTORY_MINIMUM = 8.0  # 8% vakantietoeslag

        for idx, holiday in enumerate(setu_data.get("holidayAllowance", [])):
            for line in holiday.get("line", []):
                amount = line.get("amount", {})
                value = amount.get("value")
                unit_code = amount.get("unitCode", "")

                if unit_code.lower() == "percentage" and value is not None:
                    if value < STATUTORY_MINIMUM:
                        issues.append(
                            ValidationIssue(
                                rule="HOLIDAY_ALLOWANCE_MINIMUM",
                                severity=ValidationSeverity.CRITICAL,
                                description="Holiday allowance below statutory 8% minimum",
                                setu_field=f"holidayAllowance[{idx}]",
                                setu_value=f"{value}%",
                                statutory_value="8% (wettelijk minimum)",
                                recommendation=f"Increase holiday allowance to at least 8%",
                            )
                        )

        return issues

    def _check_vacation_days_minimum(self, setu_data: dict) -> list[ValidationIssue]:
        """Rule 5: SETU leave.paidLeave must be >= statutory minimum (4x weekly hours/year)."""
        issues = []

        # Statutory minimum: 4 weeks of paid vacation per year
        # This is complex to validate without knowing working hours
        # For now, flag if paidLeave seems very low

        for idx, leave in enumerate(setu_data.get("leave", [])):
            for paid in leave.get("paidLeave", []):
                amount = paid.get("amount", {})
                value = amount.get("value")
                unit_code = amount.get("unitCode", "")

                # Check if it looks like days per year
                if value is not None and "day" in unit_code.lower():
                    if value < 20:  # 4 weeks * 5 days = 20 days minimum for full-time
                        issues.append(
                            ValidationIssue(
                                rule="VACATION_DAYS_MINIMUM",
                                severity=ValidationSeverity.WARNING,
                                description="Paid leave may be below statutory minimum (4x weekly hours)",
                                setu_field=f"leave[{idx}].paidLeave",
                                setu_value=f"{value} {unit_code}",
                                statutory_value="Minimum 4 weeks/year (20 days for full-time)",
                                recommendation="Verify paid leave meets 4x weekly working hours requirement",
                            )
                        )

        return issues

    def _check_regulatory_impact(self, setu_data: dict, statutory_data: dict) -> list[ValidationIssue]:
        """Rule 6: When regulatory change is 'effective', flag impacted SETU sections."""
        issues = []

        for reg in statutory_data.get("regulatoryChanges", []):
            status = reg.get("status")
            if status == "effective":
                impact_areas = reg.get("impactAreas", [])
                reg_name = reg.get("name", "Unknown regulation")
                effective_date = reg.get("effectiveDate", "Unknown date")

                for area in impact_areas:
                    # Check if SETU document has this section
                    if area in setu_data and setu_data[area]:
                        issues.append(
                            ValidationIssue(
                                rule="REGULATORY_IMPACT",
                                severity=ValidationSeverity.INFO,
                                description=f"Regulation '{reg_name}' affects this section",
                                setu_field=area,
                                statutory_field=f"regulatoryChanges ({reg.get('code')})",
                                statutory_value=f"Effective {effective_date}",
                                recommendation=f"Review {area} for compliance with {reg_name}",
                            )
                        )

        return issues

    def _check_sv_premie_changes(self, statutory_data: dict) -> list[ValidationIssue]:
        """Rule 7: Detect SV-premie changes (informational for cost recalculation)."""
        issues = []

        sv_versions = statutory_data.get("socialInsurancePremiums", [])
        if len(sv_versions) >= 2:
            # Compare latest vs previous
            latest = sv_versions[-1]
            previous = sv_versions[-2]

            latest_period = latest.get("effectivePeriod", {}).get("validFrom", "unknown")

            # Simplified: just flag that there are multiple versions
            issues.append(
                ValidationIssue(
                    rule="SV_PREMIE_RECALCULATION_TRIGGER",
                    severity=ValidationSeverity.INFO,
                    description="Social insurance premiums have changed - recalculate employer costs",
                    statutory_field="socialInsurancePremiums",
                    statutory_value=f"New rates effective {latest_period}",
                    recommendation="Recalculate total employer cost projections for linked SETU documents",
                )
            )

        return issues
