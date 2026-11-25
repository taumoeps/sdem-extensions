"""sdem-bian infer --step link (MX-45…MX-53; the SDEM 0.22 plan, step 3b, proof P1 as the owner chose it — R-D11): with sdem-bian
installed, `sdem link` on every one of SDEM's 0.20 examples, its approved links removed, proposes exactly what SDEM 0.21 proposed
(SDEM's baseline, tests/golden/0.21-link-scratch) — every field of every proposal, except who made it and its number. Made-up data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDEM = Path(os.environ.get('SDEM_HOME') or next((d / n for d in HERE.parents for n in ('sdem', 'bian-sdem-framework') if (d / n / 'sdem' / 'cli.py').is_file()), HERE.parents[3] / 'sdem'))
BASE = SDEM / 'tests' / 'golden' / '0.21-link-scratch'
PROV = ('created_by',)   # who made it; its number is 0.21's (MX-53: the whole run's order)
BINS = [Path(sys.executable).parent, Path(sys.executable).parent / 'Scripts']   # Windows installs commands in Scripts\


def installed():
    return shutil.which('sdem-bian', path=os.pathsep.join(map(str, BINS))) is not None


@unittest.skipUnless(BASE.is_dir() and installed() and not os.environ.get('SDEM_RELEASED'), 'needs an SDEM (0.22 onward) checkout with the 0.21 baseline, and sdem-bian installed beside it')
class LinkAsBefore(unittest.TestCase):
    def test_every_example_proposes_what_sdem_0_21_proposed(self):
        made_by_bian = 0
        for b in sorted(BASE.glob('*.json')):
            ex = SDEM / 'examples' / '0.20' / b.stem
            if b.stem == 'reference-structure' or not any((d / 'bian.json').is_file() for d in (ex, ex / 'sdem')): continue   # SDEM 0.22 (BX-15): a design without BIAN is a core one — not BIAN's to prove
            src = ex / 'sdem' if (ex / 'sdem' / 'mappings.json').exists() else ex
            t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
            ws = t / 'ws'; shutil.copytree(src, ws)
            m = json.loads((ws / 'mappings.json').read_text(encoding='utf-8')); m['mappings'] = []; (ws / 'mappings.json').write_text(json.dumps(m), encoding='utf-8')
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'SDEM_FORM': '0.20', 'PATH': os.pathsep.join([*map(str, BINS), os.environ.get('PATH', '')])}
            r = subprocess.run([sys.executable, '-m', 'sdem', 'link', '--workspace', str(ws), '--out', str(t / 'links'), '--no-review'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=t)
            self.assertEqual(r.returncode, json.loads(b.read_text(encoding='utf-8'))['exit'], f'{b.stem}: {r.stderr[-400:]}')
            now = json.loads((t / 'links' / 'proposals.json').read_text(encoding='utf-8'))['mappings']
            key = lambda p: (p['source']['id'], p['relationship'], p['target']['id'])
            strip = lambda p: {k: v for k, v in p.items() if k not in PROV}
            then = {key(p): strip(p) for p in json.loads(b.read_text(encoding='utf-8'))['proposals']}
            got = {key(p): strip(p) for p in now}
            if got != then:   # say exactly what differs: the links, then each field
                why = [f'only before: {k}' for k in sorted(set(then) - set(got))][:3] + [f'only now: {k}' for k in sorted(set(got) - set(then))][:3]
                for k in sorted(set(got) & set(then)):
                    for f in sorted(set(got[k]) | set(then[k])):
                        if got[k].get(f) != then[k].get(f): why.append(f'{k} {f}: before {json.dumps(then[k].get(f))[:220]} — now {json.dumps(got[k].get(f))[:220]}')
                self.fail(f'{b.stem}: ' + ' | '.join(why[:4]))
            made_by_bian += sum(1 for p in now if str(p.get('created_by', '')).startswith('bian '))
        self.assertGreater(made_by_bian, 100)   # BIAN's rules ran here, not in SDEM (160 on SDEM 0.21's examples)


if __name__ == '__main__':
    unittest.main()
