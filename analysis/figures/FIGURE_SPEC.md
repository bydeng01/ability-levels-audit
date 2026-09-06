# Figure requirements

## Text load

- Measure before cutting: `pdftotext -bbox` → word-boxes, glyphs, text-ink %,
  words per square inch. Compare panels against each other.
- Cut anything the caption, or the sentence beside the figure, already states.
  Keep anything only recoverable from the drawing: ratios, counts, `k`.
- Retighten axis limits after a cut; a vacated band must not read as blank paper.
- A denominator or unit repeated on every row belongs in the caption once.

## Terminology

- Figure strings use the body's vocabulary. Census them against the body before
  shipping; a word the body never uses does not belong on the page.
- Panel titles must not outrun the body's own hedge.

## Palette

- One meaning per hue, constant across every figure in the paper.
- Never reuse a hue that already carries a meaning as a generic accent.

## Encoding

- Jitter goes on the categorical axis, never the measured one.
- A reference band computed from one subgroup must not be drawn under another.
- Value labels sit at their own value, or are omitted.
- One visual token (grey band, marker fill, dash pattern) must not mean two
  things, within a figure or across figures.
- Every mark must be decodable from the figure plus its caption alone.
- Size titles and labels from measured string widths, not character counts.

## Caption

- Lead with the take-away. Status and scope second, stated once for all panels.
- Sentence case, not Title Case.
- Caption after the figure; never set caption spacing by hand.
- Match the body's dash and hyphenation style.
- After a cut, the clauses that became the sole source of a fact are untouchable.

## Build and compliance

- Author the canvas at exactly the width it is included at. Never crop to
  content on save.
- No Type 3 fonts; embed everything.
- Legible in greyscale: hue must be redundant with position. Check it, don't
  assume it.
- Compile-test every caption change and confirm the page count did not move.
- Diff rendered images, not file hashes; plot libraries stamp timestamps.
- Re-run the data selftest after any change. Treat every edit as encoding-only
  until the numbers prove otherwise.
