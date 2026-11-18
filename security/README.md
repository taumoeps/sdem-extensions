# sdem-security — the security architecture, as an SDEM metamodel extension

Adds a **security architecture** to an SDEM workspace — controls, threats and trust boundaries in five security layers,
**S1 Business · S2 Service Domain · S3 Data · S4 Application · S5 Technology**, the security views of A1, A2, A3 (data),
A3 (application) and A4 — without changing A1–A4. Install it, switch it on in a workspace, take it off again.

Built on public sources only: **NIST SP 800-53 Rev. 5** controls (the catalogue ids, titles and families ship in
`sdem_security/catalogue.json`, from NIST's OSCAL file — public domain), **NIST CSF 2.0** functions and categories (ids only),
**STRIDE** threat categories and **NIST SP 800-207** (Zero Trust) for trust boundaries. Spec: [`docs/security-aspect-spec.md`](docs/security-aspect-spec.md). Audit for review: [`docs/audit-2026-11-19.md`](docs/audit-2026-11-19.md) — 23 findings, not yet fixed.

## Install and switch on

```
pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=security"      # into SDEM's environment (SDEM 0.19 or later)
sdem profile include ext:security --workspace <ws> --person <you> --reason "security design"   # a person's decision, recorded
sdem profile adopt   --workspace <ws> --person <you> --reason "the security layer"             # adds security.json
```

## Use

```
sdem security catalogue at rest                          # find a NIST control: SC-28 Protection of Information at Rest
sdem security propose design.json --workspace <ws> --person <you> --dry-run     # controls, threats, boundaries — a change set
sdem connect SEC-SC28 PROTECTS DATA-CONSENT --workspace <ws> --person <you> --evidence design_document:<ref>
sdem security coverage --workspace <ws>                  # per record: its controls, what enforces them, its threats — by S1–S5
sdem security threats  --workspace <ws>                  # a STRIDE checklist per record — prompts for a person, never records
sdem security review   --workspace <ws>                  # what the security design still lacks, weakest first
sdem security document --workspace <ws> [-o review.md]   # the review as a document: findings, coverage per S1–S5, threats, the STRIDE checklist
sdem trace SEC-SC28 --graph <graph>                      # trace and impact follow the security links like any other
```

Record types `SEC.S.SecurityControl`, `SEC.S.Threat`, `SEC.S.TrustBoundary`; links into A1–A4 `PROTECTS`, `ENFORCED_BY`,
`THREATENS`, `BOUNDS` (approved by a person, with evidence), and `mitigates` (control → threat). The security standard's eight
rules run in `sdem comply` as warnings — switching security on never stops a design's work.

A worked, made-up example for SDEM's `payment-initiation-v3`: [`examples/payment-initiation-v3/`](examples/payment-initiation-v3/).

## Remove

Take `ext:security` out of the workspace's `sdem-profile.json` (and its `security.json`), or `pip uninstall sdem-security` —
a workspace that still includes it is then refused with a message naming it, never checked as if its security records were not there.
