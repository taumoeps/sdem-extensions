# template — start an SDEM extension here

Copy this folder, then rename `hello` everywhere (folder, package, `pyproject.toml`, the manifest):

```
cp -R template myext && cd myext
# rename: sdem_hello → sdem_myext, sdem-hello → sdem-myext, "hello" → "myext"
pip install -e .            # into SDEM's environment
sdem extensions             # listed
sdem myext show <workspace>
```

What it shows, in about fifty lines:

- **the manifest** (`sdem_hello/sdem-extension.json`) and `--manifest`, which is how SDEM recognises an extension (EXT-05, EXT-15);
- **SDEM only through its commands** — `sdem --version` and `sdem check --workspace … --json` (EXT-02, EXT-03), and the supported versions checked (EXT-04);
- **read-only** — it writes nothing (EXT-07);
- **a test** against SDEM's made-up payment example (EXT-14).

The rules are SDEM's extension contract, EXT-01…EXT-15. An extension that sends anything anywhere also needs a dry run and a person's step first (EXT-08) — see `desnre/`.
