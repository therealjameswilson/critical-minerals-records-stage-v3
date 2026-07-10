# U.S. and PRC Access to Critical Minerals, 1993–2026

V3 is a public, statistics-only research demonstrator for comparing separately
defined indicators of U.S. and People's Republic of China access to rare-earth
elements, critical minerals, and strategic resources from 1993 through 2026.

**Live site:**
[therealjameswilson.github.io/critical-minerals-records-stage-v3/records-stage.html](https://therealjameswilson.github.io/critical-minerals-records-stage-v3/records-stage.html)

## What makes V3 different

The [V2 site](https://therealjameswilson.github.io/critical-minerals-records-stage-v2/records-stage.html)
is a FRUS-led history of U.S. strategic-resource access from 1861 through 1992.
V3 starts in 1993 and does not use FRUS or narrative records as evidence. Every
displayed value must come from a frozen U.S. Government statistical source,
retain its unit and period, and expose a source locator and caveat.

V3 does not produce a composite “access score.” Mine production, reserves,
processing, trade, import reliance, recycling, and stockpiles describe different
parts of access and remain separate indicator lanes.

## First public data release

The initial release ingests two official USITC DataWeb workbooks downloaded on
July 10, 2026:

- U.S. imports for consumption, reported country of origin, selected partners
  and 25 HTS4 categories, 1993–2026.
- U.S. domestic exports, reported destination, the same selected partners and
  categories, 1993–2026.

The workbooks include both a mixed series (full years through 2025 plus
January–April 2026) and a comparable January–April series for every year. The
site defaults to the comparable series.

These workbooks support a U.S. access lens and a U.S.-reported bilateral lens.
They do **not** measure total PRC imports, PRC access to third-country supply,
mine ownership, processing control, or end use. The PRC comparison lane remains
visibly unfilled until a compatible U.S. Government series is loaded.

## Rebuild and validate

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/ingest_dataweb_exports.py
python scripts/validate_v3_data.py
python -m pytest tests -q
python -m http.server 8000
```

Then open <http://localhost:8000/records-stage.html>.

## Repository map

- `records-stage.html` — public comparison workbench
- `methodology.html` — public evidence and comparison rules
- `assets/v3.css`, `assets/v3.js` — accessible responsive interface
- `data/source-files/` — frozen official source workbooks
- `data/v3/dataweb-series.json` — generated compact trade-value series
- `data/v3/dataset-registry.json` — source artifacts, hashes, gaps, and status
- `scripts/ingest_dataweb_exports.py` — reproducible XLSX normalizer
- `scripts/validate_v3_data.py` — provenance and semantic validator
- `docs/data-contract.md` — observation-first contract for future datasets
- `schemas/` — machine-readable build and observation contracts

## Trust rules

- No unpublished, model-generated, interpolated, or demo values.
- Missing, suppressed, blank, and reported zero states stay distinct.
- China and Hong Kong remain separate statistical/customs areas.
- U.S. imports use reported origin; U.S. exports use reported destination.
- Publication year never substitutes for observation year.
- Annual and year-to-date values are not overlaid unless month coverage matches.
- Product codes are trade categories, not claims about mine origin or ownership.
- Derived values must identify their inputs and formula.

This is an independent public research demonstrator, not an official U.S.
Department of State, USITC, Census Bureau, USGS, or U.S. Government product.
