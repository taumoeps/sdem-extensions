# The security aspect — `sdem-security` (spec)

> **Status: approved (2026-11-18) — the owner approved SX-D1…SX-D6 as recommended, with S1–S5 and a Security 3D stack; being built.** The first metamodel extension
> ([SDEM metamodel extensions spec](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-metamodel-extensions-spec.md), MX-01…MX-15).
> It adds a **security architecture** in five layers, **S1–S5**, each the security view of one Architecture plate (A1, A2, A3-1, A3-2, A4) —
> without changing A1–A4; installed, it can be removed again (MX-03, MX-10). The owner's structure, 2026-11-18. Frameworks agreed with the owner, 2026-11-18 (§2). Made-up data only in its examples.

## 1. What it answers

For any design: **what must be protected, against what, by which controls, enforced where, and with what evidence** — and what is not yet protected. One dataset, so the Design document, the 3D view, `sdem comply` and the agent all say the same.

## 2. Frameworks — method, notation, content

| Role | Framework | How it is used | Licence (checked 2026-11-18) |
|---|---|---|---|
| Method | **TOGAF** (security in the ADM) | where security work sits in the design document (requirements, risks, controls per layer) — referenced, not copied | The Open Group — cited only |
| Notation | **ArchiMate** risk and security modelling | each type is drawn as an ArchiMate element (§3); SDEM already uses ArchiMate names | The Open Group — element names only |
| Outcomes | **NIST CSF 2.0** (CSWP 29, 2024) | every control carries its CSF function — Govern, Identify, Protect, Detect, Respond, Recover — and may carry a category (e.g. `PR.AA`) | NIST publication; identifiers and short names only are shipped |
| Controls | **NIST SP 800-53 Rev. 5**, from NIST's OSCAL catalogue | the reference catalogue a control is chosen from, by id (`IA-2`, `SC-8`, `SC-28`) | OSCAL content: *"in the public domain within the United States … we waive copyright and related rights in the work worldwide … even for commercial purposes"* ([usnistgov/oscal-content, LICENSE.md](https://github.com/usnistgov/oscal-content/blob/main/LICENSE.md)) |
| Trust | **NIST SP 800-207** Zero Trust Architecture | trust boundaries and where policy is enforced (§3, `SEC.S.TrustBoundary`) | NIST publication; concepts only |
| Threats | **STRIDE** | each threat's category: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege | a published method; category names only |
| Optional | MITRE ATT&CK (technique ids on a threat), OWASP ASVS (an A3 level) | an attribute that cites an id; nothing shipped | cited only |
| Not used | SABSA, ISO/IEC 27001 Annex A text, CIS Controls | may be cited by identifier in `evidence`, never reproduced | proprietary or restricted |

> As built in SDEM (2026-11-18): the security architecture is a profile layer placed **across** the stack (LR-11), shipped as this extension's pack and switched on with `sdem profile include ext:security`. Links use ArchiMate kinds SDEM knows.

## 3. Record types (layer `S`, across the stack — file `security.json`; types named `SEC.S.<Name>`, as profile layer types are)

| Type | ArchiMate | Required attributes | Optional attributes |
|---|---|---|---|
| **SEC.S.SecurityControl** — a measure that protects something | Requirement (a control measure) | `security_layer` (S1–S5), `control_id` (an SP 800-53 id, e.g. `SC-28`, checked against the catalogue), `csf_function` (GV · ID · PR · DE · RS · RC), `control_kind` (preventive · detective · corrective), `implementation_status` (planned · partial · implemented · not_applicable) | `csf_category` (e.g. `PR.DS`), `requirements` (ids in `requirements.json` it meets), `evidence` (`kind:reference`, needed before `implemented`), `owner` |
| **SEC.S.Threat** — what could go wrong to what | Assessment | `security_layer` (S1–S5), `stride` (one or more of S · T · R · I · D · E), `likelihood`, `impact` (low · medium · high) | `treatment` (mitigate · accept · transfer · avoid), `attack_ref` (ATT&CK id), `description` |
| **SEC.S.TrustBoundary** — where trust changes and policy is enforced | Grouping | `boundary_kind` (network · identity · tenant · process) | `enforcement` (what enforces it, e.g. an API gateway, mTLS) |

