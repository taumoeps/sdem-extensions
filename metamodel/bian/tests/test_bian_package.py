"""sdem-bian against the SDEM it is installed with (BP-01…BP-11): SDEM finds it and reads its data; its data is identical to SDEM's
built-in copy while that fallback exists (BP-11); SDEM's answers are the same with it as without it. Needs SDEM in the same
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
    def test_the_data_is_sdems_builtin_copy(self):   # BP-11: no drift while the fallback exists
        from sdem.parts import write_package_data
        out = Path(tempfile.mkdtemp())
        try:
            files = write_package_data(out)
            differ = [f for f in files if (out / f).read_bytes() != (sdem_bian.DATA / f).read_bytes()]
            self.assertEqual(differ, [], 'the package and SDEM disagree — regenerate with scripts/bian_package.py, or change both')
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_sdem_finds_it_and_reads_its_data(self):   # BP-05
        from sdem import parts
        parts._PKG.clear()
        p = parts.package()
        self.assertTrue(p and p.get('data'), p)
        self.assertEqual(Path(p['data']).resolve(), sdem_bian.DATA.resolve())
        self.assertEqual(parts.catalogue_dir().resolve(), (sdem_bian.DATA / 'catalogue').resolve())

    def test_sdem_bian_runs_sdems_bian_commands(self):   # BP-01
        r = subprocess.run([prog('sdem-bian'), 'search', 'payment', 'rail', '--json'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn('Payment Rail', r.stdout)
        self.assertIn('bian', sdem_cli('extensions').stdout)


if __name__ == '__main__':
    unittest.main()
