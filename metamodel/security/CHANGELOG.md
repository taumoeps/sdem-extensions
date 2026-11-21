# sdem-security — changelog

All made-up data. Rule ids: the [security aspect spec](docs/security-aspect-spec.md) (SEC-…), the [audit](docs/audit-2026-11-19.md) (AUD-…),
SDEM's [metamodel extensions](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-metamodel-extensions-spec.md) (MX-…) and
[extension lifecycle](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-extension-lifecycle-spec.md) (EL-…) specs.

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
