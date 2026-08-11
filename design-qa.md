# BME chart conclusions and ZX-style data map — Design QA

## Source truth and target

- Conclusion-card reference: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-5308f154-2c68-4071-9f4a-92fc7a0d02fd.png` (`2178 × 1452`).
- ZX data-map reference: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-5c0d7b2e-c359-4317-93de-824e3e656c15.png` (`2272 × 1192`).
- Local implementation route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh`.
- Browser viewport and implementation captures: `1280 × 720`, device density unchanged from the in-app browser.
- Same-input comparison: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/15-reference-implementation-comparison.png`.
- Implementation evidence:
  - Data map: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/07-local-data-map-final.png`.
  - SPC conclusion: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/09-local-spc-conclusion-card.png`.
  - Customer Pareto conclusion: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/10-local-pareto-conclusions.png`.
  - Incoming PPM conclusion: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/11-local-incoming-conclusion.png`.
  - Rework lead-time conclusion: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/12-local-rework-lead-conclusion.png`.
  - Rework volume conclusion: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/13-local-rework-volume-conclusion.png`.
  - Open-rework conclusion: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-conclusion-audit/14-local-open-rework-conclusion.png`.
- State: BME Chinese page, default suppliers and quality gates, `2025-08-11` to `2026-08-11`.

## Full-view and focused comparison

- The BME data map now uses the same information structure as ZX: Community, Supplier, one column per source/quality gate, green `已接入`, red `缺失`, and a final `加载格式 / 当前方式` row.
- BME-specific truth is retained rather than copied blindly: all connected BME sources show `手动 Excel`; End of QC and API remain missing; no API refresh control is shown because BME has no API connection.
- The compact BME table fits the available desktop content width without horizontal scrolling (`793 px` table inside an `817 px` client area), while retaining all eight quality gates plus API.
- Every rendered analysis chart now has the same red-accented `本期结论` card directly below it. The conclusion text is generated from the current filtered chart data, not hard-coded display copy.

## Chart coverage

Browser DOM verification found exactly `7` Plotly charts and `7` `.bme-chart-conclusion` cards in the default BME state:

1. SPC control chart — process stability, trigger breakdown, specification breaches, and the correct follow-up action.
2. Main quality-issue Pareto — top issue, defect quantity, share, and missing issue-description count.
3. Customer NC Pareto — top supplier/model/defect-code combination and its Top-15 share.
4. Incoming-supplier return PPM — highest supplier, numerator, denominator, and IQC record coverage.
5. Rework lead-time trend — latest median, change versus previous month with data, P90 availability, and metric boundary.
6. Monthly closed-rework volume — total, peak month, and small-sample warning.
7. Open-rework aging — open count, longest-running model, days, status, and follow-up action.

The SPC selector's I-MR, stability-only I-MR, p-chart, and X-bar/R branches each generate a method-specific conclusion when selected.

## Required fidelity surfaces

- Fonts and typography: existing BME/ZX typography and optical hierarchy are preserved; conclusion labels and body weights match the accepted Pareto card.
- Spacing and layout rhythm: conclusions sit directly beneath their chart, with consistent margins, border radius, left accent, and section spacing. The data-map expander follows the ZX hierarchy.
- Colors and visual tokens: existing green loaded, red missing, blue manual-Excel, pale-blue canvas, and white card tokens are reused.
- Image quality and assets: the target contains no new raster assets; existing brand and chart assets remain unchanged.
- Copy and content: every conclusion states the current result, relevant boundary or denominator, and a concrete next check without inventing defect-code meanings or root causes.

## Interaction, accessibility, and runtime checks

- The data map updates with supplier, quality-gate, and date filters because its statuses are built from the filtered BME event frame.
- The table retains semantic table/row/header structure; status meaning is communicated by text as well as color.
- Conclusion cards use semantic text and sufficient contrast; visual inspection does not establish full keyboard or screen-reader compliance.
- Browser console errors: none.
- `PYTHONPYCACHEPREFIX=/tmp/quality-pycache PYTHONPATH=.vendor python3 -m py_compile app.py`: passed.
- `git diff --check`: passed.
- `PYTHONPATH=.vendor python3 -m unittest discover -s tests`: 18 tests passed.

## Comparison history

### Pass 1 — blocked

- P1: The default BME page rendered seven charts but only the main issue Pareto had a `本期结论` card.
- P1: The BME data map used four KPI cards plus a record-volume heatmap, which did not match the requested ZX connection-status matrix.
- Fix: Added filter-aware conclusions to all seven charts and rebuilt the data map around the existing ZX table/status components.

### Pass 2 — blocked

- P2: The first BME matrix preserved all quality gates but required horizontal scrolling, hiding Rework and API in the initial viewport.
- Fix: Applied a BME-scoped compact table layout, reduced cell/pill padding, and preserved readable text labels.

### Pass 3 — passed

- Post-fix measurement confirms the entire table fits its container without horizontal overflow.
- Browser verification confirms a one-to-one `7 charts = 7 conclusions` relationship.
- No actionable P0, P1, or P2 issue remains for the requested scope.

final result: passed
