"""sdem-security against SDEM's bundled example (EXT-14): the pack is a valid metamodel extension, a person switches it on, controls
and threats go in as a change set, their links reach A1–A4, and coverage, threats and review report from the workspace.
Needs SDEM installed in the same environment (pip install -e security there); skipped otherwise. Synthetic data only."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sdem_security as S  # noqa: E402

SDEM = shutil.which('sdem', path=str(Path(sys.executable).parent)) or shutil.which('sdem')
DESIGN = {'layer': 'S', 'reason': 'a made-up security design', 'changes': [
    {'op': 'add', 'record': {'id': 'SEC-SC28', 'type': 'SEC.S.SecurityControl', 'version': '1', 'name': 'Protection at rest', 'lifecycle_status': 'planned',
                             'attributes': {'security_layer': 'S3', 'control_id': 'SC-28', 'csf_function': 'PR', 'control_kind': 'preventive', 'implementation_status': 'planned'}}},
    {'op': 'add', 'record': {'id': 'THR-DISCLOSE', 'type': 'SEC.S.Threat', 'version': '1', 'name': 'Payment instruction disclosed', 'lifecycle_status': 'planned',
                             'attributes': {'security_layer': 'S3', 'stride': ['I'], 'likelihood': 'medium', 'impact': 'high'}}}],
    'relationships': {'add': [{'source': 'SEC-SC28', 'kind': 'mitigates', 'target': 'THR-DISCLOSE'}]}}


def run(*args, ok=(0,)):
    r = subprocess.run([SDEM, *map(str, args)], capture_output=True, text=True)
    assert r.returncode in ok, f"sdem {' '.join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return json.loads(r.stdout) if r.stdout.strip().startswith('{') else r.stdout + r.stderr


@unittest.skipUnless(SDEM, 'SDEM is not installed in this environment')
class SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); ws = cls.ws = cls.tmp / 'ws'
        run('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation')
        cls.included = run('profile', 'include', 'ext:security', '--workspace', ws, '--person', 'steven', '--reason', 'security design', '--json')
        run('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'the security layer')
        (cls.tmp / 'design.json').write_text(json.dumps(DESIGN))
        run('security', 'propose', cls.tmp / 'design.json', '--workspace', ws, '--person', 'steven')
        for src, rel, tgt in (('SEC-SC28', 'PROTECTS', 'ENT-PAY-INSTR'), ('THR-DISCLOSE', 'THREATENS', 'ENT-PAY-INSTR'), ('SEC-SC28', 'PROTECTS', 'PRC-PAY-01')):
            run('connect', src, rel, tgt, '--workspace', ws, '--person', 'steven', '--evidence', 'design_document:security-design#1', '--rationale', 'made-up example')

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_manifest_names_its_pack(self):  # MX-01
        m = S.manifest(); self.assertIn('metamodel', m['kind']); self.assertTrue(Path(m['pack']).is_file())

    def test_the_catalogue_is_nists(self):
        hits = [c['id'] for c in S.catalogue()['controls'] if c['id'] in ('SC-28', 'IA-2', 'AU-12')]
        self.assertEqual(sorted(hits), ['AU-12', 'IA-2', 'SC-28'])
        self.assertIn('public domain', S.catalogue()['source']['licence'])

    def test_switched_on_by_a_person_and_checked(self):  # MX-10, MX-04
        self.assertEqual(self.included['kind'], 'metamodel extension')
        self.assertTrue(run('check', '--workspace', self.ws, '--json')['ok'])

    def test_coverage_follows_the_links_into_two_layers(self):  # MX-05
        rows = {r['id']: r for r in run('security', 'coverage', '--workspace', self.ws, '--json')['items']}
        self.assertTrue(rows['ENT-PAY-INSTR']['protected']); self.assertEqual(rows['ENT-PAY-INSTR']['security_layer'], 'S3')
        self.assertEqual(rows['ENT-PAY-INSTR']['threats'], ['THR-DISCLOSE'])
        self.assertTrue(rows['PRC-PAY-01']['protected']); self.assertEqual(rows['PRC-PAY-01']['security_layer'], 'S1')

    def test_threats_are_prompts_not_records(self):  # SX-D4
        d = run('security', 'threats', '--workspace', self.ws, '--json')
        ent = next(x for x in d['items'] if x['id'] == 'ENT-PAY-INSTR')
        self.assertEqual(ent['stated'], ['I']); self.assertNotIn('I', ent['not_yet_considered'])

    def test_review_runs_the_security_standard(self):  # MX-14
        d = run('security', 'review', '--workspace', self.ws, '--json')
        self.assertIn('findings', d); self.assertTrue(all(str(f['rule']).startswith('SEC-') for f in d['findings']))


if __name__ == '__main__':
    unittest.main()
