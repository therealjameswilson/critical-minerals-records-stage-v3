# V3 statistical data contract

The canonical partner-level trade table is `data/processed/trade_long.csv`. It is source-bucket long rather than one-row-per-mineral total, because USITC quantity units are not freely additive. National USGS history is published under a separate contract and is never merged into partner-level calculations.

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
