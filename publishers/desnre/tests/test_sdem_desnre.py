"""sdem desnre (the DESNRE site's docs/desnre-publish-design.md DP-01…DP-16; SDEM's EXT-01…EXT-15), against SDEM's made-up
payment example and a stand-in for the site's API (fake_site.py: the same contract, a store in memory).

Needs SDEM: a checkout next to this repository (../bian-sdem-framework), or SDEM_HOME.
    python -m unittest discover -s desnre/tests
"""
import json, contextlib, io, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # desnre/
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'tests'))
import sdem_desnre as X   # noqa: E402
from fake_site import Site   # noqa: E402

SDEM = Path(os.environ.get('SDEM_HOME') or next((d / 'bian-sdem-framework' for d in HERE.parents if (d / 'bian-sdem-framework').is_dir()), HERE.parents[2] / 'bian-sdem-framework'))   # an SDEM checkout beside this repository, however deep the extension sits
EXAMPLE = SDEM / 'examples' / 'payment-initiation'   # 0.19's form, as the site's four plates and pull know it
EXAMPLE_NOW = SDEM / 'examples' / '0.20' / 'payment-initiation'   # SDEM 0.20: the same example migrated (DL-D9, opt-in)


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
        st = m['workspace']['status']                                                              # SDEM's own health figures, for the Health tab
        self.assertEqual(st['state'], 'clear'); self.assertIn('completeness', st)                  # null when the design includes no completeness standard
        self.assertFalse({'workspace', 'next', 'sources', 'name'} & set(st))                       # nothing about the publisher's computer
        self.assertNotIn(str(self.tmp), json.dumps(m))
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


    def test_supports_sdem_018_onwards(self):   # desnre 0.7.0: SDEM 0.18 and 0.19; 0.9.0: 0.20 too; 0.10.2: any additive change before 1.0 (MIP-01, the owner's MIP-D2)
        for v in ('0.18.0', '0.19.0', '0.20.0', '0.21.0'): self.assertTrue(X.in_range(v, X.MANIFEST['sdem']), v)
        for v in ('0.14.0', '0.17.0', '0.19.0'): self.assertTrue(X.in_range(v, X.MANIFEST['metamodel']), v)
        self.assertFalse(X.in_range('0.17.0', X.MANIFEST['sdem'])); self.assertFalse(X.in_range('1.0.0', X.MANIFEST['sdem']))

    def test_a_full_design_builds_without_its_fields_and_locations(self):   # SDEM 0.19: fields and locations are in the workspace, not drawn
        v2 = SDEM / 'examples' / 'payment-initiation-v2'
        if not v2.exists(): self.skipTest('needs SDEM 0.19 (examples/payment-initiation-v2)')
        body = X.build(str(v2), 0.5)
        ids = {n[0] for n in body['nodes']}
        self.assertNotIn('LOC-XA', ids); self.assertFalse(any(i.startswith('F-PAY-INSTR-') for i in ids))
        self.assertIn('BEV-PAY-EXECUTED', ids); self.assertIn('CHN-OBAPI', ids)



@unittest.skipUnless((SDEM / 'examples' / 'payment-initiation-v2').exists(), 'needs SDEM 0.19 or later')
class PathTests(unittest.TestCase):   # PL-01: a path is the line between the nodes it connects, not a shape (the owner, 2026-11-16)
    def test_a_path_is_sent_as_a_labelled_line(self):
        sys.path.insert(0, str(SDEM))
        m = X.build(str(SDEM / 'examples' / 'payment-initiation-v2'), 0.5); N = m['nodes']
        self.assertNotIn('PATH-PAY-CORE-HSM', [n[0] for n in N])
        self.assertIn(('INF-CORE-LEDGER-HOST', 'DEV-PAY-HSM', 'path · Core ledger host to HSM · tls'), [(N[e[0]][0], N[e[1]][0], e[3]) for e in m['edges']])


