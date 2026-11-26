"""The template extension, against SDEM's made-up payment example (EXT-14). Needs SDEM: ../sdem (or ../bian-sdem-framework) or SDEM_HOME."""
import contextlib, io, json, os, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import sdem_hello as H   # noqa: E402

SDEM = Path(os.environ.get('SDEM_HOME') or next((d / n for d in HERE.parents for n in ('sdem', 'bian-sdem-framework') if (d / n / 'sdem' / 'cli.py').is_file()), HERE.parents[2] / 'bian-sdem-framework'))   # an SDEM checkout beside this repository, however deep the extension sits
EXAMPLE = SDEM / 'examples' / '0.20' / 'library-holds'   # SDEM 0.22: the core's own example — a publisher needs no BIAN (the banking ones are sdem-bian's)


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = H.main(list(argv))
    return code, out.getvalue()


class HelloTests(unittest.TestCase):
    def test_the_manifest_is_what_sdem_reads(self):
        code, out = run('--manifest')
        self.assertEqual(code, 0); self.assertEqual(json.loads(out)['command'], 'sdem-hello')

    def test_supported_versions(self):
        self.assertTrue(H.supported('0.18.2', '>=0.18,<0.19')); self.assertFalse(H.supported('0.19.0', '>=0.18,<0.19'))

    @unittest.skipUnless(EXAMPLE.exists(), 'needs SDEM next to this repository (or SDEM_HOME)')
    def test_show_a_clean_workspace(self):
        os.environ['PATH'] = os.pathsep.join([str(SDEM / '.venv' / 'bin'), os.environ.get('PATH', '')])
        code, out = run('show', str(EXAMPLE))
        self.assertEqual(code, 0, out); self.assertIn('clean', out)


if __name__ == '__main__':
    unittest.main()
