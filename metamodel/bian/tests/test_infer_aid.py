"""sdem-bian infer --step aid --phase … (MX-54; the SDEM 0.22 plan, step 3c, proof P1 as the owner chose it — R-D11): with sdem-bian
installed, `sdem aid` from scratch on every one of SDEM's 0.20 examples (each scenario of SDEM's baseline, tests/golden/0.21-aid-scratch)
infers exactly what SDEM 0.21 inferred — every record, link, proposal and run-record field — with BIAN's part given by sdem-bian at each
phase, which the run record says (`phases_by`). Made-up data only."""
import gzip, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDEM = Path(os.environ.get('SDEM_HOME') or next((d / n for d in HERE.parents for n in ('sdem', 'bian-sdem-framework') if (d / n / 'sdem' / 'cli.py').is_file()), HERE.parents[3] / 'sdem'))
BASE = SDEM / 'tests' / 'golden' / '0.21-aid-scratch'
SCRIPT = SDEM / 'scripts' / 'golden' / 'aid_scratch.py'
BINS = [Path(sys.executable).parent, Path(sys.executable).parent / 'Scripts']   # Windows installs commands in Scripts\


MOVED = ('reference-structure__',)   # SDEM 0.22 (BX-15): the reference structure is generated from SDEM's core — it has no BIAN layer now


def _norm(x):
    """What moved with SDEM 0.22 and nothing else: SDEM's own version stamp (sdem.version) and the metamodel's (0.19.0 → 0.20.0, R-D3)."""
    if isinstance(x, dict): return {k: ('<metamodel>' if k == 'metamodel_version' else _norm(v)) for k, v in x.items() if k != 'sdem'}
    if isinstance(x, list): return [_norm(v) for v in x]
    return x


def _uses_bian(example):
    ex = SDEM / 'examples' / '0.20' / example
    return any((d / 'bian.json').is_file() for d in (ex, ex / 'sdem'))


def installed():
    return shutil.which('sdem-bian', path=os.pathsep.join(map(str, BINS))) is not None


@unittest.skipUnless(BASE.is_dir() and SCRIPT.is_file() and installed() and not os.environ.get('SDEM_RELEASED'), 'needs an SDEM (0.22 onward) checkout with the 0.21 baseline, and sdem-bian installed beside it')
class AidAsBefore(unittest.TestCase):
    def test_every_example_infers_what_sdem_0_21_inferred(self):
        out = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, out, True)
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PATH': os.pathsep.join([*map(str, BINS), os.environ.get('PATH', '')])}
        r = subprocess.run([sys.executable, str(SCRIPT), str(SDEM), str(out)], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        by = set()
        for b in sorted(BASE.glob('*.json.gz')):
            if b.name.startswith(MOVED) or not _uses_bian(b.name.split('__')[0]): continue   # SDEM 0.22: a design without BIAN is a core one — not BIAN's to prove
            then = _norm(json.loads(gzip.open(b, 'rt', encoding='utf-8').read()))
            now = json.loads((out / b.name[:-3]).read_text(encoding='utf-8'))
            by.add(((now.get('record') or {}).pop('phases_by', None)))
            now = _norm(now)
            if now != then:   # say where it differs first
                why = [k for k in sorted(set(now) | set(then)) if now.get(k) != then.get(k)]
                self.fail(f'{b.name[:-8]}: differs in {why}: {json.dumps(now.get("stderr_tail"))[:300]}')
        self.assertEqual(by, {f"bian {json.loads((HERE.parent / 'sdem_bian' / 'sdem-extension.json').read_text(encoding='utf-8'))['version']}"})   # sdem-bian gave BIAN's part of every run


if __name__ == '__main__':
    unittest.main()
