"""CLI application for the CAO Intelligence Engine."""

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="cao-engine",
    help="CAO Intelligence Engine - Process Dutch CAO documents into structured data",
)
console = Console()


def _get_settings():
    from cao_engine.config import Settings
    from cao_engine.logging_setup import setup_logging

    settings = Settings()
    setup_logging(settings.log_level, settings.log_format)
    return settings


# --- OCR Commands ---


@app.command()
def process_single(
    pdf_path: Path = typer.Argument(..., help="Path to a CAO PDF file"),
) -> None:
    """Process a single CAO PDF through Mistral OCR."""
    settings = _get_settings()
    from cao_engine.ocr.processor import OCRProcessor

    if not pdf_path.exists():
        console.print(f"[red]File not found: {pdf_path}[/red]")
        raise typer.Exit(1)

    processor = OCRProcessor(settings)
    result = processor.process_single(pdf_path)

    console.print(Panel(
        f"[green]File:[/green] {pdf_path.name}\n"
        f"[green]Pages:[/green] {result.total_pages}\n"
        f"[green]Model:[/green] {result.model}\n"
        f"[green]Output:[/green] {settings.ocr_dir / pdf_path.stem}.md",
        title="OCR Complete",
    ))


@app.command()
def process_batch(
    directory: Path = typer.Argument(..., help="Directory containing CAO PDFs"),
) -> None:
    """Process all CAO PDFs in a directory through OCR."""
    settings = _get_settings()
    from cao_engine.ocr.processor import OCRProcessor

    if not directory.is_dir():
        console.print(f"[red]Not a directory: {directory}[/red]")
        raise typer.Exit(1)

    processor = OCRProcessor(settings)
    results = processor.process_batch(directory)

    table = Table(title="Batch OCR Results")
    table.add_column("File")
    table.add_column("Pages", justify="right")
    table.add_column("Status")

    for pdf_path, result, error in results:
        if result:
            table.add_row(pdf_path.name, str(result.total_pages), "[green]OK[/green]")
        else:
            table.add_row(pdf_path.name, "-", f"[red]{error}[/red]")

    console.print(table)


# --- Extraction Commands ---


@app.command()
def extract(
    ocr_path: Path = typer.Argument(..., help="Path to OCR markdown file (.md)"),
    cao_naam: str | None = typer.Option(
        None, "--cao", help="CAO name (auto-detected if not set)"
    ),
    parallel: bool = typer.Option(
        True, "--parallel/--sequential", help="Use parallel extraction (5x faster)"
    ),
) -> None:
    """Extract structured CAO data from OCR markdown output (parallel by default)."""
    settings = _get_settings()
    from cao_engine.extraction.moment_extractor import MomentExtractor
    from cao_engine.extraction.parser import CAOExtractor
    from cao_engine.models import CAODocument, ProcessingInfo
    from cao_engine.storage.json_store import JSONStore
    from cao_engine.storage.moment_store import MomentStore

    if not ocr_path.exists():
        console.print(f"[red]File not found: {ocr_path}[/red]")
        raise typer.Exit(1)

    markdown_text = ocr_path.read_text(encoding="utf-8")
    name = cao_naam or ocr_path.stem

    console.print(f"[bold]Extracting data from:[/bold] {ocr_path.name}")

    if parallel:
        # NEW: Parallel extraction (5x faster!)
        from cao_engine.extraction.parallel_extractor import ParallelCAOExtractor

        console.print("  [bold cyan]→ Running parallel extraction (5x faster)...[/bold cyan]")
        extractor = ParallelCAOExtractor(settings)
        metadata, loongebouw, arbeidsvoorwaarden, inlenersbeloning, momenten_set = (
            extractor.extract_all_parallel(markdown_text, name)
        )
        name = metadata.cao_naam or name
    else:
        # OLD: Sequential extraction (slower)
        extractor = CAOExtractor(settings)

        console.print("  Extracting metadata...")
        metadata = extractor.extract_metadata(markdown_text)
        name = metadata.cao_naam or name

        console.print("  Extracting loongebouw...")
        loongebouw = extractor.extract_loongebouw(markdown_text)

        console.print("  Extracting arbeidsvoorwaarden...")
        arbeidsvoorwaarden = extractor.extract_arbeidsvoorwaarden(markdown_text)

        console.print("  Extracting inlenersbeloning...")
        inlenersbeloning = extractor.extract_inlenersbeloning(markdown_text)

        console.print("  [bold]Extracting momenten...[/bold]")
        moment_extractor = MomentExtractor(settings)
        momenten_set = moment_extractor.extract_moments(markdown_text, name)

    # Assemble full document
    now = datetime.utcnow()
    doc = CAODocument(
        metadata=metadata,
        loongebouw=loongebouw,
        arbeidsvoorwaarden=arbeidsvoorwaarden,
        inlenersbeloning=inlenersbeloning,
        momenten=momenten_set.momenten,
        processing=ProcessingInfo(
            ocr_model=settings.ocr_model,
            ocr_timestamp=now,
            extraction_timestamp=now,
            extraction_model=settings.extraction_model,
            source_file=str(ocr_path),
        ),
    )

    # Save
    json_store = JSONStore(settings)
    doc_path = json_store.save(doc)

    moment_store = MomentStore(settings)
    moment_path = moment_store.save(momenten_set)

    console.print(Panel(
        f"[green]CAO:[/green] {name}\n"
        f"[green]Functiegroepen:[/green] {len(loongebouw.functie_groepen)}\n"
        f"[green]Toeslagen:[/green] {len(arbeidsvoorwaarden.toeslagen)}\n"
        f"[green]Momenten:[/green] {momenten_set.count}\n"
        f"[green]Document:[/green] {doc_path}\n"
        f"[green]Momenten:[/green] {moment_path}",
        title="Extraction Complete",
    ))


