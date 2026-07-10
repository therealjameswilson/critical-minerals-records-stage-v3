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
    "us_domestic_exports_1993-2026.xlsx": "204dbe2f51cf3d0f5eaf554359dac50a27c45c3572b17d268b12629fea59f19c",
    "usgs_ds140_rare_earths_2020.xlsx": "0aed33ac422b49ec77b7c550d0e53e57a59b5a38ae315ea37d8e1088fc0bb85f",
    "assets/vendor/chart.js/chart.umd.min.js": "48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a",
}
EXPECTED_DOWNLOAD_TIMESTAMPS = {
    "us_imports_for_consumption_1993-2026.xlsx": "2026-07-10T16:57:38",
    "us_domestic_exports_1993-2026.xlsx": "2026-07-10T18:23:15",
}
REQUIRED_LONG_COLUMNS = [
    "reporter", "flow", "partner", "partner_iso", "hts", "hts_desc", "mineral",
    "processing_stage", "year", "ytd_flag", "value_usd", "qty1", "qty1_unit",
    "qty2", "qty2_unit", "source", "retrieved_at",
]
USGS_DS140_COLUMNS = [
    "source_id", "commodity", "year", "period_type", "geography", "geography_code", "metric",
    "metric_label", "value", "unit", "value_status", "method_status", "method_note_id",
    "source_value_raw", "source_formula", "scope_note", "source", "source_file", "source_sheet",
    "source_cell", "source_url", "download_url", "worksheet_last_modified", "package_modified_at",
    "source_publication_date", "retrieved_at",
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
        PROCESSED / "usgs_rare_earths_historical.csv",
        PROCESSED / "usgs_rare_earths_metadata.json",
        PROCESSED / "usgs_rare_earths_data_dictionary.csv",
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
    require(manifest.get("schema_version") == "3.2.0", "query manifest schema mismatch")
    require(manifest.get("denominator_scope") == "selected_18_partners", "manifest denominator scope is not explicit")
    require(manifest.get("annual_coverage") == [1993, 2025], "annual coverage must stop at 2025")
    require(manifest.get("ytd_coverage") == [1993, 2026], "YTD coverage must end at 2026")
    require(manifest.get("ytd_months") == "January-April", "YTD month window missing")
    source_hashes = {Path(row["file"]).name: row["sha256"] for row in manifest.get("sources", [])}
    for filename, expected_timestamp in EXPECTED_DOWNLOAD_TIMESTAMPS.items():
        expected = EXPECTED_HASHES[filename]
        require(source_hashes.get(filename) == expected, f"manifest hash mismatch: {filename}")
        source = next((row for row in manifest.get("sources", []) if Path(row["file"]).name == filename), None)
        download_timestamp = next(
            (
                row["value"]
                for row in (source or {}).get("query_parameters", [])
                if row.get("parameter") == "Download Date"
            ),
            None,
        )
        require(
            download_timestamp == expected_timestamp,
            f"manifest download timestamp mismatch: {filename}",
        )

    usgs_metadata = load_json(PROCESSED / "usgs_rare_earths_metadata.json")
    manifest_usgs = manifest.get("usgs_rare_earths_source", {})
    require(manifest_usgs == usgs_metadata, "manifest USGS metadata differs from standalone metadata")
    require(usgs_metadata.get("sha256") == EXPECTED_HASHES["usgs_ds140_rare_earths_2020.xlsx"], "USGS metadata hash mismatch")
    require(usgs_metadata.get("coverage") == [1900, 2020], "USGS metadata coverage mismatch")
    require(usgs_metadata.get("data_year_count") == 121, "USGS data-year count mismatch")
    require(usgs_metadata.get("normalized_rows") == 847, "USGS metadata row count mismatch")
    require(usgs_metadata.get("formula_cells") == [f"E{row}" for row in range(107, 113)], "USGS formula-cell inventory mismatch")
    require(usgs_metadata.get("package_modified_at") == "2024-06-04T18:22:38Z", "USGS package modification timestamp mismatch")
    require(
        usgs_metadata.get("embedded_notes_sha256") == "798f8935664ca1e91b9dc7ca860c9fd0e9ad2e923d5c3fe2a2c11d4dc38ce345",
        "USGS embedded-notes hash mismatch",
    )
    require(usgs_metadata.get("status_counts") == {"available": 695, "not_available": 150, "withheld": 2}, "USGS status inventory mismatch")
    require(usgs_metadata.get("source_last_modified") == "2023-09-27", "USGS source modification date mismatch")
    require(usgs_metadata.get("source_publication_date") == "2024-06-04", "USGS page publication date mismatch")
    require(usgs_metadata.get("retrieved_at") == "2026-07-10", "USGS retrieval date mismatch")
    require(usgs_metadata.get("public_domain") is True, "USGS public-domain designation missing")
    require(manifest.get("processed", {}).get("usgs_rare_earths_rows") == 847, "manifest USGS row count mismatch")

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

    with (PROCESSED / "usgs_rare_earths_historical.csv").open(encoding="utf-8", newline="") as handle:
        usgs_reader = csv.DictReader(handle)
        require((usgs_reader.fieldnames or []) == USGS_DS140_COLUMNS, "USGS normalized column contract changed")
        usgs_rows = list(usgs_reader)
    require(len(usgs_rows) == 847, "USGS normalized row count mismatch")
    require({int(row["year"]) for row in usgs_rows} == set(range(1900, 2021)), "USGS year coverage mismatch")
    require({row["geography_code"] for row in usgs_rows} == {"USA", "WLD"}, "USGS geography contract mismatch")
    require(
        {row["metric"] for row in usgs_rows}
        == {"production", "imports", "exports", "apparent_consumption", "unit_value_current_usd", "unit_value_constant_1998_usd"},
        "USGS metric inventory mismatch",
    )
    require(
        {(row["geography_code"], row["metric"]) for row in usgs_rows}
        == {
            ("USA", "production"), ("USA", "imports"), ("USA", "exports"),
            ("USA", "apparent_consumption"), ("USA", "unit_value_current_usd"),
            ("USA", "unit_value_constant_1998_usd"), ("WLD", "production"),
        },
        "USGS geography-metric combinations changed",
    )
    usgs_status_counts = {
        status: sum(row["value_status"] == status for row in usgs_rows)
        for status in ("available", "not_available", "withheld")
    }
    require(usgs_status_counts == {"available": 695, "not_available": 150, "withheld": 2}, "USGS CSV status counts mismatch")
    require(
        all(
            (
                row["value_status"] == "available"
                and row["value"] != ""
                and row["method_status"] not in {"not_available", "withheld_to_avoid_proprietary_disclosure"}
            )
            or (
                row["value_status"] == "not_available"
                and row["value"] == ""
                and row["source_value_raw"] == "NA"
                and row["method_status"] in {"not_available", "negative_calculation_published_as_not_available"}
            )
            or (row["value_status"] == "withheld" and row["value"] == "" and row["source_value_raw"] == "W" and row["method_status"] == "withheld_to_avoid_proprietary_disclosure")
            for row in usgs_rows
        ),
        "USGS value/status/method preservation mismatch",
    )
    require(len({row["source_cell"] for row in usgs_rows}) == 847, "USGS source-cell identifiers are not unique")
    formula_rows = [row for row in usgs_rows if row["source_formula"]]
    require(
        [(row["source_cell"], row["source_formula"]) for row in formula_rows]
        == [(f"E{row}", f"=(C{row}-D{row})") for row in range(107, 113)],
        "USGS source formulas were not preserved exactly",
    )
    require(
        all(row["method_status"] == "estimated_material_balance_using_estimated_reo" for row in formula_rows),
        "USGS formula method status mismatch",
    )
    require(
        all(
            row["source_id"] == "usgs-ds140-rare-earths-2020"
            and row["commodity"] == "rare_earths"
            and row["period_type"] == "annual"
            and row["source_file"] == "data/raw/usgs_ds140_rare_earths_2020.xlsx"
            and row["source_sheet"] == "Rare earths"
            and row["source_url"] == "https://www.usgs.gov/media/files/rare-earths-historical-statistics-data-series-140"
            and row["worksheet_last_modified"] == "2023-09-27"
            and row["package_modified_at"] == "2024-06-04T18:22:38Z"
            for row in usgs_rows
        ),
        "USGS row provenance changed",
    )
    require(
        all(as_float(row["value"]) is not None and (as_float(row["value"]) or 0) >= 0 for row in usgs_rows if row["value_status"] == "available"),
        "USGS available values must be finite and nonnegative",
    )

    expected_method_notes = {
        "Production": "embedded-notes:production",
        "Imports": "embedded-notes:imports",
        "Exports": "embedded-notes:exports",
        "Apparent consumption": "embedded-notes:apparent-consumption",
        "Unit value ($/t)": "embedded-notes:unit-value-current",
        "Unit value (98$/t)": "embedded-notes:unit-value-constant-1998",
        "World production": "embedded-notes:world-production",
    }
    require(
        all(row["method_note_id"] == expected_method_notes[row["metric_label"]] for row in usgs_rows),
        "USGS method-note mapping changed",
    )
    interpolated_years = {
        *range(1911, 1915), *range(1918, 1922), 1932,
        *range(1942, 1945), *range(1946, 1950),
    }
    for row in usgs_rows:
        if row["value_status"] != "available":
            continue
        year = int(row["year"])
        label = row["metric_label"]
        if label in {"Production", "World production"}:
            expected_method = "source_series_reo_content_method_not_cell_specific"
        elif label in {"Imports", "Exports"}:
            expected_method = "estimated_reo_equivalent"
        elif label == "Unit value ($/t)":
            expected_method = "estimated_weighted_average_imports_exports"
        elif label == "Unit value (98$/t)":
            expected_method = "calculated_cpi_adjustment_1998_base"
        elif year in interpolated_years:
            expected_method = "interpolated"
        elif year <= 1999:
            expected_method = "estimated_material_balance"
        elif year <= 2008:
            expected_method = "estimated_material_balance_using_estimated_reo"
        else:
            expected_method = "calculated_using_estimated_reo"
        require(row["method_status"] == expected_method, f"USGS method mismatch: {row['source_cell']}")

    missing_years = {
        (row["geography_code"], row["metric"]): {
            int(item["year"])
            for item in usgs_rows
            if item["geography_code"] == row["geography_code"]
            and item["metric"] == row["metric"]
            and item["value_status"] == "not_available"
        }
        for row in usgs_rows
    }
    require(
        missing_years[("USA", "production")]
        == {*range(1911, 1915), *range(1918, 1925), *range(1926, 1948), 1949},
        "USGS production missing-year set mismatch",
    )
    require(missing_years[("USA", "imports")] == {*range(1900, 1922), 1932, 1934, 1935, 1952}, "USGS import missing-year set mismatch")
    require(missing_years[("USA", "exports")] == {*range(1900, 1942), 1951, 1952, 1966}, "USGS export missing-year set mismatch")
    require(missing_years[("USA", "apparent_consumption")] == {2011}, "USGS apparent-consumption missing-year set mismatch")
    require(missing_years[("USA", "unit_value_current_usd")] == set(range(1900, 1922)), "USGS current-unit-value missing years mismatch")
    require(missing_years[("USA", "unit_value_constant_1998_usd")] == set(range(1900, 1922)), "USGS constant-unit-value missing years mismatch")
    require(missing_years[("WLD", "production")] == set(), "USGS world production must be complete")
    require(
        {
            int(row["year"])
            for row in usgs_rows
            if row["geography_code"] == "USA" and row["metric"] == "production" and row["value"] == "0"
        }
        == {*range(2001, 2012), 2016, 2017},
        "USGS explicit zero-production years mismatch",
    )

    usgs_lookup = {(int(row["year"]), row["geography_code"], row["metric"]): row for row in usgs_rows}
    for row in formula_rows:
        year = int(row["year"])
        imports = as_float(usgs_lookup[(year, "USA", "imports")]["value"])
        exports = as_float(usgs_lookup[(year, "USA", "exports")]["value"])
        observed = as_float(row["value"])
        require(
            imports is not None and exports is not None and observed == imports - exports,
            f"USGS cached formula value does not reconcile: {row['source_cell']}",
        )
    usgs_audit_points = {
        (1900, "USA", "production"): (227, "available", "B6"),
        (1956, "USA", "production"): (None, "withheld", "B62"),
        (1962, "USA", "production"): (None, "withheld", "B68"),
        (1993, "USA", "production"): (17800, "available", "B99"),
        (1993, "WLD", "production"): (46700, "available", "H99"),
        (2001, "USA", "production"): (0, "available", "B107"),
        (2001, "USA", "apparent_consumption"): (10100, "available", "E107"),
        (2011, "USA", "apparent_consumption"): (None, "not_available", "E117"),
        (2020, "USA", "production"): (39000, "available", "B126"),
        (2020, "USA", "imports"): (7200, "available", "C126"),
        (2020, "USA", "exports"): (39500, "available", "D126"),
        (2020, "USA", "apparent_consumption"): (6700, "available", "E126"),
        (2020, "WLD", "production"): (243000, "available", "H126"),
    }
    for key, (expected_value, expected_status, expected_cell) in usgs_audit_points.items():
        row = usgs_lookup.get(key)
        require(row is not None, f"missing USGS audit point: {key}")
        if row is None:
            continue
        observed_value = as_float(row["value"])
        require(observed_value == expected_value, f"USGS value mismatch: {key}")
        require(row["value_status"] == expected_status, f"USGS status mismatch: {key}")
        require(row["source_cell"] == expected_cell, f"USGS source-cell mismatch: {key}")

    require(all("usgs" not in row["source"].casefold() for row in rows), "USGS rows leaked into DataWeb trade_long.csv")

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
    require(summary.get("schema_version") == "3.2.0", "site summary schema mismatch")
    require(summary_path.stat().st_size <= 150_000, "site-summary.json exceeds 150 KB budget")
    require(summary["headline"]["year"] == 2025 and close(summary["headline"]["value"], 0.6040394784), "headline claim mismatch")
    prc = summary["prc_supply_origins"]
    require(prc["status"] == "loaded" and prc["coverage"] == [1993, 2024], "PRC site series not loaded or mislabeled")
    require(prc["yearly"][0]["positive_origin_count"] == 14, "PRC 1993 origin count mismatch")
    require(prc["yearly"][-1]["positive_origin_count"] == 33, "PRC 2024 origin count mismatch")
    require(close(prc["yearly"][-1]["hhi_value_0_1"], 0.4059395639), "PRC 2024 HHI mismatch")
    usgs_context = summary.get("usgs_rare_earths_context", {})
    require(usgs_context.get("status") == "loaded", "USGS site context is not loaded")
    require(usgs_context.get("full_coverage") == [1900, 2020], "USGS full coverage missing from site context")
    require(usgs_context.get("displayed_coverage") == [1993, 2020], "USGS displayed coverage mismatch")
    require(usgs_context.get("unit") == "metric_tons_reo_equivalent", "USGS site unit mismatch")
    usgs_site_rows = usgs_context.get("series", [])
    require(len(usgs_site_rows) == 28, "USGS site context must contain 28 annual rows")
    require([row["year"] for row in usgs_site_rows] == list(range(1993, 2021)), "USGS site-year sequence mismatch")
    usgs_1993 = next((row for row in usgs_site_rows if row["year"] == 1993), {})
    usgs_2011 = next((row for row in usgs_site_rows if row["year"] == 2011), {})
    usgs_2020 = next((row for row in usgs_site_rows if row["year"] == 2020), {})
    require(usgs_1993.get("us_production") == 17800 and close(usgs_1993.get("us_share_of_world_production", -1), 17800 / 46700), "USGS 1993 site context mismatch")
    require(usgs_2011.get("us_apparent_consumption") is None, "USGS 2011 unavailable apparent consumption became a value")
    require(
        usgs_2020.get("us_production") == 39000
        and usgs_2020.get("us_imports") == 7200
        and usgs_2020.get("us_exports") == 39500
        and usgs_2020.get("us_apparent_consumption") == 6700
        and usgs_2020.get("world_production") == 243000
        and close(usgs_2020.get("us_share_of_world_production", -1), 39000 / 243000),
        "USGS 2020 site context mismatch",
    )
    require(usgs_context.get("latest") == usgs_2020, "USGS latest site context mismatch")
    require(
        {row["flow"] for row in summary["sources"]}
        == {"imports_for_consumption", "domestic_exports", "china_reported_imports", "usgs_rare_earths_context"},
        "site provenance does not expose all four frozen inputs",
    )

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
        "USGS national balance",
        "not a partner-level HTS series",
        "The published series ends in 2020",
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
        f"847 USGS source-cell rows, 25 explorer shards, 32 PRC reporter years, exact audited headline 60.4%."
    )
    return 0


def fail(errors: list[str]) -> int:
    print("V3 validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
