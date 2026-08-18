**Comparison Target**

- Source visual truth: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-239fbfc2-61de-4a0e-a1a8-9c98777d2876.png`
- Browser-rendered implementation: `/tmp/bme-top-filter-implementation.png`
- Combined focused comparison: `/tmp/bme-filter-side-by-side.png`
- Route and state: `http://127.0.0.1:8511/?scope=BME_CMW&lang=zh`, expanded top filter, all three suppliers selected, default one-year date range.
- Viewport: 1280 x 720 CSS px, device scale factor 1.
- Source pixels: 2746 x 416. Implementation pixels: 1280 x 720. For the focused comparison, the implementation filter region was cropped to 870 x 195 and both regions were normalized to 1100 px width.

**Full-view Comparison Evidence**

- The implementation keeps the existing BME page hierarchy and places one compact, full-width filter card directly below the dashboard header.
- The sidebar now contains only the dashboard page choices and language switch for the BME route; the duplicate current-page card and analytical filters are absent.
- The first screen retains the management summary immediately below the filter, so the new control surface does not displace the primary decision content excessively.

**Focused Region Comparison Evidence**

- The combined comparison confirms the reference pattern was adapted rather than copied: white enterprise card, thin neutral border, horizontal controls, clear reset action, and collapsible disclosure.
- The BME version intentionally contains only Supplier and Period. Preset management, Add New, Save and Search, and the large reference filter inventory were excluded because they are not part of the current dashboard requirement.

**Required Fidelity Surfaces**

- Fonts and typography: existing Inter/PingFang system preserved; labels, values, disclosure title, and reset action remain readable at 1280 px with no truncation.
- Spacing and layout rhythm: 46 px controls, aligned baseline, 16 px internal padding, 10 px radius, and 18 px section gap provide a compact but non-crowded filter band.
- Colors and visual tokens: white surface, neutral border, Decathlon-blue selected tags, and neutral reset button match the dashboard design system without implying risk status.
- Image quality and asset fidelity: no image or illustrative asset is present in either filter surface, so no raster/vector substitution was required.
- Copy and content: bilingual labels are concise and complete; current supplier/date scope is repeated in a low-emphasis status line for clarity.

**Findings**

- No actionable P0, P1, or P2 differences remain.
- [P3] The BME filter is intentionally less dense than the reference because only two analysis dimensions are currently reliable. Adding empty filter controls solely for visual similarity would reduce usability.

**Comparison History**

- Iteration 1: selected supplier tags inherited a red global style and the sidebar still showed a duplicate current-page card. Both were classified P2 because red could be confused with a risk state and the extra card contradicted the requested sidebar simplification.
- Fixes: scoped the selected tags to Decathlon blue and suppressed the duplicate current-page card on the BME route.
- Post-fix evidence: `/tmp/bme-top-filter-implementation.png` and `/tmp/bme-filter-side-by-side.png`. The final browser capture shows blue tags, a page/language-only BME sidebar, and no overflow or clipped copy.

**Primary Interactions Tested**

- Cleared all supplier selections and confirmed the scope changed to no supplier selected.
- Used Reset and confirmed CMW, FSD, and TEKTRO were restored.
- Switched Chinese to English and confirmed the filter labels, scope text, and reset action remained aligned and complete.
- Clicked the Risk anchor and confirmed `#bme-risk` reached the correct section.
- Browser error/warning log after interaction: 0 entries.

**Implementation Checklist**

- [x] Move Supplier and Period from the sidebar to the dashboard top.
- [x] Keep the BME sidebar focused on page selection and language.
- [x] Add clear scope feedback, Reset, collapse behavior, and responsive wrapping.
- [x] Preserve bilingual copy and existing analytical logic.
- [x] Verify the browser-rendered state and console.

**Open Questions**

- None for the current two-filter scope.

**Follow-up Polish**

- If additional reliable filter dimensions are introduced later, add them in the same card using the existing wrap behavior rather than returning filters to the sidebar.

final result: passed

---

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
