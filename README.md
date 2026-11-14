# SDEM extensions

Extensions for [SDEM](https://github.com/taumoeps/bian-sdem-framework), each its own package. Installed beside SDEM, an extension becomes part of the `sdem` command: `sdem <name> …`.

| Extension | Does | Install |
|---|---|---|
| [**desnre**](desnre/) | puts a made-up SDEM workspace on the DESNRE site's 3D view — `sdem desnre create`, then `sdem desnre publish` | `pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=desnre"` |

Start a new one from [**template/**](template/).

## Install and use

Into the **same environment as SDEM** (for SDEM's own checkout, its `.venv`):

```
pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=desnre"
sdem extensions                 # lists what is installed, what each reads and where it sends data
sdem desnre --help
```

From a clone, `pip install -e sdem-extensions/desnre` — changes in the clone take effect at once.

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
