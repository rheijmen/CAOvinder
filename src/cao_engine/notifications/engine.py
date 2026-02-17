"""Notification engine - reads moments, matches subscriptions, fires events.

The engine periodically scans the MomentStore for upcoming moments
and generates CAOEvents for matching subscribers.
"""

from datetime import date

import structlog

from cao_engine.models.events import CAOEvent, CAOEventType
from cao_engine.models.momenten import Moment, MomentCategorie
from cao_engine.models.subscriptions import Subscriber
from cao_engine.storage.moment_store import MomentStore

logger = structlog.get_logger(__name__)

# Map moment categories to event types
CATEGORY_TO_EVENT: dict[MomentCategorie, CAOEventType] = {
    MomentCategorie.LOON: CAOEventType.LOON_WIJZIGING,
    MomentCategorie.DOCUMENT: CAOEventType.CAO_GEWIJZIGD,
    MomentCategorie.UITKERING: CAOEventType.LOON_WIJZIGING,
    MomentCategorie.TOESLAG: CAOEventType.TOESLAG_WIJZIGING,
    MomentCategorie.PENSIOEN: CAOEventType.PENSIOEN_WIJZIGING,
    MomentCategorie.WETTELIJK: CAOEventType.WETGEVING_WIJZIGING,
    MomentCategorie.INLENERSBELONING: CAOEventType.ILB_ELEMENT_WIJZIGING,
}


class NotificationEngine:
    """Scans moments and generates notification events."""

    def __init__(self, moment_store: MomentStore) -> None:
        self._store = moment_store

    def scan_upcoming(
        self, days_ahead: int = 30, subscribers: list[Subscriber] | None = None
    ) -> list[CAOEvent]:
        """Scan for upcoming moments and generate events.

        Returns CAOEvents for all moments occurring within days_ahead.
        If subscribers are provided, filters events based on their subscriptions.
        """
        moments = self._store.query_upcoming(days_ahead=days_ahead)

        if not moments:
            logger.info("No upcoming moments found", days_ahead=days_ahead)
            return []

        events: list[CAOEvent] = []
        for moment in moments:
            event = self._moment_to_event(moment)
            if subscribers:
                if self._matches_any_subscriber(event, moment, subscribers):
                    events.append(event)
            else:
                events.append(event)

        logger.info("Generated events", count=len(events), days_ahead=days_ahead)
        return events

    def scan_date_range(self, start: date, end: date) -> list[CAOEvent]:
        """Scan for moments in a specific date range."""
        moments = self._store.query_by_date_range(start, end)
        return [self._moment_to_event(m) for m in moments]

    def _moment_to_event(self, moment: Moment) -> CAOEvent:
        """Convert a Moment to a CAOEvent for notification."""
        event_type = CATEGORY_TO_EVENT.get(moment.categorie, CAOEventType.CAO_GEWIJZIGD)

        beschrijving_parts = [moment.beschrijving]
        if moment.doelgroep:
            beschrijving_parts.append(f"Doelgroep: {moment.doelgroep}")
        if moment.datum:
            beschrijving_parts.append(f"Datum: {moment.datum.isoformat()}")

        return CAOEvent(
            event_type=event_type,
            cao_naam=moment.cao_naam,
            beschrijving=" | ".join(beschrijving_parts),
            oude_waarde=moment.oude_waarde,
            nieuwe_waarde=moment.nieuwe_waarde,
            moment_id=moment.moment_id,
            bron_artikel=moment.bron_artikel,
            details={
                "categorie": moment.categorie,
                "type": moment.type,
                "percentage": str(moment.percentage) if moment.percentage else None,
                "bedrag": str(moment.bedrag) if moment.bedrag else None,
                "bron_tekst": moment.bron_tekst,
                "voorwaarden": moment.voorwaarden,
            },
        )

    def _matches_any_subscriber(
        self, event: CAOEvent, moment: Moment, subscribers: list[Subscriber]
    ) -> bool:
        """Check if an event matches any subscriber's filters."""
        for sub in subscribers:
            if not sub.active:
                continue

            # Check global subscriptions
            if event.event_type in sub.global_event_types:
                return True

            # Check CAO-specific subscriptions
            for cao_sub in sub.cao_subscriptions:
                if (
                    cao_sub.cao_naam == event.cao_naam
                    and (not cao_sub.event_types or event.event_type in cao_sub.event_types)
                    and moment.datum
                ):
                    days_until = (moment.datum - date.today()).days
                    if days_until <= cao_sub.lead_time_days:
                        return True

        return False