# --- Moments Commands ---


@app.command()
def moments(
    cao_naam: str | None = typer.Option(None, "--cao", help="Filter by CAO name"),
    categorie: str | None = typer.Option(None, "--categorie", help="Filter by category"),
    days: int = typer.Option(90, "--days", help="Show moments in the next N days"),
) -> None:
    """List extracted moments from the moment store."""
    settings = _get_settings()
    from cao_engine.models.momenten import MomentCategorie
    from cao_engine.storage.moment_store import MomentStore

    store = MomentStore(settings)

    if categorie:
        try:
            cat = MomentCategorie(categorie)
        except ValueError as e:
            console.print(f"[red]Unknown category: {categorie}[/red]")
            valid = ", ".join(c.value for c in MomentCategorie)
            console.print(f"Valid: {valid}")
            raise typer.Exit(1) from e
        moment_list = store.query_by_categorie(cat, cao_naam)
    elif days:
        moment_list = store.query_upcoming(days_ahead=days, cao_naam=cao_naam)
    else:
        moment_list = store.query_upcoming(days_ahead=365, cao_naam=cao_naam)

    if not moment_list:
        console.print("[yellow]No moments found.[/yellow]")
        if not store.list_caos():
            console.print("No CAOs in the moment store. Run 'extract' first.")
        return

    table = Table(title=f"CAO Momenten ({len(moment_list)} found)")
    table.add_column("CAO", max_width=25)
    table.add_column("Categorie")
    table.add_column("Type")
    table.add_column("Datum")
    table.add_column("Beschrijving", max_width=40)
    table.add_column("Bron", max_width=20)

    for m in moment_list:
        table.add_row(
            m.cao_naam,
            m.categorie.value,
            m.type.value,
            m.datum.isoformat() if m.datum else m.datum_beschrijving or "?",
            m.beschrijving[:40],
            m.bron_artikel or "-",
        )

    console.print(table)


@app.command()
def moment_detail(
    moment_id: str = typer.Argument(..., help="Moment ID to display"),
) -> None:
    """Show full details for a specific moment including original CAO text."""
    settings = _get_settings()
    from cao_engine.storage.moment_store import MomentStore

    store = MomentStore(settings)

    for ms in store.load_all():
        for m in ms.momenten:
            if m.moment_id == moment_id:
                lines = [
                    f"[bold]CAO:[/bold] {m.cao_naam}",
                    f"[bold]Categorie:[/bold] {m.categorie.value}",
                    f"[bold]Type:[/bold] {m.type.value}",
                    f"[bold]Datum:[/bold] {m.datum or m.datum_beschrijving or 'Onbekend'}",
                ]
                freq = f" ({m.frequentie})" if m.frequentie else ""
                lines.append(f"[bold]Terugkerend:[/bold] {'Ja' if m.terugkerend else 'Nee'}{freq}")
                lines.append(f"[bold]Element:[/bold] {m.element}")
                if m.percentage:
                    lines.append(f"[bold]Percentage:[/bold] {m.percentage}%")
                if m.bedrag:
                    lines.append(f"[bold]Bedrag:[/bold] EUR {m.bedrag}")
                if m.doelgroep:
                    lines.append(f"[bold]Doelgroep:[/bold] {m.doelgroep}")
                if m.bron_artikel:
                    lines.append(f"[bold]Artikel:[/bold] {m.bron_artikel}")
                lines.append(f"\n[bold]Beschrijving:[/bold]\n{m.beschrijving}")
                lines.append("\n[bold]Originele CAO-tekst:[/bold]")
                lines.append(f"[italic]{m.bron_tekst}[/italic]")
                if m.voorwaarden:
                    lines.append("\n[bold]Voorwaarden:[/bold]")
                    for v in m.voorwaarden:
                        lines.append(f"  - {v}")
                console.print(Panel(
                    "\n".join(lines),
                    title=f"Moment: {moment_id}",
                ))
                return

    console.print(f"[red]Moment not found: {moment_id}[/red]")


# --- SETU Extraction Commands ---