**Not new types — SDEM already holds them (used by the aspect's rules, §6):** information classification (`access_classification`, every record), personal data (`personal_information`, `retention_period` on `A3.DataEntity`), API authentication (`security_scheme` on `A3.ApplicationInterface`), network trust (`zone_kind`, `zone_level` on `A4.NetworkZone`; `internet_facing` on `A3.ApplicationInterface` and A4 infrastructure), transport protection (`protocol`, `encrypted` on `A4.Path`), and **security requirements** (category `security` in `requirements.json`). The aspect gives `access_classification` its values: `public · internal · confidential · restricted`.

## 4. Links

| Link | From → to | Meaning | ArchiMate | Evidence to approve |
|---|---|---|---|---|
| **PROTECTS** | SecurityControl → A1 process, business object · A2 service domain · A3 data entity, component, interface, API operation · A4 node, zone, path, system software, deployment | the control protects that record | association (directed) | a design reference (`design:` or `document:`) |
| **ENFORCED_BY** | SecurityControl → A3 component, interface · A4 node, system software, deployment | the record carries the control out (IA-2 by Identity; SC-12 by key custody) | realization (record realises the control) | a design reference; for `implemented`, an implementation reference (`config:`, `test:`) |
| **THREATENS** | Threat → any A1–A4 record | the threat applies to that record | association (threatens) | a design reference or a threat-model session (`review:`) |
| **MITIGATES** | SecurityControl → Threat (inside the aspect) | the control reduces the threat | association (mitigates) | — (inside the aspect) |
| **BOUNDS** | TrustBoundary → A4 network zone · A3 component, interface | the records inside the boundary | aggregation | a design reference |

Links into A1–A4 are proposed and approved like SDEM's own (`sdem link`, `sdem approve`), by a person (CTL-21). No inference in the first version (MX-D4): every record and link comes from a person or a source.

## 5. The five security layers (the owner's structure, 2026-11-18)

| Layer | Security view of | Holds |
|---|---|---|
| **S1 Business Security Architecture** | A1 | business risks, information classification, roles and separation of duties, consent and authorisation rules, security requirements |
| **S2 Service Domain Security Architecture** | A2 | which BIAN domains are security functions (Party Authentication, Fraud Evaluation); the protection each domain's control record and information need — stated before any application exists |
| **S3 Data Security Architecture** | A3-1 | classification per entity and field, personal data, retention, protection at rest, who reads and writes what |
| **S4 Application Security Architecture** | A3-2 | authentication and authorisation per interface and operation, input validation, sessions, audit events |
| **S5 Technology Security Architecture** | A4 | zones as trust boundaries, encryption on paths, keys and secrets, hardening, logging, backup and recovery |

**Every control and threat belongs to one security layer** — a required attribute `security_layer` (S1 … S5) on `SEC.S.SecurityControl` and `SEC.S.Threat`; a trust boundary is S5 (network) or S4 (identity, process, tenant). Its links still reach any layer: IA-2 sits in S4 and also **PROTECTS** the A1 process it guards — the lines down the stack are security running through the design.

### Per layer — typical controls and threats

| Layer | Typical controls (SP 800-53) | Typical threats (STRIDE) |
|---|---|---|
| A1 Business | AC-5 separation of duties (roles on processes), PM/RA risk governance, PT privacy | R — a customer denies a consent; E — a role acts beyond its duty |
| A2 BIAN | IA-2/IA-8 on Party Authentication; SI-4 monitoring on Fraud Evaluation | S — a party impersonated; T — a payment order altered |
| A3 Application | IA-2, AC-3, SC-8, SC-28, SI-10 input validation, AU-2/AU-12 audit events | S, T, I — on interfaces and data entities; R — no audit of an operation |
| A4 Technology | SC-7 boundary protection, SC-8 in transit, SC-12/SC-13 keys and cryptography, AU-9, CP-9/CP-10 backup and recovery | D — the edge flooded; I — a path unencrypted; T — keys exposed |

## 6. Standards (`sdem comply`) — shipped with the aspect

| Rule | Check | NIST |
|---|---|---|
| **SEC-S01** | Every data entity with `personal_information` is `confidential` or `restricted` (S01a), and is **PROTECTED** by at least one control (S01b); `sdem security review` names any without an SC-28 control (protection at rest) — SDEM's cross-layer rules check *every* linked record, so "one of them is SC-28" is the review's, not a rule's | SC-28 · PR.DS |
| **SEC-S02** | Every `internet_facing` interface has `security_scheme` `oauth2`, `openIdConnect` or `mutualTLS` | IA-2, IA-8 · PR.AA |
| **SEC-S03** | Every path has `encrypted: true` and a `protocol` (a path crossing zones: error; inside a zone: warning) | SC-8 · PR.DS |
| **SEC-S04** | Every DMZ (`zone_kind: dmz`, the internet edge) is **BOUNDED** by a trust boundary | SC-7 · PR.IR |
| **SEC-S05** | A control `implemented` has `evidence` and at least one **ENFORCED_BY** | CA-2 · ID.IM |
| **SEC-S06** | A threat rated high (likelihood or impact) has a **MITIGATES**, or `treatment: accept` under a person's exception (`sdem exception grant`) | RA-3, RA-7 · ID.RA |
| **SEC-S07** | Every `security` requirement is met by at least one control (`requirements`) | PL-8 · GV.PO |
| **SEC-S08** | A component that accesses personal data is **PROTECTED** by an audit control (AU-2 or AU-12) | AU-2, AU-12 · DE.CM |
| **SEC-S09** | S1 — a business process with `criticality` high or critical is **PROTECTED** by at least one control | AC-5, AC-3 · GV.RR |
| **SEC-S10** | S2 — a service domain is **PROTECTED** by at least one control; only where BIAN is on (computed by `sdem security review`) | AC-3, SI-7 · PR.AA |
| **SEC-S11** | S3 — an application component records the data it reads or writes (an access link), so the data's protection reaches it (computed by `sdem security review`, so it reads either form) | CM-12 · ID.AM-07 |
| **SEC-S12** | S3 — personal data states its `retention_period` | SI-12 · PR.DS |
| **SEC-S13** | S4 — an `internet_facing` interface is **PROTECTED** by a control (authorisation per operation, input validation) | AC-3, SI-10 · PR.AA |
| **SEC-S14** | S4 — an application component states its `recovery_time_objective` and `recovery_point_objective` | CP-9, CP-10 · RC.RP |
| **SEC-S15** | S5 — system software states its `end_of_support` | SA-22, SI-2 · ID.AM-08 |

**SX-12 — every security layer is checked** *(the owner, 2026-11-22: "ok implement")*: SEC-S09…S15 give S1, S2 and S4 their first rules and S3 and S5 more, each a warning on an attribute or link SDEM already has — no new design type, no new link between design layers. **SX-13 — other standards, by reference only**: a control may name clauses of other standards it also meets in `also_satisfies` (e.g. `ISO/IEC 27001:2022 A.8.24`, `APRA CPS 234 para 21`, `PCI DSS 4.0.1 3.5.1`, `OWASP ASVS 5.0 V8`); no standard's text is shipped (ISO, PCI and CIS are licensed; NIST is public domain), and nothing checks the reference.

A value not given is `unresolved`, never compliant (PR-11a, PR-20) — e.g. the example's two paths whose `encrypted` is not given.

**As built (0.1.1, 2026-11-19 — after an external review found the first build short of this table):**

| Check | Where it runs | What it checks |
|---|---|---|
| SEC-S01a, SEC-S01b | the standard (`sdem comply`, `sdem check`) | personal data classified `confidential` or `restricted`; protected by at least one control |
| SEC-S01 (SC-28 specifically) | `sdem security review` | personal data with no SC-28 control — SDEM's cross-layer rules check *every* linked record, so "one of them is SC-28" cannot be a rule |
| SEC-S02 | the standard | an `internet_facing` interface has `oauth2`, `openIdConnect` or `mutualTLS` |
| SEC-S03a, SEC-S03b | the standard | a path is `encrypted: true` (a); it names its `protocol` (b) |
| SEC-S04 | the standard | a DMZ is bounded by a trust boundary |
| SEC-S05a, SEC-S05b | the standard | an implemented control has `control_evidence`; an implemented or partial one has an ENFORCED_BY |
| SEC-S06a, SEC-S06b | the standard | a high-**impact** threat (a) or a high-**likelihood** threat (b) has a mitigating control |
| SEC-S07 | `sdem security review` | every `security` requirement in `requirements.json` is met by a control (`meets_requirements`) — the registry is not a record SDEM rules can follow |
| SEC-S08 | `sdem security review` | every component that accesses personal data is PROTECTED by an AU-2 or AU-12 control — a two-step path SDEM rules cannot express |

Not yet: the evidence in `control_evidence` is a reference only — nothing checks its content, age or result (the review's finding D); approval-time rules that block are not shipped (finding C). Both are next (P1).

**As built (0.1.3, 2026-11-19 — after the audit, [`audit-2026-11-19.md`](audit-2026-11-19.md)):**
- **Only a control that can act counts** — not one marked `not_applicable`, retired or deprecated — for protection, S07, S08 and SC-28.
- **The computed checks follow the standard's own rules (PR-11a):** not decidable yet → `unresolved` (a planned component or operation; a
  requirement still proposed); a person's exception holds any of them (`sdem exception grant --rule SEC-S08`, MX-17 — the pack lists them
  as `computed_rules`). S07 skips retired and superseded requirements and reports a control naming a requirement the registry lacks.
  S08 reaches personal data held on a field (`A3.DataAttribute`) and access by an API operation (audited by its own control, or by the
  interface or component that serves it).
