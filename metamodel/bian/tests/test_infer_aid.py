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
            then = json.loads(gzip.open(b, 'rt', encoding='utf-8').read())
            now = json.loads((out / b.name[:-3]).read_text(encoding='utf-8'))
            by.add(((now.get('record') or {}).pop('phases_by', None)))
            if now != then:   # say where it differs first
                why = [k for k in sorted(set(now) | set(then)) if now.get(k) != then.get(k)]
                self.fail(f'{b.name[:-8]}: differs in {why}: {json.dumps(now.get("stderr_tail"))[:300]}')
        self.assertEqual(by, {f"bian {json.loads((HERE.parent / 'sdem_bian' / 'sdem-extension.json').read_text(encoding='utf-8'))['version']}"})   # sdem-bian gave BIAN's part of every run


if __name__ == '__main__':
    unittest.main()
