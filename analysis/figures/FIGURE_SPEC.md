# Figure maintenance

Run the analysis commands in the [repository README](../../README.md) before
building the figures. Shared calculations are in `_data.py`; canvas dimensions,
fonts, colours, and PDF checks are in `_style.py`.

## Layout and encoding

- Build at the intended inclusion width, based on the manuscript's 5.5-inch text
  width. Keep the declared canvas when saving.
- Use the Times-compatible font stack and embed TrueType fonts in PDFs.
- Keep arm and response-pole colours consistent across figures. Use position,
  marker shape, or line style to make the encodings readable in greyscale.
- Jitter only categorical coordinates. Reference bands apply only to the subgroup
  used to calculate them; value labels connect to their measured values.
- Measure text dimensions for label placement. Keep counts and ratios that cannot
  be read accurately from the marks; put shared denominators and definitions in
  the caption.

## Captions and checks

Captions should identify every marker and reference line, the inference unit,
interval type, and exploratory status where applicable. For the power panels,
explain the 80% crossing bracket and distinguish the zero-shift rejection rate
from test size under the symmetry null. State the Monte Carlo uncertainty.

After a figure change, check the data from the repository root:

```bash
python3 analysis/figures/_data.py
```

Render the affected figure and inspect it at its intended print size, including a
greyscale view. The figure scripts use Poppler (`pdfinfo`, `pdffonts`, `pdftotext`)
to check canvas size, embedded fonts, clipping, and text overlaps. Missing tools
are reported by the scripts. If a caption or canvas changes, also compile the
manuscript and inspect its layout.

`check_fig3.py` is an author tool for the 2026-08-22 manuscript caption. It requires
the local TeX source, a rendered `fig3.pdf`, and `qpdf`; it is separate from public
reproduction. Its wording and layout checks need updating when the manuscript
changes. From this directory:

```bash
python3 check_fig3.py /path/to/neurips_2026.tex
```
