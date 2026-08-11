# BME simplified data map and KPI layout — Design QA

## Source truth and target

- Current BME before-state: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-d2dd2676-2598-4cc0-aae9-1e36124b3337.png`.
- Textile simplicity reference: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-80f00af8-462a-4350-8846-d7d3f0a8df82.png` (`2380 × 2400`).
- Requested outcome: use Textile's concise hierarchy for the BME data-map and KPI area without changing BME metrics or pretending BME has an API.
- Local route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh`.
- Browser viewport: `1280 × 720` CSS pixels, browser density unchanged.
- Implementation captures:
  - Top/data map: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-simple-layout-qa/01-local-top.png` (`1280 × 720`).
  - KPI region: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-simple-layout-qa/02-local-kpis.png` (`1280 × 720`).
- Same-input comparison: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-simple-layout-qa/03-reference-implementation.png` (`2580 × 1500`).
- Density normalization: the Textile source was proportionally padded into a `1280 × 1440` panel; the two BME implementation captures were stacked into an equal `1280 × 1440` panel.
- State: Chinese BME page, all three suppliers, all available quality gates, `2025-08-11` to `2026-08-11`.

## Findings

- No actionable P0, P1, or P2 mismatch remains for the requested scope.
- The BME hero now flows directly into the expanded `数据地图`, matching Textile's hierarchy. The redundant numbered section title and explanatory paragraph are removed.
- The data map keeps one necessary warning only: `172 条记录缺少日期，未计入本期 KPI 和图表。` The longer duplicate methodology caption is removed.
- The KPI cards now follow the data map directly without another section title. Notes are shortened to denominators or decision boundaries only.
- Desktop uses a stable `4 + 3` layout, preventing the previous dense `5 + 2` arrangement. At widths below `1100 px` it becomes two columns and below `720 px` one column.
- KPI calculations and displayed values remain unchanged: `3,393`, `7,875`, `3,018`, `5.40%`, `488`, `3`, and `2`.

## Intentional differences from Textile

- BME retains more table columns because it has eight real quality gates across three suppliers; collapsing them would hide source coverage.
- BME has no API, so the Textile refresh button and cache timestamp are not copied.
- BME uses four columns rather than Textile's three because seven cards read cleanly as `4 + 3` and avoid an orphan third row.

## Required fidelity surfaces

- Fonts and typography: existing shared BME/Textile heading, table, status-pill, KPI-label, value, and note styles are reused. Shorter labels avoid unnecessary wrapping.
- Spacing and layout rhythm: redundant headings and captions are removed; the hero, data map, KPI grid, and SPC section now form a tighter vertical sequence.
- Colors and visual tokens: existing pale-blue canvas, white cards, blue top accents, and green/red/blue data-map pills remain unchanged.
- Image quality and assets: no new asset is required; brand and chart assets are unchanged.
- Copy and content: only redundant or formula-like small copy was shortened. Denominators, missing-data boundaries, and no-PPM conditions remain visible.

## Interaction and runtime checks

- Supplier, quality-gate, and date filters remain upstream of the same BME calculations.
- DOM verification confirms the removed headings/captions no longer render, while all seven KPI labels and values remain.
- Browser console errors: `0`.
- Rendered page contains no Streamlit exception or error state.
- `PYTHONPYCACHEPREFIX=/tmp/quality-pycache PYTHONPATH=.vendor python3 -m py_compile app.py`: passed.
- `git diff --check`: passed.
- `PYTHONPATH=.vendor python3 -m unittest discover -s tests`: 18 tests passed.

## Comparison history

### Pass 1 — passed

- The combined comparison confirms that BME now follows Textile's concise information hierarchy while preserving BME-specific data coverage and metric boundaries.
- Focused KPI capture confirms readable labels, consistent card heights, a balanced `4 + 3` grid, and no unnecessary second section heading.
- No visual fix was required after this comparison.

final result: passed
