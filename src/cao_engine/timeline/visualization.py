"""Timeline visualization module for generating interactive HTML/SVG timelines."""

import json
from pathlib import Path

import structlog

from cao_engine.models.timeline import CAOTimeline, TimelineEntry

logger = structlog.get_logger(__name__)


class TimelineVisualizer:
    """Generates interactive HTML visualizations of CAO timelines."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the visualizer.

        Args:
            template_dir: Optional custom template directory
        """
        self.template_dir = template_dir or Path(__file__).parent / "templates"

    def generate_html(
        self,
        timeline: CAOTimeline,
        title: str | None = None,
        show_filters: bool = True,
        show_legend: bool = True,
    ) -> str:
        """Generate an interactive HTML timeline.

        Args:
            timeline: The timeline to visualize
            title: Optional custom title (defaults to CAO name)
            show_filters: Show category filter buttons
            show_legend: Show color legend

        Returns:
            Complete HTML document as string
        """
        title = title or f"Timeline: {timeline.cao_naam}"

        # Prepare timeline data for JSON embedding
        timeline_data = self._prepare_timeline_data(timeline)

        # Generate HTML
        html = self._generate_html_document(
            title=title,
            timeline_data=timeline_data,
            timeline=timeline,
            show_filters=show_filters,
            show_legend=show_legend,
        )

        return html

    def generate_svg(self, timeline: CAOTimeline, width: int = 1200, height: int = 600) -> str:
        """Generate an SVG timeline visualization.

        Args:
            timeline: The timeline to visualize
            width: SVG width in pixels
            height: SVG height in pixels

        Returns:
            SVG document as string
        """
        # This is a simplified SVG generator
        # For production, consider using a proper SVG library

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            '<rect width="100%" height="100%" fill="white"/>',
        ]

        # Add timeline axis
        svg_parts.append(f'<line x1="50" y1="{height//2}" x2="{width-50}" y2="{height//2}" stroke="black" stroke-width="2"/>')

        # Add entries (simplified)
        if timeline.entries:
            x_step = (width - 100) / max(len(timeline.entries), 1)
            for i, entry in enumerate(timeline.entries):
                x = 50 + i * x_step
                y = height // 2

                # Add circle for entry
                color = self._get_category_color(entry.categorie)
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{color}"/>')

                # Add label
                if entry.datum:
                    svg_parts.append(
                        f'<text x="{x}" y="{y-15}" text-anchor="middle" font-size="10">'
                        f'{entry.datum.isoformat()}</text>'
                    )

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _prepare_timeline_data(self, timeline: CAOTimeline) -> str:
        """Prepare timeline data for JSON embedding in HTML."""
        # Convert timeline entries to JSON-serializable format
        entries_data = []
        for entry in timeline.entries:
            entry_dict = {
                "id": entry.entry_id,
                "type": entry.entry_type.value,
                "date": entry.datum.isoformat() if entry.datum else None,
                "dateDescription": entry.datum_beschrijving,
                "title": entry.titel,
                "description": entry.beschrijving,
                "category": entry.categorie,
                "icon": entry.icon,
                "impactLevel": entry.impact_level,
                "oldValue": entry.oude_waarde,
                "newValue": entry.nieuwe_waarde,
                "percentage": entry.percentage,
                "amount": entry.bedrag,
                "sourceArticle": entry.bron_artikel,
                "sourceText": entry.bron_tekst,
                "isRecurring": entry.is_recurring,
                "recurrenceInfo": entry.recurrence_info,
                "isFuture": entry.is_future,
                "tags": entry.tags,
            }
            entries_data.append(entry_dict)

        timeline_json = {
            "caoNaam": timeline.cao_naam,
            "caoVersie": timeline.cao_versie,
            "generatedAt": timeline.generated_at.isoformat(),
            "entries": entries_data,
            "statistics": {
                "total": timeline.total_entries,
                "future": timeline.future_entries,
                "past": timeline.past_entries,
            },
            "categories": timeline.categories,
            "dateRange": {
                "start": timeline.start_date.isoformat() if timeline.start_date else None,
                "end": timeline.end_date.isoformat() if timeline.end_date else None,
            },
        }

        return json.dumps(timeline_json, ensure_ascii=False, indent=2)

    def _generate_html_document(
        self,
        title: str,
        timeline_data: str,
        timeline: CAOTimeline,
        show_filters: bool,
        show_legend: bool,
    ) -> str:
        """Generate the complete HTML document."""
        # Category colors for consistent visualization
        category_colors = {
            "loon": "#3498db",      # Blue
            "document": "#27ae60",  # Green
            "uitkering": "#f39c12", # Orange
            "toeslag": "#9b59b6",   # Purple
            "wettelijk": "#e74c3c", # Red
            "pensioen": "#1abc9c",  # Turquoise
            "werknemer": "#34495e", # Dark gray
            "overig": "#95a5a6",    # Light gray
        }

        html = f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="timeline-container">
        <header class="timeline-header">
            <h1>{title}</h1>
            <div class="timeline-stats">
                <span class="stat">Totaal: {timeline.total_entries} gebeurtenissen</span>
                <span class="stat">Toekomst: {timeline.future_entries}</span>
                <span class="stat">Verleden: {timeline.past_entries}</span>
            </div>
        </header>

        {self._generate_filters_html(timeline.categories) if show_filters else ""}
        {self._generate_legend_html(category_colors) if show_legend else ""}

        <div class="timeline-wrapper">
            <div class="timeline-line"></div>
            <div class="timeline-today-marker" id="todayMarker">
                <div class="today-label">Vandaag</div>
            </div>
            <div class="timeline-entries" id="timelineEntries">
                {self._generate_entries_html(timeline)}
            </div>
        </div>
    </div>

    <script>
        const timelineData = {timeline_data};
        {self._get_javascript_code()}
    </script>
