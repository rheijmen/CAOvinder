"""Notification event models - what the notification engine produces."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CAOEventType(StrEnum):
    """Types of notification events produced by the engine."""

    # CAO-level events
    CAO_NIEUW = "cao_nieuw"
    CAO_GEWIJZIGD = "cao_gewijzigd"
    CAO_VERLOPEN = "cao_verlopen"
    CAO_AVV_VERLEEND = "cao_avv_verleend"
    CAO_AVV_VERLOPEN = "cao_avv_verlopen"

    # Salary events
    LOON_WIJZIGING = "loon_wijziging"
    LOONTABEL_BIJGEWERKT = "loontabel_bijgewerkt"

    # Allowance/benefit events
    TOESLAG_WIJZIGING = "toeslag_wijziging"
    VERGOEDING_WIJZIGING = "vergoeding_wijziging"
    PENSIOEN_WIJZIGING = "pensioen_wijziging"

    # Regulatory events
    WML_AANPASSING = "wml_aanpassing"
    WETGEVING_WIJZIGING = "wetgeving_wijziging"

    # Inlenersbeloning events
    ILB_ELEMENT_WIJZIGING = "ilb_element_wijziging"
    ILB_CORRECTIEFACTOR = "ilb_correctiefactor"

    # Processing events
    EXTRACTIE_COMPLEET = "extractie_compleet"
    EXTRACTIE_MISLUKT = "extractie_mislukt"
    VALIDATIE_FOUT = "validatie_fout"


class CAOEvent(BaseModel):
    """An event produced by the notification engine.

    Events are generated when moments are detected, when CAO data changes
    between versions, or when processing milestones are reached.
    """

    event_type: CAOEventType
    cao_naam: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    beschrijving: str = Field(..., description="Human-readable event description")
    details: dict | None = None
    oude_waarde: str | None = None
    nieuwe_waarde: str | None = None
    moment_id: str | None = Field(None, description="Related moment ID if applicable")
    bron_artikel: str | None = Field(None, description="CAO article reference")
