# sdem-bian — changes

## 1.1.1 — 2026-11-24

- `sdem-bian infer` answers in ASCII JSON, the same bytes on every platform (on Windows a rationale's ↔ reached SDEM as â†”); its link proof now runs, and passes, on Windows too.

## 1.1.0 — 2026-11-24

- **BIAN's link rules run here** (SDEM 0.22 plan, step 3b): `sdem-bian infer --step link` runs SDEM's rules engine through `sdem.api` with BIAN's own steps (`rules_bian.py`, generated from SDEM and held identical, BP-11) and answers SDEM with BIAN's proposals, candidates and target design whole (MX-45…MX-53). With it installed, `sdem link` runs only the core's rules itself; what it proposes is SDEM 0.21's, every field, except who made it (`created_by: bian 1.1.0`) and its number — proved on SDEM's 13 examples (`tests/test_infer_link.py`).
- The manifest says `"infers": ["link"]`; `sdem aid`'s BIAN steps follow in step 3c.

## 1.0.3 — 2026-11-22

- Supports SDEM's metamodel 0.19.0 (the Data Architecture: data domains, ownership, read and write on access links). Nothing else changes.

## 1.0.2 — 2026-11-22

- **BIAN's business objects without a download** (SDEM's BO-01…BO-09): the catalogue carries `objects-14.0.0.json` — every service domain's business objects, typed fields only, no descriptions — and `sdem bian objects suggest`, which says which BIAN object each of a design's data entities may be, with the evidence and a person's two commands; `--object <Object>` now works from the base. Written from SDEM's own copy (BP-11).

## 1.0.1 — 2026-11-22

- **BIAN's own attributes** (SDEM's BX-04, BP-02): `data/attributes.json` carries the 31 attribute definitions of BIAN's types, so everything BIAN adds to a design now comes from this package. SDEM uses them only while BIAN is on; an SDEM without this file's support, or this package's 1.0.0, uses SDEM's own copy (BP-10). Nothing else changed.

## 1.0.0 — 2026-11-21 (with SDEM 0.20.0)

- **For metamodel 0.18.0** (SDEM 0.20.0.dev1): the A2 metamodel file carries the new version; supports metamodel `>=0.17,<0.19`. `sdem bian update` opens each workspace in its own form (a root may hold workspaces in 0.19's and 0.20's). Regenerated from SDEM with `scripts/bian_package.py`.

## 1.0.0.dev2

- **Its own `sdem bian` commands** (SDEM 0.20 step 3, ST-20…ST-22): `bian.py` and `inferences.py`, written against `sdem.api` 0.1 — the only part of SDEM's code it uses. SDEM runs them for `sdem bian …` when this package is installed; the answers are the same as SDEM's own.

## 1.0.0.dev1

- **First version** (SDEM 0.20 step 2, BP-01…BP-11): BIAN's A2 metamodel (15 types), 23 within-layer rules, 10 link types, 46
  inference rules and the BIAN 14 catalogue, taken verbatim from SDEM 0.19 — with it installed, SDEM's answers are the same as 0.19's.