</body>
</html>'''
        return html

    def _generate_filters_html(self, categories: list[str]) -> str:
        """Generate HTML for category filters."""
        filters = ['<div class="timeline-filters">']
        filters.append('<button class="filter-btn active" data-category="all">Alle</button>')

        for category in sorted(categories):
            display_name = category.replace("_", " ").title()
            color = self._get_category_color(category)
            filters.append(
                f'<button class="filter-btn" data-category="{category}" '
                f'style="border-left: 4px solid {color}">{display_name}</button>'
            )

        filters.append('</div>')
        return '\n'.join(filters)

    def _generate_legend_html(self, category_colors: dict[str, str]) -> str:
        """Generate HTML for color legend."""
        legend = ['<div class="timeline-legend">']
        for category, color in category_colors.items():
            display_name = category.replace("_", " ").title()
            legend.append(
                f'<div class="legend-item">'
                f'<span class="legend-color" style="background: {color}"></span>'
                f'<span class="legend-label">{display_name}</span>'
                f'</div>'
            )
        legend.append('</div>')
        return '\n'.join(legend)

    def _generate_entries_html(self, timeline: CAOTimeline) -> str:
        """Generate HTML for timeline entries."""
        entries_html = []

        for entry in timeline.entries:
            date_str = entry.datum.strftime("%d-%m-%Y") if entry.datum else entry.datum_beschrijving or "Geen datum"
            color = self._get_category_color(entry.categorie)

            entry_class = "timeline-entry"
            if entry.is_future:
                entry_class += " future"
            if entry.is_recurring:
                entry_class += " recurring"

            entry_html = f'''
            <div class="{entry_class}" data-category="{entry.categorie}" data-id="{entry.entry_id}">
                <div class="entry-marker" style="background: {color}">
                    <span class="entry-icon">{entry.icon or "📌"}</span>
                </div>
                <div class="entry-content">
                    <div class="entry-date">{date_str}</div>
                    <div class="entry-title">{entry.titel}</div>
                    <div class="entry-description">{entry.beschrijving}</div>
                    {self._generate_entry_details_html(entry)}
                </div>
            </div>
            '''
            entries_html.append(entry_html)

        return '\n'.join(entries_html)

    def _generate_entry_details_html(self, entry: TimelineEntry) -> str:
        """Generate HTML for entry details (expandable section)."""
        details = []

        if entry.oude_waarde or entry.nieuwe_waarde:
            details.append('<div class="entry-changes">')
            if entry.oude_waarde:
                details.append(f'<span class="old-value">Was: {entry.oude_waarde}</span>')
            if entry.nieuwe_waarde:
                details.append(f'<span class="new-value">Wordt: {entry.nieuwe_waarde}</span>')
            details.append('</div>')

        if entry.percentage or entry.bedrag:
            details.append('<div class="entry-values">')
            if entry.percentage:
                details.append(f'<span class="percentage">Percentage: {entry.percentage}%</span>')
            if entry.bedrag:
                details.append(f'<span class="amount">Bedrag: €{entry.bedrag}</span>')
            details.append('</div>')

        if entry.bron_artikel:
            details.append(f'<div class="entry-source">Bron: {entry.bron_artikel}</div>')

        if entry.bron_tekst:
            details.append(
                f'<div class="entry-source-text">'
                f'<details><summary>Originele tekst</summary>'
                f'<blockquote>{entry.bron_tekst}</blockquote>'
                f'</details></div>'
            )

        return '\n'.join(details) if details else ''

    def _get_category_color(self, category: str) -> str:
        """Get color for a category."""
        colors = {
            "loon": "#3498db",
            "document": "#27ae60",
            "uitkering": "#f39c12",
            "toeslag": "#9b59b6",
            "wettelijk": "#e74c3c",
            "pensioen": "#1abc9c",
            "werknemer": "#34495e",
            "inlenersbeloning": "#16a085",
        }
        return colors.get(category, "#95a5a6")

    def _get_css_styles(self) -> str:
        """Get CSS styles for the timeline."""
        return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }

        .timeline-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .timeline-header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .timeline-header h1 {
            color: #2c3e50;
            margin-bottom: 1rem;
        }

        .timeline-stats {
            display: flex;
            justify-content: center;
            gap: 2rem;
            font-size: 0.9rem;
            color: #7f8c8d;
        }

        .timeline-filters {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }

        .filter-btn {
            padding: 0.5rem 1rem;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .filter-btn:hover {
            background: #f0f0f0;
        }

        .filter-btn.active {
            background: #3498db;
            color: white;
            border-color: #3498db;
        }

        .timeline-legend {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }

        .timeline-wrapper {
            position: relative;
            padding: 2rem 0;
        }

        .timeline-line {
            position: absolute;
            left: 50%;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #cbd5e0;
            transform: translateX(-50%);
        }

        .timeline-today-marker {
            position: absolute;
            left: 0;
            right: 0;
            height: 2px;
            background: #e74c3c;
            z-index: 10;
        }

        .today-label {
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            background: #e74c3c;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.8rem;
        }

        .timeline-entries {
            position: relative;
        }

        .timeline-entry {
            display: flex;
            align-items: flex-start;
            margin-bottom: 2rem;
            opacity: 0;
            animation: fadeIn 0.5s forwards;
            position: relative;
        }

        .timeline-entry:nth-child(odd) {
            flex-direction: row-reverse;
        }

        .timeline-entry:nth-child(odd) .entry-content {
            text-align: right;
            margin-right: 2rem;
        }

        .timeline-entry:nth-child(even) .entry-content {
            margin-left: 2rem;
        }

        .entry-marker {
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #3498db;
            z-index: 5;
            cursor: pointer;
            transition: transform 0.3s;
        }

        .entry-marker:hover {
            transform: translateX(-50%) scale(1.2);
        }

        .entry-icon {
            font-size: 1.2rem;
        }

        .entry-content {
            flex: 1;
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 45%;
        }

        .entry-date {
            font-size: 0.85rem;
            color: #7f8c8d;
            margin-bottom: 0.5rem;
        }

        .entry-title {
            font-weight: bold;
            margin-bottom: 0.5rem;
            color: #2c3e50;
        }

        .entry-description {
            color: #555;
            margin-bottom: 0.5rem;
        }

        .entry-changes,
        .entry-values,
        .entry-source {
            margin-top: 0.5rem;
            font-size: 0.9rem;
        }

        .old-value {
            color: #e74c3c;
            margin-right: 1rem;
        }

        .new-value {
            color: #27ae60;
        }

        .entry-source-text {
            margin-top: 0.5rem;
        }

        .entry-source-text summary {
            cursor: pointer;
            color: #3498db;
            font-size: 0.9rem;
        }

        .entry-source-text blockquote {
            margin-top: 0.5rem;
            padding: 0.5rem;
            background: #f8f9fa;
            border-left: 3px solid #3498db;
            font-style: italic;
            color: #666;
        }

        .timeline-entry.future .entry-marker {
            opacity: 0.7;
            border: 2px dashed white;
        }

        .timeline-entry.recurring .entry-marker::after {
            content: "🔄";
            position: absolute;
            top: -8px;
            right: -8px;
            font-size: 0.8rem;
        }

        .timeline-entry.hidden {
            display: none;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (max-width: 768px) {
            .timeline-entry {
                flex-direction: column !important;
            }

            .timeline-entry .entry-content {
                text-align: left !important;
                margin: 1rem !important;
                max-width: 100% !important;
            }

            .timeline-line {
                left: 20px;
            }

            .entry-marker {
                left: 20px !important;
            }
        }
        '''

    def _get_javascript_code(self) -> str:
        """Get JavaScript code for interactive features."""
        return '''
        // Position today marker
        function positionTodayMarker() {
            const today = new Date();
            const entries = timelineData.entries.filter(e => e.date);

            if (entries.length > 0) {
                const dates = entries.map(e => new Date(e.date));
                const minDate = new Date(Math.min(...dates));
                const maxDate = new Date(Math.max(...dates));
                const totalDays = (maxDate - minDate) / (1000 * 60 * 60 * 24);
                const daysFromStart = (today - minDate) / (1000 * 60 * 60 * 24);
                const percentage = (daysFromStart / totalDays) * 100;

                const todayMarker = document.getElementById('todayMarker');
                if (todayMarker && percentage >= 0 && percentage <= 100) {
                    todayMarker.style.top = `${percentage}%`;
                }
            }
        }

        // Filter functionality
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const category = this.dataset.category;

                // Update active button
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                // Filter entries
                document.querySelectorAll('.timeline-entry').forEach(entry => {
                    if (category === 'all' || entry.dataset.category === category) {
                        entry.classList.remove('hidden');
                    } else {
                        entry.classList.add('hidden');
                    }
                });
            });
        });

        // Expand/collapse entry details
        document.querySelectorAll('.entry-marker').forEach(marker => {
            marker.addEventListener('click', function() {
                const entry = this.closest('.timeline-entry');
                const content = entry.querySelector('.entry-content');
                content.classList.toggle('expanded');
            });
        });

        // Initialize
        positionTodayMarker();

        // Search functionality
        function searchTimeline(query) {
            const lowerQuery = query.toLowerCase();
            document.querySelectorAll('.timeline-entry').forEach(entry => {
                const content = entry.textContent.toLowerCase();
                if (content.includes(lowerQuery)) {
                    entry.classList.remove('hidden');
                } else {
                    entry.classList.add('hidden');
                }
            });
        }
        '''