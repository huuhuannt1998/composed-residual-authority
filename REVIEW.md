# Adversarial Review — TENANTSAFE

Target: IEEE S&P · 7pp of 13 · reviewed 2026-08-24
Reviewer stance: hostile-but-fair PC member. This reviews my own draft; findings are
weighted toward what a reviewer would reject on, not what is already good.

> **STATUS 2026-08-24 — C1, C3 and C5 are FIXED.** §2 now cites five
> authentication-verification works (two surveys plus three schemes, each with its
> verification method named); §4 carries a subsection distinguishing the residue
> from HRU safety; §8 reports the false-positive experiment (10/10 legitimate
> operations succeed in both arms). References 9 → 14, 13 of 14 RKA-VERIFIED.
> **C2 and C4 remain open.**

## Readiness judgment

**NOT ready to submit** (C2, C4 open). The technical core is sound and unusually well evidenced for
a paper this early, but the scholarly apparatus is not at venue standard and one
positioning claim is currently unsupported by any citation. Estimated 2–3 weeks of work.

## Strongest version of this paper

A transition calculus makes "was authority actually extinguished?" a checkable question,
and applying it to a shipping platform finds a residue that is *composed*: a deleted
user's surviving session plus a household automation together reach device actuation
that neither reaches alone, with nothing in the authorization state naming the removed
person. The remedy platforms implement inspects objects one at a time and therefore
cannot see it. A four-line fix closes it at 19 ns.

---

## CRITICAL

### C1. ~~The paper's central positioning claim has no supporting citation~~ — FIXED
**Evidence.** §2: "A reader searching for formal verification of smart homes will
surface a substantial body of work... That literature verifies *authentication*:
session-key establishment and mutual identification" — cited to `meier2013tamarin`,
which is the **Tamarin tool paper**, not smart-home authentication work.

**Why it matters.** The identification-versus-authority disambiguation is the paper's
primary defense against "this overlaps existing formal smart-home work." The outline
made landing it a binding commitment. As written, the paper characterizes a literature
it never cites, and supports that characterization with a citation that is about
something else. A reviewer who works in that area will read this as either careless or
as evidence the authors have not read the field. It is the single most likely cause of
rejection.

**Fix.** Cite 6–10 actual smart-home authentication-verification papers (AVISPA-checked
schemes, Real-or-Random proofs, BAN-logic analyses) and, for at least two, state in one
clause what each proves. The claim "none proves properties of authority" must be
supported by naming the works it ranges over.

### C2. Fourteen references is still below venue norm — PARTLY ADDRESSED
**Evidence.** `refs.bib` has 9 entries. §§6–11 contain **zero** citations.

**Why it matters.** IEEE S&P papers typically carry 40–60 references. Nine signals an
unfinished literature review regardless of the technical content, and Results,
Discussion and Limitations making comparative claims with no citations invites
"unsupported" on each.

**Fix.** Target 35–50. Minimum additions: smart-home authentication verification (C1);
capability and token revocation (OAuth revocation, capability-revocation literature);
HRU follow-on safety results (take-grant, typed access matrix, SPM); IoT access control
surveys; technology-facilitated-abuse work beyond the two cited; Matter/CSA
specification; Alloy and TLA+ applications in security.

### C3. ~~Novelty collision with HRU safety is unaddressed~~ — FIXED
**Evidence.** §4 defines the authority residue and cites `harrison1976protection` only
for undecidability.

**Why it matters.** HRU safety asks whether a right can leak to a subject that does not
have it. A reviewer will say the residue is HRU safety renamed, and the paper never
argues otherwise. This is the most dangerous novelty objection because it is superficially
correct.

**Fix.** Add a paragraph in §4 distinguishing them explicitly. The available argument:
HRU safety quantifies over reachable *command sequences* in a single access matrix;
the residue quantifies over reachable *traces after a designated transition*, and its
objects (sessions, automations, bindings) are not access-matrix cells at all. State
what the residue can express that HRU safety cannot, or concede the relationship and
claim the contribution as instantiation rather than formulation.

