#!/usr/bin/env python3
"""Import the official 1970-1990 rare-earth trade tables.

The importer preserves the product categories, published symbols, units, and
footnotes in USGS Statistical Compendium tables 3 and 4. The tables identify
the Bureau of the Census as their source. They remain separate from the later
USGS Data Series 140 standardized series and never imply partner-country flows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "history-stack"
DETAIL_OUTPUT = DATA / "trade-details.json"
RESEARCH_OUTPUT = DATA / "trade-research.json"

IMPORT_URL = "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/mineral-pubs/rare-earth/stats/tbl3.txt"
EXPORT_URL = "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/mineral-pubs/rare-earth/stats/tbl4.txt"
CENSUS_GUIDE_URL = "https://www2.census.gov/library/publications/economic-census/1982/Guide_to_the_1982_Economic_Censuses.pdf"
CENSUS_REQUEST_URL = "https://www2.census.gov/programs-surveys/trade/reference/products/orderform.html"

YEAR_RE = re.compile(r"\b(19\d{2})\b")
VALUE_TOKEN_RE = re.compile(r"^(?:NA|--|\(\d+/\)|\d[\d,]*)$")


def fetch_text(url: str, cache_path: Path | None = None) -> str:
    if cache_path and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    request = Request(url, headers={"User-Agent": "critical-minerals-records-stage/2.0"})
    with urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8")
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
    return text


def canonical_category(source_label: str) -> str:
    label = re.sub(r"-+$", "", source_label.strip())
    label = re.sub(r"\d+/$", "", label).strip()
    label = re.sub(r"\s+", " ", label)
    lowered = label.lower()
    if lowered.startswith("total"):
        return "Published total"
    if lowered.startswith("thorium ore"):
        return "Thorium ore and concentrates"
    if "pyrophoric alloys" in lowered:
        return "Ferrocerium and other pyrophoric alloys"
    if lowered.startswith("cerium compounds"):
        return "Cerium compounds"
    if lowered.startswith("mixtures of rare-earth"):
        return "Mixtures of rare-earth oxides and chlorides"
    if lowered.startswith("cerium salts"):
        return "Cerium salts"
    if lowered.startswith("rare-earth oxide"):
        return "Rare-earth oxide excluding cerium oxide"
    if lowered.startswith("rare-earth alloys"):
        return "Rare-earth alloys"
    if lowered.startswith("rare-earth metals including"):
        return "Rare-earth metals including scandium and yttrium"
    if lowered.startswith("other rare-earth metals"):
        return "Other rare-earth metals"
    raise ValueError(f"Unrecognized source category: {source_label!r}")


def category_slug(category: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")


def parsed_blocks(text: str, values_per_year: int) -> list[tuple[list[int], list[tuple[str, list[str]]]]]:
    lines = text.splitlines()
    blocks: list[tuple[list[int], list[tuple[str, list[str]]]]] = []
    index = 0
    while index < len(lines):
        years = [int(value) for value in YEAR_RE.findall(lines[index])]
        if not years or not all(1970 <= year <= 1990 for year in years) or "Table" in lines[index]:
            index += 1
            continue
        expected_values = len(years) * values_per_year
        pending_label: list[str] = []
        records: list[tuple[str, list[str]]] = []
        index += 1
        while index < len(lines):
            line = lines[index]
            next_years = [int(value) for value in YEAR_RE.findall(line)]
            if next_years and all(1970 <= year <= 1990 for year in next_years) and "Table" not in line:
                break
            stripped = line.strip()
            if stripped.startswith(("See footnotes", "NA  Not available", "Source:")) or re.match(r"^[1-4]/", stripped):
                break
            tokens = stripped.split()
            tail = tokens[-expected_values:] if len(tokens) >= expected_values else []
            if tail and all(VALUE_TOKEN_RE.fullmatch(token) for token in tail):
                label_part = " ".join(tokens[:-expected_values])
                raw_label = " ".join([*pending_label, label_part]).strip()
                pending_label = []
                if raw_label:
                    records.append((raw_label, tail))
            elif stripped and any(character.isalpha() for character in stripped):
                if not any(marker in stripped for marker in ("Quantity", "Metric tons", "U.S. imports", "U.S. exports")):
                    pending_label.append(stripped)
            index += 1
        if records:
            blocks.append((years, records))
    return blocks


def measure(token: str, unit: str, unavailable_footnote: str) -> dict:
    if re.fullmatch(r"\d[\d,]*", token):
        value = int(token.replace(",", ""))
        return {"value": value, "display": f"{value:,}", "unit": unit, "status": "reported", "source_symbol": token}
    if token == "NA":
        return {"value": None, "display": "Not available", "unit": unit, "status": "not-available", "source_symbol": token}
    if token == "--":
        return {"value": None, "display": "Published dash", "unit": unit, "status": "published-dash", "source_symbol": token}
    if token == "(3/)":
        return {"value": None, "display": "Less than 0.5", "unit": unit, "status": "less-than", "source_symbol": token}
    if token == "(2/)":
        return {"value": None, "display": unavailable_footnote, "unit": unit, "status": "not-available", "source_symbol": token}
    raise ValueError(f"Unrecognized table value: {token!r}")


def classification_note(year: int, category: str, direction: str) -> str:
    notes = ["The table preserves the contemporaneous published categories and symbols."]
    if direction == "imports" and category == "Published total":
        notes.append("The source notes that totals may not add because of independent rounding.")
    if direction == "imports" and category == "Mixtures of rare-earth oxides and chlorides" and year < 1989:
        notes.append("Before 1989, the source combines rare-earth oxides and chlorides.")
    if direction == "exports" and category == "Rare-earth metals including scandium and yttrium" and 1971 <= year <= 1977:
        notes.append("For 1971-1977, the source says this category includes rare-earth compounds and mixtures.")
    if direction == "exports" and category == "Published total":
        notes.append("The export total includes thorium ore and concentrates and is not equivalent to a modern rare-earth-element product total.")
    if year >= 1989:
        notes.append("The source warns that categories for 1989 and 1990 are not necessarily comparable with previous years following implementation of the Harmonized Tariff System.")
    return " ".join(notes)


def import_rows(text: str, access_date: str) -> list[dict]:
    rows: list[dict] = []
    for years, records in parsed_blocks(text, values_per_year=2):
        for source_label, values in records:
            category = canonical_category(source_label)
            for offset, year in enumerate(years):
                rows.append({
                    "id": f"census-usgs-rare-earth-{year}-imports-{category_slug(category)}",
                    "year": year,
                    "mineral_id": "rare-earth-elements",
                    "direction": "imports",
                    "category": category,
                    "source_category_label": source_label,
                    "quantity": measure(values[offset * 2], "metric tons", "Not separately available"),
                    "trade_value": measure(values[offset * 2 + 1], "thousand current U.S. dollars", "Not separately available"),
                    "is_total": category == "Published total",
                    "source_id": "usgs-statistical-compendium",
                    "source_origin_agency": "Bureau of the Census",
                    "publication_title": "Rare Earths Statistical Compendium",
                    "table_or_page": "Table 3, U.S. imports for consumption of rare-earths",
                    "source_url": IMPORT_URL,
                    "access_date": access_date,
                    "transcription_status": "machine-parsed-reviewed-official-table",
                    "classification_note": classification_note(year, category, "imports"),
                    "confidence": "high",
                })
    return rows


def export_rows(text: str, access_date: str) -> list[dict]:
    rows: list[dict] = []
    for years, records in parsed_blocks(text, values_per_year=1):
        for source_label, values in records:
            category = canonical_category(source_label)
            for offset, year in enumerate(years):
                rows.append({
                    "id": f"census-usgs-rare-earth-{year}-exports-{category_slug(category)}",
                    "year": year,
                    "mineral_id": "rare-earth-elements",
                    "direction": "exports",
                    "category": category,
                    "source_category_label": source_label,
                    "quantity": measure(values[offset], "metric tons", "Not separately available"),
                    "trade_value": {"value": None, "display": "Not published in this table", "unit": "thousand current U.S. dollars", "status": "not-published", "source_symbol": None},
                    "is_total": category == "Published total",
                    "source_id": "usgs-statistical-compendium",
                    "source_origin_agency": "Bureau of the Census",
                    "publication_title": "Rare Earths Statistical Compendium",
                    "table_or_page": "Table 4, U.S. exports of rare-earths",
                    "source_url": EXPORT_URL,
                    "access_date": access_date,
                    "transcription_status": "machine-parsed-reviewed-official-table",
                    "classification_note": classification_note(year, category, "exports"),
                    "confidence": "high",
                })
    return rows


def detail_rows(import_text: str, export_text: str, access_date: str) -> list[dict]:
    rows = import_rows(import_text, access_date) + export_rows(export_text, access_date)
    rows.sort(key=lambda row: (row["year"], 0 if row["direction"] == "imports" else 1, row["is_total"], row["category"]))
    identifiers = [row["id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate rare-earth trade detail identifiers")
    return rows


def research_rows(details: list[dict]) -> list[dict]:
    total_ids = {(row["year"], row["direction"]): row["id"] for row in details if row["is_total"]}
    rows = []
    for year in range(1970, 1991):
        import_title = "U.S. Imports for Consumption and General Imports, TSUSA Commodity by Country of Origin" if year < 1989 else "U.S. Imports for Consumption and General Imports, HTSUSA Commodity by Country of Origin"
        rows.append({
            "id": f"census-ft-{year}-rare-earth-partners",
            "year": year,
            "mineral_id": "rare-earth-elements",
            "title": f"Recover the {year} rare-earth country breakdown",
            "status": "source-acquisition",
            "objective": "Transcribe country-of-origin imports and country-of-destination exports without inferring bilateral flows from national totals.",
            "reports": [
                {
                    "series": "FT 246",
                    "title": import_title,
                    "role": "Import quantity and value by contemporaneous commodity classification and country of origin",
                    "official_description_url": CENSUS_GUIDE_URL,
                },
                {
                    "series": "FT 446",
                    "title": "U.S. Exports, Schedule B Commodity by Country",
                    "role": "Export quantity and value by contemporaneous Schedule B commodity and country of destination",
                    "official_description_url": CENSUS_GUIDE_URL,
                },
            ],
            "control_total_ids": [total_ids[(year, "imports")], total_ids[(year, "exports")]],
            "required_fields": [
                "classification system and code",
                "published commodity description",
                "country code and historical country name",
                "quantity and original unit",
                "customs or f.a.s. value basis",
                "report page or table",
                "human-review status",
            ],
            "classification_notes": [
                f"Do not map {year} commodity categories directly to current HS codes without a reviewed concordance.",
                "Reconcile country rows to the corresponding published category total, not to the differently standardized Data Series 140 aggregate.",
                "Do not draw atlas trade-flow lines until the partner rows and their units have been reviewed.",
            ],
            "source_ids": ["census-historical-trade", "usgs-statistical-compendium"],
            "official_request_url": CENSUS_REQUEST_URL,
            "completeness": "research-queue",
        })
    return rows


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--access-date", default=date.today().isoformat())
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--detail-output", type=Path, default=DETAIL_OUTPUT)
    parser.add_argument("--research-output", type=Path, default=RESEARCH_OUTPUT)
    args = parser.parse_args()
    import_cache = args.cache_dir / "rare-earth-imports-table-3.txt" if args.cache_dir else None
    export_cache = args.cache_dir / "rare-earth-exports-table-4.txt" if args.cache_dir else None
    details = detail_rows(fetch_text(IMPORT_URL, import_cache), fetch_text(EXPORT_URL, export_cache), args.access_date)
    research = research_rows(details)
    write(args.detail_output, details)
    write(args.research_output, research)
    print(f"Wrote {len(details)} rare-earth trade detail rows for 1970-1990 and {len(research)} research queues")


if __name__ == "__main__":
    main()
