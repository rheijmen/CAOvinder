"""Timeline models for visualizing CAO developments and notifications."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .events import CAOEvent, CAOEventType
from .momenten import Moment, MomentCategorie, MomentType


class TimelineEntryType(StrEnum):
    """Type of timeline entry for visual differentiation."""

    MOMENT = "moment"                # Scheduled moment from CAO
    NOTIFICATION = "notification"    # Generated notification event
    DOCUMENT = "document"            # CAO document lifecycle event
    REGULATORY = "regulatory"        # Regulatory/legal change
    MILESTONE = "milestone"          # Important milestone/marker


class TimelineEntry(BaseModel):
    """A single entry in the CAO timeline."""

    # Core fields
    entry_id: str = Field(..., description="Unique identifier for this entry")
    entry_type: TimelineEntryType
    datum: date | None = Field(None, description="Date of the event")
    datum_beschrijving: str | None = Field(None, description="Date description if no exact date")

    # Display fields
    titel: str = Field(..., description="Short title for timeline display")
    beschrijving: str = Field(..., description="Full description")
    categorie: str = Field(..., description="Category for color coding")
    icon: str | None = Field(None, description="Icon identifier for visual display")

    # Impact/change fields
    impact_level: str = Field("medium", description="low/medium/high impact")
    oude_waarde: str | None = None
    nieuwe_waarde: str | None = None
    percentage: str | None = None
    bedrag: str | None = None

    # Source/reference
    bron_artikel: str | None = None
    bron_tekst: str | None = None

    # Metadata
    is_recurring: bool = Field(False, description="Is this a recurring event?")
    recurrence_info: str | None = None
    is_future: bool = Field(False, description="Is this a future event?")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")

    # Original source reference
    source_moment_id: str | None = None
    source_event_id: str | None = None

    @classmethod
    def from_moment(cls, moment: Moment) -> "TimelineEntry":
        """Create a timeline entry from a Moment."""
        is_future = moment.datum and moment.datum > date.today() if moment.datum else False

        # Determine impact level based on category and type
        impact_level = "high" if moment.categorie in [
            MomentCategorie.LOON,
            MomentCategorie.DOCUMENT,
            MomentCategorie.WETTELIJK
        ] else "medium"

        # Create tags for filtering
        tags = [moment.categorie.value, moment.type.value]
        if moment.functiegroep_codes:
            tags.extend(moment.functiegroep_codes)
        if moment.terugkerend:
            tags.append("recurring")

        return cls(
            entry_id=f"moment_{moment.moment_id}",
            entry_type=TimelineEntryType.MOMENT,
            datum=moment.datum,
            datum_beschrijving=moment.datum_beschrijving,
            titel=moment.beschrijving[:100],  # Truncate for title
            beschrijving=moment.beschrijving,
            categorie=moment.categorie.value,
            icon=_get_icon_for_category(moment.categorie),
            impact_level=impact_level,
            oude_waarde=moment.oude_waarde,
            nieuwe_waarde=moment.nieuwe_waarde,
            percentage=str(moment.percentage) if moment.percentage else None,
            bedrag=str(moment.bedrag) if moment.bedrag else None,
            bron_artikel=moment.bron_artikel,
            bron_tekst=moment.bron_tekst,
            is_recurring=moment.terugkerend,
            recurrence_info=moment.frequentie,
            is_future=is_future,
            tags=tags,
            source_moment_id=moment.moment_id
        )

    @classmethod
    def from_event(cls, event: CAOEvent) -> "TimelineEntry":
        """Create a timeline entry from a CAOEvent."""
        # Map event type to category
        category_map = {
            CAOEventType.CAO_NIEUW: "document",
            CAOEventType.CAO_GEWIJZIGD: "document",
            CAOEventType.CAO_VERLOPEN: "document",
            CAOEventType.LOON_WIJZIGING: "loon",
            CAOEventType.TOESLAG_WIJZIGING: "toeslag",
            CAOEventType.WML_AANPASSING: "wettelijk",
            CAOEventType.WETGEVING_WIJZIGING: "wettelijk",
        }

        categorie = category_map.get(event.event_type, "overig")

        return cls(
            entry_id=f"event_{event.event_type}_{event.timestamp.timestamp()}",
            entry_type=TimelineEntryType.NOTIFICATION,
            datum=event.timestamp.date(),
            titel=event.beschrijving[:100],
            beschrijving=event.beschrijving,
            categorie=categorie,
            icon=_get_icon_for_event_type(event.event_type),
            impact_level="high" if "cao_" in event.event_type.value else "medium",
            oude_waarde=event.oude_waarde,
            nieuwe_waarde=event.nieuwe_waarde,
            bron_artikel=event.bron_artikel,
            bron_tekst=event.details.get("bron_tekst") if event.details else None,
            is_future=False,
            tags=[event.event_type.value, categorie],
            source_event_id=event.moment_id
        )


class CAOTimeline(BaseModel):
    """Complete timeline for a CAO with all entries and metadata."""

    cao_naam: str
    cao_versie: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Timeline data
    entries: list[TimelineEntry] = Field(default_factory=list)

    # Timeline boundaries
    start_date: date | None = None
    end_date: date | None = None

    # Statistics
    total_entries: int = 0
    future_entries: int = 0
    past_entries: int = 0

    # Categories present
    categories: list[str] = Field(default_factory=list)

    def add_entry(self, entry: TimelineEntry) -> None:
        """Add an entry to the timeline and update statistics."""
        self.entries.append(entry)
        self._update_stats()

    def add_moment(self, moment: Moment) -> None:
        """Add a moment to the timeline."""
        entry = TimelineEntry.from_moment(moment)
        self.add_entry(entry)

    def add_event(self, event: CAOEvent) -> None:
        """Add an event to the timeline."""
        entry = TimelineEntry.from_event(event)
        self.add_entry(entry)

    def sort_entries(self) -> None:
        """Sort entries chronologically, with undated entries at the end."""
        def sort_key(entry: TimelineEntry) -> tuple:
            if entry.datum:
                return (0, entry.datum)
            else:
                return (1, datetime.max.date())

        self.entries.sort(key=sort_key)

    def filter_by_category(self, category: str) -> list[TimelineEntry]:
        """Get entries filtered by category."""
        return [e for e in self.entries if e.categorie == category]

    def filter_by_date_range(self, start: date, end: date) -> list[TimelineEntry]:
        """Get entries within a date range."""
        return [
            e for e in self.entries
            if e.datum and start <= e.datum <= end
        ]

    def get_future_entries(self) -> list[TimelineEntry]:
        """Get all future entries."""
        return [e for e in self.entries if e.is_future]

    def get_recurring_entries(self) -> list[TimelineEntry]:
        """Get all recurring entries."""
        return [e for e in self.entries if e.is_recurring]

    def _update_stats(self) -> None:
        """Update timeline statistics."""
        self.total_entries = len(self.entries)
        self.future_entries = len([e for e in self.entries if e.is_future])
        self.past_entries = self.total_entries - self.future_entries

        # Update date boundaries
        dated_entries = [e for e in self.entries if e.datum]
        if dated_entries:
            dates = [e.datum for e in dated_entries]
            self.start_date = min(dates)
            self.end_date = max(dates)

        # Update categories
        self.categories = list(set(e.categorie for e in self.entries))


def _get_icon_for_category(category: MomentCategorie) -> str:
    """Get icon identifier for a moment category."""
    icon_map = {
        MomentCategorie.LOON: "💰",
        MomentCategorie.DOCUMENT: "📄",
        MomentCategorie.UITKERING: "💵",
        MomentCategorie.WERKNEMER: "👤",
        MomentCategorie.TOESLAG: "➕",
        MomentCategorie.WETTELIJK: "⚖️",
        MomentCategorie.PENSIOEN: "🏦",
        MomentCategorie.INLENERSBELONING: "💼",
    }
    return icon_map.get(category, "📌")


def _get_icon_for_event_type(event_type: CAOEventType) -> str:
    """Get icon identifier for an event type."""
    icon_map = {
        CAOEventType.CAO_NIEUW: "🆕",
        CAOEventType.CAO_GEWIJZIGD: "✏️",
        CAOEventType.CAO_VERLOPEN: "⏰",
        CAOEventType.LOON_WIJZIGING: "💰",
        CAOEventType.TOESLAG_WIJZIGING: "➕",
        CAOEventType.WML_AANPASSING: "📊",
        CAOEventType.WETGEVING_WIJZIGING: "⚖️",
    }
    return icon_map.get(event_type, "📌")