### C4. Zero figures
**Evidence.** 3 tables, 0 figures, 7 of 13 pages used.

**Why it matters.** The composed-residue mechanism is a structural argument that is hard
to hold in prose. Reviewers skim figures first. Four were planned and none exist.

**Fix.** At minimum: (a) the two-path asymmetry (service call re-resolves; read and admin
paths trust the captured object), and (b) the deputy path as a sequence diagram showing
the event crossing from the removed principal to the automation's context. These two
carry most of the paper.

### C5. ~~The monitor is never tested for false positives~~ — FIXED
**Evidence.** §8 reports closure of both residues and a per-decision cost. There is no
experiment showing TSMON leaves legitimate operation intact.

**Why it matters.** A reference monitor that denies too much is useless, and a reviewer
will ask immediately. "It closes the attack" without "it does not break normal use" is
half an evaluation. This is the most concrete missing experiment in the paper.

**Fix.** Run the executability workloads through the patched instance: onboard a member,
grant access, actuate as a current member, deactivate, remove. Report that every
legitimate workflow still succeeds, with counts. This is a few hours' work using the
existing harness and it converts a one-sided result into a proper evaluation.

---

## MAJOR

### M1. The headline result is N=1
One platform, one version. Stated honestly in §10, but the abstract and title generalize
to "smart-home transitions." Either soften the framing or add a second platform where
source is available.

### M2. Determinacy coding is single-analyst
κ=0.923 is test-retest. §6 says so. A reviewer will still discount the determinacy
contribution. A second coder on 24 cells is a day of work and removes the objection.

### M3. Tamarin intractability is presented as a finding
§5 reports that the base model did not terminate in Tamarin and did in Alloy. A reviewer
may read this as "the authors could not write a good Tamarin model." Either strengthen
the structural argument (no cryptographic content to anchor constraint solving) with a
citation, or demote it to a footnote and keep the tool split as a design choice.

### M4. No disclosure, at a venue that asks
§10 states plainly that the finding was not disclosed. That honesty is correct and should
stay. Be aware it is a live rejection risk at IEEE S&P specifically, and the PC may
require disclosure before acceptance.

### M5. Three of four platforms are never observed
The determinacy result rests on documentation for Google Home, Alexa and SmartThings.
The paper is explicit, but the contribution is weaker than the abstract's framing implies.

---

## MINOR

- One overfull hbox, two underfull boxes.
- Abstract is ~330 words; S&P convention is closer to 200–250.
- `zeng2019multiuser` cannot pass DOI-based validation (USENIX registers no DOIs). Keep
  the citation; the gate exception is documented.
- Table 2 (`tab:survives`) would read better with the two blocked rows visually separated
  from the five surviving ones.

---

## Decisive experiment to add (priority order)

1. **Monitor false-positive check** (C5). RQ: does TSMON deny any legitimate operation?
   Workloads: the five executability workflows. Metric: success rate per workflow, patched
   vs unpatched. Expected: 5/5 both. Supports: "closes the residue without breaking normal
   use." Cannot support: absence of false positives outside the tested workflows.
2. **Second coder** (M2). 24 cells, independent, report inter-rater κ.
3. **Second platform at L3** (M1). Home Assistant is the only open one; consider openHAB
   or Domoticz to test whether the read/write asymmetry generalizes.

## Revision checklist

- [x] C1 cite the authentication-verification literature the paper characterizes
- [~] C2 references 9 → 14; target 35–50
- [x] C3 distinguish the residue from HRU safety explicitly
- [ ] C4 add the two load-bearing figures
- [x] C5 run and report the monitor false-positive experiment
- [ ] M2 second coder for determinacy
- [ ] M3 soften or support the Tamarin claim
- [ ] Minor: abstract length, box warnings, table layout
