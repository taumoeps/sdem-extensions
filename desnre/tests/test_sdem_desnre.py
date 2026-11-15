"""sdem desnre (the DESNRE site's docs/desnre-publish-design.md DP-01…DP-16; SDEM's EXT-01…EXT-15), against SDEM's made-up
payment example and a stand-in for the site's API (fake_site.py: the same contract, a store in memory).

Needs SDEM: a checkout next to this repository (../bian-sdem-framework), or SDEM_HOME.
    python -m unittest discover -s desnre/tests
"""
import json, contextlib, io, os, shutil, sys, tempfile, time, unittest
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
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            code, _, err = run('create', str(ws), '--site', site.url)   # signed in, but not a terminal and no --yes: refused, nothing written
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

    def test_not_signed_in_nothing_is_sent(self):   # DA-40, EXT-12
        ws = self.copy()
        real, X.token = X.token, (lambda k: '')   # not this Mac's Keychain
        try:
            code, _, err = run('create', str(ws), '--yes', '--by', 'a tester', '--site', 'http://127.0.0.1:9')
        finally:
            X.token = real
        self.assertEqual(code, 1); self.assertIn('you are not signed in', err); self.assertIn('/account, then: sdem desnre login', err)
        self.assertFalse((ws / 'extensions').exists())                                              # refused before anything was built or recorded

    def env(self, **tokens):   # tokens only from these values, never this Mac's Keychain
        real = X.token
        X.token = lambda k: tokens.get(k, '')
        self.addCleanup(setattr, X, 'token', real)

    def test_login_checks_the_token_and_keeps_it(self):   # DA-40
        kept = []
        real = X.keep_token; X.keep_token = lambda v: kept.append(v) or True; self.addCleanup(setattr, X, 'keep_token', real)
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            sys.stdin = io.StringIO('desnre_alice\n'); self.addCleanup(setattr, sys, 'stdin', sys.__stdin__)
            code, text, err = run('login', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('signed in as @alice', text); self.assertEqual(kept, ['desnre_alice'])
            sys.stdin = io.StringIO('desnre_nobody\n')
            self.assertEqual(run('login', '--site', site.url)[0], 1)
            sys.stdin = io.StringIO('not-a-token\n')
            self.assertIn('not a DESNRE token', run('login', '--site', site.url)[2])

    def test_create_publish_list_remove_on_your_own_page(self):   # DA-20, DA-21, DP-10…DP-13
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            ws = self.copy(); url = site.url
            self.assertIn('@alice', run('whoami', '--site', url)[1])
            code, text, err = run('create', str(ws), '--name', 'payment', '--yes', '--by', 'a tester', '--no-open', '--site', url)
            self.assertEqual(code, 0, err); self.assertIn('a draft — not public', text); self.assertIn('/u/alice/payment?draft=', text)
            self.assertIn(f'sdem desnre publish {ws}', text)                                       # it says the next step
            self.assertIn('0 live model(s)', run('list', '--site', url)[1])                        # a draft is not live
            code, text, err = run('publish', str(ws), '--site', url)                              # by the workspace: its recorded name
            self.assertEqual(code, 0, err); self.assertIn('/u/alice/payment', text); self.assertIn('your page:', text)
            code, text, _ = run('list', '--site', url, '--json')
            self.assertEqual(json.loads(text)['items'][0]['workspace'], ws.name)
            self.assertEqual(run('list', '--hero', '--site', url, '--json')[1].count('"name"'), 0)   # nothing on the hero page
            self.assertEqual(run('remove', 'payment', '--site', url)[0], 0)
            self.assertIn('0 live model(s)', run('list', '--site', url)[1])

    def test_the_hero_page_is_the_owners(self):   # DA-24
        with Site(people={'desnre_alice': ('alice', False), 'desnre_owner': ('steven', True)}) as site:
            ws = self.copy()
            self.env(DESNRE_TOKEN='desnre_alice')
            code, _, err = run('create', str(ws), '--hero', '--yes', '--by', 'a tester', '--no-open', '--site', site.url)
            self.assertEqual(code, 1); self.assertIn("the hero page is the site owner's", err)
            self.env(DESNRE_TOKEN='desnre_owner')
            self.assertEqual(run('create', str(ws), '--hero', '--name', 'payment', '--no-open', '--site', site.url)[0], 0)
            code, text, err = run('publish', 'payment', '--hero', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('?model=payment', text)

    def test_pull_applies_accepted_change_sets_with_sdem(self):   # DW-24
        ws = self.copy()
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            d = 'alice/' + X.slug(ws)
            good = {'id': 'cs-1', '_design': d, 'status': 'accepted', 'accepted_at': '1', 'layer': 'A1', 'reason': 'rename the payments capability',
                    'changes': [{'op': 'update', 'record': {'id': 'CAP-PAY-000', 'type': 'A1.BusinessCapability', 'version': '1.1', 'name': 'Payments (renamed)', 'lifecycle_status': 'active'}}]}
            bad = {'id': 'cs-2', '_design': d, 'status': 'accepted', 'accepted_at': '2', 'layer': 'A1', 'reason': 'a kind that does not exist',
                   'changes': [{'op': 'add', 'record': {'id': 'X-1', 'type': 'A1.NoSuchKind', 'version': '1', 'name': 'x', 'lifecycle_status': 'active'}}]}
            site.changes += [good, {**bad, 'status': 'proposed'}]
            code, text, err = run('pull', str(ws), '--dry-run', '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('would apply cs-1', text); self.assertEqual(good['status'], 'accepted')   # a dry run changes nothing
            self.assertNotIn('Payments (renamed)', (ws / 'a1-business.json').read_text())
            code, text, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('applied cs-1', text); self.assertEqual(good['status'], 'pulled')
            self.assertIn('Payments (renamed)', (ws / 'a1-business.json').read_text())                                          # applied by SDEM itself
            site.changes[1]['status'] = 'accepted'
            code, _, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 1); self.assertIn('refused by SDEM', err); self.assertIn('NoSuchKind', err)
            self.assertEqual(site.changes[1]['status'], 'accepted')                                                               # not marked pulled


    def test_pull_a_profile_change_checks_and_adopts_it(self):   # DW-32
        ws = self.copy()
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            d = 'alice/' + X.slug(ws)
            good = {'format': 'sdem-profile/1', 'name': 'acme-payments', 'version': 1, 'description': 'made up',
                    'types': [{'type': 'ACME.A3.PaymentsService', 'extends': 'A3.ApplicationComponent', 'name': 'Payments service', 'definition': 'a made-up kind', 'source': 'acme standard §1'}]}
            bad = {'format': 'sdem-profile/1', 'name': 'acme', 'version': 1, 'types': [{'type': 'ACME.A3.X', 'extends': 'A3.NoSuchKind', 'name': 'x'}]}
            (ws / 'workspace.json').write_text('{}')                                                                    # as sdem new starts one
            site.changes += [{'id': 'cs-p1', '_design': d, 'status': 'accepted', 'accepted_at': '1', 'layer': 'profile', 'reason': 'our payments service kind', 'profile': good}]
            code, text, err = run('pull', str(ws), '--dry-run', '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('would apply cs-p1', text); self.assertFalse((ws / 'sdem-profile.json').exists())
            code, text, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('adopted', text); self.assertEqual(site.changes[0]['status'], 'pulled')
            self.assertIn('ACME.A3.PaymentsService', (ws / 'sdem-profile.json').read_text())
            self.assertIn('profile', json.loads((ws / 'workspace.json').read_text()))                                   # recorded by sdem profile adopt
            site.changes.append({'id': 'cs-p2', '_design': d, 'status': 'accepted', 'accepted_at': '2', 'layer': 'profile', 'reason': 'broken', 'profile': bad})
            code, _, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 1); self.assertIn('refused by SDEM', err)
            self.assertIn('ACME.A3.PaymentsService', (ws / 'sdem-profile.json').read_text())                            # put back as it was

    def test_a_profile_in_a_folder_sdem_new_did_not_start_is_checked_not_adopted(self):
        ws = self.copy()
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            site.changes.append({'id': 'cs-p1', '_design': 'alice/' + X.slug(ws), 'status': 'accepted', 'accepted_at': '1', 'layer': 'profile', 'reason': 'ours',
                                 'profile': {'format': 'sdem-profile/1', 'name': 'acme', 'version': 1, 'types': []}})
            code, text, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('NOT adopted', text); self.assertTrue((ws / 'sdem-profile.json').exists())


    def _site_change(self, ws, name):   # what the site recorded: the capability renamed on the web, and what it was before
        recs = json.loads((ws / 'a1-business.json').read_text())['instances']
        was = next(r for r in recs if r['id'] == 'CAP-PAY-000')
        web = {**was, 'version': '1.1', 'name': name}
        return {'id': 'cs-w1', '_design': 'alice/' + X.slug(ws), 'status': 'accepted', 'accepted_at': '1', 'layer': 'A1', 'reason': 'renamed on the web',
                'changes': [{'op': 'update', 'record': web}], 'relationships': {}, 'before': {'records': {'CAP-PAY-000': was}, 'links': {}}}

    def _local_rename(self, ws, name):   # the architect changes the same record in the workspace, with SDEM
        recs = json.loads((ws / 'a1-business.json').read_text())['instances']
        r = {**next(x for x in recs if x['id'] == 'CAP-PAY-000'), 'version': '1.2', 'name': name}
        f = ws / 'local-cs.json'; f.write_text(json.dumps({'layer': 'A1', 'reason': 'renamed locally', 'changes': [{'op': 'update', 'record': r}]}))
        out = X.run_sdem(ws, ['change', 'propose', str(f), '--workspace', str(ws), '--agent', 'architect', '--person', 'a tester', '--json']); f.unlink()
        self.assertEqual(out.returncode, 0, out.stdout[-400:])

    def test_pull_stops_on_a_record_changed_in_both_places(self):   # DW-53
        ws = self.copy()
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            site.changes.append(self._site_change(ws, 'Payments (web)'))
            self._local_rename(ws, 'Payments (local)')
            code, _, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 1); self.assertIn('CAP-PAY-000', err); self.assertIn('name: workspace "Payments (local)" · web "Payments (web)"', err)
            self.assertIn('--keep-local', err); self.assertEqual(site.changes[0]['status'], 'accepted')                         # nothing done
            code, text, err = run('pull', str(ws), '--keep-local', '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('kept the workspace', text); self.assertEqual(site.changes[0]['status'], 'pulled')
            self.assertIn('Payments (local)', (ws / 'a1-business.json').read_text())

    def test_pull_take_web_and_a_change_already_there(self):   # DW-53
        ws = self.copy()
        with Site(people={'desnre_alice': ('alice', False)}) as site:
            self.env(DESNRE_TOKEN='desnre_alice')
            site.changes.append(self._site_change(ws, 'Payments (web)'))
            self._local_rename(ws, 'Payments (local)')
            code, text, err = run('pull', str(ws), '--take-web', '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('the web won', text)
            body = (ws / 'a1-business.json').read_text(); self.assertIn('Payments (web)', body); self.assertNotIn('Payments (local)', body)
            again = {**self._site_change(ws, 'Payments (web)'), 'id': 'cs-w2', 'accepted_at': '2'}
            again['changes'][0]['record'] = next(r for r in json.loads(body)['instances'] if r['id'] == 'CAP-PAY-000')            # what the workspace has now
            site.changes.append(again)
            code, text, err = run('pull', str(ws), '--by', 'a tester', '--site', site.url)
            self.assertEqual(code, 0, err); self.assertIn('already in the workspace', text); self.assertEqual(site.changes[1]['status'], 'pulled')


if __name__ == '__main__':
    unittest.main()
