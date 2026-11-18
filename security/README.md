# sdem-security — the security architecture, as an SDEM metamodel extension

Adds a **security architecture** to an SDEM workspace — controls, threats and trust boundaries in five security layers,
**S1 Business · S2 Service Domain · S3 Data · S4 Application · S5 Technology**, the security views of A1, A2, A3 (data),
A3 (application) and A4 — without changing A1–A4. Install it, switch it on in a workspace, take it off again.

Built on public sources only: **NIST SP 800-53 Rev. 5** controls (the catalogue ids, titles and families ship in
`sdem_security/catalogue.json`, from NIST's OSCAL file — public domain), **NIST CSF 2.0** functions and categories (ids only),
**STRIDE** threat categories and **NIST SP 800-207** (Zero Trust) for trust boundaries. Spec: [`docs/security-aspect-spec.md`](docs/security-aspect-spec.md). Audit for review: [`docs/audit-2026-11-19.md`](docs/audit-2026-11-19.md) — 23 findings; the P0 ones are fixed in 0.1.3 (see its status column).

## What you get, and from where

Security in SDEM is four parts. This package is the first; the others are installed or released separately.

| Part | What it adds | How you get it |
|---|---|---|
| **sdem-security** (this package, 0.2.0) | layer S and its record and link types; the security standard (SEC-S01a…S06b) and its own checks (SEC-S07, SEC-S08, SEC-LAYER); the NIST SP 800-53 catalogue; the commands `catalogue`, `coverage`, `threats`, `review`, `document`, `propose`, `remove`, `restore`, `purge` | below |
| **SDEM** 0.19.0 | metamodel extensions: a layer across the stack (LR-11), `ext:` packs, switching one off (`sdem profile exclude`, MX-16), exceptions to an extension's own checks (MX-17), the security layer's document (`sdem document --layer S`) | `pip install "git+https://github.com/taumoeps/bian-sdem-framework@v0.19.0"` |
| **sdem-desnre** 0.8.0 (the DESNRE publisher) | publishes the design with its security layer and this extension's results — review, coverage, STRIDE checklist and the review document — with no local folder paths | `pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=desnre"` |
| **The DESNRE site and its AI agent** | the 3D *Security* view (S1–S5; controls and threats in red); the Security tab (tiles per S-layer, records, figures, Document Output with the layer document and the review); security in Health, Metamodel, Connections and Document Output; the agent's `security_review` tool, and a 9.7 *Security architecture* section (with threats in 5 and SDEM's findings in 10) in the design document it writes | live at desnre.vercel.app — nothing to install; it shows security for a design published with sdem-security and desnre 0.8.0 installed |

The site shows the extension's results as they were when the design was last published: publish again after the security design changes.

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
sdem security remove   --workspace <ws> --person <you> --reason "…"   # switch it off again — archived, not lost (below)
sdem security restore  --archive archive/ext-security-<date>.json --workspace <ws> --person <you> --reason "…"   # back on, from the archive
sdem security purge    --workspace <ws> --person <you> --reason "…" --dry-run   # delete the archived data — never the default
sdem trace SEC-SC28 --graph <graph>                      # trace and impact follow the security links like any other
```

Record types `SEC.S.SecurityControl`, `SEC.S.Threat`, `SEC.S.TrustBoundary`; links into A1–A4 `PROTECTS`, `ENFORCED_BY`,
`THREATENS`, `BOUNDS` (approved by a person, with evidence), and `mitigates` (control → threat). The security standard's eight
rules (SEC-S01a…SEC-S06b) run in `sdem comply` as warnings, and `review` adds three checks of its own (SEC-S07, SEC-S08,
SEC-LAYER) — a person can grant an exception to any of them (`sdem exception grant --rule SEC-S08 …`). Switching security on never
stops a design's work.

A worked, made-up example for SDEM's `payment-initiation-v3`: [`examples/payment-initiation-v3/`](examples/payment-initiation-v3/).

## The whole life — on this machine, in the workspace, on DESNRE

Every step is a person's, and says what it does on each side ([extension lifecycle spec](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-extension-lifecycle-spec.md), EL-01…EL-17):

| Step | In the workspace | On the DESNRE site |
|---|---|---|
| install (`pip install`) | nothing yet | nothing yet |
| switch on (`sdem profile include ext:security`, `adopt`) | layer S starts, a recorded decision | after the next publish: Security shown |
| **remove** | the layer, its connections and exceptions **archived** — nothing deleted | after the next publish: Security hidden, and the site **says** it was switched off, when, by whom and why |
| **restore** | back from the archive, the same link ids | after the next publish: Security shown again |
| **purge** | the archive deleted (ids stay retired) — never the default | the next publish asks the site to remove security from its previous version and document history |
| uninstall (`pip uninstall`) | no data touched; a workspace still including it is refused | unchanged |

Nothing changes on the site without a publish, and publishing is always your step.

## Remove

```
sdem security remove --workspace <ws> --person <you> --reason "…" --dry-run      # then without --dry-run
```

A person's decision, recorded. SDEM takes `ext:security` out of the profile and keeps the security layer and every connection that
touches it, whole, in `archive/ext-security-<date>.json`; their link ids are never given again. The design passes its checks
afterwards. (Needs SDEM 0.19.0 as tagged on 2026-11-19 or later — `sdem profile exclude`, MX-16.) Do not delete `security.json` by hand: its connections would
be left behind. Uninstalling the package while a workspace still includes it makes SDEM refuse that workspace with a message naming
it — never check it as if its security records were not there.
