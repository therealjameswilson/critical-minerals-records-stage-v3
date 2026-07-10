# Methodology

## Scope

V3 covers 1993–2026 and uses only official U.S. Government statistical
publications, workbooks, and query exports. It is not a continuation of the
FRUS evidentiary method used by V2.

## Current layer

The first release freezes two USITC DataWeb XLSX exports. DataWeb republishes
official U.S. merchandise-trade statistics originating with the Census Bureau.
The imported sheet reports imports for consumption on a customs-value basis;
the exported sheet reports domestic exports on an F.A.S.-value basis.

The source query selects 18 partners and 25 four-digit HTS categories. Those
partners are not the world total. Product categories are not the same as mined
materials, and several categories contain multiple materials or manufactured
goods.

## Time treatment

The source provides:

1. full annual values through 2025 plus January–April 2026; and
2. January–April year-to-date values for every year from 1993 through 2026.

The public explorer defaults to the second series because its month coverage is
consistent. When the mixed annual/current-YTD series is selected, 2026 is marked
partial and is not presented as directly comparable with prior full years.

## Aggregation

DataWeb's HTS4 value sheets sometimes split one partner/category across source
rows with different quantity descriptions. V3 sums the value rows within the
same flow, partner, HTS4 category, and period. It does not combine physical
quantities across unlike units.

## Interpretation

- Import partner means reported country of origin, not mine origin, ownership,
  route, processing location, or end use.
- Export partner means reported destination, not the partner's total imports.
- Domestic exports exclude foreign exports and are not interchangeable with
  total exports.
- China and Hong Kong remain separate source-reported partners.
- No loaded series currently uses the PRC as reporting economy.

## Verification

The raw files are committed unchanged and identified by SHA-256. Rebuilding the
browser data from those files must produce no Git diff. Validation checks year
bounds, roles, units, array lengths, hashes, query metadata, public caveats, and
the absence of FRUS-era data artifacts.
