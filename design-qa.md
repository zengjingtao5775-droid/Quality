# BME Overflow Regression QA — 2026-08-12

## Evidence

- Source screenshots:
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-c9909ad0-d44d-4b39-805f-41a10c18de35.png` (`2240 × 2376`).
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-77911dbc-f0cb-4566-8c48-3b24871681e3.png` (`2284 × 2654`).
- Browser-rendered implementation:
  - `/tmp/bme-overflow-final/fsd-en.png` (`1280 × 720`).
  - `/tmp/bme-overflow-final/supplementary-en.png` (`1280 × 720`).
- Normalized same-input comparisons:
  - `/tmp/bme-overflow-final/compare-fsd.png`.
  - `/tmp/bme-overflow-final/compare-supp.png`.
- State: English BME dashboard, default one-year period, all suppliers, desktop viewport `1280 × 720`, density 1.

## Findings and comparison history

1. Earlier P1: embedded Plotly range sliders created duplicate mini-plots, occupied chart space, and overlapped the next subplot. Fix: remove embedded sliders from all multi-panel product and supplementary charts.
2. Earlier P1: dozens of categories were compressed into each panel, causing unreadable angled labels and cross-row overflow. Fix: use a management-focused Top 5 in every IQC/PQC/FQC and supplementary panel.
3. Earlier P1: one-category PQC expanded visually while neighboring IQC and FQC were overcrowded. Fix: preserve a five-slot category range and fixed relative bar width.
4. Post-fix evidence: FSD IQC/PQC/FQC and CMW incoming/rework panels have no slider, no duplicated miniature chart, no cross-panel label overlap, and consistent five-item density.

## Required fidelity surfaces

- Typography: English panel titles, horizontal measure labels, and angled category labels remain readable.
- Spacing and layout: two-up first row and full-width second row remain; controls no longer consume subplot space.
- Colors: existing gate colors and semantic conclusion styling are unchanged.
- Image assets: none are used in these chart regions.
- Copy: business labels and conclusions are unchanged; only the visible category count is reduced to Top 5.

## Verification

- Primary interactions tested: English route load and scrolling through FSD products and CMW supplementary analysis.
- Browser console errors: 0.
- BME regression suite: 22 tests passed.
- Python compilation and `git diff --check`: passed.

final result: passed

---

# BME Dashboard Display QA

## Evidence

- Source visual truth:
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-d85fe649-94a8-4bd3-850e-eea6b174b7c2.png`
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-93fa6b86-5dc4-48ed-acd6-840ea8866822.png`
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-3ffca93a-6149-4234-85ba-1d277848f9a8.png`
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-1d5bbade-a623-4beb-8de6-1c7c912adf16.png`
- Implementation route: `http://127.0.0.1:8502/?scope=BME_CMW&lang=zh` and `lang=en`
- Implementation screenshots:
  - `/tmp/bme-ui-audit-english/data-map-en.png`
  - `/tmp/bme-ui-audit-english/cmw-charts-en.png`
- Viewport: Codex in-app browser desktop viewport, 1280 × 720 CSS px, device scale factor 1.
- State: default one-year period, all BME suppliers, Chinese and English views.

## Full-view and focused comparison

The supplied screenshots showed three P1 display failures: English axis-label clipping and cross-panel overflow, long English status pills overlapping adjacent cells, and redundant range sliders covering neighboring charts. Focused browser checks were performed on the English data map, CMW paired product charts, FSD two-plus-one chart grid, and Chinese supplementary analysis.

## Comparison history

1. Earlier finding: every product panel showed a slider and one-category PQC expanded into a full-width block. Fix: sliders are conditional above five categories; all panels reserve five visual slots and bars use a fixed relative width. Post-fix evidence: browser-rendered FSD PQC keeps one normal-width bar with no slider.
2. Earlier finding: three supplementary sliders obscured chart content. Fix: 2.5%-height conditional sliders, 24% vertical subplot spacing, and increased figure height. Post-fix evidence: browser-rendered supplementary panels and conclusion no longer overlap.
3. Earlier finding: `Return Quantity` was clipped and the right-panel `Defect Rate` crossed chart boundaries. Fix: compact English measure labels, panel-specific outside positioning, and English-only outer margins. Post-fix evidence: `Return Qty` and `Defect Rate` are fully visible beside their own panels.
4. Earlier finding: `Not connected` pills and long data-map headers collided. Fix: `Missing` status and shorter English headers. Post-fix evidence: every pill stays within its table cell.

## Required fidelity surfaces

- Fonts and typography: existing Inter / PingFang SC / Microsoft YaHei stack retained; compact English labels use 12 px and remain readable.
- Spacing and layout rhythm: paired chart structure retained, with conditional controls and larger supplementary row separation.
- Colors and visual tokens: existing blue, amber, green, and red semantic tokens retained without introducing new colors.
- Image quality and assets: no image assets are present in the affected dashboard regions; no placeholders or raster substitutions were introduced.
- Copy and content: English status and measure wording was shortened without changing business meaning.

## Findings

No actionable P0, P1, or P2 display mismatch remains in the four reported regions.

## Primary interactions tested

- Chinese and English route loading.
- Data-map rendering in English.
- CMW paired chart rendering.
- FSD two-plus-one chart layout.
- Conditional range-slider presence.
- Supplementary chart scrolling and layout.

No browser console error was visible during the tested interactions.

final result: passed
