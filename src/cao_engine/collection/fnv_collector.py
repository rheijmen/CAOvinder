"""FNV CAO Collector - sitemap-driven incremental collection of CAO PDFs.

Uses the FNV sitemap (cao-sector.xml) to detect changed pages, then deep-crawls
only those pages for new PDFs. Maintains a manifest to avoid re-downloading.

Full scan: crawls all 1000+ pages (~15-20 min)
Incremental scan: only pages changed since last run (typically seconds to minutes)
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

BASE_URL = "https://www.fnv.nl"
SITEMAP_URL = f"{BASE_URL}/sitemaps/cao-sector.xml"
SECTOR_INDEX = f"{BASE_URL}/cao-sector"
SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
HEADERS = {"User-Agent": "CAOvinder/0.1 (cao-engine; research)"}
MAX_CRAWL_DEPTH = 2
REQUEST_DELAY = 0.3
MANIFEST_FILENAME = ".fnv_manifest.json"

console = Console()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CollectedPDF:
    url: str
    filename: str
    sector: str
    subsector: str
    saved_path: Path | None = None
    size_kb: int = 0
    is_new: bool = False
    skipped: bool = False


@dataclass
class CrawlStats:
    pages_visited: int = 0
    pages_skipped: int = 0
    pdfs_found: int = 0
    pdfs_new: int = 0
    pdfs_skipped: int = 0
    pdfs_failed: int = 0


# ---------------------------------------------------------------------------
# Manifest — tracks what we already have
# ---------------------------------------------------------------------------

class Manifest:
    """JSON manifest tracking downloaded PDFs and page modification dates."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict = {"last_scan": None, "page_dates": {}, "pdfs": {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def last_scan(self) -> datetime | None:
        ts = self.data.get("last_scan")
        return datetime.fromisoformat(ts) if ts else None

    def page_lastmod(self, url: str) -> str | None:
        return self.data.get("page_dates", {}).get(url)

    def set_page_lastmod(self, url: str, lastmod: str) -> None:
        self.data.setdefault("page_dates", {})[url] = lastmod

    def has_pdf(self, url: str) -> bool:
        return url in self.data.get("pdfs", {})

    def add_pdf(self, url: str, filename: str, size_kb: int, sector: str) -> None:
        self.data.setdefault("pdfs", {})[url] = {
            "filename": filename,
            "size_kb": size_kb,
            "sector": sector,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def pdf_count(self) -> int:
        return len(self.data.get("pdfs", {}))

    def save(self) -> None:
        self.data["last_scan"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get_client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)


def _fetch_html(client: httpx.Client, url: str) -> str | None:
    try:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError:
        return None


def _extract_links(html: str, base_url: str) -> list[str]:
    pattern = r'href=["\']([^"\']+)["\']'
    raw = re.findall(pattern, html)
    links = []
    for href in raw:
        if href.startswith(("mailto:", "tel:", "#")):
            continue
        links.append(urljoin(base_url, href))
    return links


def _extract_pdf_links(html: str, base_url: str) -> list[str]:
    pdfs = []
    for link in _extract_links(html, base_url):
        clean = link.split("?")[0]
        if ".pdf" in clean.lower():
            if clean not in pdfs:
                pdfs.append(clean)
    return pdfs


def _is_fnv_sector_link(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.netloc in ("www.fnv.nl", "fnv.nl", "")
        and "/cao-sector/" in parsed.path
        and not parsed.path.endswith((".pdf", ".jpg", ".png", ".gif"))
    )


# ---------------------------------------------------------------------------
# Sitemap parsing
# ---------------------------------------------------------------------------

def fetch_sitemap(client: httpx.Client) -> dict[str, str]:
    """Fetch FNV cao-sector sitemap, return {url: lastmod} mapping."""
    resp = client.get(SITEMAP_URL)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    pages: dict[str, str] = {}
    for url_elem in root.findall(".//s:url", SITEMAP_NS):
        loc = url_elem.find("s:loc", SITEMAP_NS)
        lastmod = url_elem.find("s:lastmod", SITEMAP_NS)
        if loc is not None and loc.text:
            pages[loc.text] = lastmod.text if lastmod is not None else ""
    return pages


def find_changed_pages(
    sitemap: dict[str, str], manifest: Manifest
) -> list[str]:
    """Return page URLs that have changed since last scan."""
    changed = []
    for url, lastmod in sitemap.items():
        prev = manifest.page_lastmod(url)
        if prev != lastmod:
            changed.append(url)
    return changed


# ---------------------------------------------------------------------------
# Sector tree (for full scans)
# ---------------------------------------------------------------------------

def get_sector_tree(client: httpx.Client) -> dict[str, list[str]]:
    """Build sector -> subsector mapping from the index page."""
    html = _fetch_html(client, SECTOR_INDEX)
    if not html:
        raise RuntimeError(f"Could not fetch {SECTOR_INDEX}")

    all_links = _extract_links(html, SECTOR_INDEX)
    sector_links: list[str] = []
    subsector_links: list[str] = []

    for link in all_links:
        parsed = urlparse(link)
        if not parsed.path.startswith("/cao-sector/"):
            continue
        if parsed.netloc and parsed.netloc not in ("www.fnv.nl", "fnv.nl"):
            continue
        path = parsed.path.rstrip("/")
        parts = path.split("/")
        full = urljoin(BASE_URL, path)
        if len(parts) == 3 and full not in sector_links:
            sector_links.append(full)
        elif len(parts) == 4 and full not in subsector_links:
            subsector_links.append(full)

    tree: dict[str, list[str]] = {s: [] for s in sector_links}
    for sub in subsector_links:
        parent = "/".join(sub.rstrip("/").split("/")[:-1])
        tree.setdefault(parent, []).append(sub)
    return tree


# ---------------------------------------------------------------------------
# Deep crawl
# ---------------------------------------------------------------------------

def deep_crawl_pdfs(
    client: httpx.Client,
    start_url: str,
    max_depth: int = MAX_CRAWL_DEPTH,
    stats: CrawlStats | None = None,
) -> list[str]:
    """Crawl a page and follow internal links for PDF links."""
    if stats is None:
        stats = CrawlStats()

    visited: set[str] = set()
    pdf_urls: list[str] = []

    def _crawl(url: str, depth: int) -> None:
        normalized = url.split("?")[0].rstrip("/")
        if normalized in visited or depth > max_depth:
            return
        visited.add(normalized)

        html = _fetch_html(client, url)
        if html is None:
            return
        stats.pages_visited += 1

        for pdf_url in _extract_pdf_links(html, url):
            if pdf_url not in pdf_urls:
                pdf_urls.append(pdf_url)

        if depth < max_depth:
            for link in _extract_links(html, url):
                if _is_fnv_sector_link(link):
                    link_norm = link.split("?")[0].rstrip("/")
                    if link_norm not in visited:
                        time.sleep(REQUEST_DELAY)
                        _crawl(link, depth + 1)

    _crawl(start_url, 0)
    return pdf_urls


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

def download_pdf(
    client: httpx.Client,
    url: str,
    output_dir: Path,
    sector: str,
    subsector: str,
) -> CollectedPDF:
    """Download a single PDF."""
    clean_url = url.split("?")[0]
    filename = clean_url.split("/")[-1]
    filename = httpx.URL(filename).path or "unknown.pdf"

    filepath = output_dir / filename
    result = CollectedPDF(
        url=url, filename=filename, sector=sector, subsector=subsector
    )

    if filepath.exists():
        result.saved_path = filepath
        result.size_kb = filepath.stat().st_size // 1024
        result.skipped = True
        return result

    try:
        resp = client.get(url, timeout=60.0)
        resp.raise_for_status()
        content = resp.content
        if not content[:5].startswith(b"%PDF"):
            result.skipped = True
            return result
        filepath.write_bytes(content)
        result.saved_path = filepath
        result.size_kb = len(content) // 1024
        result.is_new = True
    except httpx.HTTPError:
        pass

    return result


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------

def collect_incremental(
    output_dir: Path,
    cao_only: bool = False,
) -> tuple[list[CollectedPDF], CrawlStats]:
    """Incremental collection: only crawl pages changed since last scan.

    Uses the FNV sitemap lastmod dates compared against the manifest.
    Falls back to a full scan if no manifest exists.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(output_dir / MANIFEST_FILENAME)
    stats = CrawlStats()
    all_pdfs: list[CollectedPDF] = []

    with _get_client() as client:
        # Step 1: Fetch sitemap
        console.print("[bold]Fetching FNV sitemap...[/bold]")
        sitemap = fetch_sitemap(client)
        console.print(f"Sitemap: [bold]{len(sitemap)}[/bold] pages")

        if manifest.last_scan is None:
            console.print(
                "[yellow]No previous scan found — running full collection.[/yellow]"
            )
            return collect_full(output_dir, cao_only=cao_only)

        # Step 2: Find changed pages
        changed = find_changed_pages(sitemap, manifest)
        if not changed:
            console.print("[green]No changes detected since last scan.[/green]")
            console.print(
                f"Last scan: {manifest.last_scan.strftime('%Y-%m-%d %H:%M')}, "
                f"manifest has {manifest.pdf_count()} PDFs"
            )
            return all_pdfs, stats

        console.print(
            f"[bold]{len(changed)}[/bold] pages changed since "
            f"{manifest.last_scan.strftime('%Y-%m-%d %H:%M')}"
        )
        stats.pages_skipped = len(sitemap) - len(changed)

        # Step 3: Deep-crawl only changed pages
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning changes...", total=len(changed))

            for i, page_url in enumerate(changed):
                label = page_url.replace(BASE_URL, "")
                progress.update(task, description=f"Crawling {label}...")

                sector, subsector = _url_to_sector(page_url)
                pdf_urls = deep_crawl_pdfs(client, page_url, stats=stats)

                for pdf_url in pdf_urls:
                    if cao_only and not _is_cao_filename(pdf_url):
                        continue
                    if manifest.has_pdf(pdf_url):
                        stats.pdfs_skipped += 1
                        continue
                    if any(p.url == pdf_url for p in all_pdfs):
                        continue

                    stats.pdfs_found += 1
                    result = download_pdf(
                        client, pdf_url, output_dir, sector, subsector
                    )

                    if result.is_new and result.saved_path:
                        stats.pdfs_new += 1
                        manifest.add_pdf(
                            pdf_url, result.filename, result.size_kb,
                            f"{sector}/{subsector}"
                        )
                    elif result.skipped:
                        stats.pdfs_skipped += 1
                        if not manifest.has_pdf(pdf_url) and result.saved_path:
                            manifest.add_pdf(
                                pdf_url, result.filename, result.size_kb,
                                f"{sector}/{subsector}"
                            )
                    else:
                        stats.pdfs_failed += 1

                    all_pdfs.append(result)
                    time.sleep(REQUEST_DELAY)

                # Update page lastmod in manifest
                if page_url in sitemap:
                    manifest.set_page_lastmod(page_url, sitemap[page_url])

                progress.update(task, completed=i + 1)
                time.sleep(REQUEST_DELAY)

        manifest.save()

    return all_pdfs, stats


def collect_full(
    output_dir: Path,
    cao_only: bool = False,
) -> tuple[list[CollectedPDF], CrawlStats]:
    """Full collection: crawl all sectors and download all PDFs.

    Also fetches the sitemap to populate the manifest for future incremental runs.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(output_dir / MANIFEST_FILENAME)
    stats = CrawlStats()
    all_pdfs: list[CollectedPDF] = []

    with _get_client() as client:
        # Fetch sitemap for manifest population
        console.print("[bold]Fetching FNV sitemap + sector tree...[/bold]")
        try:
            sitemap = fetch_sitemap(client)
        except Exception:
            sitemap = {}
        tree = get_sector_tree(client)

        total_pages = sum(max(len(subs), 1) for subs in tree.values())
        console.print(
            f"Found [bold]{len(tree)}[/bold] sectors, "
            f"[bold]{sum(len(s) for s in tree.values())}[/bold] subsectors"
        )

        page_counter = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            console=console,
        ) as progress:
            task = progress.add_task("Crawling sectors...", total=total_pages)

            for sector_url, subsectors in tree.items():
                sector_name = sector_url.rstrip("/").split("/")[-1]
                pages_to_crawl = subsectors if subsectors else [sector_url]

                for page_url in pages_to_crawl:
                    parts = page_url.rstrip("/").split("/")
                    subsector_name = parts[-1] if len(parts) > 3 else ""
                    label = (
                        f"{sector_name}/{subsector_name}"
                        if subsector_name else sector_name
                    )
                    progress.update(task, description=f"Crawling {label}...")

                    pdf_urls = deep_crawl_pdfs(client, page_url, stats=stats)

                    for pdf_url in pdf_urls:
                        if cao_only and not _is_cao_filename(pdf_url):
                            continue
                        if any(p.url == pdf_url for p in all_pdfs):
                            continue

                        stats.pdfs_found += 1
                        result = download_pdf(
                            client, pdf_url, output_dir,
                            sector_name, subsector_name,
                        )

                        if result.is_new and result.saved_path:
                            stats.pdfs_new += 1
                        elif result.skipped:
                            stats.pdfs_skipped += 1
                        else:
                            stats.pdfs_failed += 1

                        # Always register in manifest
                        if result.saved_path:
                            manifest.add_pdf(
                                pdf_url, result.filename, result.size_kb,
                                f"{sector_name}/{subsector_name}"
                            )

                        all_pdfs.append(result)
                        time.sleep(REQUEST_DELAY)

                    page_counter += 1
                    progress.update(task, completed=page_counter)
                    time.sleep(REQUEST_DELAY)

        # Store sitemap dates for future incremental runs
        for url, lastmod in sitemap.items():
            manifest.set_page_lastmod(url, lastmod)

        manifest.save()

    return all_pdfs, stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _url_to_sector(url: str) -> tuple[str, str]:
    """Extract sector and subsector names from a cao-sector URL."""
    path = urlparse(url).path.rstrip("/")
    parts = path.split("/")
    # /cao-sector/sector/subsector/...
    sector = parts[2] if len(parts) > 2 else ""
    subsector = parts[3] if len(parts) > 3 else ""
    return sector, subsector


def _is_cao_filename(url: str) -> bool:
    """Check if a PDF URL looks like an actual CAO document."""
    fname = url.split("/")[-1].lower()
    return "cao" in fname or bool(re.match(r"^\d+-.*-\d{2}-\d{2}-\d{4}", fname))
