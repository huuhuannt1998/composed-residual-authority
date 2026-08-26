# Anonymizing the artifact for review

The S&P 2027 call requires that an artifact repository, **and the account
hosting it**, not identify authors or institutions. It also freezes artifacts at
the submission deadline — no updates afterwards.

`github.com/huuhuannt1998/composed-residual-authority` **cannot serve as the
review link**: the account name matches the author's identity. A separate
anonymized mirror is needed (Anonymous GitHub or GitFront).

## Fixed already

- [x] **Hardcoded session paths removed.** `p1e15_scope_sweep.sh` and
      `run_version_study.sh` embedded
      `/private/tmp/.../-Users-huanbui-Research-TenantSafe-P11/...` and
      `/Users/huanbui/...`. Both were a username leak *and* a portability bug —
      the scripts could not run anywhere else. Now driven by `ALLOY_TOOLS_DIR`
      and `TS_WORKDIR`, with a clear failure message when unset.
- [x] **No remaining username or absolute-path leaks** in any tracked `.sh`,
      `.py`, `.als` or `.spthy`.

## Must be handled before the mirror is published

- [ ] **Sibling-project names.** `models/tenantsafe_base.spthy`,
      `models/tenantsafe_channels.als`, `EXPERIMENTS.md` and
      `research_design_detailed.md` name **FABRICPROOF** and carry its internal
      project id. The reference is scientifically real — the persistent-versus-
      linear fact discipline was genuinely inherited — so **do not delete it**;
      that would misrepresent provenance. Neutralize the name instead: "a
      sibling project at the Matter protocol layer". Strip the `prj_…` ids,
      which carry no meaning outside our own knowledge base.
- [ ] **Repository and branch naming.** Do not reuse the `NAME-P<number>`
      convention visible across the sibling directories (`FABRICPROOF-P2`,
      `HOMEPROV-P13`, …). The numbering is itself a fingerprint linking the
      submission to every other project under the same account.
- [ ] **Commit metadata.** Author name and email are in the git history. Either
      publish the mirror without history, or rewrite it with a neutral identity.
      A fresh single commit is simpler and safer.
- [ ] **RKA identifiers.** `jrn_`, `dec_`, `clm_`, `man_` ids appear throughout
      the tracking documents. They do not identify a person, but they do reveal
      internal tooling. Harmless; noted so the decision is deliberate.

## Deliberately left alone

- **`@gmail` inside `coding/snapshots/*.html`.** These are archived *vendor*
  documentation pages; the string belongs to the vendor's own content, not to
  us. Editing them would corrupt the frozen corpus and break the SHA-256
  verification that makes the documentation study reproducible. The corpus must
  stay byte-identical to what was retrieved.

## Before publishing the mirror, re-run

```bash
grep -rlniE 'huuhuannt|huanbui|@gmail|/Users/|FABRICPROOF|HOMEPROV|-P[0-9]+' . \
  --exclude-dir=.git --exclude-dir=snapshots
```

Expect: no hits outside `coding/snapshots/`.
