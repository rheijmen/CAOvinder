"""
Retry mechanism for failed 3-LLM pipeline steps
Allows continuing from a failed step without re-running successful steps
"""
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from pydantic import BaseModel

from cao_engine.config import Settings
from cao_engine.extraction.mistral_reviewer import MistralReviewer
from cao_engine.extraction.mistral_judge import MistralJudge
from cao_engine.compliance.setu_compliance_engine import SETUComplianceEngine

console = Console()
app = typer.Typer()

class PipelineState(BaseModel):
    """Track the state of a 3-LLM pipeline run"""
    cao_name: str
    ocr_file: str
    gemini_complete: bool = False
    gemini_output_file: Optional[str] = None
    mistral_complete: bool = False
    mistral_output_file: Optional[str] = None
    judge_complete: bool = False
    judge_output_file: Optional[str] = None
    final_setu_file: Optional[str] = None

    def save(self, path: Path):
        """Save state to JSON file"""
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        """Load state from JSON file"""
        return cls.model_validate_json(path.read_text())


@app.command()
def retry_from_step(
    ocr_file: str = typer.Argument(help="Path to OCR markdown file"),
    step: int = typer.Option(2, help="Step to retry from (1=Gemini, 2=Mistral, 3=Judge)"),
    cao: Optional[str] = typer.Option(None, help="CAO name (if not in state file)"),
):
    """Retry 3-LLM pipeline from a specific step"""
    settings = Settings()
    ocr_path = Path(ocr_file)

    if not ocr_path.exists():
        console.print(f"[red]Error: OCR file not found: {ocr_file}[/red]")
        raise typer.Exit(1)

    # Load markdown content
    markdown_text = ocr_path.read_text()

    # Check for state file
    state_file = settings.setu_raw_dir / "pipeline_state" / f"{ocr_path.stem}.state.json"

    if state_file.exists():
        console.print(f"[green]Found pipeline state file[/green]")
        state = PipelineState.load(state_file)
        cao_name = cao or state.cao_name
    else:
        if not cao:
            console.print("[red]Error: No state file found and --cao not provided[/red]")
            raise typer.Exit(1)
        cao_name = cao
        state = PipelineState(cao_name=cao_name, ocr_file=ocr_file)

    console.print(f"\n[bold]Retrying 3-LLM Pipeline from Step {step}[/bold]")
    console.print(f"CAO: {cao_name}")
    console.print(f"OCR: {ocr_path.name}")

    # Step 1: Load or skip Gemini
    if step <= 1:
        console.print("\n[yellow]Step 1 would re-run Gemini (use main pipeline for full run)[/yellow]")
        raise typer.Exit(1)
    else:
        # Load existing Gemini output
        gemini_file = settings.setu_raw_dir / "gemini" / f"{ocr_path.stem}.gemini.json"
        if not gemini_file.exists():
            console.print(f"[red]Error: Gemini output not found: {gemini_file}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold]Step 1/3:[/bold] Loading existing Gemini output")
        with open(gemini_file) as f:
            gemini_output = json.load(f)
        console.print(f"  ✓ Loaded from: {gemini_file.name}")
        console.print(f"  Fields: {len([k for k in gemini_output.keys() if gemini_output[k]])}")

    # Step 2: Mistral Review (if needed)
    mistral_output = None
    if step <= 2:
        console.print(f"\n[bold]Step 2/3:[/bold] Mistral Large (Reviewer) - RETRY")
        reviewer = MistralReviewer(settings.mistral_api_key, settings.extraction)

        try:
            mistral_output = reviewer.review(markdown_text, gemini_output, cao_name)

            # Save Mistral output
            mistral_file = settings.setu_raw_dir / "mistral" / f"{ocr_path.stem}.mistral.json"
            mistral_file.parent.mkdir(parents=True, exist_ok=True)
            with open(mistral_file, "w") as f:
                json.dump(mistral_output, f, indent=2, default=str)

            console.print(f"  ✓ Mistral review saved: {mistral_file.name}")
            console.print(f"  Fields: {len([k for k in mistral_output.keys() if mistral_output[k]])}")

            state.mistral_complete = True
            state.mistral_output_file = str(mistral_file)
        except Exception as e:
            console.print(f"[red]  ✗ Mistral review failed: {e}[/red]")
            # Save state before exiting
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state.save(state_file)
            raise typer.Exit(1)
    else:
        # Load existing Mistral output
        mistral_file = settings.setu_raw_dir / "mistral" / f"{ocr_path.stem}.mistral.json"
        if not mistral_file.exists():
            console.print(f"[red]Error: Mistral output not found: {mistral_file}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold]Step 2/3:[/bold] Loading existing Mistral output")
        with open(mistral_file) as f:
            mistral_output = json.load(f)
        console.print(f"  ✓ Loaded from: {mistral_file.name}")
        console.print(f"  Fields: {len([k for k in mistral_output.keys() if mistral_output[k]])}")

    # Step 3: Judge (if we got this far)
    if mistral_output:
        console.print(f"\n[bold]Step 3/3:[/bold] Mistral Small 2506 (Judge)")
        judge = MistralJudge(settings.mistral_api_key)

        try:
            final_setu, judge_report = judge.judge(gemini_output, mistral_output, cao_name)

            # Save final SETU
            setu_file = settings.setu_dir / f"{ocr_path.stem}.setu.json"
            with open(setu_file, "w") as f:
                json.dump(final_setu, f, indent=2, default=str)

            # Save judge report
            report_file = settings.setu_reports_dir / f"{ocr_path.stem}.judge_report.json"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            with open(report_file, "w") as f:
                json.dump(judge_report, f, indent=2)

            console.print(f"  ✓ Final SETU: {setu_file.name}")
            console.print(f"  ✓ Judge report: {report_file.name}")
            console.print(f"  Fields in final: {len([k for k in final_setu.keys() if final_setu[k]])}")

            # Run compliance check on final output
            console.print(f"\n[bold]Final Compliance Check:[/bold]")
            compliance = SETUComplianceEngine()
            validation = compliance.validate(final_setu)

            console.print(f"  Status: [{'green' if validation.is_compliant else 'yellow'}]{validation.compliance_status}[/]")
            console.print(f"  Coverage: {validation.field_coverage:.1f}%")
            if validation.errors:
                console.print(f"  [red]Errors: {len(validation.errors)}[/red]")

            state.judge_complete = True
            state.judge_output_file = str(report_file)
            state.final_setu_file = str(setu_file)

            console.print(f"\n[bold green]✓ Pipeline retry completed successfully![/bold green]")
        except Exception as e:
            console.print(f"[red]  ✗ Judge failed: {e}[/red]")
            raise typer.Exit(1)
        finally:
            # Save state
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state.save(state_file)


if __name__ == "__main__":
    app()