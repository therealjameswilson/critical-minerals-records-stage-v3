# critical-minerals-records-stage-v3

A static, reproducible statistical record of U.S.–PRC critical-mineral trade signals from 1993 through 2026.

**Public site:** <https://therealjameswilson.github.io/critical-minerals-records-stage-v3/>

V3 changes the evidentiary model used by the 1861–1992 predecessor. It does not use FRUS as evidence. Its public claims resolve to frozen USITC DataWeb workbooks and, for the China-reporter sourcing view, frozen UN Comtrade API responses.

## What the site argues—and what it does not

The site centers two descriptive findings:

1. In 2025, China supplied **60.4%** of the value of U.S. rare-earth-proxy imports among the **18 origins selected in the DataWeb query** (HTS 2805, 2846, and 8505).
2. China-reporter imports of HS 2846 changed from 14 positive reported origins in 1993 to 33 in 2024, with Myanmar, Laos, Malaysia, and Viet Nam becoming leading origins.

The first denominator is not World. The supplied DataWeb workbooks contain 18 individually selected partners, so this repository never labels that calculation as China’s share of all U.S. imports. The second finding establishes changing trade origins, not state intent or proof that the PRC “cultivated” those sources.

Trade data are access signals. They do not directly measure reserves, mine ownership, beneficial ownership, processing capacity, or control of third-country assets.

## Repository layout

```text
index.html
records-stage.html                 compatibility redirect
methodology.html
assets/
  v3.css
  v3.js
  vendor/chart.js/
data/
  raw/
    us_imports_for_consumption_1993-2026.xlsx
    us_domestic_exports_1993-2026.xlsx
    un_comtrade_china/2846/        1993–2024 frozen responses + manifest
  processed/
    trade_long.csv
    china_share_of_us_imports.csv
    supplier_diversification_index.csv
    unit_value.csv
    prc_supplier_origin_index.csv
    classification_breaks.csv
    query_manifest.json
    site-summary.json
    explorer/*.json
scripts/
  build_trade_data.py
  download_un_comtrade_china.py
  validate_data.py
tests/
```

## Frozen USITC DataWeb inputs

Place these exact files in `data/raw/`:

- `us_imports_for_consumption_1993-2026.xlsx`
- `us_domestic_exports_1993-2026.xlsx`

The included files were retrieved from [USITC DataWeb](https://dataweb.usitc.gov/) on **2026-07-10**.

| Parameter | Value |
|---|---|
| Classification | HTS Items |
| Aggregation | HTS4; break out commodities |
| Periods | Full years plus January–April YTD, 1993–2026 |
| Measures | Customs Value or FAS Value; First Unit of Quantity; Second Unit of Quantity |
| Partners | Australia, Brazil, Canada, Chile, China, Democratic Republic of the Congo, Estonia, France, Germany, Hong Kong, India, Japan, Malaysia, Myanmar (Burma), Russia, South Africa, South Korea, Vietnam |
| Partner aggregation | Break out countries |
| HTS headings | 2504, 2601, 2602, 2603, 2605, 2606, 2609, 2610, 2611, 2612, 2805, 2825, 2836, 2846, 7202, 7502, 7901, 8001, 8101, 8103, 8105, 8106, 8110, 8112, 8505 |
| Import programs / provision codes / districts | All, aggregated |

The exact exported query-parameter rows, source-row counts, byte sizes, and SHA-256 digests are copied into `data/processed/query_manifest.json` at build time.

## Reproduce the processed data

Python 3.11 or later is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/build_trade_data.py
python scripts/validate_data.py
python -m pytest -q
```

The build is deterministic for the frozen raw inputs. CI rebuilds `data/processed/` and fails if the tracked output changes.

To refresh the optional China-reporter series from the official UN Comtrade public API:

```bash
python scripts/download_un_comtrade_china.py --force
python scripts/build_trade_data.py
python scripts/validate_data.py
```

The downloader makes one annual, one-product request at a time for China-reporter imports of HS 2846, 1993–2024. It throttles requests, retries 429/5xx responses, snapshots raw bytes, records every request URL and SHA-256 digest, fails at the 500-row preview ceiling, and reconciles the sum of partner values to World. China has no comparable annual record for 2025–2026 in this frozen series.

## Normalized data contract

`data/processed/trade_long.csv` begins with the requested fields:

```text
reporter, flow, partner, partner_iso, hts, hts_desc, mineral,
processing_stage, year, ytd_flag, value_usd, qty1, qty1_unit,
qty2, qty2_unit, source, retrieved_at
```

It then adds source-row, period, suppression, measurement-quality, classification-break, and denominator fields. See `data/processed/data_dictionary.csv` and `docs/data-contract.md`.

Two quantity rules are essential:

- Value and first quantity join losslessly by flow, period, country, HTS4, source description, and normalized source quantity bucket.
- A second quantity at HTS4 does **not** identify its matching first-unit/value bucket. It is therefore emitted as an independent `quantity_measure_slot=second` row, with `value_usd` blank. It is never copied onto every first-unit row.

Numeric `_Suppressed` fields in DataWeb quantity sheets are preserved in `suppression_raw`. A positive count sets `quantity_incomplete=true` and excludes that bucket from unit-value calculations.

Annual 2026 source cells are structural zeros while the YTD sheets contain January–April observations. The ETL converts annual 2026 to explicit unavailable values and keeps the comparable YTD series separate.

## Derived tables

- `china_share_of_us_imports.csv`: China divided by the selected-partner value sum, by mineral family, year, and period.
- `supplier_diversification_index.csv`: positive non-China supplier count and value HHI within the selected origin set.
- `unit_value.csv`: value divided by a strictly matched, positive, unsuppressed first quantity, with quantity unit and value-coverage share retained.
- `prc_supplier_origin_index.csv`: annual China-reporter HS 2846 World value, positive-origin count, value HHI, and leading origin.
- `classification_breaks.csv`: general HS revision checkpoints plus the observed HTS 8505 measurement-regime break in 2019.

HTS 2805 and 8505 are broad proxy headings. HTS 2805 includes products beyond rare-earth metals; HTS 8505 includes non-rare-earth and non-permanent-magnet products. HTS 2846 is the cleanest four-digit rare-earth-compounds heading in this build.

## Static site

No application server or build framework is required. Serve the repository root locally:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/>. Chart.js 4.5.1 is vendored under `assets/vendor/chart.js/`; the site has no runtime CDN dependency. `site-summary.json` loads first, and the explorer fetches one HTS shard on demand.

## Source and licensing notes

- Source workbooks: [USITC DataWeb](https://dataweb.usitc.gov/). See the [DataWeb quantity FAQ](https://www.usitc.gov/applications/dataweb/faqs), [partner definitions](https://www.usitc.gov/faq/question/what_meant_country_merchandise_trade_statistics.htm), and [HTS archive](https://www.usitc.gov/harmonized_tariff_information/hts/archive/list).
- China-reporter source: [UN Comtrade API](https://uncomtrade.org/docs/un-comtrade-api/). Raw response snapshots retain the source’s metadata and revision vintage.
- Site code and original documentation: MIT License; see `LICENSE`.
- Chart.js: MIT License; see `assets/vendor/chart.js/LICENSE.md`.
- U.S. Government and UN source data retain their source-specific terms. The repository’s MIT License does not relicense third-party data or trademarks.

## Citation

Use the repository release or commit hash together with the source retrieval vintage. Machine-readable project metadata are in `CITATION.cff`.
