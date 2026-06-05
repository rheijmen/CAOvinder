# CAO Timeline Visualization Feature

## Overview
The CAO Timeline feature provides an interactive visual representation of all developments, changes, and notifications related to each Collective Labour Agreement (CAO). This allows users to see a chronological overview of past events and upcoming changes.

## Features

### Visual Timeline
- **Interactive HTML visualization** with color-coded categories
- **Chronological ordering** of all events and moments
- **Expandable details** for each event showing source text and references
- **Today marker** showing the current position in time
- **Future vs Past differentiation** with visual indicators

### Event Categories
Each event is color-coded by category:
- 🔵 **Loon (Salary)** - Blue: Salary increases, periodic raises
- 🟢 **Document** - Green: CAO lifecycle events (start, end, AVV)
- 🟡 **Uitkering (Payments)** - Orange: Holiday allowances, year-end bonuses
- 🟣 **Toeslag (Allowances)** - Purple: Allowance changes
- 🔴 **Wettelijk (Legal)** - Red: Regulatory and legal changes
- 🟦 **Pensioen (Pension)** - Turquoise: Pension-related changes
- ⚫ **Werknemer (Employee)** - Dark gray: Employee-specific moments
- 🟫 **Overig (Other)** - Light gray: Other events

### Interactive Features
- **Filter by category** - Click filter buttons to show/hide specific event types
- **Expandable details** - Click on event markers to see full information
- **Hover tooltips** - Quick information on hover
- **Search functionality** (in JavaScript) - Find specific events
- **Responsive design** - Works on mobile and desktop

## Usage

### Generate Timeline for Specific CAO
```bash
python -m cao_engine generate-timeline "CAO Metaal en Techniek"
```

Options:
- `--format {html|json|both}` - Output format (default: both)
- `--no-future` - Exclude future events
- `--no-notifications` - Exclude generated notification events
- `--output-dir PATH` - Custom output directory

### Generate Timelines for All CAOs
```bash
python -m cao_engine generate-all-timelines
```
This also creates an `index.html` file with an overview of all timelines.

### List Available Timelines
```bash
python -m cao_engine list-timelines
```

## Output Files

### Timeline Files
- `data/timelines/{cao_name}_timeline.html` - Interactive HTML visualization
- `data/timelines/{cao_name}_timeline.json` - Timeline data in JSON format
- `data/timelines/index.html` - Overview page listing all CAO timelines

### Viewing Timelines
1. Open the HTML file in any modern web browser
2. Use the filter buttons to focus on specific categories
3. Click on event markers for detailed information
4. Scroll or use browser zoom to navigate long timelines

## Data Sources

The timeline combines data from multiple sources:
1. **Moments** - Extracted date-driven events from CAO documents
2. **Notifications** - Generated reminder events (30, 7, 1 day before)
3. **Document Lifecycle** - CAO start/end dates, AVV periods
4. **Regulatory Changes** - Legal and regulatory updates

## Implementation

### Components
- `src/cao_engine/models/timeline.py` - Timeline data models
- `src/cao_engine/timeline/generator.py` - Timeline generation logic
- `src/cao_engine/timeline/visualization.py` - HTML/SVG rendering
- `src/cao_engine/timeline/storage.py` - Timeline persistence
- `src/cao_engine/cli.py` - CLI commands

### Timeline Entry Structure
Each timeline entry contains:
- **Date and time** information
- **Title and description**
- **Category and type** classification
- **Impact level** (high/medium/low)
- **Source reference** (CAO article)
- **Original text** from the CAO
- **Changes** (old value → new value)
- **Affected groups** (functiegroep codes)

## Example Timeline Events

### Salary Increase
- Date: 2024-07-01
- Category: Loon
- Description: "7% salary increase for employees 21+ in groups B-J"
- Source: Article 41 lid 1

### Holiday Allowance Payment
- Date: 2024-05-31
- Category: Uitkering
- Description: "Annual holiday allowance payment"
- Recurring: Yearly

### CAO Expiry
- Date: 2026-01-31
- Category: Document
- Description: "CAO Metaal en Techniek expires"
- Impact: High

## Benefits

1. **Compliance Tracking** - Never miss important CAO changes
2. **Planning** - Prepare for upcoming changes in advance
3. **Historical Context** - Understand the evolution of agreements
4. **Notification Management** - See when notifications will be sent
5. **Visual Understanding** - Quick grasp of CAO lifecycle and changes

## Future Enhancements

Potential improvements:
- Export to PDF/PNG for reports
- Comparison between multiple CAO timelines
- Integration with calendar systems
- Real-time updates from CAO sources
- Advanced filtering and search
- Timeline annotations and comments