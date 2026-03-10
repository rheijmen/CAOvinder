"""Human-friendly mapping management system.

This module provides CLI tools for CAO experts to:
1. Search for correct SETU mappings
2. Add new Dutch/English terminology
3. View mapping statistics
4. Learn from validation feedback
"""

from pathlib import Path
from typing import Any

import structlog
import typer
import yaml

logger = structlog.get_logger(__name__)

app = typer.Typer(help="Manage CAO→SETU field mappings")

MAPPINGS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "cao_setu_mappings.yaml"


def load_mappings() -> dict[str, Any]:
    """Load human-editable YAML mappings."""
    if not MAPPINGS_FILE.exists():
        logger.error("Mappings file not found", path=str(MAPPINGS_FILE))
        raise FileNotFoundError(f"Mappings file not found: {MAPPINGS_FILE}")

    with open(MAPPINGS_FILE) as f:
        return yaml.safe_load(f)


def save_mappings(data: dict[str, Any]) -> None:
    """Save mappings back to YAML file."""
    with open(MAPPINGS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    logger.info("Mappings saved", path=str(MAPPINGS_FILE))


@app.command()
def search(
    term: str = typer.Argument(..., help="Dutch or English term to search for"),
    language: str = typer.Option("both", help="Language: 'nl', 'en', or 'both'"),
) -> None:
    """Search for correct SETU mapping for a CAO term.

    Examples:
        cao-mapping search "eenmalige uitkering"
        cao-mapping search "bonus" --language en
        cao-mapping search "algemene loonsverhoging"
    """
    data = load_mappings()
    mappings = data["mappings"]

    term_lower = term.lower()
    matches = []

    for mapping_id, mapping in mappings.items():
        # Search in Dutch aliases
        if language in ("nl", "both"):
            for alias in mapping.get("aliases_nl", []):
                if term_lower in alias.lower():
                    matches.append((mapping_id, mapping, alias, "nl"))

        # Search in English aliases
        if language in ("en", "both"):
            for alias in mapping.get("aliases_en", []):
                if term_lower in alias.lower():
                    matches.append((mapping_id, mapping, alias, "en"))

    if not matches:
        typer.echo(f"❌ No mappings found for '{term}'")
        typer.echo("\n💡 Suggestions:")
        typer.echo("   - Try a shorter term (e.g., 'bonus' instead of 'bonus payment')")
        typer.echo("   - Check spelling")
        typer.echo("   - Use 'cao-mapping list' to see all available mappings")
        return

    typer.echo(f"\n✅ Found {len(matches)} mapping(s) for '{term}':\n")

    for mapping_id, mapping, matched_alias, lang in matches:
        typer.echo(f"{'='*80}")
        typer.echo(f"Concept: {mapping['concept_id']}")
        typer.echo(f"Matched alias ({lang}): {matched_alias}")
        typer.echo(f"\n✅ CORRECT SETU field: {mapping['setu_field']}")
        typer.echo(f"\nDescription:\n{mapping['description']}")
        typer.echo(f"\nDecision logic:\n{mapping['decision_logic']}")

        if mapping.get("examples"):
            typer.echo("\n📋 Real CAO examples:")
            for ex in mapping["examples"][:3]:
                typer.echo(f"   - {ex['cao']}: \"{ex['text']}\"")

        if mapping.get("notes"):
            typer.echo(f"\n📝 Notes:\n{mapping['notes']}")


@app.command()
def list_all() -> None:
    """List all available CAO→SETU mappings."""
    data = load_mappings()
    mappings = data["mappings"]

    typer.echo(f"\n📚 CAO→SETU Mapping Registry (v{data['version']})")
    typer.echo(f"Last updated: {data['last_updated']}")
    typer.echo(f"SETU version: {data['setu_version']}\n")

    for i, (mapping_id, mapping) in enumerate(mappings.items(), 1):
        typer.echo(f"{i}. {mapping['concept_id']}")
        typer.echo(f"   SETU field: {mapping['setu_field']}")
        typer.echo(f"   Dutch aliases: {', '.join(mapping['aliases_nl'][:5])}")
        if len(mapping["aliases_nl"]) > 5:
            typer.echo(f"                  (+{len(mapping['aliases_nl']) - 5} more)")
        typer.echo()


@app.command()
def add_alias(
    concept: str = typer.Argument(..., help="Concept ID (e.g., general_salary_increase)"),
    alias: str = typer.Argument(..., help="New alias to add"),
    language: str = typer.Option("nl", help="Language: 'nl' or 'en'"),
) -> None:
    """Add a new Dutch/English alias to a mapping.

    Examples:
        cao-mapping add-alias general_salary_increase "structurele loonsverhoging" --language nl
        cao-mapping add-alias supplementary_arrangement "13th month" --language en
    """
    data = load_mappings()
    mappings = data["mappings"]

    if concept not in mappings:
        typer.echo(f"❌ Concept '{concept}' not found. Use 'cao-mapping list' to see available concepts.")
        raise typer.Exit(1)

    field_name = f"aliases_{language}"
    if field_name not in mappings[concept]:
        typer.echo(f"❌ Invalid language '{language}'. Use 'nl' or 'en'.")
        raise typer.Exit(1)

    # Check if alias already exists
    existing = mappings[concept][field_name]
    if alias.lower() in [a.lower() for a in existing]:
        typer.echo(f"⚠️  Alias '{alias}' already exists for {concept}")
        return

    # Add alias
    mappings[concept][field_name].append(alias)
    data["mappings"] = mappings
    data["last_updated"] = "2026-03-10"  # TODO: Use actual date

    save_mappings(data)

    typer.echo(f"✅ Added '{alias}' ({language}) to {concept}")
    typer.echo(f"   SETU field: {mappings[concept]['setu_field']}")


@app.command()
def show_stats() -> None:
    """Show mapping statistics."""
    data = load_mappings()
    mappings = data["mappings"]

    total_mappings = len(mappings)
    total_nl_aliases = sum(len(m.get("aliases_nl", [])) for m in mappings.values())
    total_en_aliases = sum(len(m.get("aliases_en", [])) for m in mappings.values())
    total_examples = sum(len(m.get("examples", [])) for m in mappings.values())

    typer.echo(f"\n📊 Mapping Statistics (v{data['version']})")
    typer.echo(f"{'='*50}")
    typer.echo(f"Total mappings:        {total_mappings}")
    typer.echo(f"Dutch aliases:         {total_nl_aliases}")
    typer.echo(f"English aliases:       {total_en_aliases}")
    typer.echo(f"Real CAO examples:     {total_examples}")
    typer.echo(f"\nLast updated:          {data['last_updated']}")
    typer.echo(f"Target SETU version:   {data['setu_version']}")

    # Show learning stats if available
    if "learning" in data and "unmapped_terms" in data["learning"]:
        unmapped = len(data["learning"]["unmapped_terms"])
        if unmapped > 0:
            typer.echo(f"\n⚠️  Unmapped terms found: {unmapped}")
            typer.echo("   Run 'cao-mapping show-unmapped' to review")


@app.command()
def show_unmapped() -> None:
    """Show unmapped terms found in validation feedback (learning system)."""
    data = load_mappings()

    if "learning" not in data or "unmapped_terms" not in data["learning"]:
        typer.echo("✅ No unmapped terms found yet")
        return

    unmapped = data["learning"]["unmapped_terms"]

    if not unmapped:
        typer.echo("✅ No unmapped terms found yet")
        return

    typer.echo(f"\n⚠️  Found {len(unmapped)} unmapped term(s):\n")

    for i, item in enumerate(unmapped, 1):
        typer.echo(f"{i}. \"{item['term']}\"")
        typer.echo(f"   Frequency: {item['count']} CAOs")
        typer.echo(f"   Suggested mapping: {item.get('suggested_mapping', 'None')}")
        typer.echo(f"   Status: {item['status']}")
        if item.get("notes"):
            typer.echo(f"   Notes: {item['notes']}")
        typer.echo()


@app.command()
def validate_yaml() -> None:
    """Validate the YAML mappings file for correctness."""
    try:
        data = load_mappings()

        # Check required top-level fields
        required_fields = ["version", "last_updated", "setu_version", "mappings"]
        for field in required_fields:
            if field not in data:
                typer.echo(f"❌ Missing required field: {field}")
                raise typer.Exit(1)

        # Check each mapping
        mappings = data["mappings"]
        for mapping_id, mapping in mappings.items():
            required_mapping_fields = [
                "concept_id",
                "setu_field",
                "setu_root_property",
                "description",
                "aliases_nl",
                "aliases_en",
                "decision_logic",
                "setu_structure",
            ]
            for field in required_mapping_fields:
                if field not in mapping:
                    typer.echo(f"❌ Mapping '{mapping_id}' missing field: {field}")
                    raise typer.Exit(1)

        typer.echo(f"✅ YAML validation passed")
        typer.echo(f"   {len(mappings)} mappings validated successfully")

    except Exception as e:
        typer.echo(f"❌ Validation failed: {e}")
        raise typer.Exit(1)


@app.command()
def export_for_llm(
    output_file: Path = typer.Option(
        Path("cao_setu_mappings_for_llm.txt"),
        help="Output file for LLM-friendly format"
    ),
) -> None:
    """Export mappings in LLM-friendly format for prompts.

    This generates a concise text format optimized for including in extraction prompts.
    """
    data = load_mappings()
    mappings = data["mappings"]

    output = []
    output.append("=== CAO → SETU FIELD MAPPINGS ===\n")

    for i, (mapping_id, mapping) in enumerate(mappings.items(), 1):
        output.append(f"{i}. {mapping['description'].strip()}")
        output.append(f"   Dutch: {', '.join(mapping['aliases_nl'][:8])}")
        output.append(f"   English: {', '.join(mapping['aliases_en'][:6])}")
        output.append(f"   ✅ SETU field: {mapping['setu_field']}")
        output.append(f"   {mapping['decision_logic'].strip()}\n")

    with open(output_file, "w") as f:
        f.write("\n".join(output))

    typer.echo(f"✅ Exported LLM-friendly mappings to {output_file}")
    typer.echo(f"   {len(mappings)} mappings, {sum(len(m['aliases_nl']) + len(m['aliases_en']) for m in mappings.values())} total aliases")


if __name__ == "__main__":
    app()
