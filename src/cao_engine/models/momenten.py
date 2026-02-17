"""Momenten (Moments) models - the ground truth for the notification engine.

A "moment" is any date-driven trigger, rule, or event within a CAO that affects
remuneration, employment conditions, or compliance. Each moment stores the original
CAO rule text (bron_tekst) so notifications always reference the contractual basis.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from .arbeidsvoorwaarden import FlexDecimal


class MomentCategorie(StrEnum):
    """Categories of moments that can be extracted from a CAO."""

    LOON = "loon"                    # Salary-related moments
    DOCUMENT = "document"            # CAO lifecycle moments
    UITKERING = "uitkering"          # Payment moments (vakantietoeslag, eindejaarsuitkering)
    WERKNEMER = "werknemer"          # Employee-specific calculated moments
    TOESLAG = "toeslag"              # Allowance change moments
    WETTELIJK = "wettelijk"          # Legal/regulatory moments
    PENSIOEN = "pensioen"            # Pension-related moments
    INLENERSBELONING = "inlenersbeloning"  # Temp worker compensation moments


class MomentType(StrEnum):
    """Specific types of moments within categories."""

    # Loon
    LOONSVERHOGING = "loonsverhoging"                    # CAO salary increase
    PERIODIEKE_VERHOGING = "periodieke_verhoging"        # Step increase (trede)
    LEEFTIJDSLOON_OVERGANG = "leeftijdsloon_overgang"    # Age-based salary transition
    MINIMUMLOON_AANPASSING = "minimumloon_aanpassing"    # Statutory minimum wage change

    # Document lifecycle
    CAO_INGANGSDATUM = "cao_ingangsdatum"                # CAO start date
    CAO_EINDDATUM = "cao_einddatum"                      # CAO end date / expiry
    AVV_INGANGSDATUM = "avv_ingangsdatum"                # AVV start
    AVV_EINDDATUM = "avv_einddatum"                      # AVV end
    NAWERKING_START = "nawerking_start"                  # Continuation period start

    # Uitkeringen
    VAKANTIETOESLAG_UITBETALING = "vakantietoeslag_uitbetaling"  # Holiday allowance payment
    EINDEJAARSUITKERING = "eindejaarsuitkering"          # Year-end bonus
    EENMALIGE_UITKERING = "eenmalige_uitkering"          # One-time payment

    # Werknemer (calculated per employee)
    VOLGENDE_PERIODIEK = "volgende_periodiek"             # Next salary step
    LEEFTIJDSOVERGANG = "leeftijdsovergang"              # Age transition
    PROEFTIJD_EINDE = "proeftijd_einde"                  # End of probation
    CONTRACT_OVERGANG = "contract_overgang"               # Contract phase transition

    # Toeslag
    TOESLAG_WIJZIGING = "toeslag_wijziging"              # Allowance rate change
    TOESLAG_NIEUW = "toeslag_nieuw"                      # New allowance
    TOESLAG_VERVALLEN = "toeslag_vervallen"              # Allowance expired
    VERGOEDING_WIJZIGING = "vergoeding_wijziging"        # Reimbursement change

    # Wettelijk
    WML_AANPASSING = "wml_aanpassing"                    # Statutory minimum wage
    SV_PREMIE_WIJZIGING = "sv_premie_wijziging"          # Social insurance premium
    FISCALE_WIJZIGING = "fiscale_wijziging"              # Tax change
    WETGEVING_WIJZIGING = "wetgeving_wijziging"          # Law/regulation change

    # Pensioen
    PENSIOENPREMIE_WIJZIGING = "pensioenpremie_wijziging"  # Pension premium change
    PENSIOEN_FRANCHISE_WIJZIGING = "pensioen_franchise_wijziging"

    # Inlenersbeloning
    ILB_ELEMENT_WIJZIGING = "ilb_element_wijziging"      # ILB element change
    ILB_CORRECTIEFACTOR = "ilb_correctiefactor"          # Correction factor update

    # Catch-all
    OVERIG = "overig"


class Moment(BaseModel):
    """A single date-driven moment extracted from a CAO.

    This is the ground truth record that the notification engine uses
    to determine what notifications to send and when.
    """

    # Identity
    moment_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    cao_naam: str = Field(..., description="Which CAO this moment belongs to")
    categorie: MomentCategorie = Field(..., description="Moment category")
    type: MomentType = Field(..., description="Specific moment type")

    # Timing
    datum: date | None = Field(None, description="Fixed date if known")
    datum_beschrijving: str | None = Field(
        None,
        description="Date description when exact date is unknown",
    )
    terugkerend: bool = Field(False, description="Is this a recurring moment?")
    frequentie: str | None = Field(
        None, description="Recurrence: jaarlijks, halfjaarlijks, maandelijks, eenmalig"
    )
    trigger: str | None = Field(
        None,
        description="What triggers this moment (e.g. verjaardag, dienstjaar)",
    )

    # What changes
    beschrijving: str = Field(..., description="Human-readable description of the moment")
    element: str = Field(
        ..., description="Which element changes: loon, toeslag, verlof, pensioen, etc."
    )
    oude_waarde: str | None = Field(None, description="Previous value (for changes)")
    nieuwe_waarde: str | None = Field(None, description="New value")
    percentage: FlexDecimal = Field(None, description="Change percentage if applicable")
    bedrag: FlexDecimal = Field(None, description="Amount if applicable")

    # Scope - who is affected
    doelgroep: str | None = Field(
        None, description="Who is affected: functiegroep, leeftijdscategorie, alle werknemers, etc."
    )
    functiegroep_codes: list[str] = Field(
        default_factory=list, description="Specific functiegroep codes affected"
    )
    voorwaarden: list[str] = Field(
        default_factory=list, description="Conditions that must be met for this moment to apply"
    )

    # Source traceability
    bron_artikel: str | None = Field(
        None, description="CAO article reference (e.g. Artikel 12 lid 3)"
    )
    bron_tekst: str = Field(
        ..., description="Original rule text from the CAO document (verbatim)"
    )
    bron_pagina: int | None = Field(None, description="Page number in source PDF")

    # Processing metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")


class MomentenSet(BaseModel):
    """Collection of moments for a single CAO, stored as one JSON file."""

    cao_naam: str
    cao_versie: str | None = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    momenten: list[Moment] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.momenten)

    def by_categorie(self, categorie: MomentCategorie) -> list[Moment]:
        """Filter moments by category."""
        return [m for m in self.momenten if m.categorie == categorie]

    def by_date_range(self, start: date, end: date) -> list[Moment]:
        """Filter moments within a date range."""
        return [
            m for m in self.momenten
            if m.datum is not None and start <= m.datum <= end
        ]

    def upcoming(self, from_date: date | None = None) -> list[Moment]:
        """Get all future moments, sorted by date."""
        ref = from_date or date.today()
        future = [m for m in self.momenten if m.datum is not None and m.datum >= ref]
        return sorted(future, key=lambda m: m.datum)  # type: ignore[arg-type]
