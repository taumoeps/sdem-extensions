"""sdem-bian against the SDEM it is installed with (BP-01…BP-11): SDEM finds it and reads its data — since SDEM 0.22 its
only source of BIAN (BX-15); SDEM's answers are the same with it as without it. Needs SDEM in the same
environment — skipped without it unless SDEM_REQUIRED=1 (CI)."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
try:
    import sdem_bian   # the installed copy — the one SDEM finds
except ImportError:
    sys.path.insert(0, str(HERE)); import sdem_bian  # noqa: E402

try:
    import sdem  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False
NEED = os.environ.get('SDEM_REQUIRED') == '1'


def prog(name): return shutil.which(name, path=str(Path(sys.executable).parent)) or shutil.which(name)


def sdem_cli(*args):
    exe = prog('sdem')
    return subprocess.run([exe, *map(str, args)], capture_output=True, text=True, encoding='utf-8')


class Manifest(unittest.TestCase):
    def test_it_names_a_complete_data_folder(self):
        m = sdem_bian.manifest()
        self.assertEqual((m['name'], m['kind'], m['scope']['within']), ('bian', ['metamodel'], ['A2']))
        d = Path(m['bian_data'])
        for f in ('a2-service-domain.json', 'within-layer-rules.json', 'link-types.json', 'inference-rules.json', 'catalogue/base-14.0.0.json',
                  'catalogue/inferences-14.0.0.json', 'catalogue/LICENSE'):
            self.assertTrue((d / f).is_file(), f)


@unittest.skipUnless(HAVE or NEED, 'SDEM is not installed in this environment')
class WithSdem(unittest.TestCase):
    def test_it_is_bians_only_source(self):   # SDEM 0.22 (BX-15): SDEM ships no BIAN — every row it uses comes from here, in its place (MX-55)
        from sdem import parts
        if hasattr(parts, 'write_package_data'): self.skipTest('an SDEM before 0.22 still has its own copy of BIAN')
        data = sdem_bian.HERE / 'data'
        order = json.loads((data / 'order.json').read_text(encoding='utf-8'))
        for kind, f in (('within', 'within-layer-rules.json'), ('link_types', 'link-types.json'), ('rules', 'inference-rules.json'), ('attributes', 'attributes.json')):
            self.assertEqual(len(order[kind]), len(json.loads((data / f).read_text(encoding='utf-8'))), f'{kind}: one place for each of its rows')
        self.assertTrue(list((data / 'catalogue').glob('layer-*.json')), 'the base BIAN layer, built (new.base_layer reads it)')
        self.assertTrue(list((data / 'standards').glob('sdem-pattern-bian-*.json')), "BIAN's patterns")

    def test_sdem_finds_it_and_reads_its_data(self):   # BP-05
        from sdem import parts
        parts._PKG.clear()
        p = parts.package()
        self.assertTrue(p and p.get('data'), p)
        self.assertEqual(Path(p['data']).resolve(), sdem_bian.DATA.resolve())
        self.assertEqual(parts.catalogue_dir().resolve(), (sdem_bian.DATA / 'catalogue').resolve())

    def test_its_code_uses_only_sdem_api(self):   # ST-21: never any other of SDEM's modules
        import ast
        for f in sorted(sdem_bian.HERE.glob('*.py')):
            tree = ast.parse(f.read_text(encoding='utf-8'))
            used = {n.module if n.module != 'sdem' else f"sdem.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and (n.module or '').split('.')[0] == 'sdem' for a in n.names}
            used |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names if a.name.split('.')[0] == 'sdem'}
            self.assertLessEqual(used, {'sdem.api'}, f.name)

    def test_sdem_runs_its_code_for_sdem_bian(self):   # ST-22
        from sdem import parts
        parts._PKG.clear()
        self.assertTrue(parts.package().get('code'), parts.package())

    def test_sdem_bian_runs_sdems_bian_commands(self):   # BP-01
        r = subprocess.run([prog('sdem-bian'), 'search', 'payment', 'rail', '--json'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn('Payment Rail', r.stdout)
        self.assertIn('bian', sdem_cli('extensions').stdout)


if __name__ == '__main__':
    unittest.main()
