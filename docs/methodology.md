# Methodology

## Evidentiary scope

V3 covers 1993–2026 and is statistics-first. FRUS is not used as evidence. The U.S. partner-level view comes from two frozen USITC DataWeb workbooks; the China sourcing view comes from frozen China-reporter UN Comtrade responses. Frozen USGS Data Series 140, Mineral Commodity Summaries 2026, and Minerals Yearbook 2022 files supply national and mine-production context without entering the trade derivations.

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

## USGS current-publication context layer

The [USGS Rare Earths Statistics and Information hub](https://www.usgs.gov/centers/national-minerals-information-center/rare-earths-statistics-and-information) points to the current-publication releases frozen here:

- the [MCS 2026 data release](https://doi.org/10.5066/P1WKQ63T): `usgs_mcs2026_commodities_data.csv`, `usgs_mcs2026_metadata.xml`, `usgs_mcs2026_rare_earths.pdf`, `usgs_mcs2026_rare_earths_heavy.pdf`, `usgs_mcs2026_scandium.pdf`, `usgs_mcs2026_yttrium.pdf`, and the frozen [MCS version history](https://pubs.usgs.gov/periodicals/mcs2026/versionHist.txt) as `usgs_mcs2026_version_history.txt`;
- the [MYB 2022 rare-earths tables-only release](https://www.usgs.gov/media/files/rare-earths-2022-tables-only-release): `usgs_myb2022_rare_earths_tables.xlsx`, from which only table T8, *World Mine Production of Rare Earths, by Country*, is normalized.

The ScienceBase CSV is decoded as Windows-1252 (`cp1252`). Its exact four relevant chapter labels yield 286 observations covering 2021–2025. The release year 2026 is a publication vintage, not an observation year. The MYB T8 normalization yields 65 source-row/year observations—12 countries plus the source total across 2018–2022. A combined site view leaves 2023 missing rather than interpolating between MYB 2022 and MCS 2024.

The current MCS release is version 1.3, reposted 2026-05-27. Its Rare Earths PDF has revisions not carried into the frozen ScienceBase CSV. Version 1.3 changes Brazil 2025 reserves from 21 million to 11 million metric tons and the 2025 world reserve lower bound from more than 85 million to more than 75 million metric tons. Version 1.1 moved footnote 14 away from China 2024 production and attached it to India 2025 reserves, where it reports 256,000 tons of monazite reserves from a 2015 OSCOM report but no rare-earth reserve figure. The current view therefore marks the frozen China quota note as superseded and leaves India reserves unavailable with the current context attached. The original CSV fields remain intact beside the PDF-current fields, and every change appears in `usgs_mcs2026_revision_audit.csv`; no value is silently overwritten.

The site’s U.S. rare-earth baseline keeps the 2021–2025 MCS processing stages separate. The 2025 row reports 51,000 metric tons REO equivalent of mineral-concentrate production, 8,900 tons of compounds-and-metals production, 21,000 tons of compound imports, 27,000 tons of compounds-and-metals apparent consumption, 670 mine-and-mill workers, and 67% net import reliance for compounds and metals. Mineral concentrates are marked `E`, meaning net exporter, not an estimated percentage. The reserve context is likewise kept distinct: 1.9 million metric tons REO equivalent for the United States, 44 million for China, and a world lower bound of more than 75 million. Reserves indicate geologic availability under USGS definitions, not ownership or assured access.

The bounded cross-mineral layer, [`data/processed/usgs_mcs2026_critical_mineral_reliance.csv`](../data/processed/usgs_mcs2026_critical_mineral_reliance.csv), uses a 17-row allowlist. At each source-row address the ETL asserts chapter, section, commodity, country, statistic, statistics detail, percent unit, 2025 year, expected value token, and critical-mineral flag before applying one fixed V3 family and material-scope mapping. Its explicit 20-column contract and complete mapping table are in [`docs/data-contract.md`](data-contract.md). All 17 rows are estimates. Net import reliance is U.S. dependence on all foreign sources relative to the chapter’s applicable apparent-consumption denominator; it is not a China share or mine-origin measure. Bauxite’s `>75%` and tungsten’s `>50%` leave the point-value field blank and preserve `75` or `50` only as a lower bound. Nickel’s 41% measure includes stainless-steel and alloy scrap; USGS states that excluding scrap would make reliance nearly 100%. The indicators are not summed or averaged because scopes and denominators differ and some rare-earth families overlap. Cross-mineral production is deferred because MCS production units, stages, and content bases are incompatible.

These tables answer different questions. MYB and MCS mine production locate reported extraction, not ownership, processing control, policy intent, or guaranteed access. MCS import-source shares identify direct or shipping sources and can differ from mine origin. DataWeb and Comtrade remain the reporter-specific evidence for trade access. USGS publication rows never enter the DataWeb China-share, supplier-HHI, or HTS unit-value calculations.

USGS identifies the MCS data release and MYB tables as public-domain U.S. Government works. The repository preserves their source attribution and revision vintage; its MIT License applies to original site code and documentation, not as a relicense of source data.

## China reporter layer

The repository snapshots UN Comtrade public-preview responses for China-reporter annual imports of HS 2846 by all primary origin partners, 1993–2024. Each year is requested separately. The acquisition fails if a response reaches the 500-row ceiling, omits the requested year, reports an API error, or fails to reconcile partner values to World.

China has no annual 2025–2026 record in the frozen series. No interpolation is used.

The original HS edition changes over the run (H0 through H6), and China changes from the Special to General trade system in 2000. Each change is an interpretation boundary. The public claim is descriptive: new origins became major reported sources. The trade statistics alone do not prove state cultivation, investment, or causal intent.

## Rare-earth proxies

- HTS 2846: rare-earth compounds, yttrium, and scandium; the cleanest four-digit proxy in this build.
- HTS 2805: a broad metals heading that also includes products outside the rare-earth scope.
- HTS 8505: magnets, electromagnets, holding devices, couplings, brakes, lifting heads, and parts; it does not isolate rare-earth permanent magnets.

The three-heading U.S. basket is useful as a broad dependency signal but should not be read as a chemically pure rare-earth series. China’s sourcing visual uses HS 2846 alone and is labeled accordingly.

## Reproducibility

Raw files are committed unchanged and identified by SHA-256. The ETL creates deterministic CSV and JSON outputs. Validation independently recomputes shares and HHI, verifies audited headline values, checks quantity-slot separation and suppression treatment, verifies Comtrade response hashes and World reconciliation, checks the USGS row contracts (including 286 MCS rows, 17 critical-mineral-reliance rows, 65 MYB T8 rows, the revision audit, and the explicit 2023 gap), enforces USGS/DataWeb isolation, and keeps browser payloads within their size limits.

See `README.md`, `data/processed/query_manifest.json`, and `data/processed/data_dictionary.csv` for commands and field definitions.
