"""Timeline storage module for persisting generated timelines."""

import json
from datetime import datetime
from pathlib import Path

import structlog

from cao_engine.models.timeline import CAOTimeline

logger = structlog.get_logger(__name__)


class TimelineStorage:
    """Manages storage of generated timelines."""

    def __init__(self, data_dir: Path | str = "data/timelines") -> None:
        """Initialize timeline storage.

        Args:
            data_dir: Directory for storing timeline files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_timeline(
        self,
        timeline: CAOTimeline,
        format: str = "both",
        html_content: str | None = None,
    ) -> tuple[Path | None, Path | None]:
        """Save a timeline to disk.

        Args:
            timeline: The timeline to save
            format: Save format - "json", "html", or "both"
            html_content: Pre-generated HTML content (if format includes html)

        Returns:
            Tuple of (json_path, html_path) where applicable
        """
        cao_name_clean = self._clean_filename(timeline.cao_naam)
        json_path = None
        html_path = None

        # Save JSON format
        if format in ["json", "both"]:
            json_path = self.data_dir / f"{cao_name_clean}_timeline.json"
            self._save_json(timeline, json_path)
            logger.info("Saved timeline JSON", path=str(json_path))

        # Save HTML format
        if format in ["html", "both"] and html_content:
            html_path = self.data_dir / f"{cao_name_clean}_timeline.html"
            self._save_html(html_content, html_path)
            logger.info("Saved timeline HTML", path=str(html_path))

        return json_path, html_path

    def load_timeline(self, cao_naam: str) -> CAOTimeline | None:
        """Load a timeline from disk.

        Args:
            cao_naam: Name of the CAO

        Returns:
            Timeline object or None if not found
        """
        cao_name_clean = self._clean_filename(cao_naam)
        json_path = self.data_dir / f"{cao_name_clean}_timeline.json"

        if not json_path.exists():
            logger.warning("Timeline not found", cao_naam=cao_naam, path=str(json_path))
            return None

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct the timeline
            # Note: This is simplified - in production, you'd need proper deserialization
            timeline = CAOTimeline(
                cao_naam=data["cao_naam"],
                cao_versie=data.get("cao_versie"),
                generated_at=datetime.fromisoformat(data["generated_at"]),
            )

            logger.info("Loaded timeline", cao_naam=cao_naam)
            return timeline

        except Exception as e:
            logger.error("Failed to load timeline", cao_naam=cao_naam, error=str(e))
            return None

    def list_timelines(self) -> list[str]:
        """List all available timelines.

        Returns:
            List of CAO names with saved timelines
        """
        timelines = []
        for json_file in self.data_dir.glob("*_timeline.json"):
            # Extract CAO name from filename
            cao_name = json_file.stem.replace("_timeline", "").replace("_", " ")
            timelines.append(cao_name)

        return sorted(timelines)

    def delete_timeline(self, cao_naam: str) -> bool:
        """Delete a timeline from storage.

        Args:
            cao_naam: Name of the CAO

        Returns:
            True if deleted, False if not found
        """
        cao_name_clean = self._clean_filename(cao_naam)
        deleted = False

        # Delete JSON file
        json_path = self.data_dir / f"{cao_name_clean}_timeline.json"
        if json_path.exists():
            json_path.unlink()
            deleted = True

        # Delete HTML file
        html_path = self.data_dir / f"{cao_name_clean}_timeline.html"
        if html_path.exists():
            html_path.unlink()
            deleted = True

        if deleted:
            logger.info("Deleted timeline", cao_naam=cao_naam)
        else:
            logger.warning("Timeline not found for deletion", cao_naam=cao_naam)

        return deleted

    def save_index_html(self, timelines: dict[str, CAOTimeline]) -> Path:
        """Generate and save an index HTML file listing all timelines.

        Args:
            timelines: Dictionary of CAO name to timeline

        Returns:
            Path to the saved index file
        """
        index_path = self.data_dir / "index.html"

        html = self._generate_index_html(timelines)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("Saved timeline index", path=str(index_path))
        return index_path

    def _save_json(self, timeline: CAOTimeline, path: Path) -> None:
        """Save timeline as JSON."""
        # Convert to serializable format
        data = {
            "cao_naam": timeline.cao_naam,
            "cao_versie": timeline.cao_versie,
            "generated_at": timeline.generated_at.isoformat(),
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "entry_type": e.entry_type.value,
                    "datum": e.datum.isoformat() if e.datum else None,
                    "datum_beschrijving": e.datum_beschrijving,
                    "titel": e.titel,
                    "beschrijving": e.beschrijving,
                    "categorie": e.categorie,
                    "icon": e.icon,
                    "impact_level": e.impact_level,
                    "oude_waarde": e.oude_waarde,
                    "nieuwe_waarde": e.nieuwe_waarde,
                    "percentage": e.percentage,
                    "bedrag": e.bedrag,
                    "bron_artikel": e.bron_artikel,
                    "bron_tekst": e.bron_tekst,
                    "is_recurring": e.is_recurring,
                    "recurrence_info": e.recurrence_info,
                    "is_future": e.is_future,
                    "tags": e.tags,
                }
                for e in timeline.entries
            ],
            "statistics": {
                "total_entries": timeline.total_entries,
                "future_entries": timeline.future_entries,
                "past_entries": timeline.past_entries,
            },
            "categories": timeline.categories,
            "date_range": {
                "start": timeline.start_date.isoformat() if timeline.start_date else None,
                "end": timeline.end_date.isoformat() if timeline.end_date else None,
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_html(self, html_content: str, path: Path) -> None:
        """Save HTML content to file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _clean_filename(self, cao_naam: str) -> str:
        """Clean CAO name for use as filename."""
        # Replace spaces and special characters
        clean = cao_naam.lower()
        clean = clean.replace(" ", "_")
        clean = clean.replace("/", "_")
        clean = clean.replace("\\", "_")
        clean = clean.replace(":", "_")
        clean = clean.replace("&", "and")

        # Remove other special characters
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        clean = "".join(c for c in clean if c in allowed)

        return clean

    def _generate_index_html(self, timelines: dict[str, CAOTimeline]) -> str:
        """Generate an index HTML file listing all timelines."""
        rows = []
        for cao_naam, timeline in sorted(timelines.items()):
            cao_name_clean = self._clean_filename(cao_naam)
            html_file = f"{cao_name_clean}_timeline.html"
            json_file = f"{cao_name_clean}_timeline.json"

            date_range = ""
            if timeline.start_date and timeline.end_date:
                date_range = f"{timeline.start_date.strftime('%d-%m-%Y')} tot {timeline.end_date.strftime('%d-%m-%Y')}"

            rows.append(f'''
            <tr>
                <td>{cao_naam}</td>
                <td>{timeline.total_entries}</td>
                <td>{timeline.future_entries}</td>
                <td>{date_range}</td>
                <td>{timeline.generated_at.strftime('%d-%m-%Y %H:%M')}</td>
                <td>
                    <a href="{html_file}" class="btn btn-primary">Bekijk Timeline</a>
                    <a href="{json_file}" class="btn btn-secondary" download>Download JSON</a>
                </td>
            </tr>
            ''')

        html = f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAO Timelines Overzicht</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 2rem;
            text-align: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .btn {{
            display: inline-block;
            padding: 6px 12px;
            margin: 2px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: #3498db;
            color: white;
        }}
        .btn-primary:hover {{
            background: #2980b9;
        }}
        .btn-secondary {{
            background: #95a5a6;
            color: white;
        }}
        .btn-secondary:hover {{
            background: #7f8c8d;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 2rem;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CAO Timelines Overzicht</h1>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(timelines)}</div>
                <div class="stat-label">CAO's</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(t.total_entries for t in timelines.values())}</div>
                <div class="stat-label">Totale Gebeurtenissen</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(t.future_entries for t in timelines.values())}</div>
                <div class="stat-label">Toekomstige Events</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>CAO Naam</th>
                    <th>Gebeurtenissen</th>
                    <th>Toekomstig</th>
                    <th>Periode</th>
                    <th>Gegenereerd</th>
                    <th>Acties</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
</body>
</html>'''
        return html