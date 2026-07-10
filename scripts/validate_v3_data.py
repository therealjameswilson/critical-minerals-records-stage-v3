#!/usr/bin/env python3
"""Validate the V3 statistical build, source artifacts, and public claims."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "v3" / "dataweb-series.json"
REGISTRY_PATH = ROOT / "data" / "v3" / "dataset-registry.json"
YEARS = list(range(1993, 2027))
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_measure_array(values: Any, label: str, errors: list[str]) -> None:
    require(isinstance(values, list) and len(values) == len(YEARS), f"{label}: expected {len(YEARS)} values", errors)
    if not isinstance(values, list):
        return
    for index, value in enumerate(values):
        if value is None:
            continue
        require(
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0,
            f"{label}[{index}] must be a finite nonnegative number or null",
            errors,
        )


def main() -> int:
    errors: list[str] = []
    for path in (DATA_PATH, REGISTRY_PATH):
        require(path.exists(), f"Missing required build artifact: {path.relative_to(ROOT)}", errors)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    data = load(DATA_PATH)
    registry = load(REGISTRY_PATH)

    require(data.get("schema_version") == "3.0.0", "data: unsupported schema_version", errors)
    require(data.get("years") == YEARS, "data: years must exactly cover 1993-2026", errors)
    coverage = data.get("coverage", {})
    require(coverage.get("start_year") == 1993 and coverage.get("end_year") == 2026, "data: invalid coverage boundary", errors)
    require(coverage.get("reporting_economy_iso3") == "USA", "data: initial DataWeb reporter must be USA", errors)
    require(coverage.get("current_ytd_months") == "January-April", "data: 2026 YTD month window must be explicit", errors)

    periods = data.get("periods", {})
    require(periods.get("annual_or_current_ytd", {}).get("comparable_across_all_years") is False, "data: mixed annual/current YTD period must be non-comparable", errors)
    require(periods.get("comparable_jan_apr_ytd", {}).get("comparable_across_all_years") is True, "data: Jan-Apr series must be marked comparable", errors)

    partners = data.get("partners", [])
    partner_ids = [row.get("id") for row in partners]
    require(len(partner_ids) == len(set(partner_ids)), "partners: duplicate ids", errors)
    require({"chn", "hkg"} <= set(partner_ids), "partners: China and Hong Kong must remain separate", errors)
    require(next((row.get("iso3") for row in partners if row.get("id") == "chn"), None) == "CHN", "partners: China ISO3 mismatch", errors)
    require(next((row.get("iso3") for row in partners if row.get("id") == "hkg"), None) == "HKG", "partners: Hong Kong ISO3 mismatch", errors)

    materials = data.get("materials", [])
    material_ids = [row.get("hts4") for row in materials]
    require(len(material_ids) == len(set(material_ids)), "materials: duplicate HTS4 codes", errors)
    require(all(isinstance(code, str) and re.fullmatch(r"\d{4}", code) for code in material_ids), "materials: every HTS4 must be four digits", errors)

    series = data.get("series", [])
    ids = [row.get("id") for row in series]
    require(len(ids) == len(set(ids)), "series: duplicate ids", errors)
    require({row.get("flow") for row in series} == {"imports_for_consumption", "domestic_exports"}, "series: both exact DataWeb flows are required", errors)
    required_fields = {
        "id", "flow", "value_basis", "focal_country_id", "focal_country_role",
        "reporting_economy_id", "reporting_economy_iso3", "partner_country_id",
        "partner_iso3", "partner_name", "partner_role", "hts4",
        "commodity_description", "access_interpretation", "annual_or_current_ytd",
        "comparable_jan_apr_ytd", "suppressed", "source_id",
    }
    for row in series:
        owner = f"series/{row.get('id')}"
        missing = sorted(required_fields - set(row))
        require(not missing, f"{owner}: missing fields {missing}", errors)
        require(row.get("focal_country_id") == "usa", f"{owner}: DataWeb focal country must be USA", errors)
        require(row.get("reporting_economy_id") == "usa", f"{owner}: DataWeb reporting economy must be USA", errors)
        require(row.get("partner_country_id") in partner_ids, f"{owner}: unknown partner", errors)
        require(row.get("hts4") in material_ids, f"{owner}: unknown HTS4", errors)
        if row.get("flow") == "imports_for_consumption":
            require(row.get("partner_role") == "reported_origin", f"{owner}: imports require reported_origin", errors)
            require(row.get("value_basis") == "customs_value_usd", f"{owner}: imports require customs value", errors)
        elif row.get("flow") == "domestic_exports":
            require(row.get("partner_role") == "reported_destination", f"{owner}: exports require reported_destination", errors)
            require(row.get("value_basis") == "fas_value_usd", f"{owner}: exports require FAS value", errors)
            require("not PRC total access" in row.get("access_interpretation", ""), f"{owner}: outbound interpretation must block PRC-total claim", errors)
        validate_measure_array(row.get("annual_or_current_ytd"), f"{owner}/annual_or_current_ytd", errors)
        validate_measure_array(row.get("comparable_jan_apr_ytd"), f"{owner}/comparable_jan_apr_ytd", errors)
        if isinstance(row.get("annual_or_current_ytd"), list) and isinstance(row.get("comparable_jan_apr_ytd"), list):
            require(
                row["annual_or_current_ytd"][-1] == row["comparable_jan_apr_ytd"][-1],
                f"{owner}: mixed series must use the actual January-April YTD value for 2026",
                errors,
            )
        suppression = row.get("suppressed", {})
        for key in ("annual_or_current_ytd", "comparable_jan_apr_ytd"):
            flags = suppression.get(key)
            require(isinstance(flags, list) and len(flags) == len(YEARS) and all(isinstance(flag, bool) for flag in flags), f"{owner}: malformed {key} suppression flags", errors)

    require(coverage.get("selected_partner_count") == len(partners), "coverage: selected_partner_count mismatch", errors)
    require(coverage.get("commodity_count") == len(materials), "coverage: commodity_count mismatch", errors)
    require(coverage.get("series_count") == len(series), "coverage: series_count mismatch", errors)

    sources = registry.get("sources", [])
    source_ids = {row.get("source_id") for row in sources}
    require(len(sources) == 2 and len(source_ids) == 2, "registry: expected two distinct source artifacts", errors)
    for source in sources:
        owner = f"source/{source.get('source_id')}"
        local_file = ROOT / str(source.get("local_file", ""))
        digest = source.get("sha256", "")
        require(local_file.is_file(), f"{owner}: source artifact missing", errors)
        require(bool(HEX_64.fullmatch(str(digest))), f"{owner}: malformed sha256", errors)
        if local_file.is_file() and HEX_64.fullmatch(str(digest)):
            require(file_sha256(local_file) == digest, f"{owner}: source artifact hash mismatch", errors)
        require(source.get("download_date") == "2026-07-10", f"{owner}: unexpected download date", errors)
        require(source.get("source_url") == "https://dataweb.usitc.gov/", f"{owner}: unexpected source URL", errors)
        expected = sum(row.get("source_id") == source.get("source_id") for row in series)
        require(source.get("normalized_series_count") == expected, f"{owner}: normalized count mismatch", errors)

    for row in series:
        require(row.get("source_id") in source_ids, f"series/{row.get('id')}: unknown source_id", errors)

    status = registry.get("comparison_status", {})
    require(status.get("us_access") == "live_partial", "registry: U.S. status must be live_partial", errors)
    require(status.get("prc_access") == "awaiting_prc_reporter_or_comparable_usg_series", "registry: PRC status must remain explicitly unfilled", errors)
    require(status.get("bilateral_us_prc") == "live_us_reporter_only", "registry: bilateral status must be U.S.-reporter-only", errors)

    public_html = (ROOT / "records-stage.html").read_text(encoding="utf-8")
    required_public_phrases = [
        "Official U.S. Government statistics only",
        "No FRUS-derived narrative evidence is used",
        "does not measure total PRC access",
        "January–April",
    ]
    for phrase in required_public_phrases:
        require(phrase in public_html, f"records-stage.html: missing trust phrase {phrase!r}", errors)

    forbidden_files = [ROOT / "assets" / "frus-subjects-index.js", ROOT / "data" / "history-stack"]
    for path in forbidden_files:
        require(not path.exists(), f"FRUS-era artifact must not ship in V3: {path.relative_to(ROOT)}", errors)

    if errors:
        print("V3 validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"V3 validation passed: {len(series)} series, {len(materials)} HTS4 categories, "
        f"{len(partners)} source-reported partners, {len(sources)} frozen source workbooks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
