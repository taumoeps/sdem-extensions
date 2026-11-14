# sdem desnre

Puts a made-up SDEM workspace on the DESNRE site's 3D view. An SDEM extension: install it once and it becomes part of `sdem`.

## Install (once)

Into the same environment as SDEM — for SDEM's own checkout, its `.venv`:

```
cd ~/Documents/Projects/bian-sdem-framework
.venv/bin/pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=desnre"
sdem extensions          # desnre is listed
```

From a clone of this repository: `.venv/bin/pip install -e ../sdem-extensions/desnre`.

## Use

```
sdem desnre create examples/payment-initiation      # check, build, send a draft (not public) and open the preview
sdem desnre publish examples/payment-initiation     # after looking at it: live at https://desnre.vercel.app/?model=payment-initiation
```

The first `create` of a workspace asks you to confirm it is **made-up data** (the site is public) and records who said so in the workspace (`extensions/desnre.json`). After you change the workspace, run the same two commands again; the version it replaces is kept.

| Also | |
|---|---|
| `sdem desnre create <ws> --dry-run` | check and build only; writes the model to a file, sends nothing |
| `sdem desnre create <ws> --name payment` | a different name on the site (default: the workspace folder's name) |
| `sdem desnre list` | what is live |
| `sdem desnre remove <ws>` | take it off the site |

## Tokens

Two tokens, from the environment or — on a Mac — the login Keychain under the same names, never a file: `DESNRE_PUBLISH_TOKEN` (send drafts) and `DESNRE_APPROVE_TOKEN` (publish, remove). To put them in the Keychain:

```
security add-generic-password -U -a "$USER" -s DESNRE_PUBLISH_TOKEN -w '<token>'
security add-generic-password -U -a "$USER" -s DESNRE_APPROVE_TOKEN -w '<token>'
```

## What it checks before anything is sent

1. SDEM's version and the workspace's metamodel version are ones it supports (`sdem_desnre/sdem-extension.json`).
2. The workspace is confirmed made-up data by a person.
3. `sdem check` finds no errors.
4. The model matches `sdem_desnre/desnre-model.schema.json` and is at most 2 MB.

The site's API checks the token, the schema, the size and the made-up mark again. The schema (`sdem_desnre/desnre-model.schema.json`) is owned here; the DESNRE site keeps a copy and its tests check the copy matches.

## How it fits SDEM

It follows SDEM's extension contract (EXT-01…EXT-15): its own program, `sdem-desnre`, with a manifest (`sdem-desnre --manifest`); SDEM runs it as `sdem desnre …` and it uses SDEM only through `sdem … --json`. Without installing, `desnre/sdem-desnre …` runs it too. The design: `docs/desnre-publish-design.md` in the DESNRE site (DP-01…DP-16).

## Tests

```
python -m unittest discover -s desnre/tests
```

They need SDEM next to this repository (`../bian-sdem-framework`) or `SDEM_HOME`. `tests/fake_site.py` stands in for the site's API (the same contract, a store in memory); the real API is tested in the DESNRE site.
