# BME follows Textile ZX — Design QA

## Source truth and target

- Source visual: `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-bf32ce3a-f9dc-4a51-8128-9c30f85d4253.png`
- Source pixels: `2932 × 4166` RGBA.
- Implementation route: `http://127.0.0.1:8505/?scope=BME_CMW&lang=zh`
- CSS viewport: `1280 × 720`; device pixel ratio: `2`.
- Implementation screenshots:
  - `/private/tmp/bme-textile-style-implementation.png`
  - `/private/tmp/bme-textile-style-risk-final.png`
- Same-input comparisons:
  - `/private/tmp/bme-textile-style-comparison-top.jpg`
  - `/private/tmp/bme-textile-style-comparison-risk.jpg`
- State: BME default filters, data map collapsed for the top comparison; risk cluster and Top Risk Model / Item section for the focused comparison.

## Full-view comparison evidence

The top comparison places the Textile ZX reference and BME implementation in one `2560 × 720` image. Both use the same application sidebar, hero, supplier/period chips, collapsed data-map row, compact KPI grid, pale blue canvas, white cards, Decathlon-blue accents, and the high-risk cluster as the first major analysis section.

The BME KPI content intentionally differs because BME does not currently contain ZX RPM, NQC, IV, HUGSS shipped-PO, or Jiandaoyun FQC denominators. It uses six source-supported KPIs and does not fabricate the two remaining ZX card slots.

## Focused comparison evidence

The risk comparison places the Textile ZX cluster/Pareto region and BME cluster/Pareto region in one image. BME preserves the same cluster-then-Pareto reading order. Its axes are source-supported BME measures: Bayesian-shrunk Alert-record share and Alert volume. Numeric-looking Model / Item codes are forced to a categorical axis in the Pareto chart.

## Required fidelity surfaces

- Fonts and typography: Existing project typography, heavy dashboard title, compact KPI labels, large values, bilingual copy hierarchy, line height, and wrapping are reused from Textile ZX.
- Spacing and layout rhythm: Sidebar width, hero proportions, chips, data-map expander, three-column KPI grid, section gaps, card radii, and chart widths match the existing Textile ZX system. Six BME KPI cards form two complete rows.
- Colors and visual tokens: Existing blue gradient sidebar, pale blue page background, white panels, blue top borders, semantic green/amber/red risk colors, and Plotly chart palette are reused.
- Image quality and assets: The reference contains no photography or custom raster illustration. Existing Decathlon branding, Material Symbols, Plotly controls, and code-owned decorative hero treatment are reused; no placeholder or generated asset was introduced.
- Copy and content: Page title, navigation, data-map placement, KPI hierarchy, high-risk cluster, Top Risk Model / Item Pareto, issue Pareto, trend, and more-analysis structure follow Textile ZX. BME values remain grounded in FSD/CMW/TEKTRO source data.

## Interaction and runtime checks

- BME route renders with zero Streamlit exceptions in AppTest and browser.
- Data-map expander opens and exposes the manual-Excel/API connection method table.
- Sidebar filters, date range, supplier, and quality-gate controls render and retain BME scope.
- Cluster and Top Risk Model / Item Pareto render; categorical Model / Item labels no longer become a continuous numeric axis.
- Top Risk Pareto is capped at 12 items to avoid an unusable oversized chart.
- The third `QUALITY_ALERT` route still shows `ZX + BME` and the twelve central Alert cards, with no BME-main cluster section.
- Browser script state reached `notRunning`; no `stException` panel was present.

## Comparison history

### Pass 1 — blocked

- P1: BME route incorrectly reused the third central Alert page instead of the Textile ZX main-dashboard structure.
- Fix: Restored the BME-specific vertical dashboard route and rebuilt its top structure to mirror Textile ZX.

### Pass 2 — blocked

- P1: Top Risk Model / Item initially selected hundreds of items and numeric-looking codes produced a continuous axis measured in billions.
- P2: Raw Alert share over-prioritized one-record products at 100%.
- Fix: Capped the Pareto at 12 items, forced a categorical axis, and applied a transparent 20-record Bayesian prior while retaining raw share in hover detail.

### Pass 3 — passed

- Post-fix top and focused comparison evidence is listed above.
- No actionable P0, P1, or P2 fidelity or interaction issue remains.
- Intentional difference: BME uses six truthful KPI cards rather than fabricating ZX-only RPM, NQC, IV, or FQC metrics.

final result: passed
