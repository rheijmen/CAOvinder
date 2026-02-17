"""Wage structure models - functiegroepen, schalen, treden."""

from decimal import Decimal

from pydantic import BaseModel, Field


class LeeftijdsLoon(BaseModel):
    """Age-based salary (for workers under 21)."""

    leeftijd: int = Field(..., ge=15, le=20, description="Age in years")
    percentage: Decimal = Field(..., description="Percentage of full salary")
    bedrag: Decimal | None = Field(None, description="Fixed amount if specified")


class Trede(BaseModel):
    """A step (trede) within a salary scale."""

    trede_nummer: int = Field(..., description="Step number within the scale")
    periodeloon: Decimal | None = Field(None, description="Period salary at this step")
    uurloon: Decimal | None = Field(None, description="Hourly wage if specified")
    leeftijdslonen: list[LeeftijdsLoon] = Field(
        default_factory=list, description="Age-based salary variants"
    )


class Schaal(BaseModel):
    """A salary scale within a job classification group."""

    schaal_code: str = Field(..., description="Scale identifier (e.g., 'A', '1', 'I')")
    minimum_loon: Decimal | None = Field(None, description="Minimum salary in this scale")
    maximum_loon: Decimal | None = Field(None, description="Maximum salary in this scale")
    treden: list[Trede] = Field(default_factory=list, description="Salary steps")


class FunctieGroep(BaseModel):
    """A job classification group with associated salary scales."""

    groep_code: str = Field(..., description="Group identifier")
    groep_naam: str = Field(..., description="Group name/description")
    functie_omschrijving: str | None = Field(None, description="Job description for this group")
    schalen: list[Schaal] = Field(default_factory=list, description="Salary scales in this group")


class Loongebouw(BaseModel):
    """Complete wage structure of a CAO."""

    peildatum: str | None = Field(None, description="Reference date for the salary tables")
    valuta: str = Field("EUR", description="Currency code")
    loontijdvak: str = Field("maand", description="Pay period: uur, week, maand, jaar")
    functie_groepen: list[FunctieGroep] = Field(
        default_factory=list, description="Job classification groups"
    )
