from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"


def load_json(name: str):
    return json.loads((PROCESSED / name).read_text(encoding="utf-8"))


def csv_rows(name: str):
    with (PROCESSED / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_data.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_audited_rare_earth_headline() -> None:
    row = next(
        row for row in csv_rows("china_share_of_us_imports.csv")
        if row["mineral"] == "rare_earths" and row["year"] == "2025" and row["ytd_flag"] == "false"
    )
    assert float(row["china_value_usd"]) == 554_743_883
    assert float(row["selected_partner_value_usd"]) == 918_390_110
    assert abs(float(row["china_share"]) - 0.6040394784) < 1e-10
    assert row["denominator_scope"] == "selected_18_partners"


def test_annual_2026_is_an_explicit_gap() -> None:
    with (PROCESSED / "trade_long.csv").open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["year"] == "2026" and row["ytd_flag"] == "false"]
    assert rows
    assert all(row["value_usd"] == row["qty1"] == row["qty2"] == "" for row in rows)
    assert {row["data_status"] for row in rows} == {"not_available"}


def test_second_quantity_is_not_duplicated_across_value_buckets() -> None:
    with (PROCESSED / "trade_long.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    first = [row for row in rows if row["quantity_measure_slot"] == "first"]
    second = [row for row in rows if row["quantity_measure_slot"] == "second"]
    assert first and second
    assert all(not row["qty2"] for row in first)
    assert all(not row["value_usd"] and not row["qty1"] and row["qty2_unit"] for row in second)


def test_prc_reporter_snapshot_is_complete_and_reconciled() -> None:
    manifest = json.loads(
        (ROOT / "data" / "raw" / "un_comtrade_china" / "2846" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["validation"]["observed_years"] == list(range(1993, 2025))
    assert manifest["validation"]["gaps"] == []
    assert all(row["partner_world_absolute_difference_usd"] == 0 for row in manifest["files"])


def test_usgs_ds140_preserves_source_cells_statuses_and_formulas() -> None:
    rows = csv_rows("usgs_rare_earths_historical.csv")
    assert len(rows) == 847
    assert {
        status: sum(row["value_status"] == status for row in rows)
        for status in ("available", "not_available", "withheld")
    } == {"available": 695, "not_available": 150, "withheld": 2}
    assert [
        (row["source_cell"], row["source_formula"])
        for row in rows
        if row["source_formula"]
    ] == [(f"E{source_row}", f"=(C{source_row}-D{source_row})") for source_row in range(107, 113)]
    unavailable_2011 = next(
        row for row in rows
        if row["year"] == "2011" and row["geography_code"] == "USA" and row["metric"] == "apparent_consumption"
    )
    assert unavailable_2011["value"] == ""
    assert unavailable_2011["value_status"] == "not_available"
    assert unavailable_2011["source_value_raw"] == "NA"


def test_usgs_site_context_is_separate_from_partner_trade() -> None:
    summary = load_json("site-summary.json")
    context = summary["usgs_rare_earths_context"]
    assert context["displayed_coverage"] == [1993, 2020]
    assert len(context["series"]) == 28
    assert next(row for row in context["series"] if row["year"] == 2011)["us_apparent_consumption"] is None
    assert context["latest"]["us_production"] == 39_000
    assert abs(context["latest"]["us_share_of_world_production"] - (39_000 / 243_000)) < 1e-10
    assert all("usgs" not in row["source"].casefold() for row in csv_rows("trade_long.csv"))


def test_usgs_mcs_current_view_preserves_raw_revision_evidence() -> None:
    rows = csv_rows("usgs_mcs2026_observations.csv")
    assert len(rows) == 286
    assert {
        chapter: sum(row["mcs_chapter"] == chapter for row in rows)
        for chapter in {row["mcs_chapter"] for row in rows}
    } == {
        "RARE EARTHS": 164,
        "RARE EARTHS (Heavy)": 51,
        "SCANDIUM": 30,
        "YTTRIUM": 41,
    }
    revisions = [row for row in rows if row["revision_action"] != "none"]
    assert len(revisions) == 4
    brazil = next(row for row in revisions if row["country"] == "Brazil")
    world = next(row for row in revisions if row["country"] == "World total")
    china = next(row for row in revisions if row["country"] == "China")
    india = next(row for row in revisions if row["country"] == "India")
    assert (brazil["raw_value"], brazil["current_value"], brazil["value"]) == (
        "21,000,000", "11,000,000", "11000000",
    )
    assert (world["raw_value"], world["current_value"], world["value_low"]) == (
        ">85,000,000", ">75,000,000", "75000000",
    )
    assert "Production quota" in china["raw_notes"] and china["current_notes"] == "Estimated."
    assert india["availability_status"] == "not_available" and "256,000 tons" in india["current_notes"]
    assert [
        int(row["value"])
        for row in rows
        if row["mcs_chapter"] == "YTTRIUM" and row["statistics"] == "Export"
    ] == [9, 4, 20, 3, 12]


def test_usgs_myb_mcs_site_bridge_keeps_2023_missing() -> None:
    myb_rows = csv_rows("usgs_myb2022_world_mine_production.csv")
    assert len(myb_rows) == 65
    assert {int(row["year"]) for row in myb_rows} == set(range(2018, 2023))
    summary = load_json("site-summary.json")
    context = summary["usgs_mcs2026_context"]
    assert context["status"] == "loaded"
    assert context["coverage"] == [2018, 2025]
    assert context["observation_gap"] == [2023]
    missing = next(row for row in context["series"] if row["year"] == 2023)
    assert missing["china_production"] is missing["us_production"] is missing["world_production"] is None
    assert context["latest"]["china_production"] == 270_000
    assert context["latest"]["us_production"] == 51_000
    assert context["latest"]["world_production"] == 390_000
    assert context["latest"]["china_to_us_production_ratio"] == 5.29
    assert context["import_source_snapshot"]["rare_earth_compounds_metals_china_share"] == 71


def test_usgs_critical_mineral_reliance_preserves_scope_and_bounds() -> None:
    rows = csv_rows("usgs_mcs2026_critical_mineral_reliance.csv")
    assert len(rows) == 17
    by_mineral = {row["v3_mineral"]: row for row in rows}
    assert by_mineral["natural_graphite"]["display_value"] == "100%"
    assert by_mineral["rare_earths"]["display_value"] == "67%"
    assert by_mineral["nickel"]["display_value"] == "41%"
    assert "including scrap" in by_mineral["nickel"]["scope"].lower()
    assert by_mineral["aluminum"]["display_value"] == ">75%"
    assert by_mineral["aluminum"]["value_pct"] == ""
    assert by_mineral["aluminum"]["value_low_pct"] == "75"
    assert by_mineral["aluminum"]["comparator"] == "greater_than"
    assert by_mineral["tungsten"]["display_value"] == ">50%"
    assert all(row["is_estimated"] == "True" for row in rows)


def test_usgs_us_stage_baseline_keeps_processing_stages_separate() -> None:
    summary = load_json("site-summary.json")
    stage = summary["usgs_mcs2026_context"]["us_statistical_baseline"]
    assert stage["coverage"] == [2021, 2025]
    assert stage["latest"]["mineral_concentrate_production"] == 51_000
    assert stage["latest"]["compounds_metals_production"] == 8_900
    assert stage["latest"]["compound_imports"] == 21_000
    assert stage["latest"]["apparent_consumption_compounds_metals"] == 27_000
    assert stage["latest"]["compounds_metals_net_import_reliance"]["display"] == "67"
    assert stage["latest"]["mineral_concentrate_trade_status"]["indicator_code"] == "net_exporter"
    provenance = {row["measurement_id"]: row for row in stage["measurement_provenance"]}
    assert len(provenance) == 5
    concentrate = provenance["mineral_concentrate_production"]
    assert [row["source_row_number"] for row in concentrate["source_rows"]] == [5961, 5982, 6003, 6024, 6045]
    assert concentrate["estimated_years"] == [2021, 2022, 2023, 2024, 2025]
    assert "Excludes monazite concentrates" in concentrate["source_notes"][0]["text"]
    downstream_notes = provenance["compounds_metals_production"]["source_notes"][0]["text"]
    assert "California and Utah" in downstream_notes
    assert "two significant digits" in downstream_notes
    import_notes = provenance["compound_imports"]["source_notes"][0]["text"]
    assert "REO equivalent or content" in import_notes
    assert provenance["mine_mill_employment"]["estimated_years"] == [2025]
    reserves = {row["geography"]: row for row in stage["reserves_2025"]}
    assert reserves["United States"]["value"] == 1_900_000
    assert reserves["China"]["value"] == 44_000_000
    assert reserves["World total"]["value_low"] == 75_000_000
    official = summary["us_official_baseline"]
    assert len(official["indicators"]) == 17
    assert official["qualitative_indicators"][0]["indicator_code"] == "net_exporter"


def test_site_summary_stays_small_and_labels_prc_coverage() -> None:
    summary = load_json("site-summary.json")
    assert (PROCESSED / "site-summary.json").stat().st_size <= 150_000
    assert summary["prc_supply_origins"]["coverage"] == [1993, 2024]
    assert summary["prc_supply_origins"]["yearly"][0]["positive_origin_count"] == 14
    assert summary["prc_supply_origins"]["yearly"][-1]["positive_origin_count"] == 33
