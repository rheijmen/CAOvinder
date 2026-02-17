"""Employment conditions models - toeslagen, verlof, ADV, pensioen."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, BeforeValidator, Field
from typing_extensions import Annotated


def _parse_flexible_decimal(v: Any) -> Decimal | None:
    """Parse LLM-returned values into Decimal, handling common formats.

    Handles: "30%", "€ 25", "100%", "2.5", "8,5", None, and strings
    that can't be parsed (returns None).
    """
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    if isinstance(v, str):
        # Strip currency symbols, whitespace, % signs
        cleaned = v.strip()
        cleaned = re.sub(r"[€$£\s]", "", cleaned)
        cleaned = cleaned.rstrip("%")
        # Replace comma decimal separator
        cleaned = cleaned.replace(",", ".")
        # Try to extract first number from remaining string
        match = re.match(r"^-?\d+\.?\d*", cleaned)
        if match:
            try:
                return Decimal(match.group())
            except InvalidOperation:
                return None
        return None
    return None


FlexDecimal = Annotated[Decimal | None, BeforeValidator(_parse_flexible_decimal)]


class Toeslag(BaseModel):
    """An allowance/surcharge defined in the CAO."""

    type: str = Field(..., description="Type: overwerk, onregelmatig, feestdag, ploegen, etc.")
    beschrijving: str = Field(..., description="Description of the allowance")
    percentage: FlexDecimal = Field(None, description="Percentage surcharge")
    bedrag: FlexDecimal = Field(None, description="Fixed amount")
    voorwaarden: str | None = Field(None, description="Conditions for this allowance")
    tijdvakken: str | None = Field(None, description="Time periods when applicable")


class Onkostenvergoeding(BaseModel):
    """An expense reimbursement defined in the CAO."""

    type: str = Field(..., description="Type: reiskosten, thuiswerk, maaltijd, etc.")
    bedrag: FlexDecimal = Field(None, description="Amount")
    per_eenheid: str | None = Field(None, description="Per unit: dag, km, maand, etc.")
    voorwaarden: str | None = Field(None, description="Conditions")


class VerlofRegel(BaseModel):
    """A leave entitlement rule."""

    type: str = Field(..., description="Type: vakantie, bijzonder, zorg, etc.")
    dagen: int | None = Field(None, description="Number of days")
    uren: FlexDecimal = Field(None, description="Number of hours")
    beschrijving: str = Field(..., description="Description and conditions")


class ADVRegeling(BaseModel):
    """Working time reduction arrangement (Arbeidsduurverkorting)."""

    arbeidsduur_per_week: FlexDecimal = Field(None, description="Standard hours per week")
    adv_uren_per_jaar: FlexDecimal = Field(None, description="ADV hours per year")
    adv_dagen_per_jaar: int | None = Field(None, description="ADV days per year")
    adv_percentage: FlexDecimal = Field(None, description="ADV as percentage of salary")
    compensatie: str | None = Field(None, description="Compensation method: tijd/geld/keuze")


class PensioenRegeling(BaseModel):
    """Pension arrangement details."""

    regeling: str | None = Field(None, description="Pension scheme name")
    fonds: str | None = Field(None, description="Pension fund name")
    franchise: FlexDecimal = Field(None, description="Franchise amount")
    premie_werkgever: FlexDecimal = Field(None, description="Employer contribution %")
    premie_werknemer: FlexDecimal = Field(None, description="Employee contribution %")


class ArbeidsVoorwaarden(BaseModel):
    """Employment conditions from the CAO."""

    vakantietoeslag_percentage: FlexDecimal = Field(
        None, description="Holiday allowance percentage (typically 8%)"
    )
    vakantietoeslag_grondslag: str | None = Field(
        None, description="Basis for holiday allowance"
    )
    vakantietoeslag_uitbetaling_maand: int | None = Field(
        None, description="Month of holiday allowance payment (1-12)"
    )
    eindejaarsuitkering_percentage: FlexDecimal = Field(
        None, description="Year-end bonus percentage"
    )
    eindejaarsuitkering_grondslag: str | None = Field(
        None, description="Basis for year-end bonus"
    )
    eindejaarsuitkering_voorwaarden: str | None = Field(
        None, description="Conditions for year-end bonus"
    )
    proeftijd_maanden: int | None = Field(None, description="Probation period in months")
    opzegtermijn_werknemer: str | None = Field(None, description="Employee notice period")
    opzegtermijn_werkgever: str | None = Field(None, description="Employer notice period")
    adv_regeling: ADVRegeling | None = None
    pensioen: PensioenRegeling | None = None
    toeslagen: list[Toeslag] = Field(default_factory=list)
    onkostenvergoedingen: list[Onkostenvergoeding] = Field(default_factory=list)
    verlof_regelingen: list[VerlofRegel] = Field(default_factory=list)
