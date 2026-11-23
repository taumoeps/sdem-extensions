# sdem-bian — BIAN Service Domain Architecture for SDEM

A **horizontal metamodel extension**: the A2 Service Domain layer between Business (A1) and Application (A3), its 15 types, its
within-layer rules, the link types and inference rules that reach it, and the BIAN 14 catalogue. Step 2 of SDEM 0.20
([BIAN in its own package](https://github.com/taumoeps/sdem/blob/main/docs/design/sdem-bian-package-spec.md)).

```
pip install ./metamodel/bian          # into SDEM's environment
sdem extensions                       # bian 1.0.0.dev1 — installed
sdem profile include ext:bian --workspace DIR --person P --reason "a banking design"
```

- **SDEM reads its data** (`sdem_bian/data/`) when it is installed and supports this SDEM; otherwise SDEM uses its own copy —
  identical for all of 0.20 (BP-10, BP-11), so nothing breaks either way.
- **`sdem bian …`** works as before; `sdem-bian …` runs the same commands.
- **Its data is regenerated from SDEM** with `python scripts/bian_package.py <this folder>/sdem_bian` while SDEM keeps the
  fallback; the tests fail if the two differ.
- Made-up examples only; the BIAN extract keeps its own licence (`data/catalogue/LICENSE`).
