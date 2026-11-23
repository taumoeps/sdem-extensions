# sdem desnre

Puts a made-up SDEM workspace on **your own page** of the DESNRE site, as a 3D view: `desnre.vercel.app/u/<you>/<name>`. An SDEM extension — install it once and it becomes part of `sdem`.

## Once

1. **An account:** sign up at **[desnre.vercel.app/account](https://desnre.vercel.app/account)** — email, password and a username (your page's address). Confirm your email from the link you are sent.
2. **A token:** on your account page, **Create token** (it expires after 90 days unless you choose otherwise). It is shown once — copy it.
3. **The extension,** into the same environment as SDEM:
   ```
   pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=publishers/desnre"
   sdem extensions                 # desnre is listed
   ```
4. **Sign in:** `sdem desnre login` and paste the token. On a Mac it is kept in your Keychain; elsewhere set it as the environment variable `DESNRE_TOKEN`.

## Every time

```
sdem desnre create <workspace>      # check, build, send a draft — not public — and open the preview
sdem desnre publish <workspace>     # make it live on your page: desnre.vercel.app/u/<you>/<name>
```

The first `create` of a workspace asks you to confirm it is **made-up data** (the site is public) and records who said so in the workspace (`extensions/desnre.json`). After you change the workspace, run the same two commands again; the version it replaces is kept.

| Also | |
|---|---|
| `sdem desnre create <ws> --dry-run` | check and build only; writes the model to a file, sends nothing |
| `sdem desnre create <ws> --name payment` | a different name on your page (default: the workspace folder's name) |
| `sdem desnre pull <ws>` | bring the changes you accepted on the workbench — already applied on the site — into the workspace: SDEM replays each (`sdem change propose`; a profile through `sdem profile check` and `sdem profile adopt`) and records it. A record you also changed in the workspace since stops the pull and shows both versions: `--keep-local` keeps yours, `--take-web` takes the web's. `--dry-run` checks only |
| `sdem desnre publish <name> --force` | publishing is refused while the site has workbench changes you have not pulled; `--force` replaces them (they are lost) |
| `sdem desnre list` | your live models (`--user <name>` someone else's) |
| `sdem desnre remove <ws>` | take it off your page |
| `sdem desnre whoami` · `logout` | who you are signed in as · remove the token from this computer |

Revoke a token, remove a model or delete your account on your account page at any time.

The site's hero page is the site owner's: the owner publishes there with `--hero`, signed in with an admin account.

## What it checks before anything is sent

1. You are signed in (a token that is yours, not expired or revoked).
2. SDEM's version and the workspace's metamodel version are ones it supports (`sdem_desnre/sdem-extension.json`).
3. The workspace is confirmed made-up data by a person.
4. `sdem check` finds no errors.
5. The model matches `sdem_desnre/desnre-model.schema.json` and is at most 2 MB.

The site checks the token, that the page is yours, the schema, the size and the made-up mark again. The schema is owned here; the DESNRE site keeps a copy and its tests check the copy matches.

## How it fits SDEM

It follows SDEM's extension contract (EXT-01…EXT-15): its own program, `sdem-desnre`, with a manifest (`sdem-desnre --manifest`); SDEM runs it as `sdem desnre …` and it uses SDEM only through `sdem … --json`. Uninstalling it (`pip uninstall sdem-desnre`) leaves SDEM as it was. The design: `docs/desnre-publish-design.md` and `docs/desnre-accounts-design.md` in the DESNRE site.

## Tests

```
python -m unittest discover -s desnre/tests
```

They need SDEM next to this repository (`../sdem`, or `../bian-sdem-framework` for an older checkout) or `SDEM_HOME`. `tests/fake_site.py` stands in for the site's API (accounts, own pages, the hero page; a store in memory); the real API is tested in the DESNRE site.
