"""Inlenersbeloning (temporary worker compensation) models.

The inlenersbeloning consists of elements that must be matched for temp workers:
1. Periodeloon (period salary in applicable scale)
2. ADV (working time reduction)
3. Toeslagen (all allowances)
4. Initiele loonsverhoging (initial salary increases)
5. Kostenvergoedingen (cost reimbursements)
6. Periodieken (periodic salary increments)
7. Reisuren/reistijd (travel time compensation)
8. Eenmalige uitkeringen (one-time payments)
9. Thuiswerkvergoeding (work-from-home allowance)
10. Vaste eindejaarsuitkering (fixed year-end bonus)

From 2026, this transitions to 'gelijkwaardige beloning' (equivalent compensation).
"""

from pydantic import BaseModel, Field

from .arbeidsvoorwaarden import FlexDecimal


class InlenersbeloningElement(BaseModel):
    """A single element of the inlenersbeloning."""

    element_nummer: int = Field(..., description="Element number (1-10+)")
    element_naam: str = Field(..., description="Dutch name of the element")
    beschrijving: str = Field(..., description="Description and rules")
    waarde: str | None = Field(None, description="Value or rule text")
    percentage: FlexDecimal = Field(None, description="Percentage if applicable")
    bedrag: FlexDecimal = Field(None, description="Amount if applicable")
    van_toepassing: bool = Field(True, description="Whether this element applies in this CAO")


class InlenersbeloningElementen(BaseModel):
    """Complete inlenersbeloning specification for a CAO."""

    elementen: list[InlenersbeloningElement] = Field(default_factory=list)
    opmerkingen: str | None = Field(None, description="Additional remarks")
    gelijkwaardige_beloning: bool = Field(
        False, description="Whether full equivalent compensation applies (2026+)"
    )
