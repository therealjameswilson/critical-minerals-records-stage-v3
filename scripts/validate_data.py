#!/usr/bin/env python3
"""Validate V3 source snapshots, normalized tables, derived claims, and site contract."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
YEARS = set(range(1993, 2027))
EXPECTED_HASHES = {
    "us_imports_for_consumption_1993-2026.xlsx": "fb453f549a3a9923b474a7b1fc4833b98319eef110e00920d79fb63b558d9b45",
    "us_domestic_exports_1993-2026.xlsx": "720ef6d04586002c2d2475a85ab45e0b63ad025ce0dc1a9a0fdf7a3f4f91a2c1",
    "assets/vendor/chart.js/chart.umd.min.js": "48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a",
}
REQUIRED_LONG_COLUMNS = [
    "reporter", "flow", "partner", "partner_iso", "hts", "hts_desc", "mineral",
    "processing_stage", "year", "ytd_flag", "value_usd", "qty1", "qty1_unit",
    "qty2", "qty2_unit", "source", "retrieved_at",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: str | int | float | None) -> float | None:
    if value in (None, ""):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def close(actual: float, expected: float, tolerance: float = 1e-8) -> bool:
    return math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance)


def main() -> int:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    required_files = [
        PROCESSED / "trade_long.csv",
        PROCESSED / "china_share_of_us_imports.csv",
        PROCESSED / "supplier_diversification_index.csv",
        PROCESSED / "unit_value.csv",
        PROCESSED / "prc_supplier_origin_index.csv",
        PROCESSED / "classification_breaks.csv",
        PROCESSED / "data_dictionary.csv",
        PROCESSED / "query_manifest.json",
        PROCESSED / "site-summary.json",
        PROCESSED / "explorer-index.json",
    ]
    for path in required_files:
        require(path.is_file(), f"missing processed artifact: {path.relative_to(ROOT)}")
    if errors:
        return fail(errors)

    for relative, expected in EXPECTED_HASHES.items():
        path = ROOT / relative if "/" in relative else RAW / relative
        require(path.is_file(), f"missing frozen source: {relative}")
        if path.is_file():
            require(digest(path) == expected, f"frozen source hash changed: {relative}")

    manifest = load_json(PROCESSED / "query_manifest.json")
    require(manifest.get("schema_version") == "3.1.0", "query manifest schema mismatch")
    require(manifest.get("denominator_scope") == "selected_18_partners", "manifest denominator scope is not explicit")
    require(manifest.get("annual_coverage") == [1993, 2025], "annual coverage must stop at 2025")
    require(manifest.get("ytd_coverage") == [1993, 2026], "YTD coverage must end at 2026")
    require(manifest.get("ytd_months") == "January-April", "YTD month window missing")
    source_hashes = {Path(row["file"]).name: row["sha256"] for row in manifest.get("sources", [])}
    for filename, expected in list(EXPECTED_HASHES.items())[:2]:
        require(source_hashes.get(filename) == expected, f"manifest hash mismatch: {filename}")

    with (PROCESSED / "trade_long.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        require(headers[: len(REQUIRED_LONG_COLUMNS)] == REQUIRED_LONG_COLUMNS, "trade_long required column contract changed")
        rows = list(reader)
    require(len(rows) == manifest["processed"]["trade_long_rows"] == 71026, "trade_long row count mismatch")
    require({row["reporter"] for row in rows} == {"US"}, "unexpected reporter in DataWeb long table")
    require({row["flow"] for row in rows} == {"imports_for_consumption", "domestic_exports"}, "missing exact trade flow")
    require({int(row["year"]) for row in rows} == YEARS, "long table year coverage mismatch")
    require({row["processing_stage"] for row in rows} <= {"ore", "metal", "compound", "magnet", "alloy"}, "invalid processing stage")
    require({row["partner_iso"] for row in rows if row["partner"] == "China"} == {"CHN"}, "China ISO mismatch")
    require({row["partner_iso"] for row in rows if row["partner"] == "Hong Kong"} == {"HKG"}, "Hong Kong ISO mismatch")

    annual_2026 = [row for row in rows if row["year"] == "2026" and row["ytd_flag"] == "false"]
    require(bool(annual_2026), "missing annual 2026 explicit-gap rows")
    require(
        all(row["value_usd"] == row["qty1"] == row["qty2"] == "" and row["data_status"] == "not_available" for row in annual_2026),
        "annual 2026 structural zeros were not converted to explicit unavailable values",
    )

    first_rows = [row for row in rows if row["quantity_measure_slot"] == "first"]
    second_rows = [row for row in rows if row["quantity_measure_slot"] == "second"]
    require(first_rows and second_rows, "both quantity measure slots are required")
    require(all(row["qty2"] == "" and row["qty2_unit"] == "" for row in first_rows), "Q2 was duplicated onto a first-unit value bucket")
    require(all(row["value_usd"] == "" and row["qty1"] == "" and row["qty2_unit"] for row in second_rows), "Q2 rows are not independent measure rows")
    require(all(row["value_basis"] == "quantity_only_no_lossless_hts4_value_join" for row in second_rows), "Q2 lossless-join warning missing")

    suppression_counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in first_rows:
        if int(row["suppression_raw"] or 0) > 0:
            suppression_counts[(row["flow"], row["ytd_flag"])] += 1
            require(row["quantity_incomplete"] == "true", "positive suppression count not marked incomplete")
    require(suppression_counts[("imports_for_consumption", "false")] == 6, "import annual suppression count mismatch")
    require(suppression_counts[("imports_for_consumption", "true")] == 4, "import YTD suppression count mismatch")
    require(suppression_counts[("domestic_exports", "false")] == 30, "export annual suppression count mismatch")
    require(suppression_counts[("domestic_exports", "true")] == 24, "export YTD suppression count mismatch")
    require(all(int(row["suppression_raw"] or 0) == 0 for row in second_rows), "unexpected Q2 suppression")

    value_groups: dict[tuple[str, int, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    supplier_groups: dict[tuple[str, int, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in first_rows:
        value = as_float(row["value_usd"])
        if row["flow"] != "imports_for_consumption" or value is None:
            continue
        key = row["mineral"], int(row["year"]), row["ytd_flag"]
        value_groups[key][row["partner_iso"]] += value
        if row["partner_iso"] != "CHN":
            supplier_groups[key][row["partner_iso"]] += value

    with (PROCESSED / "china_share_of_us_imports.csv").open(encoding="utf-8", newline="") as handle:
        share_rows = list(csv.DictReader(handle))
    for row in share_rows:
        key = row["mineral"], int(row["year"]), row["ytd_flag"]
        values = value_groups.get(key, {})
        total = sum(values.values())
        china = values.get("CHN", 0)
        expected = china / total if total > 0 else None
        observed = as_float(row["china_share"])
        require(
            (expected is None and observed is None) or (expected is not None and observed is not None and close(expected, observed)),
            f"China share derivation mismatch: {key}",
        )
        require(row["denominator_scope"] == "selected_18_partners", f"share denominator mislabeled: {key}")

    audit_points = {
        (1993, "false"): (26661818, 307967083, 0.0865735966),
        (2023, "false"): (741050093, 1064952324, 0.6958528343),
        (2025, "false"): (554743883, 918390110, 0.6040394784),
        (2025, "true"): (253505481, 393129628, 0.6448394192),
        (2026, "true"): (283191927, 481591943, 0.5880329418),
    }
    for (year, ytd), (china, total, share) in audit_points.items():
        row = next(item for item in share_rows if item["mineral"] == "rare_earths" and item["year"] == str(year) and item["ytd_flag"] == ytd)
        require(as_float(row["china_value_usd"]) == china, f"rare-earth China value mismatch: {year}/{ytd}")
        require(as_float(row["selected_partner_value_usd"]) == total, f"rare-earth selected total mismatch: {year}/{ytd}")
        require(close(as_float(row["china_share"]) or -1, share), f"rare-earth share mismatch: {year}/{ytd}")

    with (PROCESSED / "supplier_diversification_index.csv").open(encoding="utf-8", newline="") as handle:
        diversity_rows = list(csv.DictReader(handle))
    for row in diversity_rows:
        key = row["mineral"], int(row["year"]), row["ytd_flag"]
        positive = [value for value in supplier_groups.get(key, {}).values() if value > 0]
        total = sum(positive)
        expected_count = len(positive)
        expected_hhi = sum((value / total) ** 2 for value in positive) if total else None
        observed_hhi = as_float(row["hhi_value_0_1"])
        require(int(row["non_china_supplier_count"]) == expected_count, f"supplier count mismatch: {key}")
        require(
            (expected_hhi is None and observed_hhi is None) or (expected_hhi is not None and observed_hhi is not None and close(expected_hhi, observed_hhi)),
            f"HHI mismatch: {key}",
        )

    with (PROCESSED / "unit_value.csv").open(encoding="utf-8", newline="") as handle:
        unit_rows = list(csv.DictReader(handle))
    for row in unit_rows:
        quantity = as_float(row["matched_quantity"])
        value = as_float(row["matched_value_usd"])
        observed = as_float(row["unit_value_usd_per_unit"])
        require(quantity is not None and quantity > 0 and value is not None, "invalid unit-value denominator")
        require(observed is not None and close(observed, value / quantity), "unit-value arithmetic mismatch")
        require(row["data_status"] == "reported_matched_unsuppressed_quantity", "unit-value status mismatch")

    breaks = list(csv.DictReader((PROCESSED / "classification_breaks.csv").open(encoding="utf-8", newline="")))
    break_ids = {row["break_note_id"] for row in breaks}
    require("hts8505-unit-regime-2019" in break_ids, "8505 measurement break missing")
    require({f"hs-revision-{year}" for year in (1996, 2002, 2007, 2012, 2017, 2022)} <= break_ids, "HTS revision checkpoints missing")

    comtrade_dir = RAW / "un_comtrade_china" / "2846"
    comtrade_manifest = load_json(comtrade_dir / "manifest.json")
    require(comtrade_manifest["validation"]["status"] == "passed", "Comtrade acquisition did not pass")
    require(comtrade_manifest["validation"]["observed_years"] == list(range(1993, 2025)), "Comtrade year coverage mismatch")
    for record in comtrade_manifest["files"]:
        path = comtrade_dir / record["file"]
        require(path.is_file(), f"missing Comtrade response: {record['file']}")
        if path.is_file():
            require(digest(path) == record["sha256"], f"Comtrade response hash mismatch: {record['file']}")
        require(record["count"] < 500, f"Comtrade preview ceiling reached: {record['year']}")
        require(record["partner_world_absolute_difference_usd"] == 0, f"Comtrade World reconciliation failed: {record['year']}")

    with (PROCESSED / "prc_supplier_origin_index.csv").open(encoding="utf-8", newline="") as handle:
        prc_index = list(csv.DictReader(handle))
    require(len(prc_index) == 32, "PRC supplier-origin index must contain 32 annual rows")
    require([int(row["year"]) for row in prc_index] == list(range(1993, 2025)), "PRC origin-index year coverage mismatch")
    require(all(as_float(row["world_value_usd"]) == as_float(row["partner_sum_usd"]) for row in prc_index), "PRC origin-index World reconciliation mismatch")

    summary_path = PROCESSED / "site-summary.json"
    summary = load_json(summary_path)
    require(summary_path.stat().st_size <= 150_000, "site-summary.json exceeds 150 KB budget")
    require(summary["headline"]["year"] == 2025 and close(summary["headline"]["value"], 0.6040394784), "headline claim mismatch")
    prc = summary["prc_supply_origins"]
    require(prc["status"] == "loaded" and prc["coverage"] == [1993, 2024], "PRC site series not loaded or mislabeled")
    require(prc["yearly"][0]["positive_origin_count"] == 14, "PRC 1993 origin count mismatch")
    require(prc["yearly"][-1]["positive_origin_count"] == 33, "PRC 2024 origin count mismatch")
    require(close(prc["yearly"][-1]["hhi_value_0_1"], 0.4059395639), "PRC 2024 HHI mismatch")
    require({row["flow"] for row in summary["sources"]} == {"imports_for_consumption", "domestic_exports", "china_reported_imports"}, "site provenance does not expose all three frozen inputs")

    explorer_index = load_json(PROCESSED / "explorer-index.json")
    require(len(explorer_index) == 25, "expected 25 explorer shards")
    for entry in explorer_index:
        path = ROOT / entry["file"]
        require(path.is_file(), f"missing explorer shard: {entry['hts']}")
        if path.is_file():
            require(path.stat().st_size == entry["bytes"], f"explorer size mismatch: {entry['hts']}")
            require(path.stat().st_size <= 250_000, f"explorer shard exceeds 250 KB: {entry['hts']}")

    public_html = (ROOT / "index.html").read_text(encoding="utf-8")
    required_phrases = [
        "18 selected partners, not World",
        "FRUS is not an evidentiary source here",
        "do not, by themselves, prove policy intent",
        "2026 shown as Jan–Apr YTD",
        "assets/vendor/chart.js/chart.umd.min.js",
    ]
    for phrase in required_phrases:
        require(phrase in public_html, f"index.html missing trust language: {phrase!r}")
    for html_path in (ROOT / "index.html", ROOT / "methodology.html", ROOT / "records-stage.html", ROOT / "404.html"):
        text = html_path.read_text(encoding="utf-8")
        for reference in re.findall(r'(?:href|src)=["\']([^"\']+)', text):
            if reference.startswith(("http://", "https://", "data:", "#", "mailto:")):
                continue
            clean = reference.split("?", 1)[0].split("#", 1)[0]
            if not clean or clean in {".", "./"}:
                continue
            require((html_path.parent / clean).exists(), f"broken local reference in {html_path.name}: {reference}")
    require(not (ROOT / "data" / "v3").exists(), "obsolete data/v3 output still ships")
    require(not (ROOT / "scripts" / "ingest_dataweb_exports.py").exists(), "obsolete value-only ETL still ships")

    if errors:
        return fail(errors)
    print(
        f"Validation passed: {len(rows):,} normalized rows, {len(unit_rows):,} unit-value rows, "
        f"25 explorer shards, 32 PRC reporter years, exact audited headline 60.4%."
    )
    return 0


def fail(errors: list[str]) -> int:
    print("V3 validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
