"""sdem-bian — BIAN Service Domain Architecture as an SDEM metamodel extension (step 2 of SDEM 0.20; BP-01…BP-11).

It carries BIAN's data: the A2 metamodel, its within-layer rules, link types and inference rules, and the BIAN catalogue. SDEM reads
them from its data folder when it is installed (and supports this SDEM); otherwise SDEM uses its built-in copy, identical for 0.20.

    sdem-bian --manifest     what it is, and where its data is (SDEM reads this)
    sdem-bian <command> …    the same as sdem bian <command> … — SDEM's own commands, which read this package's data

Switch BIAN on or off in a workspace — a person's decision: sdem profile include ext:bian / exclude ext:bian.
"""
import json, shutil, subprocess, sys
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
    exe = shutil.which('sdem', path=str(Path(sys.executable).parent)) or shutil.which('sdem') or 'sdem'   # EXT-02: through SDEM's command line
    return subprocess.call([exe, 'bian', *argv])


if __name__ == '__main__':
    sys.exit(entry())
