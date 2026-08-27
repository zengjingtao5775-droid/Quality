# BME Machine Data hybrid matrix — Design QA

## Comparison target

- Source visual truth:
  - `/Users/eric/.codex/generated_images/01a01402-fe53-79e1-b16c-4e55c64e6cb2/exec-8dd04210-4749-4623-b623-d08a28a4e2b4.png` — option 3 priority rail
  - `/Users/eric/.codex/generated_images/01a01402-fe53-79e1-b16c-4e55c64e6cb2/exec-a9ea3e78-b8c3-49ea-bd33-d58d1205ab5c.png` — option 2 grouped matrix
- Normalized hybrid target: `/tmp/bme-risk-hybrid-source-target.png`
- Implementation screenshot: `/tmp/bme-risk-hybrid-selected.png`
- Combined comparison evidence: `/tmp/bme-risk-hybrid-comparison.png`
- Source pixels: 1942 × 809 for each ideation image.
- Implementation state: BME_CMW, Chinese, R12M, matrix point selected; existing Streamlit navigation and sidebar retained.
- Browser viewport used for interaction verification: 1560 × 1000 CSS px, device scale factor 1. A focused crop was normalized for the comparison board because the source consists of two independently generated concepts rather than one exact application frame.

## Findings

- No actionable P0, P1, or P2 mismatch remains.
- Information architecture: the implementation keeps option 3's left-side Top 5 priority rail and option 2's right-side grouped model × component matrix. The existing product title, KPI context, filter, and SPC drill-down remain outside the visual comparison crop.
- Fonts and typography: Inter with PingFang SC / Microsoft YaHei fallbacks matches the dashboard system; hierarchy, weights, wrapping, and shortened display labels remain readable. Exact source component names remain in hover content.
- Spacing and layout rhythm: the 24/76 rail-to-matrix split, restrained card border, compact headings, grouped column separators, and alternating matrix rows match the selected direction within the existing 1280 px application content constraint.
- Colors and visual tokens: Decathlon blue, specification red, SPC amber, cool-slate grid/borders, recurrence outline, and selected-state blue follow the source direction and existing BME tokens.
- Image quality and assets: the selected design contains no product imagery, logos, decorative raster assets, or custom illustrations requiring generation. The visible marks are data-driven Plotly visualizations and native UI text.
- Copy and content: `优先关注`, grouped system names, risk legend, machine-calibration unavailability, and the warning that blank cells are not zero risk are present. No prediction score or unsupported result was introduced.
- Intentional source deviation: empty reference cells are not rendered as “normal” circles because missing or absent risk evidence must not be presented as confirmed zero risk.

## Interaction and console evidence

- Clicked a different risk point in the grouped matrix.
- The process selector changed from `CMW · I-MR · 26''EXPL900HD · BB右碗` to `CMW · I-MR · 24"EXPL900 · 变把（指拨）锁紧螺丝`, confirming the existing SPC drill-down remains functional.
- Browser console errors/warnings: none.
- Streamlit AppTest: `exceptions=0`; both `优先关注` and `分组风险矩阵` rendered.

## Comparison history

1. Initial implementation evidence: `/tmp/bme-risk-hybrid-implementation-v2.png`.
   - P2: a recurrence number badge appeared on every recurring cell, making the dense matrix noisy.
   - P2: long source component labels competed with the grouped headers.
2. Fixes applied:
   - capped marker-size scaling;
   - limited the recurrence count badge to one highest-priority point per component while retaining recurrence outlines on all relevant points;
   - shortened only the visible axis labels while preserving exact source names in hover details.
3. Post-fix evidence: `/tmp/bme-risk-hybrid-selected.png` and `/tmp/bme-risk-hybrid-comparison.png`.
   - The rail and matrix are visually separated, group headers remain readable, risk colors stay dominant, and recurrence no longer overwhelms the relationship view.

## Follow-up polish

- P3: on very wide screens, a future BME-only content-width token could give the matrix more horizontal breathing room without changing other dashboard pages.

## Implementation checklist

- [x] Priority rail uses current risk data, not invented scores.
- [x] Matrix groups Top 15 source components by functional system.
- [x] Specification/SPC/recurrence/selected semantics are distinct.
- [x] Click-to-SPC detail remains functional.
- [x] Machine prediction remains unavailable without Machine ID and calibration history.
- [x] Browser, console, AppTest, unit tests, compile, and diff checks completed.

final result: passed
