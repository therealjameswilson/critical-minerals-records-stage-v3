# critical-minerals-records-stage-v3

A static, reproducible statistical record of U.S.–PRC critical-mineral trade signals from 1993 through 2026.

**Public site:** <https://therealjameswilson.github.io/critical-minerals-records-stage-v3/>

V3 changes the evidentiary model used by the 1861–1992 predecessor. It does not use FRUS as evidence. Its public claims resolve to frozen USITC DataWeb workbooks, frozen UN Comtrade API responses for the China-reporter sourcing view, and frozen USGS statistical releases for national rare-earth context: Data Series 140, the 2026 Mineral Commodity Summaries (MCS), and the 2022 Minerals Yearbook (MYB) advance tables.

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
    usgs_ds140_rare_earths_2020.xlsx
    usgs_mcs2026_commodities_data.csv
    usgs_mcs2026_metadata.xml
    usgs_mcs2026_rare_earths.pdf
    usgs_mcs2026_rare_earths_heavy.pdf
    usgs_mcs2026_scandium.pdf
    usgs_mcs2026_yttrium.pdf
    usgs_mcs2026_version_history.txt
    usgs_myb2022_rare_earths_tables.xlsx
    un_comtrade_china/2846/        1993–2024 frozen responses + manifest
  processed/
    trade_long.csv
    china_share_of_us_imports.csv
    supplier_diversification_index.csv
    unit_value.csv
    prc_supplier_origin_index.csv
    classification_breaks.csv
    usgs_rare_earths_historical.csv
    usgs_rare_earths_metadata.json
    usgs_rare_earths_data_dictionary.csv
    usgs_mcs2026_observations.csv
    usgs_mcs2026_revision_audit.csv
    usgs_mcs2026_critical_mineral_reliance.csv
    usgs_mcs2026_metadata.json
    usgs_myb2022_world_mine_production.csv
    usgs_publications_data_dictionary.csv
    query_manifest.json
    site-summary.json
    explorer/*.json
scripts/
  build_trade_data.py
  download_un_comtrade_china.py
  usgs_publications.py
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

## Frozen USGS statistical inputs

### Data Series 140

`data/raw/usgs_ds140_rare_earths_2020.xlsx` is the rare-earth workbook published with [USGS Data Series 140](https://www.usgs.gov/media/files/rare-earths-historical-statistics-data-series-140). It supplies national rare-earth-oxide-equivalent production, imports, exports, apparent consumption, unit values, and world production for 1900–2020. The public site displays the 1993–2020 portion alongside the trade record.

The ETL preserves source `NA` and `W` cells as `not_available` and `withheld`, respectively, and retains the workbook’s six formulas verbatim beside their cached numeric values. Method labels follow the embedded notes: estimated REO-equivalent trade, specified apparent-consumption calculation/interpolation periods, weighted-average unit values, and the CPI conversion. Production cells retain a source-series qualification because USGS does not label each one as reported or estimated. USGS identifies the source and usage as public domain.

This is a national historical context layer, not partner-level HTS trade. It never enters the DataWeb China-share, supplier-HHI, or HTS unit-value calculations.

### 2026 Mineral Commodity Summaries

The complete frozen MCS input inventory is `data/raw/usgs_mcs2026_commodities_data.csv`, `data/raw/usgs_mcs2026_metadata.xml`, `data/raw/usgs_mcs2026_rare_earths.pdf`, `data/raw/usgs_mcs2026_rare_earths_heavy.pdf`, `data/raw/usgs_mcs2026_scandium.pdf`, `data/raw/usgs_mcs2026_yttrium.pdf`, and `data/raw/usgs_mcs2026_version_history.txt`. The CSV uses Windows-1252 (`cp1252`) encoding. Filtering its exact chapter labels—`RARE EARTHS`, `RARE EARTHS (Heavy)`, `SCANDIUM`, and `YTTRIUM`—yields **286 source observations**.

`data/processed/usgs_mcs2026_observations.csv` retains every filtered source row and separates the raw ScienceBase value and note from the current-PDF view. The frozen version history identifies the current MCS release as version 1.3, reposted 2026-05-27. `data/processed/usgs_mcs2026_revision_audit.csv` makes the reconciliation explicit:

- Version 1.3 changes Brazil 2025 reserves from `21,000,000` metric tons in the frozen CSV to `11,000,000` in the current Rare Earths PDF.
- Version 1.3 changes the 2025 world-total reserve lower bound from `>85,000,000` to `>75,000,000` metric tons.
- Version 1.1 moves footnote 14 away from China 2024 production, so the frozen production-quota note is retained but marked superseded.
- Version 1.1 attaches footnote 14 to India 2025 reserves: a 2015 OSCOM report gave 256,000 tons of monazite reserves but did not report rare-earth reserves. The reserve value therefore remains unavailable.

The raw CSV is never silently rewritten. The PDF-current value or note, original value or note, revision action, and revision source remain auditable. MCS 2026 is the **publication vintage**; its tabular observations cover 2021–2025. It is not a 2026 observation series.

The site also publishes a stage-separated U.S. rare-earth baseline for 2021–2025 from those observations. Its 2025 snapshot reports 51,000 metric tons REO equivalent of mineral-concentrate production, 8,900 tons of compounds-and-metals production, 21,000 tons of compound imports, 27,000 tons of compounds-and-metals apparent consumption, 670 mine-and-mill workers, and 67% net import reliance for compounds and metals. Mineral concentrates carry the source indicator `E`, meaning **net exporter**; `E` is not an estimated percentage. Production at the concentrate stage must not be added to compounds-and-metals production. The reserve context preserves the current-PDF figures of 1.9 million metric tons REO equivalent for the United States, 44 million for China, and a world lower bound of more than 75 million. Reserves describe geologic availability under USGS definitions, not ownership or assured access.

[`data/processed/usgs_mcs2026_critical_mineral_reliance.csv`](data/processed/usgs_mcs2026_critical_mineral_reliance.csv) adds **17 explicitly selected, source-row-addressed 2025 indicators** for V3 mineral families. Its 20-column contract and complete allowlist are in [`docs/data-contract.md`](docs/data-contract.md). At each allowed row, the ETL asserts the exact MCS chapter, section, commodity, country, statistic, statistics detail, unit, year, expected value token, and 2025 critical-mineral flag; each validated row then receives one fixed V3 family and scope label. Every row is an MCS estimate and retains its chapter-specific material scope, original value token, notes, comparator, and mapping boundary. Net import reliance measures U.S. dependence on **all foreign sources** as a share of the relevant apparent-consumption denominator. It is never a China share, mine-origin measure, or partner-trade statistic. Bauxite `>75%` and tungsten `>50%` are strict lower bounds, not point estimates. Nickel’s 41% measure includes stainless-steel and alloy scrap; USGS states that reliance would be nearly 100% if scrap were excluded. Product scopes and denominators differ, and rare earths, heavy rare earths, scandium, and yttrium overlap, so the 17 values must not be summed or averaged. A cross-mineral production chart is deliberately deferred because MCS production units, processing stages, and content bases are not comparable.

Official sources: [USGS Rare Earths Statistics and Information](https://www.usgs.gov/centers/national-minerals-information-center/rare-earths-statistics-and-information), [MCS 2026 data release and metadata](https://doi.org/10.5066/P1WKQ63T), [Rare Earths PDF](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-rare-earths.pdf), [Heavy Rare Earths PDF](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-rare-earths-heavy.pdf), [Scandium PDF](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-scandium.pdf), [Yttrium PDF](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-yttrium.pdf), and [MCS version history](https://pubs.usgs.gov/periodicals/mcs2026/versionHist.txt).

### 2022 Minerals Yearbook advance tables

`data/raw/usgs_myb2022_rare_earths_tables.xlsx` is frozen from the [USGS Rare Earths 2022 tables-only release](https://www.usgs.gov/media/files/rare-earths-2022-tables-only-release). Only table T8, *World Mine Production of Rare Earths, by Country*, is normalized: **65 source-row/year observations** (12 countries plus the source total across 2018–2022). Tables T1–T7 remain available in the unchanged workbook but do not feed processed partner-trade series.

`data/processed/usgs_myb2022_world_mine_production.csv` and the MCS world-mine-production rows may be displayed as a contextual sequence for 2018–2022 and 2024–2025. The missing 2023 bridge is explicit; it is not interpolated. `data/processed/usgs_mcs2026_metadata.json` records the complete MCS/MYB frozen-input inventory, hashes, and row counts, while `data/processed/usgs_publications_data_dictionary.csv` defines all three publication-layer CSVs.

Mine production locates reported extraction, not ownership, processing control, or guaranteed access. MCS import-source shares identify direct or shipping sources and may differ from the mine origin of the material. No USGS context series is substituted for DataWeb country-of-origin trade or China-reporter Comtrade data, and no USGS publication row enters the DataWeb China-share, supplier-HHI, or HTS unit-value derivatives.

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

The separate USGS context tables are `data/processed/usgs_rare_earths_historical.csv`, `data/processed/usgs_mcs2026_observations.csv`, `data/processed/usgs_mcs2026_critical_mineral_reliance.csv`, and `data/processed/usgs_myb2022_world_mine_production.csv`. Their fields and source vintages are documented in the corresponding dictionaries and metadata files listed above.

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
- `usgs_rare_earths_historical.csv`: normalized national and world rare-earth-oxide-equivalent history, 1900–2020; kept analytically separate from partner-level derivations.
- `usgs_mcs2026_observations.csv`: 286 normalized MCS observations for Rare Earths, Heavy Rare Earths, Scandium, and Yttrium, with raw and current-PDF revision states kept side by side.
- `usgs_mcs2026_revision_audit.csv`: the explicit ScienceBase-CSV-to-current-PDF reconciliation log.
- `usgs_mcs2026_critical_mineral_reliance.csv`: 17 source-row-addressed, estimated 2025 U.S. net-import-reliance indicators with chapter-specific scopes and comparators preserved.
- `usgs_myb2022_world_mine_production.csv`: 65 normalized T8 source-row/year observations, 2018–2022.

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
- National statistical context: [USGS Rare Earths Statistics and Information](https://www.usgs.gov/centers/national-minerals-information-center/rare-earths-statistics-and-information), [Data Series 140](https://www.usgs.gov/media/files/rare-earths-historical-statistics-data-series-140), [MCS 2026 data release](https://doi.org/10.5066/P1WKQ63T), and [MYB 2022 tables-only release](https://www.usgs.gov/media/files/rare-earths-2022-tables-only-release). USGS identifies these U.S. Government materials as public domain.
- Site code and original documentation: MIT License; see `LICENSE`.
- Chart.js: MIT License; see `assets/vendor/chart.js/LICENSE.md`.
- U.S. Government and UN source data retain their source-specific terms. The repository’s MIT License does not relicense third-party data or trademarks.

## Citation

Use the repository release or commit hash together with the source retrieval vintage. Machine-readable project metadata are in `CITATION.cff`.
