# SDEM extensions

Extensions for [SDEM](https://github.com/taumoeps/bian-sdem-framework), each its own package. Installed beside SDEM, an extension becomes part of the `sdem` command: `sdem <name> …`.

| Extension | Does | Install |
|---|---|---|
| [**desnre**](publishers/desnre/) | puts a made-up SDEM workspace on your own page of the DESNRE site, as a 3D view — sign up at desnre.vercel.app/account, then `sdem desnre login`, `create`, `publish` | `pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=publishers/desnre"` |
| [**bian**](metamodel/bian/) | a **horizontal metamodel extension**: BIAN's Service Domain layer (A2) between Business and Application — its types, link types, inference rules and the BIAN 14 catalogue. SDEM 0.20 reads it when installed and uses its own identical copy otherwise | `pip install ./metamodel/bian` |
| [**security**](metamodel/security/) | a **metamodel extension**: adds the security architecture — controls, threats and trust boundaries in S1–S5 across A1–A4, on NIST SP 800-53 Rev. 5 and CSF 2.0 — switched on per workspace (`sdem profile include ext:security`) | `pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=metamodel/security"` |

**How the repository is laid out** — by what an extension does to SDEM (its manifest's `kind`):

| Folder | Kind | What it is |
|---|---|---|
| `publishers/` | publisher | sends a design somewhere — `desnre` |
| `metamodel/` | metamodel | adds to SDEM's metamodel. Its manifest's `scope` says how: **vertical**, a layer across A1–A4 (`"scope": {"across": ["S"]}` — `security`), or **horizontal**, more record types inside one layer (`"scope": {"within": ["A4"]}` — e.g. a network extension, planned). Tools read the scope; the folder does not split them |
| `templates/` | — | starting points for a new extension |

Start a new one from [**template/**](templates/publisher/).

## Install and use

Into the **same environment as SDEM** (for SDEM's own checkout, its `.venv`):

```
pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=publishers/desnre"
sdem extensions                 # lists what is installed, what each reads and where it sends data
sdem desnre --help
```

From a clone, `pip install -e sdem-extensions/publishers/desnre` — changes in the clone take effect at once.

## The rules every extension here follows

SDEM's extension contract, EXT-01…EXT-15 ([`docs/design/sdem-extensions-spec.md`](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-extensions-spec.md)), in short:

- **Its own program, `sdem-<name>`,** with a manifest (`sdem-extension.json`) that it prints for `--manifest` — how SDEM recognises it.
- **SDEM only through its commands** (`sdem … --json`) and the workspace files — never SDEM's code, so SDEM can change inside without breaking it. It names the SDEM versions it supports and stops outside them.
- **Read-only by default;** record changes only through SDEM change sets.
- **A dry run, and a person's step, before anything leaves the machine.** A public target takes only a workspace a person confirmed as made-up data.
- **No secrets in files** — tokens from the environment or the operating system's keychain.
- **Tested against SDEM's made-up examples** on every push (`.github/workflows/test.yml`).

An organisation's own extensions — house rules, its CMDB — belong in its own repository, usually private; they follow the same contract.

## Licence

Apache License 2.0, like SDEM.
