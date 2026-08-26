# IEEE S&P 2027 submission readiness

Audited against <https://sp2027.ieee-security.org/cfpapers.html> on 2026-08-25.

**Short answer: the manuscript is not done.** The formatting was
non-compliant in a way that risks rejection without review, which is now fixed.
What remains is not writing — it is four author-side policy obligations, one of
which is a standing PI decision that the CFP treats as mandatory.

---

## 1. Deadline

Cycle 1 (paper due 2026-06-11) has passed. The live target is **cycle 2**:

| Milestone | Date |
|---|---|
| Abstract registration | **2026-11-10** |
| Paper submission | **2026-11-17** |
| Reviews released | 2027-02-11 |
| Rebuttal due | 2027-02-16 |
| Notification | 2027-03-05 |

All deadlines 23:59:59 AoE. ~11 weeks from today. The author list is frozen at
abstract registration, so authorship must be settled by 2026-11-10.

---

## 2. Formatting — was non-compliant, now fixed

| Requirement | Status |
|---|---|
| `\documentclass[conference,compsoc]{IEEEtran}` | ✅ **FIXED** — was `[conference]`, missing `compsoc` |
| IEEEtran.cls v1.8b | ✅ v1.8b (2015/08/26) |
| US letter, not A4 | ✅ 612 × 792 pt |
| No `usenix` package (overrides compsoc) | ✅ not present |
| Unmodified margins / fonts / spacing | ✅ no overrides in the preamble |
| Anonymized: no names, affiliations, acknowledgements | ✅ `Anonymous Submission`, no acknowledgements section |
| No full CVE identifiers | ✅ none present |

**The `compsoc` omission mattered.** The CFP states that papers modifying
margins, fonts or line spacing "face rejection without review". Building against
the wrong class variant produces exactly that class of deviation. It is fixed and
verified: `\ifCLASSOPTIONcompsoc` evaluates true against the real preamble.

---

## 3. Page budget — compliant, with no margin on the body

The rule is **13 pages of body, plus up to 5 for references and appendices, 18
total** — not 13 total, which is what the layout audit was enforcing.

| Measure | Value | Limit |
|---|---|---|
| Body pages | **13** | 13 |
| Appendices | A–E, p. 13 onward | — |
| Total pages | 15 | 18 |

The body sits exactly at the limit, so any addition to it must be paid for by a
deletion. The appendix headroom is now in use: three appendices carry the
session-condition arms, the openHAB per-trial data, and the residue-search
report, none of which competes with the body budget. Three pages of total
headroom remain.

Two tooling fixes were made so this stays honest: `manuscript.yaml` now records
the CFP URL and an 18-page total cap, and `check_body_pages.py` locates the
bibliography and asserts the body ends by page 13, since the layout audit
measures only the total.

---

## 4. Manuscript gates — all clean

| Gate | Result |
|---|---|
| Layout | 0 blocks, 1 warn (underfull spacing) |
| Body / total pages | 13 / 15 — PASS |
| Overfull boxes > 10pt | 0 |
| Undefined references / citations | 0 |
| Provenance | 0 blocks |
| AI-tic | 12/12 PASS |
| Prohibited wording | PASS |
| References | 44, all validated |

---

## 5. Four author obligations — none of these are writing tasks

### 5.1 Vulnerability disclosure — **the blocker**

The CFP is not advisory here: *"Vulnerabilities must be disclosed by the rebuttal
deadline. If impossible, authors must notify PC chairs with justification and a
disclosure plan."*

The Home Assistant finding has not been disclosed, by PI decision. The paper
states this plainly rather than concealing it. Under the CFP that leaves exactly
two compliant paths, and doing neither is an ethics-grounds rejection risk:

1. **Disclose before the rebuttal deadline** (2027-02-16). The report is written
   and held at `disclosure/home-assistant-2026-08-23.md`. Disclosure at
   submission time would also let the paper report vendor response, which
   strengthens it.
2. **Notify the PC chairs at submission** with the justification and a
   disclosure plan.

This is a PI decision, not something I should resolve. It is the single largest
open risk to the submission.

### 5.2 Generative AI disclosure — mandatory, desk-rejection risk

The CFP requires disclosure in the HotCRP "Generative AI usage considerations"
field, and non-compliance carries desk rejection plus a possible multi-year
submission ban.

**This work used generative AI extensively** — drafting, experiment
implementation, analysis, and this audit. That must be disclosed accurately, and
the CFP asks specifically for: confirmation that outputs were inspected for
accuracy and originality; that model-generated ideas were independently
developed and validated; and how the resulting limitations were addressed. The
project has real material for the second and third: every empirical claim traces
to a runnable experiment with recorded controls, several model-generated results
were refuted by those experiments and recorded as supersessions rather than
quietly dropped, and the instrument bugs that were caught by their own controls
are documented.

### 5.3 ORCID — desk rejection if missing

Every author needs an ORCID at abstract registration, with the ORCID email
matching the HotCRP email and the ORCID name matching the author list exactly.

### 5.4 Conflicts of interest

Declared per PC member across co-authorship, shared institution or employer
within two years, collaboration or funding within two years, advising
relationships, and personal relationships. The CFP states that incorrect or
incomplete COI leads to immediate rejection.

---

## 6. Two content items still open

- **Residual lifetime run** — in progress, intact at +2 h; reaches +6 h then the
  termination events. Supplies Table D.
- **Independent second coder** — needs a second human analyst. Everything around
  it is ready and the paper labels the current figure intra-rater, which is
  accurate.

## 7. Recommended before submission

- If an artifact repository is submitted, anonymize it via Anonymous GitHub or
  GitFront; the CFP requires the repository and account names not to identify
  authors, and artifacts cannot be updated after the deadline.
- ~~Add a dedicated Ethics Considerations section~~ — **done**, Appendix E. It
  covers the four areas the CFP names: human subjects (none), live and
  third-party systems (none touched), disclosure status, and the misuse
  potential of the released tools. §10 now points to it rather than duplicating
  it, which also returned space to the body.
