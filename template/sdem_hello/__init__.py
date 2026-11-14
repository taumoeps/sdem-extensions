"""sdem hello — a template SDEM extension: what an extension needs, and nothing more.

    sdem hello show <workspace>        SDEM's version and the workspace's check result

It uses SDEM only through its command line (EXT-02), checks SDEM's version against its manifest (EXT-04), writes nothing (EXT-07).
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

MANIFEST = json.loads((Path(__file__).parent / 'sdem-extension.json').read_text(encoding='utf-8'))


def sdem(*args):
    """SDEM's command line — the one beside this Python (installed in SDEM's environment), else the one on the PATH."""
    exe = shutil.which('sdem', path=str(Path(sys.executable).parent)) or shutil.which('sdem') or 'sdem'
    return subprocess.run([exe, *args], capture_output=True, text=True)


def supported(version, spec):
    v = tuple(int(x) for x in re.findall(r'\d+', version)[:3])
    for clause in spec.split(','):
        op, want = re.match(r'\s*(>=|<)\s*([\d.]+)', clause).groups()
        w = tuple(int(x) for x in want.split('.')); w += (0,) * (3 - len(w))
        if not (v >= w if op == '>=' else v < w):
            return False
    return True


def show(workspace):
    version = re.search(r'\d+\.\d+\.\d+', sdem('--version').stdout).group(0)
    if not supported(version, MANIFEST['sdem']):
        print(f"sdem hello: SDEM {version} is not one this extension supports ({MANIFEST['sdem']})", file=sys.stderr); return 1
    r = json.loads(sdem('check', '--workspace', workspace, '--json').stdout)
    errors = sum(len(v) for v in (r.get('report') or {}).values())
    print(f"SDEM {version} · {workspace}: {'clean' if r.get('ok') else f'{errors} error(s)'}")
    return 0 if r.get('ok') else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['--manifest']:   # how SDEM recognises an extension (EXT-05, EXT-15)
        print(json.dumps(MANIFEST, indent=2)); return 0
    ap = argparse.ArgumentParser(prog='sdem hello', description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('show', help="SDEM's version and the workspace's check result"); p.add_argument('workspace')
    a = ap.parse_args(argv)
    return show(a.workspace)


def entry():
    sys.exit(main())
