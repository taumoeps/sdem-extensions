"""sdem-bian — BIAN Service Domain Architecture as an SDEM metamodel extension (step 2 of SDEM 0.20; BP-01…BP-11).

It carries BIAN's data: the A2 metamodel, its within-layer rules, link types and inference rules, and the BIAN catalogue. SDEM reads
them from its data folder when it is installed (and supports this SDEM); otherwise SDEM uses its built-in copy, identical for 0.20.

    sdem-bian --manifest     what it is, and where its data is (SDEM reads this)
    sdem-bian infer --workspace DIR --step link --json
                             BIAN's inference, for SDEM to check and list with its own (MX-45…MX-52) — SDEM runs it
    sdem-bian <command> …    the same as sdem bian <command> … — this package's own code (sdem_bian/bian.py), through sdem.api
                             (SDEM runs it for `sdem bian …` too, when this package supports its sdem.api)

Switch BIAN on or off in a workspace — a person's decision: sdem profile include ext:bian / exclude ext:bian.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / 'data'
MANIFEST = json.loads((HERE / 'sdem-extension.json').read_text(encoding='utf-8'))


def manifest():
    """The manifest, with where this installation keeps BIAN's data (BP-02)."""
    return {**MANIFEST, 'bian_data': str(DATA.resolve()), 'pack': str((HERE / 'pack.json').resolve())}   # the pack: what `sdem profile include ext:bian` folds in


def entry(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['--manifest']:
        print(json.dumps(manifest(), ensure_ascii=False)); return 0
    if argv[:1] in (['--version'], ['-V']):
        print(f"sdem-bian {MANIFEST['version']}"); return 0
    if argv[:1] in ([], ['-h'], ['--help']):
        print(__doc__.strip()); return 0
    if argv[:1] == ['infer']:   # MX-47: SDEM asks for BIAN's inference (sdem link; sdem aid in step 3c)
        from .infer import main as infer_main
        return infer_main(argv[1:])
    from sdem import api   # ST-21: the one interface to SDEM's code
    from .bian import main   # its own `sdem bian` commands (ST-22), run the way SDEM runs its own
    return api.run('bian', main, argv)


if __name__ == '__main__':
    sys.exit(entry())
