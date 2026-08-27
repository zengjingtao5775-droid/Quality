# BME Machine Data hybrid matrix — Design QA

## Comparison target

- Source visual truth:
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-31944100-21c1-4968-9bc2-a84339d475c4.png` — option 3 priority rail
  - `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-3b69d172-611e-438b-8faa-fde1ee8ef4fa.png` — option 2 grouped matrix
- Implementation screenshot: `/tmp/bme-risk-fullqa.png`
- Combined comparison evidence: `/tmp/bme-risk-comparison.png`
- Implementation state: BME_CMW, Chinese, R12M, matrix point selected; the existing Streamlit navigation and sidebar are retained.
- Browser viewport: 1574 × 914 CSS px, matching the supplied reference width closely.

## Findings

- No actionable P0, P1, or P2 mismatch remains.
- Information architecture: option 3's left Top 5 priority rail is combined with option 2's right grouped model × component matrix. The title and four real-data KPIs are now one integrated header instead of five visually separate blocks.
- Layout: the rail/matrix split is 20/80. The matrix is the main visual, while the rail remains wide enough to show full model names at the target viewport.
- Density: recurrence number circles were removed from the matrix. A dark outline preserves cross-model recurrence, and exact counts remain in hover detail.
- Typography: horizontal two-line component labels use a smaller axis font and no longer collide. Exact source component names remain unchanged in data and hover content.
- Grouping: `太阳花锁紧盖` is classified with wheel/chassis components, removing the visually awkward one-column `其他` group and matching the selected reference's functional grouping.
- Visual rhythm: borders, shadows, row bands, group bands, and grid lines are lighter. Priority bars are thin continuous stacks with a neutral remainder instead of dense in-bar numbers.
- Colors: specification red, SPC amber, recurrence slate outline, and selected blue remain distinct and consistent with the existing BME palette.
- Data boundary: no unsupported prediction score was added. Machine calibration risk remains unavailable without Machine ID and calibration history.
- Intentional source deviation: blank matrix cells are not rendered as confirmed-normal circles because missing risk evidence is not equivalent to verified zero risk.

## Interaction and console evidence

- The grouped matrix rendered 84 clickable risk points.
- Clicking a different point changed the process selector from `CMW · I-MR · RCR FP · 坐垫与坐垫杆（螺母）` to `CMW · I-MR · RCR FP · 膨胀吊心`, confirming click-to-SPC drill-down.
- Browser console errors: none.
- Streamlit AppTest: `exceptions=0`; the matrix title and Plotly charts rendered.

## Fix history

1. P1: 15 horizontal component labels initially collided at the target viewport.
   - Fixed by using concise two-line display labels and a 10 px axis font while preserving exact source names in hover data.
2. P1: long model names clipped in the 18% rail.
   - Fixed by changing the rail/matrix split to 20/80 and enabling axis auto margins.
3. P2: the last one-column `其他` group competed with the wheel/chassis header.
   - Fixed by grouping the source `太阳花` component with wheel/chassis.
4. P2: recurrence badges and independent KPI cards created visual noise.
   - Fixed by replacing badges with outlines and replacing cards with a compact summary strip.

## Implementation checklist

- [x] Priority rail uses current risk data, not invented scores.
- [x] Matrix groups Top 15 source components by functional system.
- [x] Specification/SPC/recurrence/selected semantics are distinct.
- [x] Click-to-SPC detail remains functional.
- [x] Machine prediction remains unavailable without Machine ID and calibration history.
- [x] Browser comparison, console check, AppTest, unit tests, compile, and diff checks completed.

final result: passed
