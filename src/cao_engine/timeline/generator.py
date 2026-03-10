"""Timeline generator for CAO developments and notifications."""

from datetime import date, datetime, timedelta
from pathlib import Path

import structlog

from cao_engine.models.events import CAOEvent, CAOEventType
from cao_engine.models.momenten import Moment
from cao_engine.models.timeline import CAOTimeline
from cao_engine.notifications.engine import NotificationEngine
from cao_engine.storage.moment_store import MomentStore

logger = structlog.get_logger(__name__)


class TimelineGenerator:
    """Generates comprehensive timelines for CAOs."""

    def __init__(self, moment_store: MomentStore | None = None, moment_dir: Path | None = None) -> None:
        """Initialize the timeline generator.

        Args:
            moment_store: Optional moment store instance.
            moment_dir: Optional moment directory path. Used if moment_store is None.
        """
        if moment_store:
            self._store = moment_store
        else:
            # Create a settings object with the moment directory
            from cao_engine.config import Settings
            settings = Settings()
            if moment_dir:
                settings.momenten_dir = moment_dir
            self._store = MomentStore(settings)

    def generate_timeline(
        self,
        cao_naam: str,
        include_future: bool = True,
        include_notifications: bool = True,
        date_range: tuple[date, date] | None = None,
    ) -> CAOTimeline:
        """Generate a complete timeline for a CAO.

        Args:
            cao_naam: Name of the CAO
            include_future: Include future moments
            include_notifications: Generate and include notification events
            date_range: Optional date range to limit the timeline

        Returns:
            Complete timeline with all entries
        """
        logger.info("Generating timeline", cao_naam=cao_naam)

        # Create timeline
        timeline = CAOTimeline(cao_naam=cao_naam)

        # Load moments
        try:
            moments = self._store.load(cao_naam).momenten
        except FileNotFoundError:
            logger.warning("No moments found for CAO", cao_naam=cao_naam)
            moments = []

        # Add moments to timeline
        for moment in moments:
            # Skip if outside date range
            if date_range and moment.datum:
                start_date, end_date = date_range
                if not (start_date <= moment.datum <= end_date):
                    continue

            # Skip future moments if not included
            if not include_future and moment.datum and moment.datum > date.today():
                continue

            timeline.add_moment(moment)

        # Generate notification events if requested
        if include_notifications and moments:
            events = self._generate_notification_events(cao_naam, moments, date_range)
            for event in events:
                timeline.add_event(event)

        # Add document lifecycle events
        lifecycle_events = self._generate_lifecycle_events(cao_naam, moments)
        for event in lifecycle_events:
            timeline.add_event(event)

        # Sort entries chronologically
        timeline.sort_entries()
        timeline._update_stats()

        logger.info(
            "Timeline generated",
            cao_naam=cao_naam,
            total_entries=timeline.total_entries,
            future_entries=timeline.future_entries,
        )

        return timeline

    def generate_all_timelines(
        self,
        include_future: bool = True,
        include_notifications: bool = True,
    ) -> dict[str, CAOTimeline]:
        """Generate timelines for all CAOs with moments.

        Returns:
            Dictionary mapping CAO names to their timelines
        """
        timelines = {}

        # Get all CAO names from the moment store
        cao_names = self._store.list_caos()

        for cao_naam in cao_names:
            try:
                timeline = self.generate_timeline(
                    cao_naam=cao_naam,
                    include_future=include_future,
                    include_notifications=include_notifications,
                )
                timelines[cao_naam] = timeline
            except Exception as e:
                logger.error("Failed to generate timeline", cao_naam=cao_naam, error=str(e))

        logger.info("Generated timelines for all CAOs", count=len(timelines))
        return timelines

    def _generate_notification_events(
        self,
        cao_naam: str,
        moments: list[Moment],
        date_range: tuple[date, date] | None = None,
    ) -> list[CAOEvent]:
        """Generate notification events from moments.

        These are simulated notification events that would be sent
        based on the moments.
        """
        events = []

        # Use notification engine to generate events
        engine = NotificationEngine(self._store)

        # For each moment with a date, generate a notification event
        for moment in moments:
            if not moment.datum:
                continue

            # Skip if outside date range
            if date_range:
                start_date, end_date = date_range
                if not (start_date <= moment.datum <= end_date):
                    continue

            # Create notification events at different lead times
            lead_times = [30, 7, 1]  # Days before the moment
            for lead_days in lead_times:
                notification_date = moment.datum - timedelta(days=lead_days)

                # Skip past notifications
                if notification_date < date.today():
                    continue

                event = CAOEvent(
                    event_type=self._get_event_type_for_moment(moment),
                    cao_naam=cao_naam,
                    timestamp=datetime.combine(notification_date, datetime.min.time()),
                    beschrijving=f"Herinnering: {moment.beschrijving} (over {lead_days} dagen)",
                    details={
                        "lead_time_days": lead_days,
                        "moment_id": moment.moment_id,
                        "categorie": moment.categorie.value,
                        "type": moment.type.value,
                    },
                    moment_id=moment.moment_id,
                    bron_artikel=moment.bron_artikel,
                )
                events.append(event)

        return events

    def _generate_lifecycle_events(
        self, cao_naam: str, moments: list[Moment]
    ) -> list[CAOEvent]:
        """Generate CAO document lifecycle events.

        These are derived from document-related moments.
        """
        events = []

        # Find CAO start and end dates from moments
        for moment in moments:
            if moment.type == "cao_ingangsdatum" and moment.datum:
                event = CAOEvent(
                    event_type=CAOEventType.CAO_NIEUW,
                    cao_naam=cao_naam,
                    timestamp=datetime.combine(moment.datum, datetime.min.time()),
                    beschrijving=f"CAO {cao_naam} is ingegaan",
                    details={"source": "moment", "moment_id": moment.moment_id},
                    moment_id=moment.moment_id,
                )
                events.append(event)

            elif moment.type == "cao_einddatum" and moment.datum:
                event = CAOEvent(
                    event_type=CAOEventType.CAO_VERLOPEN,
                    cao_naam=cao_naam,
                    timestamp=datetime.combine(moment.datum, datetime.min.time()),
                    beschrijving=f"CAO {cao_naam} verloopt",
                    details={"source": "moment", "moment_id": moment.moment_id},
                    moment_id=moment.moment_id,
                )
                events.append(event)

        return events

    def _get_event_type_for_moment(self, moment: Moment) -> CAOEventType:
        """Map moment type to appropriate event type."""
        type_map = {
            "loonsverhoging": CAOEventType.LOON_WIJZIGING,
            "periodieke_verhoging": CAOEventType.LOON_WIJZIGING,
            "cao_ingangsdatum": CAOEventType.CAO_NIEUW,
            "cao_einddatum": CAOEventType.CAO_VERLOPEN,
            "toeslag_wijziging": CAOEventType.TOESLAG_WIJZIGING,
            "wml_aanpassing": CAOEventType.WML_AANPASSING,
            "pensioenpremie_wijziging": CAOEventType.PENSIOEN_WIJZIGING,
        }
        return type_map.get(moment.type.value, CAOEventType.CAO_GEWIJZIGD)

    def create_timeline_summary(self, timeline: CAOTimeline) -> dict:
        """Create a summary of the timeline for reporting.

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "cao_naam": timeline.cao_naam,
            "generated_at": timeline.generated_at.isoformat(),
            "total_entries": timeline.total_entries,
            "future_entries": timeline.future_entries,
            "past_entries": timeline.past_entries,
            "date_range": {
                "start": timeline.start_date.isoformat() if timeline.start_date else None,
                "end": timeline.end_date.isoformat() if timeline.end_date else None,
            },
            "categories": {},
            "recurring_entries": len(timeline.get_recurring_entries()),
            "upcoming_30_days": 0,
        }

        # Count by category
        for category in timeline.categories:
            summary["categories"][category] = len(timeline.filter_by_category(category))

        # Count upcoming in next 30 days
        if timeline.entries:
            today = date.today()
            thirty_days = today + timedelta(days=30)
            upcoming = timeline.filter_by_date_range(today, thirty_days)
            summary["upcoming_30_days"] = len(upcoming)

        return summary