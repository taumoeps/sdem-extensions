# sdem-security — changelog

All made-up data. Rule ids: the [security aspect spec](docs/security-aspect-spec.md) (SEC-…), the [audit](docs/audit-2026-11-19.md) (AUD-…),
SDEM's [metamodel extensions](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-metamodel-extensions-spec.md) (MX-…) and
[extension lifecycle](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-extension-lifecycle-spec.md) (EL-…) specs.

## 0.4.3 — 2026-11-22

- **Each link type says its ArchiMate kind** (SDEM MID-07, SDEM 0.21.3): PROTECTS is an *association*, ENFORCED_BY a *realization*, THREATENS an *influence*, BOUNDS an *aggregation* (`"archimate"` on each of the 45 link types); tested.

## 0.4.2 — 2026-11-22

- **How it is drawn, declared** (SDEM MID-09): the manifest's `viewer.overlay` says which design layer each of S1–S5 overlays, how each of its types is drawn and placed (beside, below, or round what it links to) and how each link is drawn — so a viewer draws it with no code written for it.

## 0.4.1 — 2026-11-22

- **Protection inherited from a protected whole is said** (SDEM MID-02): `sdem security coverage` gives `inherited_from` — the whole (an interface, a service domain, a zone) whose control covers a record with none of its own, climbing composition and aggregation. Said beside `protected`, never counted as a control of the record's own; a view shows it instead of working it out.

## 0.4.0 — 2026-11-22

- **Every security layer is checked** (SX-12). Seven new rules, each a warning with its NIST control and CSF reference: a critical business process has a control (S1, SEC-S09); a service domain has a control (S2, SEC-S10 — computed, and only where BIAN is on); an application records the data it uses (S3, SEC-S11, CM-12) and personal data states its retention (SEC-S12, SI-12); an internet-facing interface has a control (S4, SEC-S13) and an application states its recovery time and point (SEC-S14, CP-9); system software states when its support ends (S5, SEC-S15, SA-22). On the Payment example they find the two applications that record no data they use.
- **Supports SDEM's metamodel 0.19.0** (the Data Architecture). SEC-S11 is computed by `sdem security review`, so it reads a design's access links in either form.
- **A control may name other standards it meets** (SX-13): `also_satisfies` — ISO/IEC 27001, APRA CPS 234, PCI DSS or OWASP ASVS clauses, by reference only.
- Tested with SDEM's fixes of 2026-11-22: a control's trace is the trace of what it protects (FT-09), and impact names a linked control as directly affected (KG-Q-09).

## 0.3.2 — 2026-11-22

- **Each record says its layer as the design numbers it** (SDEM's XA-10): the JSON of review, coverage and threats gives every record a `design_layer` — its stable layer (business, bian, data, application, technology) and the number and name this design uses (with BIAN, Technology is A5) — and a `numbering` note. The fields it had (`layer`, the types) stay, in the numbering security's rules are written in. The DESNRE agent had labelled two A5 communication paths A4 while translating those numbers itself; the guide now tells it to quote `design_layer`.
- `--workspace .` works on a workspace in SDEM 0.20's form (its 0.19 copy was given an empty folder name).

## 0.3.1 — 2026-11-22

- **The AI agent's guide is the extension's own** (SDEM's XA-02, XA-07): `agent_guide` in the manifest says what layer S, its links and its reports mean — what the DESNRE site's agent was told in code written for security alone. It names no layer numbers, so it reads the same with or without BIAN. Its reports (review, coverage, threats, document) were already in the manifest; the publisher now runs them from there (XA-01, XA-03).

## 0.3.0 — 2026-11-21 (with SDEM 0.20.0)

- **A workspace in SDEM 0.20's form** (SDEM's DL-22). Coverage, threats, review and the document read it as 0.19 held it — the copy SDEM writes with `export_019` (Data's records in the Application file, each approved `ACCESSED_BY` as access), proven record by record by SDEM's P2 — the form these rules are written in; records keep their ids, so security's own links hold. Switching security on and off, restoring, purging and proposing go through SDEM's commands on the workspace itself, as before.
- **A design without BIAN** (A1 Business, A2 Data, A3 Application, A4 Technology) is never told its BIAN security layer (S2) is empty.
- CI also runs against SDEM `release/0.20`; on SDEM 0.19 nothing changes (the 0.20 test is skipped there).
- **Security with or without BIAN** (SDEM 0.20 step 1, BX-50, BX-51): its six link types to BIAN's A2 types (PROTECTS and THREATENS to service domains, control records, business objects) require `ext:bian`. On a core-only design they are left out — and `sdem profile show` says so — and security covers S1, S3, S4, S5 (S2 empty, said so by SEC-LAYER); with BIAN on, as before.

## 0.2.1 — 2026-11-19

- **Inheritance in scope (MX-32a).** A type another extension or a profile adds inside a layer (e.g. a network extension's firewall,
  extending `A4.Node`) is placed by its nearest SDEM type: in coverage, the STRIDE checklist, SEC-S08 and the "no control" list.
  SDEM's own types still match exactly — an artifact is not widened to infrastructure.
- **The manifest says what it builds on (MX-41):** `builds_on` (the SDEM types, attributes and link kinds it names), `enhances`,
  and `protected_means` — also in `coverage --json` (MX-25).
- **The catalogue's source is pinned (MX-29, AUD-20)** to NIST OSCAL commit `5006f18`, whose file matches the recorded sha256.
- **Catalogue search by id (AUD-08):** `sdem security catalogue "IA-2(1)"` finds the enhancement.
- **The version check (AUD-09):** reads `>=`, `>`, `<=`, `<`, `==`; an unreadable range or SDEM version refuses instead of passing;
  no SDEM installed is a message, not a traceback; `catalogue` needs no SDEM.
- **The review document (AUD-11):** a record's name cannot make a heading, list item, table row or HTML; escaped once.
- **Tests:** each change, and the standard's rules shown firing (SEC-S05a, SEC-S05b, SEC-S06b) — not only present.

## 0.2.0 — 2026-11-19

The extension lifecycle (EL-01, EL-04…EL-06, EL-16): `restore` and `purge`; the manifest's `viewer`; `remove` and `restore` say what
the DESNRE site will do. With sdem-desnre 0.8.0 the design's state (on/off, since, by, why) is published.

## 0.1.3 — 2026-11-19

The audit's P0 fixes (AUD-01…AUD-07, AUD-10, AUD-12, AUD-16…AUD-18, AUD-24…AUD-32): `remove`; computed checks unresolved when not
decidable and exceptable (MX-17); only controls that can act count; one scope from the pack; S07 skips superseded requirements;
S08 reaches fields and API operations; `review` never reports an all-clear it cannot vouch for.

## 0.1.2, 0.1.1, 0.1.0 — 2026-11-18…19

`sdem security document`; SEC-S03b, SEC-S06b, SEC-S07, SEC-S08; S2 in the example; the first release — layer S (S1–S5),
NIST SP 800-53 Rev. 5 catalogue, STRIDE, the security standard, `catalogue`, `coverage`, `threats`, `review`, `propose`.
