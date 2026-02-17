"""Notification message templates.

Each notification contains: wat, was/wordt, wanneer, impact, actie, bron.
"""

from cao_engine.models.events import CAOEvent


def format_notification(event: CAOEvent) -> str:
    """Format a CAOEvent into a human-readable notification message."""
    lines = [
        f"=== CAO Notificatie: {event.cao_naam} ===",
        "",
        f"Type: {event.event_type.value}",
        f"Wat: {event.beschrijving}",
    ]

    if event.oude_waarde and event.nieuwe_waarde:
        lines.append(f"Was: {event.oude_waarde}")
        lines.append(f"Wordt: {event.nieuwe_waarde}")

    details = event.details or {}
    if details.get("percentage"):
        lines.append(f"Percentage: {details['percentage']}%")
    if details.get("bedrag"):
        lines.append(f"Bedrag: EUR {details['bedrag']}")

    if event.bron_artikel:
        lines.append(f"Bron: {event.bron_artikel}")

    if details.get("bron_tekst"):
        lines.append("")
        lines.append("Originele CAO-tekst:")
        lines.append(f'"{details["bron_tekst"]}"')

    if details.get("voorwaarden"):
        lines.append("")
        lines.append("Voorwaarden:")
        for v in details["voorwaarden"]:
            lines.append(f"  - {v}")

    lines.append("")
    lines.append(f"Tijdstip melding: {event.timestamp.isoformat()}")

    return "\n".join(lines)


def format_notification_html(event: CAOEvent) -> str:
    """Format a CAOEvent as an HTML email body."""
    details = event.details or {}

    html_parts = [
        f"<h2>CAO Notificatie: {event.cao_naam}</h2>",
        f"<p><strong>Type:</strong> {event.event_type.value}</p>",
        f"<p><strong>Wat:</strong> {event.beschrijving}</p>",
    ]

    if event.oude_waarde and event.nieuwe_waarde:
        html_parts.append(
            f"<p><strong>Was:</strong> {event.oude_waarde} "
            f"&rarr; <strong>Wordt:</strong> {event.nieuwe_waarde}</p>"
        )

    if details.get("percentage"):
        html_parts.append(f"<p><strong>Percentage:</strong> {details['percentage']}%</p>")

    if event.bron_artikel:
        html_parts.append(f"<p><strong>Bron:</strong> {event.bron_artikel}</p>")

    if details.get("bron_tekst"):
        html_parts.append(
            f'<blockquote style="border-left:3px solid #ccc;padding-left:12px;color:#555">'
            f"{details['bron_tekst']}</blockquote>"
        )

    return "\n".join(html_parts)
