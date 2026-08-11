# BME SPC explanation and problem-priority — Design QA

## Source truth and target

- User references:
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-b21ca905-5ecd-4abc-94ff-9b0180bcb175.png` — customer complaint cards.
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-9525f676-23e4-451d-a316-e8bc016d1d13.png` — SPC explanation popover.
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-d61c72a7-50f2-42d5-bbd6-cbbec9ed13e0.png` — Pareto conclusion.
- Local implementation route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh`.
- CSS viewport: `1280 × 720`.
- Implementation screenshots:
  - `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-spc-qa/01-customer-cards-top.png`
  - `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-spc-qa/02-spc-explanation.png`
  - `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-spc-qa/03-pareto-conclusion.png`
- Same-input comparison: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-spc-qa/04-reference-implementation-comparison.png`.
- State: BME Chinese page, default suppliers and quality gates, `2025-08-11` to `2026-08-11`; the second screenshot has the CMW I-MR explanation open.

## Full-view and focused comparison

- Customer complaint KPIs now appear immediately below the BME hero, before data completeness and analysis sections. The three values and notes are unchanged: FSD PPM `3,393`, FSD NC `7,875`, TEKTRO NC `3,018`.
- The SPC heading expands the abbreviation to `SPC（统计过程控制）`. Its introduction says in plain Chinese what SPC is for and clarifies that a red point is a process warning, not automatic proof that the item is defective.
- The CMW I-MR explanation now answers four practical questions in order: what the chart answers, how to read its lines and red points, how it is calculated, and where the data comes from. It also tells the user what to check after a warning: order, equipment, operator, and material batch.
- The Pareto conclusion is now a separate white/red decision card with a strong `本期结论` label, bold body text, and a left accent. It is visually distinct from normal captions while preserving the exact calculation and missing-description warning.

## Required fidelity surfaces

- Existing BME/ZX typography, pale-blue canvas, white cards, Decathlon blue, chart sizing, and vertical reading order are preserved.
- No KPI formula, chart dataset, SPC control-limit calculation, Pareto ranking, filter, or source path changed.
- All new copy uses ordinary Chinese except established quality terms such as SPC, I-MR, UCL/LCL, USL/LSL, Ppk, NC, PPM, and Pareto; each relevant term is explained in context.
- The SPC popover remains attached to the chart's `说明` control and does not replace or resize the chart.

## Interaction and runtime checks

- Customer cards render at the top and the later section begins directly with `客诉问题 Pareto`, so the KPIs are not duplicated.
- Opening the CMW I-MR `说明` shows all four explanation sections and the correct source workbook link; Escape closes the popover.
- Pareto chart and conclusion card render together; the first issue is `表面有划伤`, count `3,500`, share `41.7%`, with `202` unclassified records called out.
- Browser console errors: none.
- `python3 -m py_compile app.py`: passed with the project path configuration.
- `git diff --check`: passed.
- `PYTHONPATH=.vendor python3 -m unittest discover -s tests`: 18 tests passed. The first unconfigured run could not load `.xls` because system Python did not include the repo's bundled `xlrd`; the project-configured rerun passed.

## Comparison history

### Pass 1 — issues found from the user references

- P1: SPC explanation started with formulas and assumed readers already understood control charts.
- P1: Customer complaint KPI cards appeared only after multiple analysis sections.
- P2: The Pareto conclusion looked like a low-priority caption and was easy to miss.

### Pass 2 — passed

- Reordered customer KPIs, rewrote SPC help around reading and action, and promoted the Pareto sentence to a decision card.
- Visual comparison confirms the requested hierarchy changes without introducing chart or data regressions.
- No actionable P0, P1, or P2 issue remains for this scope.

final result: passed
