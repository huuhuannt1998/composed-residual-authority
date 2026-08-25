# Determinacy Codebook (E1.9)

Applied to each `(platform, transition)` cell. Coder sees the harvested EVIDENCE
for the cell, not any prior label.

**DETERMINED (D)** — documentation states what happens to authority-relevant state
across this transition, such that two competent engineers would implement the same
behaviour. Documented residues still count as D: the platform has *said* what happens.

**CONTINGENT (C)** — the transition IS addressed, but a specific authority-relevant
consequence is NOT, AND the two plausible readings give DIFFERENT authority outcomes.

**SILENT (S)** — the documentation does not address this transition for this platform
at all.

**C vs S is the hard boundary.** C requires the transition to be documented while a
consequence that flips an outcome is missing. S is total absence. When a cell documents
the transition but omits a consequence, code C — *even if the documented part is
detailed*. Detail about one consequence does not determine a different one.