- **One scope:** coverage covers what a control may PROTECT and the STRIDE checklist what a threat may THREATEN — both read from the pack's
  link types. Added: THREATENS to a business actor; PROTECTS and THREATENS to `A3.DataAttribute`, `A2.BusinessObject`,
  `A4.InfrastructureComponent`, `A4.CommunicationNetwork`. A field is protected through its data entity. STRIDE per element now
  matches §7 (a process all six; an API operation includes R).
- **`review` never reports an all-clear it cannot vouch for:** it stops with a message when `sdem comply` fails, answers in an unknown
  form, or the SEC standard is not in the profile; it takes findings by the standard's id, not by a `SEC-` prefix.
- **`sdem security remove`** switches it off (MX-16): the layer and its connections archived, their ids retired, the design still passing.
- **0.2.0 — the whole life** ([extension lifecycle spec](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-extension-lifecycle-spec.md), EL-01…EL-17): `restore` (back from an archive, the same link ids) and `purge` (the archived data deleted, never the default); the manifest's `viewer` (what it offers DESNRE); with sdem-desnre 0.8.0 the design's state — on or off, since, by, why — is published, and the site says when security was switched off. The README's *Install* and *Remove* sections give the two ways to install and every removal step.

**Every rule is a warning.** Switching security on in an existing design must not stop its work: with errors, `sdem check` (and so `sdem connect`, which refuses a change that leaves the check failing) would fail before the first control could be added. `sdem comply` and `sdem security review` report every finding; an organisation that wants them to block adds its own rules at `error` in its profile.

