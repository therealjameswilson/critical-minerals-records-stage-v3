# V3 statistical data contract

V3 is observation-first. “Access” is a dashboard of separately sourced
indicators, not a single score and not a synonym for production location.

The compact `dataweb-series.json` file is a public build artifact optimized for
the browser. Future ingesters should first produce normalized observation rows
using the contract below, then generate browser series only after comparability
checks pass.

## Geography roles

Every observation names geography by role rather than using an ambiguous
`country_id`:

- `focal_geography_id` and `focal_role`
- `reporting_area_id`
- `partner_geography_id` and `partner_role`
- `mine_origin_geography_id`
- `processing_geography_id`
- `asset_location_geography_id`
- `owner_controller_geography_id`

Fields unsupported by the source remain null. A production-location statistic
does not establish ownership. A country-of-origin trade statistic does not
establish mine origin. A destination statistic does not establish total imports.

USITC DataWeb mappings used in the first release:

- U.S. imports from China: focal `usa` as importer; reporting area `usa`;
  partner `chn` as country of origin. Mine origin, processing location, and
  ownership are null.
- U.S. exports to China: focal `usa` as reporting exporter; partner `chn` as
  reported destination. The result is never labeled “PRC total imports.”
- China, Hong Kong, Macao, and Taiwan are never silently combined.

## Measurement states

Allowed measurement states are:

- `reported`
- `reported-zero`
- `less-than`
- `greater-than`
- `range`
- `suppressed`
- `not-available`
- `not-published`
- `not-applicable`
- `source-blank`

Suppressed or missing values have no numeric value. A literal zero in the
source is `reported-zero`, not missing. Bounds preserve the reported inequality.
Physical quantities require a `quantity_basis`; currency observations require
the currency, price basis, and valuation basis.

## Comparability

No arithmetic or chart overlay is allowed unless observations belong to a
declared comparison group. Members must agree on:

- metric and material scope;
- material form and supply-chain stage;
- period and frequency;
- quantity basis or valuation basis;
- normalized unit;
- geographic role;
- classification system or reviewed crosswalk.

Examples of prohibited comparisons include China mine production versus U.S.
import value, gross-weight trade versus rare-earth-oxide-equivalent production,
reserves versus resources, and annual versus year-to-date values.

## Source artifacts

Every downloaded file or API response receives a frozen source-artifact record
with agency, title, edition/version, publication and vintage dates, landing and
download URLs, retrieval timestamp, media type, byte size, SHA-256, and an exact
source locator. A later revision creates a new artifact and vintage; it does not
overwrite the earlier source.

## Derivations

Project-derived observations identify their formula, version, input observation
IDs, missing-value rule, zero-denominator rule, and rounding rule. Missing
inputs propagate null. Composite “access,” “advantage,” or “who is winning”
scores are prohibited.

## Coverage

Coverage status distinguishes source absence from unfinished project work:

`available`, `published-null`, `suppressed`, `not-published`, `outside-series`,
`not-yet-acquired`, `not-applicable`, and `unknown`.

The public interface must show the role, unit, scope, status, period, and source
for each displayed statistic.
