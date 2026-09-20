#!/usr/bin/env python3
"""Shared canvas dimensions, typography, colours, and PDF checks.

Figures use a 5.5-inch manuscript text width. figsize_for() sets the canvas to
its intended inclusion width so font and stroke sizes remain in print points.
The font stack prefers Times-compatible serifs; PDFs embed TrueType fonts.
Arm and response-pole identities use separate colour pairs.

Call apply() before creating a figure.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402

# --------------------------------------------------------------------------
# Page geometry.  From neurips_2026.sty: textwidth=5.5in, textheight=9in,
# \normalsize = 10pt on 11pt leading.
# --------------------------------------------------------------------------
TEXTWIDTH_IN = 5.5
TEXTHEIGHT_IN = 9.0
BODY_PT = 10.0

# Print-point sizes assume the canvas is included at its declared width.
PT = {
    "base": 8.0,
    "tick": 7.0,
    "axis": 8.0,
    "title": 8.0,
    "annot": 7.0,
    "small": 6.5,
}

# Okabe-Ito palette: blue/vermillion for profile arms, green/purple for poles.
# Grey identifies the no-profile arm; other greys style reference marks.
COLOR = {
    # -- arm identity --------------------------------------------------------
    "P_nov": "#0072B2",       # blue
    "P_adv": "#D55E00",       # vermillion
    "D": "#6E6E6E",           # neutral reference
    # -- pole identity -------------------------------------------------------
    "pole_H": "#009E73",      # bluish green
    "pole_L": "#CC79A7",      # reddish purple
    # -- structure -----------------------------------------------------------
    "ink": "#1A1A1A",
    "rule": "#8C8C8C",
    "band": "#E4E4E4",
    "band_fringe": "#F2F2F2",  # the 0.40-0.42 lattice step, drawn weaker
    "band_edge": "#C4C4C4",
    "muted": "#6E6E6E",
    "faint": "#9A9A9A",
}

# Times first, then its metric-compatible free clones.  Times New Roman resolves
# on macOS; Nimbus Roman / TeX Gyre Termes on TeX Live; Liberation Serif on most
# Linux boxes.  All are metrically Times, so the figure renders identically
# wherever it is rebuilt.
#
# Ordered TrueType-first: pdf.fonttype=42 asks for TrueType embedding, and
# handing it an OpenType/CFF face (Nimbus Roman and TeX Gyre Termes are both
# .otf on most TeX installs) produces a valid but odd PDF that poppler reports
# as "Mismatch between font type and embedded font file".  Harmless, but it is
# noise in exactly the check a submission portal runs.
SERIF_STACK = [
    "Times New Roman",   # macOS, Windows           (TrueType)
    "Tinos",             # metric clone of the above (TrueType)
    "Liberation Serif",  # most Linux distributions  (TrueType)
    "Nimbus Roman",      # TeX Live                  (OpenType/CFF)
    "Nimbus Roman No9 L",
    "TeX Gyre Termes",
    "FreeSerif",
    "DejaVu Serif",
]


def resolve_serif() -> str:
    """Return the first font in SERIF_STACK actually installed, and warn if the
    match is not a Times clone.  A silent fallback to DejaVu Serif is the kind
    of drift this module exists to catch."""
    for name in SERIF_STACK:
        try:
            fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
        except Exception:
            continue
        if name == "DejaVu Serif":
            warnings.warn(
                "No Times-metric serif found; falling back to DejaVu Serif. "
                "Figure text will not match the paper's ptm body font. "
                "Install one of: " + ", ".join(SERIF_STACK[:5]),
                stacklevel=2,
            )
        return name
    return "serif"


def apply() -> str:
    """Install the house style. Call once, before creating any figure."""
    serif = resolve_serif()
    plt.rcParams.update({
        # -- embedding: no Type 3 anywhere, editable text in SVG ------------
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "pdf.compression": 6,

        # -- typography ------------------------------------------------------
        "font.family": "serif",
        "font.serif": [serif] + [f for f in SERIF_STACK if f != serif],
        "mathtext.fontset": "stix",       # Times-metric math
        "font.size": PT["base"],
        "axes.titlesize": PT["title"],
        "axes.labelsize": PT["axis"],
        "xtick.labelsize": PT["tick"],
        "ytick.labelsize": PT["tick"],
        "legend.fontsize": PT["small"],

        # -- axes ------------------------------------------------------------
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "axes.edgecolor": COLOR["ink"],
        "axes.labelcolor": COLOR["ink"],
        "text.color": COLOR["ink"],
        "axes.axisbelow": True,
        "axes.grid": False,

        # -- ticks -------------------------------------------------------------
        "xtick.color": COLOR["ink"],
        "ytick.color": COLOR["ink"],
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.6,
        "ytick.major.size": 2.6,
        "xtick.minor.size": 1.4,
        "ytick.minor.size": 1.4,
        "xtick.minor.width": 0.5,
        "ytick.minor.width": 0.5,

        # -- data ink ----------------------------------------------------------
        "lines.linewidth": 1.1,
        "lines.markersize": 3.2,
        "lines.markeredgewidth": 0.0,
        "errorbar.capsize": 2.0,

        # -- legend ------------------------------------------------------------
        "legend.frameon": False,
        "legend.handlelength": 1.2,
        "legend.handletextpad": 0.5,
        "legend.borderpad": 0.0,
        "legend.labelspacing": 0.3,

        # -- output ------------------------------------------------------------
        "figure.dpi": 300,
        "savefig.dpi": 600,
        "savefig.bbox": None,   # honour the declared canvas; see figsize_for()
    })
    return serif


def figsize_for(frac_linewidth: float, aspect: float = 0.72) -> tuple[float, float]:
    """Canvas size for a figure included at ``width=<frac>\\linewidth``.

    Authoring at exactly the displayed width is what makes the rendered point
    sizes above true.  ``aspect`` is height/width.
    """
    if not 0 < frac_linewidth <= 1.0:
        raise ValueError("frac_linewidth must be in (0, 1]")
    w = TEXTWIDTH_IN * frac_linewidth
    return (w, w * aspect)


def tidy(ax) -> None:
    """Spine and tick treatment applied to every axes."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(COLOR["ink"])
        ax.spines[side].set_linewidth(0.6)
    ax.tick_params(direction="out", pad=2)