## 7. Commands (`sdem security …`, through EXT-15)

| Command | Does |
|---|---|
| `sdem security catalogue <words>` | searches the SP 800-53 catalogue (id, title, family) — as `sdem bian search` does for BIAN |
| `sdem security coverage --workspace …` | per record in A1–A4: its classification, the controls that protect it and where they are enforced, the threats on it — and what has none |
| `sdem security threats --workspace …` | a **STRIDE checklist** per record (the STRIDE-per-element table: an actor S·R; a process or component all six; a data entity T·R·I·D; a path T·I·D) — prompts for a person, never records |
| `sdem security review --workspace …` | the reviewer's list, weakest first: rules not met, unresolved values, unevidenced controls, unmitigated high threats |
| `sdem security propose <file> --workspace … --person …` | a person's controls, threats and boundaries into the aspect, **as a change set** (`--dry-run` first; EXT-07) |

All read-only except `propose`; all take `--json`.

## 8. The viewpoint — Security Architecture, S1–S5

- **Its own 3D stack, called *Security*** — a third viewpoint on the 3D view's switch, *Architecture · Security · Metamodel*, with the same controls as the other two (focus a plate, flat 2D, connections view): five plates stacked S1 at the top to S5 at the bottom. Present only while the aspect is installed and included in the workspace; removing it removes the option.
- **Each S-plate is its A-plate with security drawn over it:** the same view model as the [Architecture viewpoint](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-architecture-viewpoint-spec.md) (same shapes, same positions), the shapes coloured by `access_classification`, each layer's controls and threats placed beside what they protect or threaten, trust boundaries drawn round what they bound; unprotected records marked.
- **Lines between plates** are the cross-layer **PROTECTS**, **ENFORCED_BY** and **THREATENS** — a control in S4 reaching down to S5 and up to S1. Choosing a control lights everything it protects and what enforces it, in every layer.
- **2D, the Design document:** the same five figures (S1–S5, one view model for both, ARV-01/02) in a new section, *Security architecture*, with a coverage table per layer; written by the agent from this data and checked by SDEM.

