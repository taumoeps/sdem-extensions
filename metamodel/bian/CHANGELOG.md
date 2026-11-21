# sdem-bian — changes

## 1.0.1 — 2026-11-22

- **BIAN's own attributes** (SDEM's BX-04, BP-02): `data/attributes.json` carries the 31 attribute definitions of BIAN's types, so everything BIAN adds to a design now comes from this package. SDEM uses them only while BIAN is on; an SDEM without this file's support, or this package's 1.0.0, uses SDEM's own copy (BP-10). Nothing else changed.

## 1.0.0 — 2026-11-21 (with SDEM 0.20.0)

- **For metamodel 0.18.0** (SDEM 0.20.0.dev1): the A2 metamodel file carries the new version; supports metamodel `>=0.17,<0.19`. `sdem bian update` opens each workspace in its own form (a root may hold workspaces in 0.19's and 0.20's). Regenerated from SDEM with `scripts/bian_package.py`.

## 1.0.0.dev2

- **Its own `sdem bian` commands** (SDEM 0.20 step 3, ST-20…ST-22): `bian.py` and `inferences.py`, written against `sdem.api` 0.1 — the only part of SDEM's code it uses. SDEM runs them for `sdem bian …` when this package is installed; the answers are the same as SDEM's own.

## 1.0.0.dev1

- **First version** (SDEM 0.20 step 2, BP-01…BP-11): BIAN's A2 metamodel (15 types), 23 within-layer rules, 10 link types, 46
  inference rules and the BIAN 14 catalogue, taken verbatim from SDEM 0.19 — with it installed, SDEM's answers are the same as 0.19's.
