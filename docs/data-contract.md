# V3 statistical data contract

Contract revision: **3.3.0**.

The canonical partner-level trade table is `data/processed/trade_long.csv`. It is source-bucket long rather than one-row-per-mineral total, because USITC quantity units are not freely additive. USGS historical and publication tables are published under separate contracts and are never merged into partner-level calculations.

## Required fields

The CSV begins with the requested contract, in this order:

| Field | Meaning |
|---|---|
| `reporter` | `US` for both DataWeb workbooks |
| `flow` | `imports_for_consumption` or `domestic_exports` |
| `partner` / `partner_iso` | Country of origin for imports; ultimate destination for exports |
| `hts` / `hts_desc` | Four-digit HTS heading and source description |
| `mineral` | Analytical proxy family |
| `processing_stage` | `ore`, `metal`, `compound`, `magnet`, or `alloy` |
| `year` | 1993–2026 |
| `ytd_flag` | `false` for full-year annual; `true` for January–April YTD |
| `value_usd` | Customs value or FAS value; blank on independent Q2 rows |
| `qty1` / `qty1_unit` | First quantity in its losslessly matched source bucket |
| `qty2` / `qty2_unit` | Independent second-quantity measure row |
| `source` / `retrieved_at` | DataWeb and the frozen retrieval vintage |

`data/processed/data_dictionary.csv` describes all appended provenance, quality, and break fields.

## Separate USGS historical context contract

