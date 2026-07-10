from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(name: str):
    return json.loads((ROOT / "data" / "v3" / name).read_text(encoding="utf-8"))


def test_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_v3_data.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_years_are_hard_bounded() -> None:
    assert load("dataweb-series.json")["years"] == list(range(1993, 2027))


def test_trade_roles_are_not_recast_as_prc_total_access() -> None:
    rows = load("dataweb-series.json")["series"]
    imports = [row for row in rows if row["flow"] == "imports_for_consumption"]
    exports = [row for row in rows if row["flow"] == "domestic_exports"]
    assert imports and exports
    assert {row["reporting_economy_iso3"] for row in rows} == {"USA"}
    assert {row["partner_role"] for row in imports} == {"reported_origin"}
    assert {row["partner_role"] for row in exports} == {"reported_destination"}
    assert all("not PRC total access" in row["access_interpretation"] for row in exports)


def test_china_and_hong_kong_are_separate() -> None:
    partners = {row["id"]: row for row in load("dataweb-series.json")["partners"]}
    assert partners["chn"]["iso3"] == "CHN"
    assert partners["hkg"]["iso3"] == "HKG"


def test_nulls_suppression_and_zero_are_distinct() -> None:
    rows = load("dataweb-series.json")["series"]
    for row in rows:
        for period in ("annual_or_current_ytd", "comparable_jan_apr_ytd"):
            assert len(row[period]) == 34
            assert len(row["suppressed"][period]) == 34
            for value, suppressed in zip(row[period], row["suppressed"][period]):
                assert value is None or value >= 0
                assert isinstance(suppressed, bool)


def test_mixed_annual_and_ytd_is_not_marked_comparable() -> None:
    periods = load("dataweb-series.json")["periods"]
    assert periods["annual_or_current_ytd"]["comparable_across_all_years"] is False
    assert periods["comparable_jan_apr_ytd"]["comparable_across_all_years"] is True


def test_mixed_series_uses_ytd_for_2026() -> None:
    for row in load("dataweb-series.json")["series"]:
        assert row["annual_or_current_ytd"][-1] == row["comparable_jan_apr_ytd"][-1]
