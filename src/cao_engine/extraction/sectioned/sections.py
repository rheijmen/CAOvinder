"""The 6 extraction bundles. Each owns a disjoint set of top-level SETU keys."""
from dataclasses import dataclass, field

from cao_engine.extraction.sectioned.section_schema import build_section_schema

_BASE = (
    "You are extracting ONE part of a Dutch CAO into SETU v2.0 InquiryPayEquity JSON.\n"
    "Extract COMPLETELY and use EXACT Dutch terminology from the CAO. Do NOT summarize.\n"
    "Use null for unknown fields. Only output the part described below.\n"
)


@dataclass(frozen=True)
class SectionSpec:
    key: str
    top_level_keys: list[str]
    prompt_focus: str
    schema: dict = field(default=None)

    def __post_init__(self) -> None:
        # frozen dataclass: set the derived schema via object.__setattr__
        object.__setattr__(self, "schema", build_section_schema(self.top_level_keys))

    def build_prompt(self, markdown: str, cao_name: str | None) -> str:
        return (
            f"{_BASE}\nFOCUS: {self.prompt_focus}\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{markdown}"
        )


SECTIONS: list[SectionSpec] = [
    SectionSpec(
        key="identity",
        top_level_keys=["documentId", "versionId", "issued", "effectivePeriod",
                        "customer", "labourAgreements", "positionProfile", "baseDefinition"],
        prompt_focus=(
            "Document identity & parties: documentId, versionId, issued date, "
            "effectivePeriod (validFrom/validTo), customer (employer name + "
            "legalId/KvK), labourAgreements, positionProfile(s) and baseDefinition(s)."
        ),
    ),
    SectionSpec(
        key="remuneration",
        top_level_keys=["remuneration"],
        prompt_focus=(
            "Salary structure: remuneration[].salaryScale[] = each functiegroep/schaal "
            "(name, minValue, maxValue, currency); salaryScale[].salaryStep[] = EVERY "
            "trede (name, value=bruto EUR amount); generalSalaryIncrease[] = each "
            "algemene loonsverhoging (effectivePeriod.validFrom, percentage). A CAO has "
            "many scales each with many steps."
        ),
    ),
    SectionSpec(
        key="allowances",
        top_level_keys=["allowance", "holidayAllowance"],
        prompt_focus=(
            "Allowances: allowance[] = every toeslag (ORT, ploegentoeslag, overwerk, "
            "reiskosten, etc.); holidayAllowance[] = vakantietoeslag (percentage + "
            "payment moment)."
        ),
    ),
    SectionSpec(
        key="leave",
        top_level_keys=["leave", "sickPay"],
        prompt_focus=(
            "Leave & sick pay: leave[] = ADV/ATV, verlof, feestdagen, bijzonder verlof; "
            "sickPay[] = loondoorbetaling bij ziekte."
        ),
    ),
    SectionSpec(
        key="pension",
        top_level_keys=["pension", "individualChoiceBudget", "sustainableEmployability"],
        prompt_focus=(
            "Pension & budgets: pension[] = pensioenregeling(en) offered by the employer "
            "(fund name, origin, contribution split); individualChoiceBudget[] = IKB; "
            "sustainableEmployability[] = duurzame inzetbaarheid / generatiepact."
        ),
    ),
    SectionSpec(
        key="supplementary",
        top_level_keys=["supplementaryArrangement", "otherArrangement"],
        prompt_focus=(
            "Supplementary: supplementaryArrangement[] = eenmalige uitkeringen, bonussen, "
            "afbouwregelingen; otherArrangement[] = remaining arrangements not covered "
            "above."
        ),
    ),
]
