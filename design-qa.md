# ZX Alert DPCP Clone — Design QA

## Source truth and normalized target

- Source visual:
  `/var/folders/fz/602qzjrn7s5g1k93jp4dk9dh0000gn/T/codex-clipboard-734ad47d-0fd0-4569-b349-db3de8e759ea.png`
- Source pixels: `2824 × 5931`
- Implementation route:
  `http://127.0.0.1:8502/?scope=ZX&page=alert&lang=zh`
- Desktop CSS viewport: `1280 × 720`
- Browser device pixel ratio: `2`
- Browser screenshot pixels: `1280 × 720` (browser-normalized capture)
- Source regions were cropped and downsampled to `1280 × 720` before comparison.

## Same-input comparison evidence

- Header / filters / cards comparison:
  `/private/tmp/zx-alert-dpcp-v2-comparison-top.png`
- Two-column chart comparison:
  `/private/tmp/zx-alert-dpcp-v2-comparison-charts.png`
- Final implementation captures:
  - `/private/tmp/zx-alert-dpcp-v2-desktop-top-final.jpg`
  - `/private/tmp/zx-alert-dpcp-v2-desktop-charts-2.jpg`
  - `/private/tmp/zx-alert-dpcp-v2-desktop-charts-3.jpg`
- Responsive capture at `635 × 837`:
  `/private/tmp/zx-alert-dpcp-v2-top-h.jpg`

## Required fidelity surfaces

- Fonts and typography: Source Sans / Arial-style compact hierarchy, weights,
  line height, number scale, wrapping, and truncation match the reference
  density. The implementation deliberately keeps ZX business labels instead of
  copying DPCP order-alert copy.
- Spacing and layout rhythm: The alert page hides the application sidebar and
  uses the DPCP blue edge, white header, `9 + 6` filter grid, alert-type strip,
  `6 × 2` card grid, and paired chart rows. At narrow width the cards become
  three columns and charts become one column.
- Colors and tokens: White panels, `#eef1f4` canvas, `#3546c4` Decathlon blue,
  pale borders, dark figures, and the yellow / cyan / periwinkle / ochre /
  purple chart palette match the reference.
- Image and icon fidelity: The source has no photography or illustration.
  Material Symbols render the settings, checkbox, info, menu, reset, download,
  and dropdown icons; Plotly supplies the chart action icons.
- Copy and content: Structure and control language follow DPCP; counts,
  filters, alert names, charts, and detail records remain truthful ZX quality
  data.

## Interaction and runtime checks

- Twelve alert cards expose real query-state links.
- Critical card drill-down returns `2,237` matching detail rows.
- Model search updates the dashboard; Reset reliably clears the search.
- CSV download, date, supplier, inspection-type, material-supplier, PO/model,
  and risk controls render and remain usable.
- Six chart panels render at desktop; chart categories are forced to categorical
  axes so numeric model and PO codes do not distort the layout.
- AppTest passed Chinese Alert, English Alert, and the existing Reporting page
  with zero application exceptions.
- Browser inspection and server output show no visible Streamlit exception or
  error panel.

## Jiandaoyun demonstration behavior

- Page loads use the last persisted snapshot and never refresh the API
  automatically.
- A successful manual refresh writes normalized data and metadata under
  `.runtime/jiandaoyun_snapshots/`.
- FQC, all-factory / third-party Gloves FQC, ZX control-plan, HUGSS shipped PO,
  and derived PO-coverage datasets use the same persistence mechanism.
- API caches no longer expire on a timer; a changed refresh token is required
  for another request.
- An isolated persistence round-trip test passed for CSV data, boolean/date
  restoration, metadata mode, and cleanup.

## Comparison history

### Pass 1 — blocked

- P1: Existing blue product sidebar, rounded cards, large page title, five-card
  layout, and four charts materially differed from DPCP.
- P2: Filters were large labeled widgets instead of the compact DPCP grid.
- Fix: Rebuilt the Alert page shell, filter density, alert strip, twelve-card
  grid, and six-panel chart layout.

### Pass 2 — blocked

- P2: Material icon ligatures displayed as words.
- P2: Numeric-looking Model values were interpreted as continuous axes.
- P2: Reset did not clear a changed Model filter.
- P2: Narrow action buttons wrapped vertically.
- Fix: Bound custom icons to Streamlit's Material Symbols font, forced category
  axes, assigned explicit callback defaults, and rebalanced action columns.

### Pass 3 — passed

- Post-fix evidence is recorded in the two combined comparison files above.
- No actionable P0, P1, or P2 visual or interaction issue remains.
- P3: DPCP contains additional order-domain filters and loading placeholders;
  the ZX version keeps only truthful quality-domain controls and populated
  analysis panels.

final result: passed