@unittest.skipUnless((SDEM / 'examples' / 'payment-initiation-v2').exists(), 'needs SDEM 0.19 or later')
class DraftTests(unittest.TestCase):   # desnre 0.7.4: the draft is drawn — links SDEM proposed and nobody has decided, dashed (the owner, 2026-11-17)
    def test_a_link_proposed_and_not_yet_decided_is_drawn_dashed(self):
        import shutil, tempfile
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, True)
        ws = tmp / 'ws'; shutil.copytree(SDEM / 'examples' / 'payment-initiation-v2', ws, ignore=shutil.ignore_patterns('graph'))
        reg = json.loads((ws / 'mappings.json').read_text(encoding='utf-8'))['mappings']
        done = next(m for m in reg if m['status'] == 'approved')
        before = X.build(str(ws), 0.5); N = [n[0] for n in before['nodes']]
        linked = {(N[e[0]], N[e[1]]) for e in before['edges']} | {(N[e[1]], N[e[0]]) for e in before['edges']}
        a, b = next((x, y) for x in N for y in N if x != y and (x, y) not in linked and x[:3] != y[:3])
        (ws / 'links').mkdir(exist_ok=True)
        (ws / 'links' / 'proposals.json').write_text(json.dumps({'mappings': [
            {'mapping_id': 'P-1', 'source': {'id': a}, 'relationship': 'SERVED_BY', 'target': {'id': b}, 'status': 'proposed'},
            {**done, 'mapping_id': 'P-2', 'status': 'proposed'}]}), encoding='utf-8')   # one new, one a person has already approved
        m = X.build(str(ws), 0.5); N = [n[0] for n in m['nodes']]
        drawn = [(N[e[0]], N[e[1]], e[2], e[3]) for e in m['edges']]
        self.assertTrue([d for d in drawn if {d[0], d[1]} == {a, b} and d[2] == 0 and d[3] == 'SERVED_BY'])   # 0: proposed — the site draws it dashed
        self.assertEqual(len(m['edges']), len(before['edges']) + 1)                                        # the approved one is not drawn a second time
        self.assertEqual(m['counts']['proposed'], 1)


if __name__ == '__main__':
    unittest.main()



