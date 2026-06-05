#!/usr/bin/env python3
"""Analyze results from Mistral-only hybrid pipeline test run."""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# CAOs that were processed
CAOS = [
    ("Achmea", "1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024"),
    ("IKEA", "1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024"),
    ("Rabobank", "1055-rabobank-cao-2024-2025-v01102024"),
    ("Metalektro", "315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024"),
]

def load_setu(filename: str) -> dict | None:
    """Load SETU JSON file."""
    filepath = Path(f"data/setu/{filename}.setu.json")
    if not filepath.exists():
        return None
    return json.loads(filepath.read_text())

def analyze_cao(name: str, filename: str) -> dict:
    """Analyze a single CAO extraction."""
    setu = load_setu(filename)

    if not setu:
        return {
            "name": name,
            "status": "❌ NOT FOUND",
            "compliance": None,
            "coverage": None,
            "scales": None,
            "confidence": None,
            "elapsed": None,
        }

    # Extract metadata
    hybrid = setu.get("_hybrid_extraction", {})
    compliance = setu.get("_compliance", {})
    table_ann = hybrid.get("table_annotator", {})

    # Count salary scales
    remuneration = setu.get("remuneration", [])
    scales_count = 0
    if remuneration:
        for rem in remuneration:
            scales = rem.get("salaryScale", [])
            scales_count += len(scales)

    return {
        "name": name,
        "status": "✅ SUCCESS",
        "compliance": compliance.get("status", "unknown"),
        "coverage": compliance.get("coverage", 0),
        "scales": scales_count,
        "confidence": table_ann.get("confidence"),
        "elapsed": setu.get("_extraction_metadata", {}).get("elapsed_seconds"),
        "merge_notes": hybrid.get("merge_notes", []),
    }

def main():
    console.print(Panel(
        "[bold cyan]Mistral-Only Hybrid Pipeline - Test Results Analysis[/bold cyan]",
        title="🎯 Analysis Report"
    ))

    # Analyze all CAOs
    results = []
    for name, filename in CAOS:
        result = analyze_cao(name, filename)
        results.append(result)

    # Create summary table
    table = Table(title="Extraction Results Summary", show_header=True, header_style="bold magenta")
    table.add_column("CAO", style="cyan", width=15)
    table.add_column("Status", width=12)
    table.add_column("Compliance", width=12)
    table.add_column("Coverage %", justify="right", width=10)
    table.add_column("Scales", justify="right", width=8)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("Time (s)", justify="right", width=10)

    for r in results:
        table.add_row(
            r["name"],
            r["status"],
            r["compliance"] or "-",
            f"{r['coverage']:.0f}%" if r['coverage'] is not None else "-",
            str(r["scales"]) if r["scales"] is not None else "-",
            f"{r['confidence']:.2f}" if r['confidence'] is not None else "-",
            f"{r['elapsed']:.1f}" if r['elapsed'] is not None else "-",
        )

    console.print(table)
    console.print()

    # Success rate
    successful = sum(1 for r in results if r["status"] == "✅ SUCCESS")
    success_rate = (successful / len(results)) * 100

    # Average metrics (only successful)
    successful_results = [r for r in results if r["status"] == "✅ SUCCESS"]
    if successful_results:
        avg_coverage = sum(r["coverage"] for r in successful_results) / len(successful_results)
        avg_scales = sum(r["scales"] for r in successful_results) / len(successful_results)
        avg_time = sum(r["elapsed"] for r in successful_results) / len(successful_results)
        avg_confidence = sum(r["confidence"] for r in successful_results if r["confidence"]) / len([r for r in successful_results if r["confidence"]])

        stats_table = Table(title="Performance Statistics", show_header=True)
        stats_table.add_column("Metric", style="yellow")
        stats_table.add_column("Value", style="green", justify="right")

        stats_table.add_row("Success Rate", f"{success_rate:.0f}% ({successful}/{len(results)})")
        stats_table.add_row("Avg Coverage", f"{avg_coverage:.1f}%")
        stats_table.add_row("Avg Salary Scales", f"{avg_scales:.1f}")
        stats_table.add_row("Avg Table Confidence", f"{avg_confidence:.2f}")
        stats_table.add_row("Avg Extraction Time", f"{avg_time:.1f}s")

        console.print(stats_table)
        console.print()

    # Show merge notes for successful extractions
    console.print(Panel("[bold]Merge Strategy Notes[/bold]", style="cyan"))
    for r in successful_results[:2]:  # Show first 2
        console.print(f"\n[bold cyan]{r['name']}:[/bold cyan]")
        for note in r["merge_notes"]:
            console.print(f"  • {note}")

    console.print()

    # Quality assessment
    compliant_count = sum(1 for r in successful_results if r["compliance"] == "compliant")
    high_coverage = sum(1 for r in successful_results if r["coverage"] and r["coverage"] >= 50)
    high_confidence = sum(1 for r in successful_results if r["confidence"] and r["confidence"] >= 0.85)

    quality_panel = Panel(
        f"[bold green]✅ {compliant_count}/{len(successful_results)} SETU Compliant[/bold green]\n"
        f"[bold yellow]📊 {high_coverage}/{len(successful_results)} High Coverage (≥50%)[/bold yellow]\n"
        f"[bold blue]🎯 {high_confidence}/{len(successful_results)} High Confidence (≥0.85)[/bold blue]",
        title="Quality Assessment",
        style="bold"
    )
    console.print(quality_panel)

if __name__ == "__main__":
    main()
