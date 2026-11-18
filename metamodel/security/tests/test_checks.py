"""The extension's own checks, without SDEM (audit 2026-11-19, AUD-02…AUD-06, AUD-12): a small made-up workspace on disk, read as
SDEM documents it. Runs anywhere — no SDEM needed. Synthetic data only."""
import datetime, json, shutil, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sdem_security as S  # noqa: E402


def rec(i, t, life='active', **at): return {'id': i, 'type': t, 'version': '1', 'name': i.lower(), 'lifecycle_status': life, 'attributes': at}
def ctl(i, cid, layer='S4', status='implemented', life='active', **at): return rec(i, 'SEC.S.SecurityControl', life, security_layer=layer, control_id=cid, implementation_status=status, **at)
def link(s, rel, t): return {'mapping_id': f'MAP-{s}-{t}', 'source': {'id': s}, 'relationship': rel, 'target': {'id': t}, 'status': 'approved'}


class Checks(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.ws, True)
        self.a1 = {'instances': [rec('ACT-CUST', 'A1.BusinessActor'), rec('PRC-PAY', 'A1.BusinessProcess')], 'relationships': []}
        self.a3 = {'instances': [rec('APP-LIVE', 'A3.ApplicationComponent'), rec('APP-NEW', 'A3.ApplicationComponent', 'planned'),
                                 rec('API-OP', 'A3.APIOperation'), rec('IFC-API', 'A3.ApplicationInterface'),
                                 rec('ENT-PAY', 'A3.DataEntity'), rec('ENT-LOG', 'A3.DataEntity'), rec('F-NAME', 'A3.DataAttribute', personal_information=True)],
                   'relationships': [{'source': 'APP-LIVE', 'kind': 'access', 'target': 'ENT-PAY'}, {'source': 'APP-NEW', 'kind': 'access', 'target': 'ENT-PAY'},
                                     {'source': 'API-OP', 'kind': 'access', 'target': 'ENT-LOG'}, {'source': 'ENT-LOG', 'kind': 'composition', 'target': 'F-NAME'},
                                     {'source': 'IFC-API', 'kind': 'composition', 'target': 'API-OP'}]}
        self.a3['instances'][4]['attributes']['personal_information'] = True
        self.sec = {'instances': [ctl('SEC-AU-NA', 'AU-12', status='not_applicable'), ctl('SEC-SC28', 'SC-28', 'S3'), ctl('SEC-AU-IFC', 'AU-2'),
                                  ctl('SEC-OLD', 'AC-3', life='retired', meets_requirements=['REQ-SEC-2'])], 'relationships': []}
        self.maps = [link('SEC-AU-NA', 'PROTECTS', 'APP-LIVE'), link('SEC-SC28', 'PROTECTS', 'ENT-LOG'), link('SEC-AU-IFC', 'PROTECTS', 'IFC-API')]
        self.reqs = [{'id': 'REQ-SEC-1', 'category': 'security', 'status': 'confirmed'}, {'id': 'REQ-SEC-2', 'category': 'security', 'status': 'proposed'},
                     {'id': 'REQ-SEC-3', 'category': 'security', 'status': 'superseded'}, {'id': 'REQ-SEC-4', 'category': 'security', 'status': 'retired'}]
        self.write()

    def write(self, exceptions=None):
        for f, d in (('a1-business.json', self.a1), ('a2-service-domain.json', {'instances': []}), ('a3-application.json', self.a3),
                     ('a4-technology.json', {'instances': []}), ('security.json', self.sec), ('mappings.json', {'mappings': self.maps}),
                     ('requirements.json', {'requirements': self.reqs})):
            (self.ws / f).write_text(json.dumps(d))
        if exceptions is not None: (self.ws / 'exceptions.json').write_text(json.dumps({'exceptions': exceptions}))

    def found(self, rule, today=None): return {f['record']: f['outcome'] for f in S.computed_findings(self.ws, today) if f['rule'] == rule}

    def test_a_control_that_cannot_act_does_not_count(self):   # AUD-03
        self.assertEqual(self.found('SEC-S08')['APP-LIVE'], 'non_compliant')   # its only audit control is not_applicable
        rows = {r['id']: r for r in S.coverage_rows(self.ws)}
        self.assertFalse(rows['APP-LIVE']['protected']); self.assertEqual(rows['APP-LIVE']['inactive_controls'], ['SEC-AU-NA'])

    def test_a_planned_subject_is_unresolved_not_failed(self):   # AUD-02, PR-11a
        self.assertEqual(self.found('SEC-S08')['APP-NEW'], 'unresolved')

    def test_s07_asks_only_live_requirements_and_checks_the_ids(self):   # AUD-05
        f = self.found('SEC-S07')
        self.assertEqual(f.get('REQ-SEC-1'), 'non_compliant')   # confirmed, no control meets it
        self.assertEqual(f.get('REQ-SEC-2'), 'unresolved')       # proposed; and the only control naming it is retired
        self.assertNotIn('REQ-SEC-3', f); self.assertNotIn('REQ-SEC-4', f)   # superseded, retired: they ask nothing
        self.sec['instances'].append(ctl('SEC-AC3', 'AC-3', meets_requirements=['REQ-NOPE'])); self.write()
        self.assertEqual(self.found('SEC-S07').get('SEC-AC3'), 'non_compliant')   # it names a requirement the registry does not hold

    def test_s08_reaches_fields_and_operations(self):   # AUD-12
        f = self.found('SEC-S08')
        self.assertNotIn('API-OP', f)   # reads a field's personal data, but its interface's AU-2 audits it
        self.maps = [m for m in self.maps if m['source']['id'] != 'SEC-AU-IFC']; self.write()
        self.assertEqual(self.found('SEC-S08').get('API-OP'), 'non_compliant')

    def test_a_persons_exception_holds_a_computed_finding(self):   # AUD-02, MX-17
        today = datetime.date(2026, 11, 19)
        self.write([{'id': 'EXC-001', 'rule': 'SEC-S08', 'records': ['APP-LIVE'], 'expires': '2026-12-31'}])
        self.assertEqual(self.found('SEC-S08', today)['APP-LIVE'], 'exception_approved')
        self.assertEqual(self.found('SEC-S08', datetime.date(2027, 1, 1))['APP-LIVE'], 'non_compliant')   # it comes back the day after it ends

    def test_scope_is_the_packs_link_types(self):   # AUD-04: coverage = what a control can protect; the checklist = what a threat can threaten
        rows = {r['id'] for r in S.coverage_rows(self.ws)}
        self.assertNotIn('ACT-CUST', rows)   # no control protects an actor ...
        self.assertIn('ACT-CUST', {x['id'] for x in S.threats_data(self.ws)})   # ... but an actor can be spoofed
        self.assertFalse([t for t in S.THREATENABLE if t not in S.STRIDE], 'every type a threat can threaten has its STRIDE categories')
        self.assertEqual(S.STRIDE['A1.BusinessProcess'], 'STRIDE'); self.assertIn('R', S.STRIDE['A3.APIOperation'])   # AUD-07, spec §7

    def test_a_field_is_protected_through_its_entity(self):
        r = {x['id']: x for x in S.coverage_rows(self.ws)}['F-NAME']
        self.assertTrue(r['protected']); self.assertEqual(r['protected_through'], ['ENT-LOG'])

    def test_an_empty_security_layer_is_said(self):
        self.assertEqual(self.found('SEC-LAYER'), {'S1': 'unresolved', 'S2': 'unresolved', 'S5': 'unresolved'})

    def test_review_never_reports_all_clear_from_an_answer_it_cannot_read(self):   # AUD-06
        real = S.sdem
        try:
            for out in ('not json', json.dumps({'items': []}), json.dumps({'findings': [], 'groups': [{'id': 'OTHER', 'kind': 'standard'}]})):
                S.sdem = lambda *a, out=out: SimpleNamespace(stdout=out, stderr='', returncode=0)
                with self.assertRaises(S.ReviewError): S.review_data(self.ws)
            mine = {'rule': 'SEC-S03a', 'standard': {'id': 'SEC'}, 'record': 'PATH-X', 'outcome': 'unresolved'}
            theirs = {'rule': 'SEC-ORG-1', 'standard': {'id': 'ORG'}, 'record': 'APP-LIVE', 'outcome': 'non_compliant'}   # an organisation's own SEC- rule
            S.sdem = lambda *a: SimpleNamespace(stdout=json.dumps({'findings': [mine, theirs], 'groups': [{'id': 'SEC', 'kind': 'standard'}]}), stderr='', returncode=0)
            rules = {f['rule'] for f in S.review_data(self.ws)['findings']}
            self.assertIn('SEC-S03a', rules); self.assertNotIn('SEC-ORG-1', rules)
        finally: S.sdem = real


if __name__ == '__main__':
    unittest.main()
