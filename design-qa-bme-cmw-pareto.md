# BME CMW Pareto Layout — Design QA

## Target and implementation

- Reference: `codex-clipboard-f8479a56-3610-4dd3-896f-b25304a34f6f.png`
- Target behavior: vertical Pareto bars, descending from left to right, angled item-code labels, and an in-chart range slider.
- Implementation route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh`

## Implemented changes

- Removed the two TEKTRO KPI cards whose values cannot be calculated.
- CMW IQC and FQC now sort by defect rate descending, using defect quantity only as the tie-breaker and bar-top label.
- Each CMW chart occupies a full row; charts are no longer forced into half-width columns.
- The y-axis title is `不良率` on the left side of the axis; `Y轴` was removed from subplot titles.
- Item codes remain complete and use a -45 degree label angle.
- The in-chart two-ended range slider remains available beneath each chart.

## Verification

- Static checks passed: `git diff --check` and Python compilation.
- Data regression suite passed: 22 tests.
- Browser screenshot comparison is blocked: the in-app browser security policy rejected the local Streamlit URL. No browser workaround was attempted.

## Result

The code and data checks pass, but the required same-viewport screenshot comparison could not be completed in this environment.

final result: blocked
