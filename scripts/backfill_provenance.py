"""Backfill provenance sidecars for the ground-truth CAOs.

Runs BOTH models sectioned (Gemini + independent Mistral) and computes per-section
inter-model agreement. Run: python3 scripts/backfill_provenance.py
"""
# ruff: noqa: E402  -- path/.env setup must run before importing cao_engine
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent / ".env"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cao_engine.config import Settings
from cao_engine.extraction.sectioned import SectionedGeminiExtractor, make_gemini_generate
from cao_engine.extraction.sectioned.mistral_sectioned import make_mistral_generate
from cao_engine.extraction.sectioned.sections import SECTIONS
from cao_engine.provenance.agreement import compute_agreement
from cao_engine.provenance.provenance_writer import write_provenance

STEMS = [
    "1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024",
    "1006-groothandel-in-bloemen-en-planten-vgb-cao-2024-2026-v08042025",
    "1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024",
    "1055-rabobank-cao-2024-2025-v01102024",
]


def main() -> None:
    settings = Settings()
    provenance_dir = settings.data_dir / "provenance"
    gemini = make_gemini_generate(settings.google_api_key, settings.gemini_model, "LOW")
    mistral = make_mistral_generate(settings.mistral_api_key, settings.extraction_model)
    for stem in STEMS:
        ocr = settings.ocr_dir / f"{stem}.md"
        if not ocr.exists():
            print(f"{stem}: SKIP (no OCR)")
            continue
        md = ocr.read_text(encoding="utf-8")
        gemini_doc = SectionedGeminiExtractor(gemini).extract(md, stem)
        mistral_doc = SectionedGeminiExtractor(mistral).extract(md, stem)
        agreement = compute_agreement(gemini_doc, mistral_doc, SECTIONS)
        path = write_provenance(stem, agreement, provenance_dir)
        print(f"{stem}: {agreement} -> {path}")


if __name__ == "__main__":
    main()
