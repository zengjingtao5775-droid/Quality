# BME data-map order and overall KPI merge — Design QA

## Source truth and target

- Source visual truth: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-60cbc0f9-7eaf-4d62-807c-c10913367852.png` (`2320 × 2361` pixels).
- Requested change: keep the existing visual language, move the data map above all KPI cards, and merge the customer-problem and current-quality cards into one bicycle-factory KPI section.
- Local implementation route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh`.
- Browser viewport: `1280 × 720` CSS pixels, device density unchanged from the in-app browser.
- Implementation captures:
  - Top/data-map state: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-kpi-order-qa/01-local-top.png` (`1280 × 720`).
  - Unified KPI state: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-kpi-order-qa/02-local-kpis.png` (`1280 × 720`).
- Same-input visual comparison: `/Users/eric/.codex/visualizations/2026/08/10/019fe981-a62d-7820-91b0-27fce1d0b990/bme-kpi-order-qa/04-side-by-side.png` (`2580 × 1500`).
- Density normalization: the source was proportionally padded into a `1280 × 1440` panel; the two implementation captures were stacked into an equal `1280 × 1440` panel. No browser or device frame was compared.
- State: BME Chinese page, all three suppliers and all available quality gates, `2025-08-11` to `2026-08-11`.

## Findings

- No actionable P0, P1, or P2 mismatch remains for the requested scope.
- The first analysis section after the hero is now `1 · 数据来源与完整性`, and the expanded data map is visible before any KPI card.
- The previous `先看客诉情况` and `当前质量情况` headings no longer render. One heading, `2 · 自行车工厂整体 KPI`, owns all seven cards.
- The seven cards retain the original values and calculation notes: FSD customer PPM `3,393`, FSD customer NC `7,875`, TEKTRO customer NC `3,018`, FSD inspection NC rate `5.40%`, CMW incoming return PPM `488`, open rework `3`, and suspected input errors `2`.
- Desktop layout uses four cards on the first row and three on the second; the existing responsive rule collapses the grid to one column on narrow screens.

## Required fidelity surfaces

- Fonts and typography: existing BME heading, KPI label, value, and note styles are unchanged; the new section title uses the existing subheader hierarchy.
- Spacing and layout rhythm: the hero-to-data-map-to-KPI sequence is clear, and the 4+3 card grid keeps consistent gaps, radii, shadows, and card heights.
- Colors and visual tokens: existing blue KPI accents, white cards, pale-blue page background, and green/red data-map status tokens are preserved.
- Image quality and assets: no new image asset was introduced; existing brand and chart assets remain untouched.
- Copy and content: the merged title describes the cards as the overall bicycle-factory KPI set; individual labels, denominators, and calculation boundaries are preserved.

## Interaction and runtime checks

- DOM order verified: `1 · 数据来源与完整性` → `2 · 自行车工厂整体 KPI` → `3 · SPC（统计过程控制）`.
- Browser DOM contains all seven KPI labels and values and contains no `先看客诉情况` heading.
- Supplier, quality-gate, and date filters remain upstream of the same calculations; this change only reorders rendering and combines the two card arrays.
- Browser console error log: `0` entries.
- Rendered page contains no Streamlit exception or error state.
- `PYTHONPYCACHEPREFIX=/tmp/quality-pycache PYTHONPATH=.vendor python3 -m py_compile app.py`: passed.
- `git diff --check`: passed.
- `PYTHONPATH=.vendor python3 -m unittest discover -s tests`: 18 tests passed.

## Comparison history

### Pass 1 — passed

- The combined visual input confirms the requested hierarchy change while preserving the accepted BME styling and metric content.
- Focused inspection of the KPI region confirms one unified heading and a readable 4+3 desktop grid; no additional focused crop was necessary because card labels, values, and notes are legible in the implementation capture.
- No visual fix was required after this pass.

final result: passed