## 9. The example — payment-initiation-v3 (made-up)

| Control | id | Protects | Enforced by |
|---|---|---|---|
| Customer authentication | IA-2 | PROC-AUTH, SD-PARTY-AUTHENTICATION, IFC-PAYMENT-INITIATION | APP-IDENT |
| Third-party authentication (OAuth2) | IA-8 | IFC-PAYMENT-INITIATION | APP-EDGE |
| Transport encryption | SC-8 | PATH-EDGE, PATH-DATA, PATH-KEY, PATH-HANDOFF | NODE-EDGE, NODE-INT |
| Protection at rest | SC-28 | DATA-CONSENT, DATA-PAYMENT, DATA-AUDIT | SYS-DB |
| Key management | SC-12 | DATA-CONSENT, DATA-PAYMENT | SYS-KMS |
| Boundary protection | SC-7 | ZONE-EDGE | NODE-EDGE |
| Input validation | SI-10 | API-PAYMENT-CREATE, API-CONSENT-CREATE | APP-PAYHUB, APP-CONSENT |
| Audit events | AU-2, AU-12 | APP-CONSENT, APP-PAYHUB | APP-EDGE, SYS-OBS |

Threats: spoofing of the third party (S, IFC-PAYMENT-INITIATION), a payment altered in flight (T, PATH-HANDOFF), consent repudiated (R, DATA-CONSENT), personal data disclosed (I, DATA-CONSENT), the edge flooded (D, ZONE-EDGE). Trust boundary: the internet edge (network, enforced by API ingress) bounding ZONE-EDGE. Written as a change set, accepted by a named person; `sdem comply` then reports what the design still lacks (the two unencrypted-or-unknown paths among them).

## 10. Where it lives

`sdem-extensions/metamodel/security/`: the manifest (`kind: ["metamodel", "checker"]`), `aspect.json` (types, links, rules, `builds_on`), the standard, the commands, the catalogue reference (§11, SX-D3), the example data and tests (EXT-14), against SDEM's examples for every version it claims (EXT-04, MX-11b).

## 11. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| SX-D1 | Three types (control, threat, trust boundary); classification and requirements reuse what SDEM holds | **yes** — the smallest set that answers §1 |
| SX-D2 | **Five security layers S1–S5**, the security views of A1, A2, A3-1, A3-2, A4; each control and threat in one (`security_layer`); a third viewpoint *Security* with five plates, each its A-plate with security drawn over it | **yes** — the owner's structure; the aspect's id stays `SEC`, and none of it is a core layer |
| SX-D3 | The SP 800-53 catalogue: ship the control ids, titles and families (from NIST's OSCAL file, with its source and checksum) | **yes** — small, public domain, works offline; the full text is linked, not shipped |
| SX-D4 | No inference: threats come from a person (`sdem security threats` only prompts) | **yes** — security judgement stays with a person |
| SX-D5 | The eight standards (§6) ship as the aspect's default standard, switched on with the aspect | **yes** — a workspace may narrow them in its profile, never weaken (PR-14) |
| SX-D6 | Build order: SDEM's core change (MX §5) → the aspect file and `sdem check` → links, trace, impact → standards and commands → the example → DESNRE's Security viewpoint (S1–S5) and document section | **yes** |
