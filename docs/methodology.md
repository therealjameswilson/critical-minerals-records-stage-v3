# Methodology

## Evidentiary scope

V3 covers 1993–2026 and is statistics-first. FRUS is not used as evidence. The U.S. partner-level view comes from two frozen USITC DataWeb workbooks; the China sourcing view comes from frozen China-reporter UN Comtrade responses. A frozen USGS Data Series 140 workbook supplies national rare-earth historical context.

## U.S. reporter layer

The DataWeb query selects 18 countries and 25 four-digit HTS headings. It contains no World total.

- Imports for consumption use customs value and country of origin.
- Domestic exports use FAS value and ultimate destination.
- “Country of origin” does not establish mine origin, ownership, processing location, or end use.
- Exports to China do not measure China’s total imports.

Full-year data end in 2025. The 2026 annual cells are structural zeros and become explicit unavailable values. January–April YTD observations form a separate comparable 1993–2026 series.

The value and first-quantity sheets align exactly by partner, heading, description, and quantity bucket. Second quantities lack a lossless HTS4 value-bucket join and remain independent measure rows. Positive DataWeb quantity-suppression counts exclude affected buckets from unit-value calculations.

## USGS historical context layer

The repository freezes `data/raw/usgs_ds140_rare_earths_2020.xlsx` from [USGS Data Series 140](https://www.usgs.gov/media/files/rare-earths-historical-statistics-data-series-140). It covers 1900–2020; the site displays 1993–2020. Quantities are metric tons of rare-earth-oxide equivalent unless the source identifies a unit-value measure.

The normalized layer retains U.S. production, imports, exports, apparent consumption, current and constant-1998-dollar unit values, and world production. Source `NA` and `W` cells remain explicit unavailable and withheld states. The workbook’s six formulas are retained exactly beside their cached values. Method labels follow the embedded notes at the series and year-range level; production cells remain generically qualified because the source does not label each as reported or estimated. USGS identifies the source and usage as public domain.

These national REO-equivalent estimates are context only. They do not identify partners or HTS products and never enter the DataWeb China-share, supplier-HHI, or HTS unit-value calculations.

## China reporter layer

The repository snapshots UN Comtrade public-preview responses for China-reporter annual imports of HS 2846 by all primary origin partners, 1993–2024. Each year is requested separately. The acquisition fails if a response reaches the 500-row ceiling, omits the requested year, reports an API error, or fails to reconcile partner values to World.

China has no annual 2025–2026 record in the frozen series. No interpolation is used.

The original HS edition changes over the run (H0 through H6), and China changes from the Special to General trade system in 2000. Both are interpretation boundaries. The public claim is descriptive: new origins became major reported sources. The trade statistics alone do not prove state cultivation, investment, or causal intent.

## Rare-earth proxies

- HTS 2846: rare-earth compounds, yttrium, and scandium; the cleanest four-digit proxy in this build.
- HTS 2805: a broad metals heading that also includes products outside the rare-earth scope.
- HTS 8505: magnets, electromagnets, holding devices, couplings, brakes, lifting heads, and parts; it does not isolate rare-earth permanent magnets.

The three-heading U.S. basket is useful as a broad dependency signal but should not be read as a chemically pure rare-earth series. China’s sourcing visual uses HS 2846 alone and is labeled accordingly.

## Reproducibility

Raw files are committed unchanged and identified by SHA-256. The ETL creates deterministic CSV and JSON outputs. Validation independently recomputes shares and HHI, verifies audited headline values, checks quantity-slot separation and suppression treatment, verifies Comtrade response hashes and World reconciliation, checks the USGS row contract and source isolation, and enforces browser-data size limits.

See `README.md`, `data/processed/query_manifest.json`, and `data/processed/data_dictionary.csv` for commands and field definitions.
