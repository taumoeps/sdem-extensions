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

    def test_a_retired_record_is_not_in_coverage(self):   # 0.4.4, SDEM MID-02 / LC-04: it has left the design
        self.a3['instances'].append(rec('APP-GONE', 'A3.ApplicationComponent', 'retired')); self.write()
        self.assertNotIn('APP-GONE', {r['id'] for r in S.coverage_rows(self.ws)})

    def test_the_viewer_draws_each_link_as_the_pack_says(self):   # 0.4.4, SDEM MID-07: one ArchiMate kind per link type — the manifest's overlay never differs
        import json as J
        here = Path(S.__file__).parent
        pack = {x['relationship']: x['archimate'] for x in J.loads((here / 'pack.json').read_text())['link_types']}
        links = J.loads((here / 'sdem-extension.json').read_text())['viewer']['overlay']['links']
        for rel, kind in links.items(): self.assertEqual(kind, pack[rel], rel)

    def test_a_field_is_protected_through_its_entity(self):
        r = {x['id']: x for x in S.coverage_rows(self.ws)}['F-NAME']
        self.assertTrue(r['protected']); self.assertEqual(r['protected_through'], ['ENT-LOG'])

    def test_protection_inherited_from_a_protected_whole_is_said_not_counted(self):   # MID-02: the view shows it, SDEM works it out
        r = {x['id']: x for x in S.coverage_rows(self.ws)}
        self.assertFalse(r['API-OP']['protected']); self.assertEqual(r['API-OP']['inherited_from'], ['IFC-API'])   # its interface's control
        self.assertNotIn('inherited_from', r['IFC-API'])                                                          # protected itself

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


class Inheritance(unittest.TestCase):   # MX-32a: a type another extension adds inside a layer is placed by its nearest SDEM type
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.ws, True)
        a3 = {'instances': [rec('SVC-1', 'ORG.A3.MicroService', 'active'), rec('ENT-P', 'A3.DataEntity', personal_information=True)],
              'relationships': [{'source': 'SVC-1', 'kind': 'access', 'target': 'ENT-P'}]}
        a4 = {'instances': [rec('FW-1', 'NET.A4.Firewall'), rec('ART-1', 'A4.Artifact')], 'relationships': []}
        for f, d in (('a1-business.json', {'instances': []}), ('a2-service-domain.json', {'instances': []}), ('a3-application.json', a3), ('a4-technology.json', a4),
                     ('security.json', {'instances': [ctl('SEC-SC7', 'SC-7', 'S5')], 'relationships': []}), ('mappings.json', {'mappings': [link('SEC-SC7', 'PROTECTS', 'FW-1')]})):
            (self.ws / f).write_text(json.dumps(d))
        S._CORE[str(self.ws.resolve())] = {'NET.A4.Firewall': ['A4.Node'], 'ORG.A3.MicroService': ['A3.ApplicationComponent'],
                                           'A4.Artifact': ['A4.InfrastructureComponent'], 'A4.Node': ['A4.InfrastructureComponent']}

    def test_a_subtype_is_in_scope_and_a_core_type_is_not_widened(self):
        rows = {r['id']: r for r in S.coverage_rows(self.ws)}
        self.assertTrue(rows['FW-1']['protected']); self.assertEqual(rows['FW-1']['kind_of'], 'A4.Node'); self.assertEqual(rows['FW-1']['security_layer'], 'S5')
        self.assertNotIn('ART-1', rows)   # A4.Artifact extends InfrastructureComponent, but SDEM's own types match exactly
        self.assertIn('FW-1', {x['id'] for x in S.threats_data(self.ws)})

    def test_s08_reaches_a_subtype_of_a_component(self):
        self.assertEqual({f['record'] for f in S.computed_findings(self.ws) if f['rule'] == 'SEC-S08'}, {'SVC-1'})


class Hardening(unittest.TestCase):   # AUD-08, AUD-09, AUD-11
    def test_version_ranges_are_read_strictly(self):
        self.assertTrue(S.supported('0.19.0', '>=0.19,<0.21')); self.assertFalse(S.supported('0.21.0', '>=0.19,<0.21'))
        self.assertTrue(S.supported('0.19.2', '>0.19.1,<=0.19.2')); self.assertTrue(S.supported('1.0.0', '==1.0'))
        with self.assertRaises(ValueError): S.supported('0.19.0', '~=0.19')   # never a silent pass

    def test_the_catalogue_finds_an_enhancement_by_its_id(self):
        out = __import__('io').StringIO()
        with __import__('contextlib').redirect_stdout(out): S.cmd_catalogue(SimpleNamespace(words=['IA-2(1)'], limit=5, json=True))
        self.assertIn('IA-2(1)', [c['id'] for c in json.loads(out.getvalue())['items']])

    def test_a_record_name_cannot_break_the_document(self):
        ws = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, ws, True)
        bad = 'Edge | gateway\n# Injected heading <script>x</script>'
        for f, d in (('a1-business.json', {'instances': []}), ('a2-service-domain.json', {'instances': []}), ('a4-technology.json', {'instances': []}),
                     ('a3-application.json', {'instances': [{**rec('IFC-1', 'A3.ApplicationInterface'), 'name': bad}], 'relationships': []}),
                     ('security.json', {'instances': [{**rec('THR-1', 'SEC.S.Threat', security_layer='S4', stride=['S|T'], likelihood='low', impact='low')}], 'relationships': []}),
                     ('mappings.json', {'mappings': [link('THR-1', 'THREATENS', 'IFC-1')]})):
            (ws / f).write_text(json.dumps(d))
        real = S.sdem
        S.sdem = lambda *a: SimpleNamespace(stdout=json.dumps({'findings': [], 'groups': [{'id': 'SEC', 'kind': 'standard'}]}) if a[:1] == ('comply',) else '{}', stderr='', returncode=0)
        try: md = S.document_md(ws)
        finally: S.sdem = real
        self.assertNotIn('\n# Injected', md); self.assertNotIn('<script>', md); self.assertIn('&lt;script&gt;', md)
        self.assertNotIn('&amp;lt;', md)   # escaped once, not twice
        row = next(l for l in md.splitlines() if l.startswith('| thr-1 (THR-1)'))   # the threats table's row
        self.assertEqual(len(row.split(' | ')), 5, row)   # the threats table keeps its five columns


if __name__ == '__main__':
    unittest.main()


class ArchiMateKinds(unittest.TestCase):   # SDEM MID-07: every link is ArchiMate's kind — the pack says which, for each of its link types
    def test_every_link_type_says_its_archimate_relationship(self):
        kinds = {'composition', 'aggregation', 'assignment', 'realization', 'serving', 'access', 'influence', 'triggering', 'flow', 'specialization', 'association'}
        pack = json.loads((Path(S.__file__).parent / 'pack.json').read_text(encoding='utf-8'))
        self.assertTrue(pack['link_types'])
        for x in pack['link_types']:
            self.assertIn(x.get('archimate'), kinds, f"{x['source_type']} {x['relationship']} {x['target_type']}")
