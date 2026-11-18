"""EL-07, EL-08: the published state of each extension — read from SDEM's recorded decisions, never from a missing file. Synthetic data."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sdem_desnre as D  # noqa: E402


def decision(ws, gid, kind, subject, at, person='steven', **details):
    (ws / 'decisions').mkdir(exist_ok=True)
    (ws / 'decisions' / f'{gid}.json').write_text(json.dumps({'id': gid, 'kind': kind, 'subject': subject, 'named_person': person, 'at': at, 'details': details}))


class ExtensionState(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def test_off_comes_from_the_decision_not_a_missing_file(self):
        decision(self.ws, 'GD-1', 'include_in_profile', 'ext:security', '2026-11-18T04:00:00+00:00')
        decision(self.ws, 'GD-2', 'exclude_from_profile', 'ext:security', '2026-11-19T09:00:00+00:00', reason='moved to its own workspace', archive='archive/ext-security-2026-11-19.json')
        st, purges = D.extension_states(self.ws, {'sdem-profile.json': {'includes': []}}, {})
        self.assertEqual(st['security']['state'], 'off'); self.assertEqual(st['security']['reason'], 'moved to its own workspace')
        self.assertEqual(st['security']['archive'], 'archive/ext-security-2026-11-19.json'); self.assertNotIn('results', st['security'])
        self.assertEqual(purges, [])

    def test_on_carries_its_results_stamped_and_never_used_is_absent(self):
        decision(self.ws, 'GD-1', 'include_in_profile', 'ext:security', '2026-11-18T04:00:00+00:00')
        st, _ = D.extension_states(self.ws, {'sdem-profile.json': {'includes': ['ext:security']}}, {'security': {'review': {'findings': []}}})
        self.assertEqual(st['security']['state'], 'on'); self.assertEqual(st['security']['since'], '2026-11-18'); self.assertTrue(st['security']['results_at'])
        self.assertNotIn('resilience', st)

    def test_a_purge_travels_to_the_site(self):
        decision(self.ws, 'GD-9', 'purge_extension_data', 'ext:security', '2026-11-20T09:00:00+00:00')
        _, purges = D.extension_states(self.ws, {'sdem-profile.json': {'includes': []}}, {})
        self.assertEqual(purges, [{'extension': 'security', 'decision': 'GD-9', 'at': '2026-11-20'}])

    def test_the_change_list_against_what_is_live(self):   # EL-08, and a design published before 0.8.0 (results only) reads as on
        on = {'extensions': {'security': {'state': 'on', 'version': '0.2.0', 'results': {'review': 1}}}}
        off = {'extensions': {'security': {'state': 'off', 'since': '2026-11-19', 'by': 'steven', 'reason': 'r'}}}
        self.assertTrue(D.extension_changes(None, on)[0].startswith('+ security'))
        self.assertTrue(D.extension_changes(on, off)[0].startswith('− security'))
        self.assertTrue(D.extension_changes({'extensions': {'security': {'review': 2}}}, on)[0].startswith('~ security'))
        self.assertEqual(D.extension_changes(on, on), [])


if __name__ == '__main__':
    unittest.main()
