# BME CMW Pareto Layout — Design QA

## Target and implementation

- References: `codex-clipboard-c680548f-8e76-403e-99fc-1f1b61adfbd7.png`, `codex-clipboard-d5cb9dc9-6242-4915-b94d-e58d35cdee20.png`, and the earlier Pareto reference `codex-clipboard-f8479a56-3610-4dd3-896f-b25304a34f6f.png`.
- Target behavior: supplier-specific KPI rows; vertical Pareto bars; left-aligned panel labels; correctly placed axis names; angled item-code labels; and a compact in-chart range slider.
- Implementation route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh`

## Implemented changes

- Factory KPI cards are grouped into two supplier rows: CMW first, FSD second.
- Removed the two TEKTRO KPI cards whose values cannot be calculated.
- CMW FQC sorts by defect rate descending, using defect quantity as its tie-breaker and bar-top label.
- CMW IQC now follows the revised business rule: bar height and sorting use return quantity, while the bar-top label shows defect rate.
- Charts now use a compact two-column rhythm: CMW IQC and FQC share one row; FSD IQC and PQC share the first row, while FQC uses the full-width second row.
- Each chart initially shows the Top 5 products so the two-up layout stays legible; the range slider still exposes the remaining products.
- The IQC panel uses `IQC` as a left-aligned panel subtitle. Its y-axis title is `退货数量`, its x-axis title is `料号` at the lower right, and each bar-top label is the defect rate.
- The CMW panel also labels the bar-top measure at the chart top (`不良率` for IQC), and all CMW y-axis names are horizontal instead of vertical.
- Item codes remain complete and use a -45 degree label angle.
- The in-chart two-ended range slider remains available beneath each chart.
- The range slider's duplicate miniature bars are hidden, and the remaining horizontal track has been reduced to a thin 2.5%-height control with the selected window and drag handles preserved.

## Verification

- Static checks passed: `git diff --check` and Python compilation.
- Data regression suite passed: 22 tests.
- Browser verification passed on the local Streamlit route. At the normal desktop viewport, CMW renders as two aligned charts on one row; FSD renders IQC and PQC on one row with FQC below. Panel titles, horizontal y-axis names, angled item codes, bar-top values, and thin draggable tracks remain readable without overlap.

## Result

The requested KPI grouping, two-up chart layout, IQC labeling, and compact slider match the supplied reference direction without changing the chart's business calculations.

final result: passed
