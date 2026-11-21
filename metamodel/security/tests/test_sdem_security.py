"""sdem-security against SDEM's bundled example (EXT-14): the pack is a valid metamodel extension, a person switches it on, controls
and threats go in as a change set, their links reach A1–A4, and coverage, threats and review report from the workspace.
Needs SDEM installed in the same environment (pip install -e security there); skipped otherwise. Synthetic data only."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sdem_security as S  # noqa: E402

SDEM = shutil.which('sdem', path=str(Path(sys.executable).parent)) or shutil.which('sdem')
import os
REQUIRED = os.environ.get('SDEM_REQUIRED') == '1'   # in CI: SDEM is installed, so these tests run — never skipped
if REQUIRED and not SDEM: raise SystemExit('SDEM_REQUIRED=1 but no sdem in this environment')
HAS_MX16 = bool(SDEM) and subprocess.run([SDEM, 'profile', 'exclude', '--help'], capture_output=True).returncode == 0   # SDEM 0.19.0 as tagged 2026-11-19: exclude, computed rules
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


@unittest.skipUnless(SDEM or REQUIRED, 'SDEM is not installed in this environment')
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

    def test_the_standard_checks_protocol_and_likelihood_too(self):  # SEC-S03b, SEC-S06b
        ids = {r['id'] for r in json.loads((Path(S.__file__).parent / 'security-standard.json').read_text())['rules']}
        self.assertTrue({'SEC-S03a', 'SEC-S03b', 'SEC-S06a', 'SEC-S06b'} <= ids)

    def test_a_security_requirement_no_control_meets_is_found(self):  # SEC-S07
        f = self.ws / 'requirements.json'; before = f.read_bytes()   # restored byte for byte — write_text would change line endings on Windows
        d = json.loads(before.decode('utf-8')); d['requirements'].append({'id': 'REQ-SEC-01', 'version': 1, 'status': 'proposed', 'name': 'Payment data is protected at rest',
            'statement': 'Payment instructions are encrypted at rest.', 'owner_layer': 'A3', 'category': 'security', 'scope': 'record', 'subject': 'ENT-PAY-INSTR'})
        f.write_text(json.dumps(d))
        try:
            found = [x for x in S.computed_findings(self.ws) if x['rule'] == 'SEC-S07']
            self.assertEqual([x['record'] for x in found], ['REQ-SEC-01'])
        finally: f.write_bytes(before)

    def test_a_component_on_personal_data_without_audit_is_found(self):  # SEC-S08
        found = sorted(x['record'] for x in S.computed_findings(self.ws) if x['rule'] == 'SEC-S08')
        self.assertEqual(found, ['CMP-PAY-CAPTURE', 'CMP-PAY-EXEC', 'CMP-PAY-VALIDATE'])   # all three read the payment instruction; none is audited

    def test_the_document_reads_the_review_coverage_and_checklist(self):  # sdem security document
        md = run('security', 'document', '--workspace', self.ws)
        self.assertTrue(md.startswith('# Security review'), md[:60])
        for h in ('## Summary', '## 1. Findings from the security rules', '## 2. Records no control protects', '## 3. Coverage by security layer',
                  '## 4. Threats and what mitigates them', '## 5. STRIDE checklist'):
            self.assertIn(h, md)
        self.assertIn('SEC-S08', md); self.assertIn('Payment instruction disclosed (THR-DISCLOSE)', md)   # a finding, and the threat with its name

    def test_review_runs_the_security_standard(self):  # MX-14 — and finds something (an empty list would pass all(); AUD-06)
        d = run('security', 'review', '--workspace', self.ws, '--json')
        self.assertTrue(d['findings'])
        self.assertTrue(all(f.get('computed') or (f.get('standard') or {}).get('id') == 'SEC' for f in d['findings']))
        self.assertIn('SEC-LAYER', {f['rule'] for f in d['findings']})   # the made-up design has controls only in S3

    def test_the_standards_rules_fire(self):  # the audit's test gap: each rule shown firing, not only present (active records: a planned one is unresolved, LC-04)
        ws = self.tmp / 'fire'; shutil.copytree(self.ws, ws)
        more = {'layer': 'S', 'reason': 'made-up records that break two rules', 'changes': [
            {'op': 'add', 'record': {'id': 'SEC-DONE', 'type': 'SEC.S.SecurityControl', 'version': '1', 'name': 'Implemented, no evidence', 'lifecycle_status': 'active',
                                     'attributes': {'security_layer': 'S4', 'control_id': 'AC-3', 'csf_function': 'PR', 'control_kind': 'preventive', 'implementation_status': 'implemented'}}},
            {'op': 'add', 'record': {'id': 'THR-LIKELY', 'type': 'SEC.S.Threat', 'version': '1', 'name': 'Likely, unmitigated', 'lifecycle_status': 'active',
                                     'attributes': {'security_layer': 'S4', 'stride': ['S'], 'likelihood': 'high', 'impact': 'low'}}}], 'relationships': {'add': []}}
        (self.tmp / 'more.json').write_text(json.dumps(more))
        run('security', 'propose', self.tmp / 'more.json', '--workspace', ws, '--person', 'steven')
        found = {(f['rule'], f['record']): f['outcome'] for f in run('security', 'review', '--workspace', ws, '--json')['findings']}
        self.assertEqual(found.get(('SEC-S05a', 'SEC-DONE')), 'non_compliant')    # implemented with no evidence
        self.assertEqual(found.get(('SEC-S05b', 'SEC-DONE')), 'non_compliant')    # implemented with nothing enforcing it
        self.assertEqual(found.get(('SEC-S06b', 'THR-LIKELY')), 'non_compliant')  # high likelihood, nothing mitigates it

    @unittest.skipUnless(HAS_MX16, 'needs SDEM 0.19.0 as tagged on 2026-11-19 or later (MX-16, MX-17)')
    def test_a_person_may_grant_an_exception_to_a_computed_rule(self):  # MX-17, AUD-02
        out = run('exception', 'grant', '--workspace', self.ws, '--rule', 'SEC-S08', '--records', 'CMP-PAY-CAPTURE', '--expires', '2099-12-31',
                  '--reason', 'audit lands with the platform release', '--person', 'steven', '--dry-run')
        self.assertIn('SEC-S08', out)

    @unittest.skipUnless(HAS_MX16, 'needs SDEM 0.19.0 as tagged on 2026-11-19 or later (MX-16, MX-17)')
    def test_removing_security_leaves_a_design_that_passes(self):  # MX-16, AUD-01
        ws = self.tmp / 'removed'; shutil.copytree(self.ws, ws)
        d = run('security', 'remove', '--workspace', ws, '--person', 'steven', '--reason', 'security moves to its own workspace', '--json')
        self.assertTrue(d['connections_retired']); self.assertFalse((ws / 'security.json').exists())
        self.assertTrue((ws / d['archive']).exists())
        self.assertTrue(run('check', '--workspace', ws, '--require-recorded', '--json')['ok'])
        self.assertNotIn('ext:security', json.loads((ws / 'sdem-profile.json').read_text())['includes'])
        back = run('security', 'restore', '--archive', d['archive'], '--workspace', ws, '--person', 'steven', '--reason', 'back on', '--json')   # EL-06
        self.assertTrue((ws / 'security.json').exists()); self.assertEqual(sorted(back['connections']), sorted(d['connections_retired']))
        run('security', 'remove', '--workspace', ws, '--person', 'steven', '--reason', 'off again')
        dry = run('security', 'purge', '--workspace', ws, '--person', 'steven', '--reason', 'a data request', '--dry-run', '--json')   # EL-16
        self.assertEqual(len(dry['purged']), 2); self.assertTrue(dry['not_reached'])


HAS_020 = bool(SDEM) and '--form' in subprocess.run([SDEM, 'new', '--help'], capture_output=True, text=True).stdout   # an SDEM that makes the 0.20 form


@unittest.skipUnless(HAS_020, 'SDEM before 0.20 has no design without BIAN in the 0.20 form')
class WithoutBian(unittest.TestCase):   # DL-22: a design without BIAN (A1 Business, A2 Data, A3 Application, A4 Technology) and security
    def test_its_bian_security_layer_is_not_asked_for(self):
        tmp = Path(tempfile.mkdtemp()); ws = tmp / 'ws'
        try:
            run('new', '--workspace', ws, '--person', 'steven', '--core', '--form', '0.20')
            (tmp / 'cap.json').write_text(json.dumps({'layer': 'business', 'reason': 'a made-up design', 'changes': [{'op': 'add', 'record': {
                'id': 'CAP-LEND', 'type': 'A1.BusinessCapability', 'version': '1', 'name': 'Lending', 'lifecycle_status': 'planned'}}]}))   # a design with something in it: comply reports its standards
            run('change', 'propose', tmp / 'cap.json', '--workspace', ws, '--agent', 'sdem-a1-business', '--person', 'steven')
            (tmp / 'app.json').write_text(json.dumps({'layer': 'application', 'reason': 'a made-up design', 'changes': [{'op': 'add', 'record': {
                'id': 'APP-LOANS', 'type': 'A3.ApplicationComponent', 'version': '1', 'name': 'Loans system', 'lifecycle_status': 'planned'}},
                {'op': 'add', 'record': {'id': 'IFC-LOANS', 'type': 'A3.ApplicationInterface', 'version': '1', 'name': 'Loans API', 'lifecycle_status': 'planned'}}]}))   # an interface: what the security standard's rules look at
            run('change', 'propose', tmp / 'app.json', '--workspace', ws, '--agent', 'sdem-a3-application', '--person', 'steven')
            run('profile', 'include', 'ext:security', '--workspace', ws, '--person', 'steven', '--reason', 'security design')
            run('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'the security layer')
            d = run('security', 'review', '--workspace', ws, '--json')
            empty = sorted(f['record'] for f in d['findings'] if f['rule'] == 'SEC-LAYER')
            self.assertEqual(empty, ['S1', 'S3', 'S4', 'S5'])   # every security layer the design has, said empty — never S2: it has no service domains
        finally: shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
