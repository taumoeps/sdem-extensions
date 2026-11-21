"""SDEM's XA-01…XA-09 (docs/design/sdem-extension-agent-context-spec.md): an extension's reports and its guide for the AI agent come from its
own manifest — the publisher names no extension. Proved with a made-up disaster-recovery extension, `dr`, that exists only in this test.
Synthetic data only."""
import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sdem_desnre as D  # noqa: E402

DR = {'name': 'drdemo', 'version': '0.1.0', 'description': 'Disaster recovery: recovery plans, targets and rehearsals for a design (made up)',
      'agent_guide': 'Layer R holds recovery plans. A plan COVERS an application; rto_minutes is its recovery-time target. Cite the plan id.',
      'scope': {'across': ['R'], 'note': 'vertical'}, 'viewer': {'results': ['gaps', 'document', '--evil', '../x']}}
NET = {'name': 'netdemo', 'version': '0.1.0', 'agent_guide': 'x' * 2500, 'scope': {'within': ['technology']}, 'results': ['zones']}


def fake(calls):
    def run(ws, args):
        calls.append(args)
        name, cmd = args[0], args[1]
        man = {'drdemo': DR, 'netdemo': NET}.get(name)
        if man is None: return subprocess.CompletedProcess(args, 2, '', 'not installed')
        if cmd == '--manifest': return subprocess.CompletedProcess(args, 0, json.dumps(man), '')
        if cmd == 'document': return subprocess.CompletedProcess(args, 0, f'# Recovery review\nfrom {ws}/plans.json\n', '')
        return subprocess.CompletedProcess(args, 0, json.dumps({'workspace': str(ws), 'items': [{'id': 'DR-1', 'covers': 'APP-PAYHUB'}]}), '')
    return run


class AgentContext(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp()); self.calls = []
        self.real, D.run_sdem = D.run_sdem, fake(self.calls); D._MANIFESTS.clear()
        self.files = {'sdem-profile.json': {'includes': ['ext:drdemo', 'ext:netdemo', 'ext:absent']}}

    def tearDown(self): D.run_sdem = self.real; D._MANIFESTS.clear()

    def test_reports_are_the_manifest_s_and_nothing_else_is_run(self):   # XA-01, XA-03
        res = D.no_local_paths(D.extension_results(self.ws, self.files), self.ws)
        self.assertEqual(sorted(res['drdemo']), ['document', 'gaps']); self.assertEqual(sorted(res['netdemo']), ['zones'])
        self.assertNotIn('absent', res)                                        # not installed: left out, the design still publishes
        self.assertNotIn('workspace', res['drdemo']['gaps'])                       # never the workspace's path
        self.assertNotIn(str(self.ws), res['drdemo']['document'])
        run = {(a[0], a[1]) for a in self.calls}
        self.assertNotIn(('drdemo', '--evil'), run); self.assertNotIn(('drdemo', '../x'), run)   # a name that could be an option or a path is never run
        self.assertIn(['drdemo', 'gaps', '--workspace', str(self.ws), '--json'], self.calls)

    def test_the_state_carries_version_scope_reports_and_guide(self):   # XA-03, XA-05
        st, _ = D.extension_states(self.ws, self.files, D.extension_results(self.ws, self.files))
        dr = st['drdemo']
        self.assertEqual((dr['state'], dr['version']), ('on', '0.1.0')); self.assertEqual(dr['scope'], {'across': ['R']})
        self.assertEqual(dr['reports'], ['gaps', 'document']); self.assertTrue(dr['agent_guide'].startswith('Layer R holds recovery plans'))
        self.assertEqual(st['netdemo']['scope'], {'within': ['technology']})      # XA-08: a horizontal one the same way

    def test_a_long_guide_is_cut_with_a_note(self):   # XA-02, XA-06
        g = D.extension_states(self.ws, self.files, {})[0]['netdemo']['agent_guide']
        self.assertLessEqual(len(g), D.GUIDE_MAX + 80); self.assertIn('cut', g)

    def test_no_line_of_the_publisher_names_an_extension(self):   # XA-09: one route for every extension
        src = (Path(D.__file__)).read_text(encoding='utf-8')
        code = '\n'.join(l.split('#')[0] for l in src.splitlines())
        for name in ('drdemo', 'netdemo'):
            self.assertIsNone(re.search(rf"['\"]{name}['\"]", code))
        self.assertNotIn('EXT_RESULTS', code); self.assertNotIn("'security':", code)


if __name__ == '__main__':
    unittest.main()