@app.command()
def extract_setu(
    ocr_path: Path = typer.Argument(..., help="Path to OCR markdown file (.md)"),
    cao_naam: str | None = typer.Option(
        None, "--cao", help="CAO name (for metadata)"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output path for SETU JSON (default: data/setu/)"
    ),
    second_opinion: bool = typer.Option(
        True, "--second-opinion/--single-llm", help="Use dual-LLM validation (Mistral + Gemini)"
    ),
) -> None:
    """Extract SETU v2.0 compliant JSON from CAO markdown using Mistral + Gemini 2.5 Flash."""
    settings = _get_settings()

    if not ocr_path.exists():
        console.print(f"[red]File not found: {ocr_path}[/red]")
        raise typer.Exit(1)

    markdown_text = ocr_path.read_text(encoding="utf-8")
    name = cao_naam or ocr_path.stem

    console.print(f"[bold cyan]Extracting SETU v2.0 from:[/bold cyan] {ocr_path.name}")

    if second_opinion:
        # Dual-LLM extraction with second opinion
        from cao_engine.extraction.second_opinion_orchestrator import DualLLMSETUExtractor

        console.print(f"[dim]Using: Mistral {settings.extraction_model} + Gemini 2.5 Flash (Second Opinion)[/dim]\n")

        extractor = DualLLMSETUExtractor(
            mistral_api_key=settings.mistral_api_key,
            gemini_api_key=settings.google_api_key,
        )

        setu_data = extractor.extract_with_second_opinion(markdown_text, name)

        # Extract confidence metadata
        metadata = setu_data.get("_orchestrator_metadata", {})
        agreements = len(metadata.get("field_agreements", []))
        disagreements = metadata.get("field_disagreements", [])
        confidence = metadata.get("overall_confidence", 0.0)

        # Display validation results
        if disagreements:
            console.print("[yellow]⚠️  Field Disagreements:[/yellow]")
            for item in disagreements[:5]:  # Show first 5
                console.print(f"  • {item['field']}: {item['resolution']}")
            if len(disagreements) > 5:
                console.print(f"  ... and {len(disagreements) - 5} more")
            console.print()

    else:
        # Single LLM extraction (Mistral only)
        from cao_engine.extraction.setu_extractor import MistralSETUExtractor

        console.print(f"[dim]Using: Mistral {settings.extraction_model} (Single LLM)[/dim]\n")

        extractor = MistralSETUExtractor(
            api_key=settings.mistral_api_key,
            model=settings.extraction_model,
        )

        setu_data = extractor.extract(markdown_text, name)
        confidence = None

    # Determine output path
    if output is None:
        setu_dir = settings.data_dir / "setu"
        setu_dir.mkdir(parents=True, exist_ok=True)
        output = setu_dir / f"{ocr_path.stem}.setu.json"

    output.write_text(json.dumps(setu_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Display summary
    summary_lines = [
        f"[green]CAO:[/green] {name}",
        f"[green]Has Remuneration:[/green] {bool(setu_data.get('remuneration'))}",
        f"[green]Allowances:[/green] {len(setu_data.get('allowance', []))}",
        f"[green]Leave Arrangements:[/green] {len(setu_data.get('leave', []))}",
    ]

    if second_opinion and confidence is not None:
        summary_lines.append(f"[green]Confidence Score:[/green] {confidence:.1%}")
        summary_lines.append(f"[green]Field Agreements:[/green] {agreements}")
        summary_lines.append(f"[green]Field Disagreements:[/green] {len(disagreements)}")

    summary_lines.append(f"[green]Output:[/green] {output}")

    console.print(Panel(
        "\n".join(summary_lines),
        title="✅ SETU v2.0 Extraction Complete",
    ))


@app.command()
def extract_statutory(
    ocr_path: Path = typer.Argument(..., help="Path to OCR markdown file (.md)"),
    cao_naam: str | None = typer.Option(None, "--cao", help="CAO name (for logging)"),
    setu_id: str | None = typer.Option(None, "--setu-id", help="Link to SETU documentId.value"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output path (default: data/statutory/)"
    ),
) -> None:
    """Extract Statutory References (WML, SV-premies, fiscal limits) from CAO markdown."""
    settings = _get_settings()
    from cao_engine.extraction.statutory_extractor import MistralStatutoryExtractor
    from cao_engine.storage.statutory_store import StatutoryStore

    if not ocr_path.exists():
        console.print(f"[red]File not found: {ocr_path}[/red]")
        raise typer.Exit(1)

    markdown_text = ocr_path.read_text(encoding="utf-8")
    name = cao_naam or ocr_path.stem

    console.print(f"[bold cyan]Extracting Statutory References from:[/bold cyan] {ocr_path.name}")
    console.print(f"[dim]Using: Mistral {settings.extraction_model}[/dim]\n")

    extractor = MistralStatutoryExtractor(
        api_key=settings.mistral_api_key,
        model=settings.extraction_model,
    )

    statutory_data = extractor.extract(markdown_text, name, setu_id)

    # Save to statutory store
    if output is None:
        store = StatutoryStore(settings)
        output = store.save(statutory_data)
    else:
        output.write_text(json.dumps(statutory_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Display summary
    summary_lines = [
        f"[green]CAO:[/green] {name}",
        f"[green]Has WML:[/green] {bool(statutory_data.get('minimumWage'))}",
        f"[green]Has SV-premies:[/green] {bool(statutory_data.get('socialInsurancePremiums'))}",
        f"[green]Has Fiscal Limits:[/green] {bool(statutory_data.get('fiscalLimits'))}",
        f"[green]Has AOW Data:[/green] {bool(statutory_data.get('stateRetirementAge'))}",
        f"[green]Has Pension Params:[/green] {bool(statutory_data.get('pensionParameters'))}",
        f"[green]Regulatory Changes:[/green] {len(statutory_data.get('regulatoryChanges', []))}",
    ]

    if setu_id:
        summary_lines.append(f"[green]Linked SETU ID:[/green] {setu_id}")

    summary_lines.append(f"[green]Output:[/green] {output}")

    console.print(Panel(
        "\n".join(summary_lines),
        title="✅ Statutory References Extraction Complete",
    ))


@app.command()
def validate_cross_reference(
    setu_path: Path = typer.Argument(..., help="Path to SETU JSON file"),
    statutory_path: Path | None = typer.Option(
        None, "--statutory", help="Path to Statutory JSON (auto-detected if not provided)"
    ),
) -> None:
    """Validate SETU document against Statutory References (7 compliance rules)."""
    settings = _get_settings()
    from cao_engine.storage.statutory_store import StatutoryStore
    from cao_engine.validation import CrossReferenceValidator, ValidationSeverity

    if not setu_path.exists():
        console.print(f"[red]SETU file not found: {setu_path}[/red]")
        raise typer.Exit(1)

    setu_data = json.loads(setu_path.read_text(encoding="utf-8"))
    setu_id = setu_data.get("documentId", {}).get("value", "unknown")

    # Auto-detect statutory file if not provided
    if statutory_path is None:
        store = StatutoryStore(settings)
        statutory_data = store.load_by_setu_id(setu_id)
        if not statutory_data:
            console.print("[yellow]No linked statutory references found. Trying latest...[/yellow]")
            all_files = store.list_all()
            if all_files:
                statutory_data = store.load(all_files[-1])
                console.print(f"[dim]Using: {all_files[-1].name}[/dim]\n")
            else:
                console.print("[red]No statutory references found in data/statutory/[/red]")
                raise typer.Exit(1)
    else:
        if not statutory_path.exists():
            console.print(f"[red]Statutory file not found: {statutory_path}[/red]")
            raise typer.Exit(1)
        statutory_data = json.loads(statutory_path.read_text(encoding="utf-8"))

    console.print("[bold cyan]Validating SETU ↔ Statutory cross-references[/bold cyan]")
    console.print(f"[dim]SETU Document: {setu_id}[/dim]")
    console.print(f"[dim]Statutory Period: {statutory_data.get('effectivePeriod', {})}[/dim]\n")

    validator = CrossReferenceValidator()
    report = validator.validate(setu_data, statutory_data)

    # Display results
    if not report.issues:
        console.print("[green]✅ No validation issues found![/green]")
        return

    # Group by severity
    criticals = [i for i in report.issues if i.severity == ValidationSeverity.CRITICAL]
    errors = [i for i in report.issues if i.severity == ValidationSeverity.ERROR]
    warnings = [i for i in report.issues if i.severity == ValidationSeverity.WARNING]
    infos = [i for i in report.issues if i.severity == ValidationSeverity.INFO]

    # Summary
    console.print("\n[bold]Validation Summary:[/bold]")
    console.print(f"  [red]Critical:[/red] {len(criticals)}")
    console.print(f"  [red]Errors:[/red] {len(errors)}")
    console.print(f"  [yellow]Warnings:[/yellow] {len(warnings)}")
    console.print(f"  [blue]Info:[/blue] {len(infos)}\n")

    # Display each issue
    for issue in criticals + errors:
        color = "red" if issue.severity == ValidationSeverity.CRITICAL else "red"
        console.print(f"[{color}]● {issue.rule}[/{color}]: {issue.description}")
        if issue.setu_field:
            console.print(f"  SETU: {issue.setu_field} = {issue.setu_value}")
        if issue.statutory_field:
            console.print(f"  Statutory: {issue.statutory_field} = {issue.statutory_value}")
        if issue.recommendation:
            console.print(f"  → {issue.recommendation}")
        console.print()

    if warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for issue in warnings:
            console.print(f"[yellow]⚠ {issue.rule}[/yellow]: {issue.description}")
            if issue.recommendation:
                console.print(f"  → {issue.recommendation}")
        console.print()

    if infos:
        console.print("[blue]Information:[/blue]")
        for issue in infos:
            console.print(f"[blue]ℹ {issue.rule}[/blue]: {issue.description}")

    if report.has_errors:
        console.print(f"\n[red]❌ Validation failed with {report.error_count} critical/error issues[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"\n[green]✅ Validation passed ({len(warnings)} warnings, {len(infos)} info)[/green]")


# --- Collection Commands ---


def _print_collection_results(
    results: list, stats: "CrawlStats", title: str = "Collection Complete"
) -> None:
    """Shared summary printer for collection commands."""
    # Only show table for new downloads
    new_results = [r for r in results if r.is_new]
    if new_results:
        table = Table(title="New CAO PDFs")
        table.add_column("Sector")
        table.add_column("File")
        table.add_column("Size", justify="right")

        for r in new_results:
            table.add_row(
                f"{r.sector}/{r.subsector}" if r.subsector else r.sector,
                r.filename[:60],
                f"{r.size_kb} KB" if r.size_kb else "-",
            )
        console.print(table)

    console.print(Panel(
        f"[green]Pages crawled:[/green] {stats.pages_visited}\n"
        f"[dim]Pages skipped (unchanged):[/dim] {stats.pages_skipped}\n"
        f"[green]PDFs found:[/green] {stats.pdfs_found}\n"
        f"[bold green]New downloads:[/bold green] {stats.pdfs_new}\n"
        f"[dim]Already had:[/dim] {stats.pdfs_skipped}\n"
        f"[red]Failed:[/red] {stats.pdfs_failed}",
        title=title,
    ))


@app.command()
def collect_fnv(
    output_dir: Path | None = typer.Option(
        None, "--output", "-o", help="Output directory (default: data/raw/)"
    ),
    cao_only: bool = typer.Option(
        False, "--cao-only", help="Only download files that look like actual CAO documents"
    ),
    full: bool = typer.Option(
        False, "--full", help="Force a full scan instead of incremental"
    ),
) -> None:
    """Collect CAO PDFs from fnv.nl (incremental by default, full with --full).

    Uses the FNV sitemap to detect which pages changed since the last scan.
    On first run (or with --full), crawls everything. Subsequent runs only
    check modified pages — typically finishing in seconds.
    """
    settings = _get_settings()
    from cao_engine.collection.fnv_collector import collect_full, collect_incremental

    dest = output_dir or settings.raw_dir
    dest.mkdir(parents=True, exist_ok=True)

    mode = "full" if full else "incremental"
    console.print(f"[bold cyan]FNV CAO Collector[/bold cyan] ({mode})")
    console.print(f"Output: {dest.resolve()}\n")

    if full:
        results, stats = collect_full(dest, cao_only=cao_only)
    else:
        results, stats = collect_incremental(dest, cao_only=cao_only)

    _print_collection_results(results, stats)


@app.command()
def triage_raw(
    raw_dir: Path | None = typer.Option(
        None, "--dir", "-d", help="Raw PDF directory (default: data/raw/)"
    ),
    execute: bool = typer.Option(
        False, "--execute", help="Actually move files (default: dry-run preview)"
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-n", help="Only process N archive candidates (for testing)"
    ),
) -> None:
    """Classify raw PDFs and archive non-relevant files.

    Keeps: CAO documents, sociale plannen, functiehandboeken.
    Archives to data/raw/old/: translations, older versions, brochures, reports, etc.

    Default is dry-run (preview). Use --execute to actually move files.
    """
    settings = _get_settings()
    from cao_engine.collection.triage import (
        TriageAction,
        execute_triage,
        triage_directory,
    )

    dest = raw_dir or settings.raw_dir
    if not dest.is_dir():
        console.print(f"[red]Not a directory: {dest}[/red]")
        raise typer.Exit(1)

    results = triage_directory(dest, limit=limit)
    if not results:
        console.print("[yellow]No PDF files found.[/yellow]")
        return

    to_archive = [r for r in results if r.action == TriageAction.ARCHIVE]
    to_keep = [r for r in results if r.action == TriageAction.KEEP]

    # Show archive candidates
    if to_archive:
        table = Table(title=f"Archiveren ({len(to_archive)} bestanden)")
        table.add_column("Bestand", max_width=65)
        table.add_column("Categorie")
        table.add_column("Reden", max_width=40)

        for r in to_archive:
            reason = r.reason
            if r.newer_version:
                reason += f" → {r.newer_version[:40]}"
            table.add_row(r.filename[:65], r.category.value, reason)
        console.print(table)

    # Summary
    mode = "[bold green]UITVOEREN[/bold green]" if execute else "[yellow]PREVIEW[/yellow]"
    console.print(Panel(
        f"Modus: {mode}\n"
        f"[green]Behouden:[/green] {len(to_keep)}\n"
        f"[yellow]Archiveren:[/yellow] {len(to_archive)}\n"
        f"[dim]Totaal:[/dim] {len(results)}",
        title="Triage Resultaat",
    ))

    if execute and to_archive:
        kept, archived = execute_triage(dest, results, dry_run=False)
        console.print(
            f"\n[green]Klaar![/green] {archived} bestanden verplaatst naar {dest / 'old'}"
        )
    elif to_archive and not execute:
        console.print(
            "\n[dim]Dit is een preview. Gebruik --execute om bestanden daadwerkelijk te verplaatsen.[/dim]"
        )


# --- Info Commands ---


@app.command()
def info() -> None:
    """Show CAO Intelligence Engine status and data overview."""
    settings = _get_settings()
    from cao_engine.storage.json_store import JSONStore
    from cao_engine.storage.moment_store import MomentStore

    json_store = JSONStore(settings)
    moment_store = MomentStore(settings)

    docs = json_store.list_documents()
    caos = moment_store.list_caos()

    ocr_files = list(settings.ocr_dir.glob("*.md"))
    raw_files = list(settings.raw_dir.glob("*.pdf"))

    console.print(Panel(
        f"[bold]PDFs in raw/:[/bold] {len(raw_files)}\n"
        f"[bold]OCR outputs:[/bold] {len(ocr_files)}\n"
        f"[bold]Structured docs:[/bold] {len(docs)}\n"
        f"[bold]CAOs with moments:[/bold] {len(caos)}",
        title="CAO Intelligence Engine",
    ))

    if caos:
        for cao_naam in caos:
            ms = moment_store.load(cao_naam)
            if ms:
                console.print(f"  {cao_naam}: {ms.count} momenten")


@app.command()
def extract_setu_pipeline(
    ocr_path: Path,
    cao: str | None = typer.Option(None, "--cao", help="CAO name for metadata"),
) -> None:
    """Extract SETU v2.0 using 3-LLM pipeline: Gemini (primary) → Mistral (reviewer) → Judge.

    Sequential pipeline:
    1. Gemini 2.5 Flash - Primary extraction (1M context, full document)
    2. Mistral Large - Reviews Gemini's work, finds gaps
    3. Mistral Small 2506 - Judges which output is best, produces final SETU + report

    Outputs:
    - data/setu_raw/gemini/*.json - Gemini's extraction
    - data/setu_raw/mistral/*.json - Mistral's review
    - data/setu/*.json - Final judged SETU v2.0
    - data/setu_reports/*.json - Judge's decision report
    """
    settings = _get_settings()
    settings.ensure_dirs()

    from cao_engine.extraction.gemini_primary import GeminiPrimaryExtractor
    from cao_engine.extraction.mistral_judge import MistralJudge
    from cao_engine.extraction.mistral_reviewer import MistralReviewer

    # Read OCR markdown
    markdown_text = ocr_path.read_text(encoding="utf-8")
    console.print("[bold cyan]3-LLM SETU Pipeline[/bold cyan]")
    console.print(f"Input: {ocr_path.name} ({len(markdown_text):,} chars)")
    console.print(f"CAO: {cao or 'Unknown'}\n")

    # Step 1: Gemini Primary Extraction
    console.print(f"[bold]Step 1/3:[/bold] {settings.gemini_model} (Primary Extractor)")
    console.print(f"[dim]  Thinking level: {settings.gemini_thinking_level}[/dim]")
    gemini = GeminiPrimaryExtractor(
        settings.google_api_key,
        settings.gemini_model,
        settings.gemini_thinking_level
    )
    gemini_output = gemini.extract(markdown_text, cao)

    # Save Gemini's output
    gemini_file = settings.setu_raw_dir / "gemini" / f"{ocr_path.stem}.gemini.json"
    gemini_file.write_text(json.dumps(gemini_output, indent=2, ensure_ascii=False))
    console.print(f"  ✓ Gemini extraction saved: {gemini_file.relative_to(settings.data_dir)}")
    console.print(f"  Fields extracted: {len(gemini_output)}\n")

    # Step 2: Mistral Review
    console.print("[bold]Step 2/3:[/bold] Mistral Large (Reviewer)")
    reviewer = MistralReviewer(settings.mistral_api_key, settings.extraction_model)
    mistral_output = reviewer.review(markdown_text, gemini_output, cao)

    # Save Mistral's output
    mistral_file = settings.setu_raw_dir / "mistral" / f"{ocr_path.stem}.mistral.json"
    mistral_file.write_text(json.dumps(mistral_output, indent=2, ensure_ascii=False))
    console.print(f"  ✓ Mistral review saved: {mistral_file.relative_to(settings.data_dir)}")
    console.print(f"  Fields extracted: {len(mistral_output)}\n")

    # Step 3: Judge
    console.print("[bold]Step 3/3:[/bold] Mistral Small 2506 (Judge)")
    judge = MistralJudge(settings.mistral_api_key, settings.judge_model)
    result = judge.judge(gemini_output, mistral_output, cao)

    final_setu = result["final_setu"]
    judge_report = result.get("judge_report", {})

    # Save final SETU
    setu_file = settings.setu_dir / f"{ocr_path.stem}.setu.json"
    setu_file.write_text(json.dumps(final_setu, indent=2, ensure_ascii=False))

    # Save judge report
    report_file = settings.setu_reports_dir / f"{ocr_path.stem}.judge_report.json"
    report_file.write_text(json.dumps(judge_report, indent=2, ensure_ascii=False))

    console.print(Panel(
        f"[green]✓ Final SETU:[/green] {setu_file.relative_to(settings.data_dir)}\n"
        f"[blue]✓ Judge Report:[/blue] {report_file.relative_to(settings.data_dir)}\n\n"
        f"[bold]Judge Statistics:[/bold]\n"
        f"  Total fields compared: {judge_report.get('total_fields_compared', '?')}\n"
        f"  Agreements: {judge_report.get('agreements', '?')}\n"
        f"  Gemini preferred: {judge_report.get('gemini_preferred', '?')}\n"
        f"  Mistral preferred: {judge_report.get('mistral_preferred', '?')}\n"
        f"  Merged: {judge_report.get('merged', '?')}",
        title="✅ 3-LLM Pipeline Complete",
    ))


# --- Timeline Commands ---


@app.command()
def extract_setu_hybrid(
    pdf_path: Path = typer.Argument(..., help="Path to CAO PDF file"),
    markdown_path: Path | None = typer.Option(None, "--markdown", help="Path to OCR markdown (auto-detected if not provided)"),
    cao: str | None = typer.Option(None, "--cao", help="CAO name for metadata"),
) -> None:
    """Extract SETU v2.0 using HYBRID pipeline: Mistral table annotation + Gemini 3.0 full extraction.

    New V3 architecture:
    1. Mistral Document AI - Schema-enforced table annotation (salary scales with Pydantic validation)
    2. Gemini 3.0 Flash Preview - Complete SETU extraction (1M context, thinking mode)
    3. Intelligent merge - Use Mistral tables (high confidence) + Gemini rest (flexibility)

    Benefits over 3-LLM pipeline:
    - 50% faster (2 API calls instead of 4)
    - Guaranteed correct table structure (Pydantic schema enforcement)
    - No review/judge complexity
    - Better salary table accuracy

    Outputs:
    - data/setu/*.setu.json - Final merged SETU v2.0
    - data/setu_reports/*.hybrid_report.json - Extraction report with confidence scores
    """
    settings = _get_settings()
    settings.ensure_dirs()

    from cao_engine.extraction.hybrid_pipeline_v3 import HybridPipelineV3

    # Validate PDF exists
    if not pdf_path.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/red]")
        raise typer.Exit(1)

    # Auto-detect markdown if not provided
    if markdown_path is None:
        # Try data/ocr_mistral_ai/*.docai.md first (new OCR)
        docai_md = settings.data_dir / "ocr_mistral_ai" / f"{pdf_path.stem}.docai.md"
        if docai_md.exists():
            markdown_path = docai_md
        else:
            # Fall back to data/ocr/*.md (old OCR)
            old_ocr_md = settings.data_dir / "ocr" / f"{pdf_path.stem}.md"
            if old_ocr_md.exists():
                markdown_path = old_ocr_md
            else:
                console.print(f"[red]No OCR markdown found for {pdf_path.name}[/red]")
                console.print("[yellow]Run: python -m cao_engine process-single {pdf_path}[/yellow]")
                raise typer.Exit(1)

    if not markdown_path.exists():
        console.print(f"[red]Markdown not found: {markdown_path}[/red]")
        raise typer.Exit(1)

    cao_name = cao or pdf_path.stem

    console.print("[bold cyan]HYBRID Pipeline V3[/bold cyan]")
    console.print(f"PDF: {pdf_path.name}")
    console.print(f"Markdown: {markdown_path.name}")
    console.print(f"CAO: {cao_name}\n")

    # Initialize hybrid pipeline
    pipeline = HybridPipelineV3(
        mistral_api_key=settings.mistral_api_key,
        gemini_api_key=settings.google_api_key,
        gemini_model=settings.gemini_model,
        gemini_thinking_level=settings.gemini_thinking_level
    )

    # Run extraction
    result = pipeline.extract(pdf_path, markdown_path, cao_name)

    # Save final SETU
    setu_file = settings.setu_dir / f"{pdf_path.stem}.setu.json"
    setu_file.write_text(json.dumps(result.setu_data, indent=2, ensure_ascii=False))

    # Save hybrid report
    report = {
        "cao_name": cao_name,
        "pdf_path": str(pdf_path),
        "markdown_path": str(markdown_path),
        "extracted_at": result.setu_data.get("_hybrid_pipeline_metadata", {}).get("extracted_at"),
        "confidence_score": result.confidence_score,
        "mistral_tables": {
            "scales_count": len(result.table_extraction.salary_scales),
            "confidence": result.table_extraction.confidence_score,
            "extraction_notes": result.table_extraction.extraction_notes
        },
        "merge_notes": result.merge_notes
    }
    report_file = settings.setu_reports_dir / f"{pdf_path.stem}.hybrid_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    console.print(Panel(
        f"[green]✓ Final SETU:[/green] {setu_file.relative_to(settings.data_dir)}\n"
        f"[blue]✓ Hybrid Report:[/blue] {report_file.relative_to(settings.data_dir)}\n\n"
        f"[bold]Extraction Statistics:[/bold]\n"
        f"  Overall confidence: {result.confidence_score:.2f}\n"
        f"  Mistral salary scales: {len(result.table_extraction.salary_scales)}\n"
        f"  Mistral table confidence: {result.table_extraction.confidence_score:.2f}\n"
        f"  Merge notes: {len(result.merge_notes)}",
        title="✅ Hybrid Pipeline V3 Complete",
    ))


# --- Timeline Commands ---


@app.command()
def generate_timeline(
    cao_naam: str = typer.Argument(..., help="Name of the CAO to generate timeline for"),
    format: str = typer.Option("both", "--format", help="Output format: html, json, or both"),
    include_future: bool = typer.Option(True, "--include-future/--no-future", help="Include future events"),
    include_notifications: bool = typer.Option(True, "--include-notifications/--no-notifications", help="Include notification events"),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Custom output directory"),
) -> None:
    """Generate a visual timeline for a specific CAO."""
    from cao_engine.storage.moment_store import MomentStore
    from cao_engine.timeline.generator import TimelineGenerator
    from cao_engine.timeline.storage import TimelineStorage
    from cao_engine.timeline.visualization import TimelineVisualizer

    settings = _get_settings()

    # Initialize components
    moment_store = MomentStore(settings)
    generator = TimelineGenerator(moment_store)
    visualizer = TimelineVisualizer()
    storage = TimelineStorage(output_dir or settings.data_dir / "timelines")

    console.print(f"[bold cyan]Generating timeline for: {cao_naam}[/bold cyan]")

    try:
        # Generate timeline
        timeline = generator.generate_timeline(
            cao_naam=cao_naam,
            include_future=include_future,
            include_notifications=include_notifications,
        )

        if timeline.total_entries == 0:
            console.print(f"[yellow]Warning: No timeline entries found for {cao_naam}[/yellow]")
            return

        # Generate HTML if requested
        html_content = None
        if format in ["html", "both"]:
            html_content = visualizer.generate_html(timeline)

        # Save timeline
        json_path, html_path = storage.save_timeline(
            timeline=timeline,
            format=format,
            html_content=html_content,
        )

        # Create summary
        summary = generator.create_timeline_summary(timeline)

        # Display results
        table = Table(title=f"Timeline: {cao_naam}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Events", str(summary["total_entries"]))
        table.add_row("Future Events", str(summary["future_entries"]))
        table.add_row("Past Events", str(summary["past_entries"]))
        table.add_row("Recurring Events", str(summary["recurring_entries"]))
        table.add_row("Upcoming (30 days)", str(summary["upcoming_30_days"]))

        if summary["date_range"]["start"] and summary["date_range"]["end"]:
            table.add_row(
                "Date Range",
                f"{summary['date_range']['start']} to {summary['date_range']['end']}"
            )

        console.print(table)

        # Show category breakdown
        if summary["categories"]:
            cat_table = Table(title="Events by Category")
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", style="white")

            for category, count in summary["categories"].items():
                cat_table.add_row(category.replace("_", " ").title(), str(count))

            console.print(cat_table)

        # Show output paths
        console.print("\n[green]✓ Timeline generated successfully![/green]")
        if json_path:
            console.print(f"  JSON: {json_path}")
        if html_path:
            console.print(f"  HTML: {html_path}")
            console.print("\n[yellow]Open the HTML file in a browser to view the interactive timeline[/yellow]")

    except Exception as e:
        console.print(f"[red]Error generating timeline: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate_all_timelines(
    format: str = typer.Option("both", "--format", help="Output format: html, json, or both"),
    include_future: bool = typer.Option(True, "--include-future/--no-future", help="Include future events"),
    include_notifications: bool = typer.Option(True, "--include-notifications/--no-notifications", help="Include notification events"),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Custom output directory"),
) -> None:
    """Generate timelines for all CAOs with available moments."""
    from cao_engine.storage.moment_store import MomentStore
    from cao_engine.timeline.generator import TimelineGenerator
    from cao_engine.timeline.storage import TimelineStorage
    from cao_engine.timeline.visualization import TimelineVisualizer

    settings = _get_settings()

    # Initialize components
    moment_store = MomentStore(settings)
    generator = TimelineGenerator(moment_store)
    visualizer = TimelineVisualizer()
    storage = TimelineStorage(output_dir or settings.data_dir / "timelines")

    console.print("[bold cyan]Generating timelines for all CAOs...[/bold cyan]")

    # Get all CAOs
    cao_names = moment_store.list_caos()
    if not cao_names:
        console.print("[yellow]No CAOs with moments found[/yellow]")
        return

    console.print(f"Found {len(cao_names)} CAO(s) with moments\n")

    # Generate timelines
    all_timelines = {}
    success_count = 0
    failed_caos = []

    with console.status("Generating timelines...") as status:
        for cao_naam in cao_names:
            status.update(f"Processing {cao_naam}...")

            try:
                # Generate timeline
                timeline = generator.generate_timeline(
                    cao_naam=cao_naam,
                    include_future=include_future,
                    include_notifications=include_notifications,
                )

                if timeline.total_entries > 0:
                    # Generate HTML if requested
                    html_content = None
                    if format in ["html", "both"]:
                        html_content = visualizer.generate_html(timeline)

                    # Save timeline
                    storage.save_timeline(
                        timeline=timeline,
                        format=format,
                        html_content=html_content,
                    )

                    all_timelines[cao_naam] = timeline
                    success_count += 1
                    console.print(f"  ✓ {cao_naam}: {timeline.total_entries} events")
                else:
                    console.print(f"  ⚠ {cao_naam}: No events found")

            except Exception as e:
                failed_caos.append(cao_naam)
                console.print(f"  ✗ {cao_naam}: {str(e)}", style="red")

    # Generate index HTML if we have timelines
    if all_timelines and format in ["html", "both"]:
        index_path = storage.save_index_html(all_timelines)
        console.print(f"\n[green]✓ Generated index file: {index_path}[/green]")

    # Summary
    console.print(Panel(
        f"[green]Successfully generated:[/green] {success_count} timeline(s)\n"
        f"[yellow]Failed:[/yellow] {len(failed_caos)} CAO(s)\n"
        f"[blue]Total events:[/blue] {sum(t.total_entries for t in all_timelines.values())}",
        title="✅ Timeline Generation Complete",
    ))

    if format in ["html", "both"]:
        console.print("\n[yellow]Open data/timelines/index.html in a browser to view all timelines[/yellow]")


@app.command()
def list_timelines(
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Custom timeline directory"),
) -> None:
    """List all available timelines."""
    from cao_engine.timeline.storage import TimelineStorage

    settings = _get_settings()
    storage = TimelineStorage(output_dir or settings.data_dir / "timelines")

    timelines = storage.list_timelines()

    if not timelines:
        console.print("[yellow]No timelines found[/yellow]")
        return

    table = Table(title="Available Timelines")
    table.add_column("CAO Name", style="cyan")
    table.add_column("Files", style="white")

    for cao_name in timelines:
        files = []
        cao_name_clean = cao_name.lower().replace(" ", "_")
        json_file = f"{cao_name_clean}_timeline.json"
        html_file = f"{cao_name_clean}_timeline.html"

        if (storage.data_dir / json_file).exists():
            files.append("JSON")
        if (storage.data_dir / html_file).exists():
            files.append("HTML")

        table.add_row(cao_name, ", ".join(files))

    console.print(table)
    console.print(f"\n[blue]Timeline directory: {storage.data_dir}[/blue]")


if __name__ == "__main__":
    app()


@app.command()
def extract_setu_mistral_hybrid(
    pdf_path: Path = typer.Argument(..., help="Path to CAO PDF file"),
    markdown_path: Path | None = typer.Option(None, "--markdown", help="Path to OCR markdown (auto-detected if not provided)"),
    cao: str | None = typer.Option(None, "--cao", help="CAO name for metadata"),
) -> None:
    """Extract SETU v2.0 using MISTRAL-ONLY hybrid pipeline: Document AI tables + Large full extraction."""
    settings = _get_settings()
    settings.ensure_dirs()

    from cao_engine.extraction.hybrid_pipeline_mistral import HybridPipelineMistral

    if not pdf_path.exists():
        console.print(f"[red]❌ PDF not found: {pdf_path}[/red]")
        raise typer.Exit(1)

    # Auto-detect markdown
    if markdown_path is None:
        docai_md = settings.data_dir / "ocr_mistral_ai" / f"{pdf_path.stem}.docai.md"
        if docai_md.exists():
            markdown_path = docai_md
        else:
            old_ocr_md = settings.data_dir / "ocr" / f"{pdf_path.stem}.md"
            if old_ocr_md.exists():
                markdown_path = old_ocr_md
            else:
                console.print("[red]❌ No OCR markdown found[/red]")
                raise typer.Exit(1)

    cao_name = cao or pdf_path.stem

    console.print(Panel(f"[bold cyan]MISTRAL-ONLY Hybrid Pipeline[/bold cyan]\nPDF: {pdf_path.name}\nMarkdown: {markdown_path.name}\nCAO: {cao_name}", title="🚀 Pure-Mistral Hybrid"))

    pipeline = HybridPipelineMistral(mistral_api_key=settings.mistral_api_key, mistral_model=settings.extraction_model)
    result = pipeline.extract(pdf_path, markdown_path, cao_name)

    setu_file = settings.setu_dir / f"{pdf_path.stem}.setu.json"
    setu_file.write_text(json.dumps(result.setu_data, indent=2, ensure_ascii=False), encoding="utf-8")

    table_file = settings.setu_dir / f"{pdf_path.stem}.tables.json"
    table_file.write_text(result.table_extraction.model_dump_json(indent=2), encoding="utf-8")

    console.print(Panel(f"  Final SETU: {setu_file}\n  Salary scales: {len(result.table_extraction.salary_scales)}\n  Elapsed: {result.elapsed_seconds:.1f}s", title="✅ Complete"))


# --- Exception Review Commands ---
# REMOVED: Confidence scoring and exception review features
# The system now produces CLEAN SETU v2.0 files that validate against official schema
