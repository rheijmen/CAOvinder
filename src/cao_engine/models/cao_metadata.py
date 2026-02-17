"""CAO metadata models - identity, lifecycle, and parties."""

from datetime import date

from pydantic import BaseModel, Field


class CAOPartij(BaseModel):
    """A party to the CAO (union or employer organization)."""

    naam: str = Field(..., description="Name of the party")
    type: str = Field(..., description="'werkgever' or 'werknemer'")
    kvk_nummer: str | None = Field(None, description="Chamber of Commerce number")


class CAOMetadata(BaseModel):
    """Core metadata for a Collective Labour Agreement."""

    cao_naam: str = Field(..., description="Official name of the CAO")
    cao_code: str | None = Field(None, description="SBI or CAO registration code")
    sbi_codes: list[str] = Field(default_factory=list, description="SBI sector codes")
    sector: str | None = Field(None, description="Industry sector")
    ingangsdatum: date | None = Field(None, description="Start date of the CAO")
    einddatum: date | None = Field(None, description="End date of the CAO")
    avv_status: bool | None = Field(None, description="Whether CAO is generally binding (AVV)")
    avv_ingangsdatum: date | None = Field(None, description="AVV start date")
    avv_einddatum: date | None = Field(None, description="AVV end date")
    partijen: list[CAOPartij] = Field(default_factory=list)
    bron_url: str | None = Field(None, description="Source URL of the PDF")
    bron_document: str | None = Field(None, description="Filename of source PDF")
    versie: str | None = Field(None, description="Version identifier")
