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


def test_site_summary_stays_small_and_labels_prc_coverage() -> None:
    summary = load_json("site-summary.json")
    assert (PROCESSED / "site-summary.json").stat().st_size <= 150_000
    assert summary["prc_supply_origins"]["coverage"] == [1993, 2024]
    assert summary["prc_supply_origins"]["yearly"][0]["positive_origin_count"] == 14
    assert summary["prc_supply_origins"]["yearly"][-1]["positive_origin_count"] == 33
