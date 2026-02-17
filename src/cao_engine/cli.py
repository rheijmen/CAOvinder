"""CLI application for the CAO Intelligence Engine."""

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


if __name__ == "__main__":
    app()
