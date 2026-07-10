# Historical U.S. Trade Data Model

The Historical Geostrategic Atlas exposes a cited U.S. trade record for every
selectable year from 1861 through 1992. Coverage does not imply that one
compatible series exists across the entire period. The interface keeps two
official series separate and names their different scopes.

## 1861-1899: Census Economic-Class Context

The selected year is matched to a published five-year average in the U.S.
Department of Commerce, Bureau of the Census, *Statistical Abstract of the
United States: 1948*:

- Table 1013, pages 908-909: value of U.S. merchandise exports and general
  imports by economic class.
- Table 1014, page 910: percentage distribution by economic class.

The normalized rows reproduce the published values and shares for "crude
materials." This is a broad class that includes mineral and non-mineral raw
materials. It is not mineral-specific, bilateral, or an annual observation.
The interface states the published period and never interpolates an annual
value.

## 1900-1992: USGS Commodity Trade

The ingestion script downloads official U.S. Geological Survey Data Series 140
workbooks and extracts numeric imports and exports cells through 1992. Each row
retains:

- mineral and year;
- import or export direction;
- original USGS-standardized unit;
- commodity-specific worksheet header;
- worksheet row and column;
- publication and download URLs;
- access date and extraction method; and
- an explicit statement that the value is a national aggregate.

The current workbooks support aluminum, bauxite, chromium, cobalt, copper,
manganese, rare earth elements, tin, and tungsten. Uranium remains in the
portal because reviewed FRUS records support its diplomatic history, but no
compatible annual U.S. imports-and-exports workbook is currently normalized.
The interface reports that gap instead of omitting uranium from the mineral
system or treating missing values as zero.

## Record Shape

Each object in `data/history-stack/trade.json` includes:

```json
{
  "year_start": 1942,
  "year_end": 1942,
  "temporal_precision": "annual",
  "direction": "imports",
  "metric": "U.S. imports",
  "material_scope": "commodity",
  "mineral_id": "tin",
  "partner_scope": "World aggregate; partner countries are not identified in this row.",
  "value": 27200,
  "unit": "metric tons (t) tin content",
  "agency": "U.S. Geological Survey",
  "table_or_page": "Tin worksheet, row 48, column 4 (Imports)",
  "source_url": "https://www.usgs.gov/media/files/tin-historical-statistics-data-series-140",
  "transcription_status": "machine-extracted-xlsx",
  "confidence": "high"
}
```

This example reproduces the committed 1942 U.S. tin-import row. The committed
JSON and official workbook control if the source series is refreshed.

## Data Rules

1. Do not combine the Census and USGS series into a continuous chart.
2. Do not infer partner countries, supplier shares, routes, or bilateral flows.
3. Do not convert physical units or current dollars without a separate,
   documented transformation record.
4. Do not treat missing, withheld, or nonnumeric cells as zero.
5. Do not use a period average as an exact-year observation.
6. Preserve publication, table or worksheet location, access date, original
   unit, and extraction status.

## Refresh and Validation

```bash
python scripts/ingest_trade_data.py --access-date YYYY-MM-DD
python scripts/validate_history_data.py
python -m pytest tests/ -q
```

Validation fails if a trade row falls outside 1861-1992, references an unknown
source or mineral, loses a required provenance field, or leaves a selectable
year without any official trade context.