def save(fig, out_dir: Path, stem: str, *, formats=("pdf", "svg", "png")) -> list[Path]:
    """Write the figure at its declared canvas size.

    ``bbox_inches='tight'`` is deliberately avoided: it crops to the drawn
    content, which silently changes the output width and reintroduces the scale
    drift this module exists to prevent.  Lay the figure out with constrained
    layout or explicit margins instead.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in formats:
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, format=ext)
        written.append(p)
    return written


def scan_text(path: Path, gap_pt: float = 0.6) -> list[str]:
    """Find text that will not survive printing: runs off the canvas, or runs
    into another run.

    Both failure modes shipped in this paper and neither is visible in a casual
    look at the PNG.  fig2's panel (c) title was cut off mid-word at the right
    canvas edge ("censoring reproduc"), and fig3's panel (a) statistics line was
    overprinted by panel (b)'s rotated y-label, with the tail of the string drawn
    *inside* panel (b) over the power curve.  A word box that leaves the canvas,
    or two boxes that intersect by more than ``gap_pt`` in both axes, is the
    signature of each.

    Needs poppler's ``pdftotext``; returns a "skipped" note if it is absent.
    """
    import re
    import subprocess

    try:
        xml = subprocess.run(["pdftotext", "-bbox", str(path), "-"],
                             capture_output=True, text=True).stdout
    except FileNotFoundError:
        return ["pdftotext not available; text-layout scan skipped"]

    page = re.search(r'width="([\d.]+)" height="([\d.]+)"', xml)
    if not page:
        return ["could not read page box from pdftotext"]
    pw, ph = float(page.group(1)), float(page.group(2))

    words = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in
             re.findall(r'<word xMin="([\d.eE+-]+)" yMin="([\d.eE+-]+)" '
                        r'xMax="([\d.eE+-]+)" yMax="([\d.eE+-]+)">(.*?)</word>', xml)]

    problems: list[str] = []
    for x0, y0, x1, y1, t in words:
        if x0 < -0.5 or x1 > pw + 0.5 or y0 < -0.5 or y1 > ph + 0.5:
            problems.append(f"text leaves the canvas: {t!r} spans "
                            f"x[{x0:.1f},{x1:.1f}] on a {pw:.1f}pt page")
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > gap_pt and oy > gap_pt:
                problems.append(f"text overlaps text: {a[4]!r} / {b[4]!r} "
                                f"({ox:.1f} x {oy:.1f} pt)")
    return problems


def verify_pdf(path: Path, expect_width_in: float, tol_pt: float = 0.75) -> list[str]:
    """Post-build submission checks. Returns a list of problems (empty == clean).

    Checks the three things that cannot be seen by looking at the figure: the
    page width (hence the LaTeX scale factor), the embedded font types, and
    whether any text is clipped or overprinted.
    """
    import re
    import subprocess

    problems: list[str] = []
    try:
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True).stdout
        m = re.search(r"Page size:\s+([\d.]+) x ([\d.]+) pts", info)
        if m:
            got_pt = float(m.group(1))
            want_pt = expect_width_in * 72.0
            if abs(got_pt - want_pt) > tol_pt:
                problems.append(
                    f"page width {got_pt:.1f}pt != expected {want_pt:.1f}pt "
                    f"(LaTeX would rescale by {want_pt / got_pt:.3f}x)"
                )
        else:
            problems.append("could not read page size from pdfinfo")
    except FileNotFoundError:
        problems.append("pdfinfo not available; page-size check skipped")

    try:
        fonts = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True).stdout
        for line in fonts.splitlines()[2:]:
            if not line.strip():
                continue
            fields = line.split()
            if "Type 3" in line:
                problems.append(f"Type 3 font embedded: {fields[0]}")
            # columns: name type encoding emb sub uni objID gen
            if len(fields) >= 6 and fields[-3] == "no":
                problems.append(f"font not embedded: {fields[0]}")
    except FileNotFoundError:
        problems.append("pdffonts not available; font-type check skipped")

    problems.extend(scan_text(path))
    return problems