`data/processed/usgs_rare_earths_historical.csv` normalizes the frozen `data/raw/usgs_ds140_rare_earths_2020.xlsx` workbook from [USGS Data Series 140](https://www.usgs.gov/media/files/rare-earths-historical-statistics-data-series-140). It contains national rare-earth-oxide-equivalent measures for 1900–2020; the site displays 1993–2020.

Each row identifies `year`, `geography`, `metric`, `value`, `unit`, `value_status`, `method_status`, exact source cell, any exact `source_formula`, frozen source file, source URLs, and source dates. `data/processed/usgs_rare_earths_data_dictionary.csv` defines every field, while `data/processed/usgs_rare_earths_metadata.json` records the digest, workbook notes, formula-cell inventory, status counts, and public-domain designation.

Source `NA` and `W` tokens become blank numeric values with `value_status=not_available` and `value_status=withheld`. The `method_status` field follows only methods stated in the embedded notes: estimated REO-equivalent imports and exports, year-specific calculated/estimated/interpolated apparent consumption, weighted-average current-dollar unit value, and the CPI-derived constant-dollar series. Production retains `source_series_reo_content_method_not_cell_specific`; the ETL does not invent a reported/estimated label for individual production cells. The analytical `geography_code` is `USA` or `WLD`; `WLD` is not represented as an ISO-3166 code.

The USGS table is national context, not partner-level HTS trade. It must not feed the DataWeb China-share, supplier-HHI, or HTS unit-value calculations.

## Separate USGS MCS 2026 publication contract

`data/processed/usgs_mcs2026_observations.csv` contains the **286** rows obtained by decoding `data/raw/usgs_mcs2026_commodities_data.csv` as Windows-1252 (`cp1252`) and selecting the exact chapter labels `RARE EARTHS`, `RARE EARTHS (Heavy)`, `SCANDIUM`, and `YTTRIUM`. Source fields retain `mcs_chapter`, `section`, `commodity`, `country`, `statistics`, `statistics_detail`, `unit`, `year`, `raw_year`, `raw_value`, `raw_notes`, the source critical-mineral flag, and other notes, plus row/file identifiers. Parsed fields keep `value`, `value_low`, `value_high`, `comparator`, `availability_status`, `indicator_code`, and `is_estimated` separate rather than forcing every source token into a number. Comparators are `exact`, `greater_than`, or `range`; availability is `available`, `explicit_zero`, `indicator`, or `not_available`. No midpoint is invented for a range. The source token `E` is an indicator meaning net exporter, not an estimated numeric value.

The same row distinguishes `raw_value` and `raw_notes` from `current_value` and `current_notes` in the current MCS PDFs. Original raw fields remain unchanged. Current-view fields may differ only when an entry in `data/processed/usgs_mcs2026_revision_audit.csv` identifies the row, original state, current state, `revision_action`, version, revision-history source, publication page, and note. The audited reconciliation covers:

- Brazil 2025 reserves, version 1.3: `21,000,000` to `11,000,000` metric tons;
- 2025 world-total reserve lower bound, version 1.3: `>85,000,000` to `>75,000,000` metric tons;
- China 2024 production, version 1.1: the raw quota note retained but marked superseded after footnote 14 moved;
- India 2025 reserves, version 1.1: value still unavailable, with footnote 14 recording 256,000 tons of monazite reserves in a 2015 OSCOM report but no rare-earth reserve figure.

`data/processed/usgs_mcs2026_metadata.json` records the frozen CSV, XML, four PDFs, version history, hashes, official URLs, filters, encoding, row counts, and revision policy. `data/processed/usgs_publications_data_dictionary.csv` defines fields in both USGS publication-layer CSVs.

MCS 2026 is a publication vintage; these source observations cover 2021–2025. The contract must not create a 2026 observation from the release year.

## Separate USGS MYB 2022 world-production contract

`data/processed/usgs_myb2022_world_mine_production.csv` contains **65** source-row/year observations from table T8 of the frozen `data/raw/usgs_myb2022_rare_earths_tables.xlsx` workbook: 12 countries plus the source total by 5 years, 2018–2022. Rows preserve the source row, value cell, marker cell, country label, normalized geography, metric, unit, `raw_value`, display value, parsed value, raw marker, footnote identifiers, and estimated/revised/status fields so reported, estimated, revised, zero, and unavailable states are not conflated. Tables T1–T7 remain in the unchanged source workbook but are not normalized into the partner-trade contract.

When MYB and MCS mine-production rows appear in a combined display, 2023 is an explicit gap. The ETL must not interpolate it. Mine production identifies the country of reported extraction, not ownership, refining location, control, or resource access. MCS import-source shares identify direct or shipping source and may not be mine origin.

Neither USGS publication table feeds `china_share_of_us_imports.csv`, `supplier_diversification_index.csv`, `unit_value.csv`, or any other DataWeb-derived measure.

## Quantity slots

Value and first quantity have an exact source join:

```text
(flow, period, partner, hts4, description, normalized first-unit bucket)
```

Second quantities have only:

```text
(flow, period, partner, hts4, description, normalized second unit)
```

At HTS4, the second row does not identify which first-unit/value bucket it belongs to. V3 therefore emits Q2 as `quantity_measure_slot=second` with `value_usd` and `qty1` blank. It never duplicates Q2 across first-unit rows.

Compatible first- and second-slot kilograms can be summed for a carefully labeled “reported mass coverage” chart. They are not represented as complete physical tonnage. Component-content units are not treated as product mass.

## Measurement states

- `reported`: positive source number
- `reported_zero`: literal source zero
- `source_blank`: empty source cell
- `not_available`: annual 2026 structural placeholder converted to a labeled gap

Numeric quantity suppression fields are preserved as `suppression_raw`. Any positive count sets `quantity_incomplete=true`. Suppressed quantity remains visible as a quality state but is excluded from unit-value calculations.

## Time basis

Annual and YTD observations are separate rows:

- annual: 1993–2025;
- January–April YTD: 1993–2026.

The source’s annual 2026 cells are zero placeholders, not full-year observations. V3 publishes them as `not_available` with blank numeric measures.

## Geographic scope

The workbooks contain 18 selected partners and no World row. U.S. share calculations use:

```text
China / sum(the 18 selected origins)
```

Every derived U.S. share carries `denominator_scope=selected_18_partners`. China and Hong Kong remain separate. U.S. domestic exports to China are never recast as China’s total imports or total resource access.

## Classification and product scope

HTS4 categories are traded-product proxies, not deposits or ownership. HTS 2805 and 8505 are broad; 2846 is the cleanest rare-earth-compounds heading used here.

General HS revision years—1996, 2002, 2007, 2012, 2017, and 2022—are flagged as continuity-review boundaries rather than assumed breaks. The observed 8505 shift from “no units collected” to kilogram-denominated buckets is marked at 2019 as a measurement-regime break.

## Derivations

- China share: China value divided by selected-partner value sum.
- Supplier count: selected non-China partners with value greater than zero.
- HHI: sum of squared value shares among those positive non-China suppliers.
- Unit value: value divided by a positive, strictly matched, unsuppressed first quantity, grouped by its retained unit basis.

Missing denominators return null. Unlike units are not combined. Derived outputs preserve period, scope, and status.
