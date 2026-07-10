#!/usr/bin/env python3
"""Freeze China-reporter UN Comtrade annual imports of HS 2846.

The script uses UN Comtrade's official, unauthenticated public-preview API and
downloads one annual, one-product response at a time.  Omitting ``partnerCode``
requests the World total and every available primary partner.  Raw response
bytes are preserved so their SHA-256 digests identify the exact retrieved
vintage.

Validation is intentionally strict:

* HTTP 429 and 5xx responses are retried with exponential backoff.
* Calls are throttled to respect the public API's one-call-per-second limit.
* API errors, missing years, and responses at the 500-row preview ceiling fail.
* The sum of non-World partner ``primaryValue`` values must match the World
  record within ``max(1 USD, abs(World) * 1e-9)``.  Trade values are normally
  integer USD, so this tolerance only accommodates representation-level noise.

The output directory is replaced only after every year passes validation.
Existing output requires ``--force``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "data" / "raw" / "un_comtrade_china" / "2846"
DATA_ENDPOINT = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
METADATA_ENDPOINT = "https://comtradeapi.un.org/public/v1/getMetadata/C/A/HS"
REPORTER_CODE = 156
REPORTER_ISO3 = "CHN"
FLOW_CODE = "M"
COMMAND_CODE = "2846"
START_YEAR = 1993
END_YEAR = 2024
MAX_RECORDS = 500
ABSOLUTE_TOLERANCE_USD = Decimal("1")
RELATIVE_TOLERANCE = Decimal("0.000000001")
RETRYABLE_HTTP_CODES = {429, *range(500, 600)}
USER_AGENT = "critical-minerals-records-stage-v3/1.0 (+public-research-snapshot)"


class DownloadError(RuntimeError):
    """Raised when retrieval or validation cannot produce a complete snapshot."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def decimal_value(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise DownloadError(f"{label}: expected a numeric value, found {value!r}")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DownloadError(f"{label}: invalid numeric value {value!r}") from error
    if not parsed.is_finite() or parsed < 0:
        raise DownloadError(f"{label}: expected a finite nonnegative value, found {value!r}")
    return parsed


def json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def metadata_url() -> str:
    return f"{METADATA_ENDPOINT}?{urlencode([('reporterCode', REPORTER_CODE)])}"


def data_url(year: int) -> str:
    parameters = [
        ("period", year),
        ("reporterCode", REPORTER_CODE),
        ("cmdCode", COMMAND_CODE),
        ("flowCode", FLOW_CODE),
        ("partner2Code", 0),
        ("customsCode", "C00"),
        ("motCode", 0),
        ("maxRecords", MAX_RECORDS),
        ("breakdownMode", "classic"),
        ("includeDesc", "true"),
        ("format", "JSON"),
    ]
    return f"{DATA_ENDPOINT}?{urlencode(parameters)}"


@dataclass
class PublicApiClient:
    min_interval_seconds: float
    max_attempts: int
    base_backoff_seconds: float
    timeout_seconds: float
    last_request_started: float | None = None

    def _throttle(self) -> None:
        if self.last_request_started is None:
            return
        elapsed = time.monotonic() - self.last_request_started
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str, label: str) -> tuple[bytes, str]:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            self._throttle()
            self.last_request_started = time.monotonic()
            request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    status = response.getcode()
                    payload = response.read()
                if status != 200:
                    raise DownloadError(f"{label}: unexpected HTTP {status}")
                return payload, utc_now()
            except HTTPError as error:
                last_error = error
                if error.code not in RETRYABLE_HTTP_CODES:
                    body = error.read().decode("utf-8", errors="replace")[:500]
                    raise DownloadError(f"{label}: HTTP {error.code}: {body}") from error
                retry_after = error.headers.get("Retry-After")
                try:
                    retry_after_seconds = float(retry_after) if retry_after else 0.0
                except ValueError:
                    retry_after_seconds = 0.0
                wait_seconds = max(retry_after_seconds, self.base_backoff_seconds * (2**attempt))
                print(
                    f"{label}: HTTP {error.code}; retrying in {wait_seconds:g}s "
                    f"({attempt + 1}/{self.max_attempts})",
                    file=sys.stderr,
                )
                time.sleep(wait_seconds)
            except URLError as error:
                last_error = error
                wait_seconds = self.base_backoff_seconds * (2**attempt)
                print(
                    f"{label}: network error {error.reason!r}; retrying in {wait_seconds:g}s "
                    f"({attempt + 1}/{self.max_attempts})",
                    file=sys.stderr,
                )
                time.sleep(wait_seconds)
        raise DownloadError(f"{label}: failed after {self.max_attempts} attempts: {last_error}")


def parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DownloadError(f"{label}: response is not valid UTF-8 JSON") from error
    if not isinstance(parsed, dict):
        raise DownloadError(f"{label}: expected a JSON object")
    api_error = parsed.get("error")
    if api_error not in (None, ""):
        raise DownloadError(f"{label}: API error: {api_error}")
    return parsed


def latest_publication_note(notes: Any) -> dict[str, Any] | None:
    if not isinstance(notes, list):
        return None
    valid_notes = [note for note in notes if isinstance(note, dict)]
    if not valid_notes:
        return None
    return max(valid_notes, key=lambda note: str(note.get("publicationDate") or ""))


def publication_metadata_by_year(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise DownloadError("publication metadata: missing data array")
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            year = int(row.get("period"))
        except (TypeError, ValueError):
            continue
        notes = row.get("notes")
        latest = latest_publication_note(notes)
        result[year] = {
            "dataset_code": row.get("datasetCode"),
            "publication_history_count": len(notes) if isinstance(notes, list) else 0,
            "latest": (
                {
                    "publication_date": latest.get("publicationDate"),
                    "publication_date_short": latest.get("publicationDateShort"),
                    "publication_note": latest.get("publicationNote"),
                    "classification_code": latest.get("classificationCode"),
                    "trade_system": latest.get("tradeSystem"),
                    "currency": latest.get("currency"),
                    "import_valuation": latest.get("importValuation"),
                    "import_partner_country": latest.get("importPartnerCountry"),
                    "import_partner2_country": latest.get("importPartner2Country"),
                }
                if latest
                else None
            ),
        }
    return result


def validate_year_response(
    payload: dict[str, Any], year: int, publication_metadata: dict[str, Any] | None
) -> dict[str, Any]:
    label = str(year)
    count = payload.get("count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise DownloadError(f"{label}: missing integer response count")
    if count >= MAX_RECORDS:
        raise DownloadError(f"{label}: response count {count} reached the {MAX_RECORDS}-row preview ceiling")

    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise DownloadError(f"{label}: missing period data")
    if len(rows) != count:
        raise DownloadError(f"{label}: response count {count} does not match {len(rows)} data rows")

    partner_codes: set[int] = set()
    classification_codes: set[str] = set()
    world_rows: list[dict[str, Any]] = []
    partner_sum = Decimal("0")

    for index, row in enumerate(rows):
        owner = f"{label}/row/{index}"
        if not isinstance(row, dict):
            raise DownloadError(f"{owner}: expected an object")
        if str(row.get("period")) != label or row.get("refYear") != year:
            raise DownloadError(f"{owner}: response period does not match {year}")
        if row.get("reporterCode") != REPORTER_CODE or row.get("reporterISO") != REPORTER_ISO3:
            raise DownloadError(f"{owner}: unexpected reporter")
        if row.get("flowCode") != FLOW_CODE or str(row.get("cmdCode")) != COMMAND_CODE:
            raise DownloadError(f"{owner}: unexpected flow or commodity")
        if row.get("partner2Code") != 0 or row.get("customsCode") != "C00" or row.get("motCode") != 0:
            raise DownloadError(f"{owner}: response is not total partner-2/customs/mode-of-transport")
        if row.get("isOriginalClassification") is not True:
            raise DownloadError(f"{owner}: expected original HS classification")

        classification_code = row.get("classificationCode")
        if not isinstance(classification_code, str) or not classification_code:
            raise DownloadError(f"{owner}: missing classification code")
        classification_codes.add(classification_code)

        partner_code = row.get("partnerCode")
        if isinstance(partner_code, bool) or not isinstance(partner_code, int):
            raise DownloadError(f"{owner}: invalid partner code")
        if partner_code in partner_codes:
            raise DownloadError(f"{owner}: duplicate partner code {partner_code}")
        partner_codes.add(partner_code)

        primary_value = decimal_value(row.get("primaryValue"), f"{owner}/primaryValue")
        if partner_code == 0:
            world_rows.append(row)
        else:
            partner_sum += primary_value

    if len(classification_codes) != 1:
        raise DownloadError(f"{label}: expected one classification code, found {sorted(classification_codes)}")
    if len(world_rows) != 1:
        raise DownloadError(f"{label}: expected exactly one World row, found {len(world_rows)}")

    classification_code = next(iter(classification_codes))
    if publication_metadata:
        latest = publication_metadata.get("latest")
        metadata_classification = latest.get("classification_code") if isinstance(latest, dict) else None
        if metadata_classification and metadata_classification != classification_code:
            raise DownloadError(
                f"{label}: response classification {classification_code} disagrees with metadata "
                f"{metadata_classification}"
            )

    world_value = decimal_value(world_rows[0].get("primaryValue"), f"{label}/World/primaryValue")
    difference = abs(partner_sum - world_value)
    tolerance = max(ABSOLUTE_TOLERANCE_USD, abs(world_value) * RELATIVE_TOLERANCE)
    if difference > tolerance:
        raise DownloadError(
            f"{label}: partner sum {partner_sum} differs from World {world_value} by {difference}, "
            f"exceeding tolerance {tolerance}"
        )

    return {
        "count": count,
        "partner_count_excluding_world": count - 1,
        "classification_codes": [classification_code],
        "world_primary_value_usd": json_number(world_value),
        "partner_primary_value_sum_usd": json_number(partner_sum),
        "partner_world_absolute_difference_usd": json_number(difference),
        "partner_world_tolerance_usd": json_number(tolerance),
    }


def build_manifest(
    *,
    started_at: str,
    completed_at: str,
    output_dir: Path,
    metadata_entry: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_years = list(range(START_YEAR, END_YEAR + 1))
    observed_years = [record["year"] for record in records]
    gaps = sorted(set(expected_years) - set(observed_years))
    return {
        "schema_version": "1.0.0",
        "dataset": {
            "title": "China-reporter annual imports of HS 2846 by origin partner",
            "source": "UN Comtrade public preview API",
            "reporter_code": REPORTER_CODE,
            "reporter_iso3": REPORTER_ISO3,
            "flow_code": FLOW_CODE,
            "commodity_code": COMMAND_CODE,
            "frequency_code": "A",
            "classification_search_code": "HS",
            "partner_scope": "World and all available primary partners",
            "partner_basis": "Country or area of origin, as declared in annual publication metadata",
            "customs_code": "C00",
            "mode_of_transport_code": 0,
            "second_partner_code": 0,
        },
        "retrieval": {
            "started_at": started_at,
            "completed_at": completed_at,
            "script": "scripts/download_un_comtrade_china.py",
            "output_directory": str(output_dir.relative_to(ROOT)),
            "public_preview_max_records": MAX_RECORDS,
        },
        "validation": {
            "status": "passed" if not gaps else "failed",
            "expected_years": expected_years,
            "observed_years": observed_years,
            "gaps": gaps,
            "partner_sum_world_rule": (
                "abs(sum(non-World partner primaryValue) - World primaryValue) "
                "<= max(1 USD, abs(World primaryValue) * 1e-9)"
            ),
            "absolute_tolerance_usd": json_number(ABSOLUTE_TOLERANCE_USD),
            "relative_tolerance": json_number(RELATIVE_TOLERANCE),
            "preview_ceiling_is_failure": True,
        },
        "publication_metadata_snapshot": metadata_entry,
        "files": records,
        "summary": {
            "year_count": len(records),
            "first_year": min(observed_years) if observed_years else None,
            "last_year": max(observed_years) if observed_years else None,
            "classification_codes": sorted(
                {code for record in records for code in record["classification_codes"]}
            ),
            "raw_response_bytes": sum(record["bytes"] for record in records),
            "raw_response_bytes_including_metadata": (
                sum(record["bytes"] for record in records) + metadata_entry["bytes"]
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory")
    parser.add_argument("--min-interval", type=float, default=1.25, help="Minimum seconds between request starts")
    parser.add_argument("--max-attempts", type=int, default=8)
    parser.add_argument("--base-backoff", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.min_interval < 1.0:
        parser.error("--min-interval must be at least 1 second for the public API")
    if args.max_attempts < 1:
        parser.error("--max-attempts must be positive")
    if args.base_backoff <= 0 or args.timeout <= 0:
        parser.error("--base-backoff and --timeout must be positive")
    return args


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and not args.force:
        raise DownloadError(f"Output directory already exists: {output_dir}; use --force to replace it")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage_dir = Path(tempfile.mkdtemp(prefix=".2846-download-", dir=output_dir.parent))
    started_at = utc_now()
    client = PublicApiClient(
        min_interval_seconds=args.min_interval,
        max_attempts=args.max_attempts,
        base_backoff_seconds=args.base_backoff,
        timeout_seconds=args.timeout,
    )

    try:
        metadata_request_url = metadata_url()
        metadata_bytes, metadata_retrieved_at = client.fetch(metadata_request_url, "publication metadata")
        metadata_payload = parse_json(metadata_bytes, "publication metadata")
        metadata_rows = metadata_payload.get("data")
        metadata_count = len(metadata_rows) if isinstance(metadata_rows, list) else 0
        metadata_by_year = publication_metadata_by_year(metadata_payload)
        metadata_filename = "publication_metadata.json"
        (stage_dir / metadata_filename).write_bytes(metadata_bytes)
        metadata_entry = {
            "file": metadata_filename,
            "url": metadata_request_url,
            "retrieved_at": metadata_retrieved_at,
            "sha256": sha256_bytes(metadata_bytes),
            "bytes": len(metadata_bytes),
            "dataset_count": metadata_count,
            "covered_requested_years": sorted(
                year for year in metadata_by_year if START_YEAR <= year <= END_YEAR
            ),
            "missing_requested_years": [
                year for year in range(START_YEAR, END_YEAR + 1) if year not in metadata_by_year
            ],
        }

        records: list[dict[str, Any]] = []
        for year in range(START_YEAR, END_YEAR + 1):
            request_url = data_url(year)
            response_bytes, retrieved_at = client.fetch(request_url, str(year))
            response_payload = parse_json(response_bytes, str(year))
            publication_metadata = metadata_by_year.get(year)
            validation = validate_year_response(response_payload, year, publication_metadata)
            filename = f"{year}.json"
            (stage_dir / filename).write_bytes(response_bytes)
            record = {
                "year": year,
                "file": filename,
                "url": request_url,
                "retrieved_at": retrieved_at,
                "sha256": sha256_bytes(response_bytes),
                "bytes": len(response_bytes),
                **validation,
                "publication_metadata": publication_metadata,
            }
            records.append(record)
            print(
                f"{year}: {validation['count']} rows, "
                f"{validation['classification_codes'][0]}, {len(response_bytes)} bytes"
            )

        completed_at = utc_now()
        manifest = build_manifest(
            started_at=started_at,
            completed_at=completed_at,
            output_dir=output_dir,
            metadata_entry=metadata_entry,
            records=records,
        )
        if manifest["validation"]["gaps"]:
            raise DownloadError(f"Missing requested years: {manifest['validation']['gaps']}")
        (stage_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        if output_dir.exists():
            shutil.rmtree(output_dir)
        stage_dir.replace(output_dir)
        print(
            f"Saved {len(records)} annual responses plus publication metadata to "
            f"{output_dir.relative_to(ROOT)}"
        )
        return 0
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DownloadError as error:
        print(f"UN Comtrade download failed: {error}", file=sys.stderr)
        raise SystemExit(1)