@unittest.skipUnless((EXAMPLE_NOW / 'business.json').exists(), "needs SDEM 0.20's example (in the 0.20 form) next to this repository")
class Form020Tests(unittest.TestCase):   # SDEM's DL-23: a workspace in the 0.20 form, published as 0.19 held it
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('SDEM_CMD', f'env PYTHONPATH={SDEM} {sys.executable} -m sdem')
        sys.path.insert(0, str(SDEM))
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-desnre-020-'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_same_design_gives_the_same_model_in_either_form(self):
        import sdem_desnre as d
        new, old = self.tmp / 'payment-initiation', self.tmp / 'old' / 'payment-initiation'
        shutil.copytree(EXAMPLE_NOW, new, ignore=shutil.ignore_patterns('graph', 'migrations'))
        shutil.copytree(EXAMPLE, old, ignore=shutil.ignore_patterns('graph', 'migrations'))
        self.assertTrue(d.is_020(new) and not d.is_020(old))
        keep = d.build_integrity; d.build_integrity = lambda ws, scale: None   # the layout-based model (an SDEM before 0.21.7): the same design either form
        try: a, b = d.model_for(old, 'pi-check', need_mark=False), d.model_for(new, 'pi-check', need_mark=False)
        finally: d.build_integrity = keep
        ids = lambda m: [n['id'] if isinstance(n, dict) else n[0] for n in m['nodes']]   # a node is [id, label, plate, …]
        edges = lambda m: {tuple([ids(m)[int(e[0])], ids(m)[int(e[1])], *e[2:]]) for e in m['edges']}
        # MIP-04: the same links — except access, which 0.19 held inside Application and the design's own form holds as an approved
        # ACCESSED_BY between Data and Application (DL-04), drawn from Data down
        data = d._data_ids(EXAMPLE)   # only an application's access to data moves between layers; access inside Business or BIAN stays
        as20 = {(t, s_, 1, 'ACCESSED_BY') if r == 'access' and t in data and s_ not in data else (s_, t, ok, r, *rest) for s_, t, ok, r, *rest in edges(a)}
        self.assertEqual(as20, edges(b))
        self.assertEqual(sorted(ids(a)), sorted(ids(b)))   # the same records
        self.assertEqual([l['code'] for l in b['layers']], ['A1', 'A2', 'A3', 'A4', 'A5'])   # SDEM 0.20: five plates, Data of its own
        self.assertEqual(len(b['zones']), 5); self.assertEqual(b['zoneLayer'], 4); self.assertNotIn('layers', a)
        on_data = {n[0] for n in b['nodes'] if n[2] == 2}
        self.assertEqual(on_data, d._data_ids(EXAMPLE) & set(ids(b)))   # exactly the drawn data records on the Data plate
        self.assertFalse(list(new.glob('a1-business.json')))   # the workspace itself only read

    def test_the_metamodel_view_is_sdems_knowledge_graphs(self):   # SDEM MID-01, MID-02: drawn from sdem model integrity --graph alone
        import sdem_desnre as d
        new = self.tmp / 'graph-check'
        shutil.copytree(EXAMPLE_NOW, new, ignore=shutil.ignore_patterns('graph', 'migrations'))
        g = json.loads(d.run_sdem(new, ['model', 'integrity', '--workspace', str(new), '--graph', '--json']).stdout)
        m = d.model_for(new, 'pi-graph', need_mark=False)
        self.assertEqual(m['source'].get('from'), 'sdem model integrity --graph')
        self.assertEqual(sorted(n[0] for n in m['nodes']), sorted(x['id'] for x in g['records']))     # every record of every graph, nothing else
        self.assertEqual(len(m['edges']), len(g['links']))                                          # every link inside and between the graphs
        self.assertEqual([l['code'] for l in m['layers']], [x['code'] for x in g['graphs']])

    def test_a_design_without_bian_is_four_plates_with_data_second(self):   # SDEM's default: A1 Business, A2 Data, A3 Application, A4 Technology
        import sdem_desnre as d
        src = self.tmp / 'core-src'; src.mkdir()
        ex = SDEM / 'examples' / 'card-fraud-alerts'
        for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json'): shutil.copy(ex / f, src / f)
        m = json.loads((ex / 'mappings.json').read_text())
        m['mappings'] = [x for x in m['mappings'] if not x['source']['type'].startswith('A2.') and not x['target']['type'].startswith('A2.')]
        (src / 'mappings.json').write_text(json.dumps(m))
        ws = self.tmp / 'core'
        r = subprocess.run([*os.environ['SDEM_CMD'].split(), 'new', '--workspace', str(ws), '--person', 'tester', '--core', '--form', '0.20', '--from', str(src)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        model = d.model_for(ws, 'core-check', need_mark=False)
        self.assertEqual([l['code'] + ' ' + l['name'] for l in model['layers']], ['A1 Business Architecture', 'A2 Data Architecture', 'A3 Application Architecture', 'A4 Technology Architecture'])
        self.assertEqual((len(model['zones']), model['zoneLayer']), (4, 3))
        self.assertEqual([x['id'] for x in model['workspace']['stack']], ['business', 'data', 'application', 'technology'])

    def test_pull_into_a_0_20_workspace_is_refused_plainly(self):
        import sdem_desnre as d
        ws = self.tmp / 'pull'; shutil.copytree(EXAMPLE_NOW, ws, ignore=shutil.ignore_patterns('graph', 'migrations'))
        with self.assertRaises(d.PublishError) as e:
            d.cmd_pull(type('A', (), {'workspace': str(ws), 'site': None, 'name': None})())
        self.assertIn("0.20", str(e.exception))


class OneVersion(unittest.TestCase):   # the manifest a site and SDEM read says the same version as the package (desnre 0.11.1–0.11.3 said 0.11.0)
    def test_manifest_and_package_agree(self):
        import re
        here = Path(__file__).resolve().parents[1]
        pkg = re.search(r'^version = "([^"]+)"', (here / 'pyproject.toml').read_text(encoding='utf-8'), re.M).group(1)
        man = json.loads((here / 'sdem_desnre' / 'sdem-extension.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(man, pkg)
