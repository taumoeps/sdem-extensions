"""sdem desnre (the DESNRE site's docs/desnre-publish-design.md DP-01…DP-16; SDEM's EXT-01…EXT-15), against SDEM's made-up
payment example and a stand-in for the site's API (fake_site.py: the same contract, a store in memory).

Needs SDEM: a checkout next to this repository (../bian-sdem-framework), or SDEM_HOME.
    python -m unittest discover -s desnre/tests
"""
import contextlib, io, json, os, shutil, sys, tempfile, time, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # desnre/
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'tests'))
import sdem_desnre as X   # noqa: E402
from fake_site import Site   # noqa: E402

SDEM = Path(os.environ.get('SDEM_HOME', HERE.parents[1] / 'bian-sdem-framework'))
EXAMPLE = SDEM / 'examples' / 'payment-initiation'


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = X.main(list(argv))
    return code, out.getvalue(), err.getvalue()


@unittest.skipUnless(EXAMPLE.exists(), 'needs an SDEM checkout next to this repository (or SDEM_HOME)')
class ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('SDEM_CMD', f'env PYTHONPATH={SDEM} {sys.executable} -m sdem')
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-desnre-'))
        cls.ws = cls.tmp / 'payment-initiation'
        shutil.copytree(EXAMPLE, cls.ws, ignore=shutil.ignore_patterns('graph', 'migrations'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def copy(self):
        ws = self.tmp / f'ws-{time.time_ns()}'
        shutil.copytree(self.ws, ws)
        return ws

    def test_the_manifest_is_what_sdem_reads(self):   # EXT-05, EXT-15
        code, out, _ = run('--manifest')
        self.assertEqual(code, 0); m = json.loads(out)
        self.assertEqual((m['name'], m['command']), ('desnre', 'sdem-desnre'))

    def test_create_asks_once_whether_it_is_made_up(self):   # EXT-10, EXT-11: never assumed
        ws = self.copy()
        code, _, err = run('create', str(ws), '--site', 'http://127.0.0.1:9')   # not a terminal, no --yes: refused, nothing written
        self.assertEqual(code, 1); self.assertIn('not yet confirmed as made-up data', err); self.assertFalse((ws / 'extensions').exists())
        m = X.confirm_made_up(ws, 'a tester', True)
        self.assertEqual((m['data'], m['marked_by']), ('synthetic', 'a tester'))
        self.assertEqual(X.confirm_made_up(ws, 'someone else', False)['marked_by'], 'a tester')   # asked once: the record stands

    def test_dry_run_builds_the_model_and_sends_nothing(self):   # DP-03, DP-04, EXT-13
        ws, out = self.copy(), self.tmp / 'm.json'
        code, text, err = run('create', str(ws), '--dry-run', '-o', str(out))
        self.assertEqual(code, 0, err); self.assertIn('dry run: nothing sent', text)
        self.assertFalse((ws / 'extensions').exists())                                              # a dry run records nothing
        m = json.loads(out.read_text(encoding='utf-8'))
        self.assertEqual((m['format'], m['format_version'], m['data']), ('desnre-model', 1, 'synthetic'))
        self.assertEqual(m['name'], ws.name)                                                       # the name: the workspace folder's
        self.assertEqual(m['source']['metamodel'], json.loads((ws / 'a1-business.json').read_text())['metamodel_version'])
        self.assertEqual(X.validate(m), [])
        again = self.tmp / 'm2.json'; run('create', str(ws), '--dry-run', '-o', str(again))
        self.assertEqual(out.read_bytes(), again.read_bytes())                                     # the same workspace, the same file

    def test_a_workspace_with_errors_is_refused(self):   # EXT-09
        ws = self.copy()
        d = json.loads((ws / 'a1-business.json').read_text()); d['instances'].append({'id': 'BROKEN'})
        (ws / 'a1-business.json').write_text(json.dumps(d))
        code, _, err = run('create', str(ws), '--dry-run', '-o', str(self.tmp / 'y.json'))
        self.assertEqual(code, 1); self.assertIn('sdem check found errors', err)

    def test_an_unsupported_sdem_version_is_refused(self):   # EXT-04
        self.assertTrue(X.in_range('0.18.3', '>=0.18,<0.19')); self.assertFalse(X.in_range('0.19.0', '>=0.18,<0.19'))
        self.assertFalse(X.in_range('0.17.9', '>=0.18,<0.19'))

    def test_no_token_no_send(self):   # EXT-12
        ws = self.copy()
        env = os.environ.pop('DESNRE_PUBLISH_TOKEN', None)
        real = X.token
        X.token = lambda k: os.environ.get(k, '')   # not this Mac's Keychain
        try:
            code, _, err = run('create', str(ws), '--yes', '--by', 'a tester', '--site', 'http://127.0.0.1:9')
        finally:
            X.token = real
            if env: os.environ['DESNRE_PUBLISH_TOKEN'] = env
        self.assertEqual(code, 1); self.assertIn('DESNRE_PUBLISH_TOKEN is not set', err)

    def test_create_publish_list_remove_end_to_end(self):   # DP-05, DP-10…DP-14
        tokens = {'DESNRE_PUBLISH_TOKEN': 'publish-' + 'x' * 24, 'DESNRE_APPROVE_TOKEN': 'approve-' + 'y' * 24}
        saved = {k: os.environ.get(k) for k in tokens}
        with Site(tokens['DESNRE_PUBLISH_TOKEN'], tokens['DESNRE_APPROVE_TOKEN']) as site:
            try:
                os.environ.update(tokens)
                ws = self.copy(); url = site.url
                code, text, err = run('create', str(ws), '--name', 'payment', '--yes', '--by', 'a tester', '--no-open', '--site', url)
                self.assertEqual(code, 0, err); self.assertIn('a draft — not public', text); self.assertIn('?model=payment&draft=', text)
                self.assertIn(f'sdem desnre publish {ws}', text)                                   # it says the next step
                self.assertIn('0 live model(s)', run('list', '--site', url)[1])                    # a draft is not live
                os.environ['DESNRE_APPROVE_TOKEN'] = tokens['DESNRE_PUBLISH_TOKEN']               # the publish token cannot approve
                self.assertEqual(run('publish', str(ws), '--site', url)[0], 1)
                os.environ['DESNRE_APPROVE_TOKEN'] = tokens['DESNRE_APPROVE_TOKEN']
                code, text, err = run('publish', str(ws), '--site', url)                         # by the workspace: its recorded name
                self.assertEqual(code, 0, err); self.assertIn('?model=payment', text)
                code, text, _ = run('list', '--site', url, '--json')
                self.assertEqual(json.loads(text)['items'][0]['workspace'], ws.name)
                self.assertEqual(run('remove', 'payment', '--site', url)[0], 0)
                self.assertIn('0 live model(s)', run('list', '--site', url)[1])
            finally:
                for k, v in saved.items():
                    if v is None: os.environ.pop(k, None)
                    else: os.environ[k] = v

if __name__ == '__main__':
    unittest.main()
