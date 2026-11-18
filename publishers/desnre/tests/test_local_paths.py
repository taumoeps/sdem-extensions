"""0.7.8: the published workspace names no folder on the architect's computer (synthetic paths only)."""
import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sdem_desnre as D  # noqa: E402


class NoLocalPaths(unittest.TestCase):
    def test_paths_become_relative_or_a_file_name_and_api_paths_stay(self):
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t) / 'ws'; (ws / 'std').mkdir(parents=True); (ws / 'std' / 'a.json').write_text('{}')
            other = Path(t) / 'elsewhere.json'; other.write_text('{}')
            got = D.no_local_paths({'chain': [{'file': str(ws / 'std' / 'a.json')}], 'inc': [str(other)], 'workspace': str(ws),
                                    'api': '/payments/{id}', 'text': 'a sentence'}, ws)
            self.assertEqual(got['chain'][0]['file'], 'std/a.json'); self.assertEqual(got['inc'], ['elsewhere.json'])
            self.assertEqual(got['workspace'], '.'); self.assertEqual(got['api'], '/payments/{id}'); self.assertEqual(got['text'], 'a sentence')

    def test_no_crash_no_username_and_paths_inside_text(self):   # AUD-25
        home = str(Path.home())
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t) / 'ws'; ws.mkdir()
            got = D.no_local_paths({'d': '~200ms', 'h': home, 'msg': f'see {home}/nowhere/x.json for it', 'etc': 'logs go to /tmp on the node', 'api': '/payments/{id}'}, ws)
            self.assertEqual(got['d'], '~200ms'); self.assertNotIn(Path(home).name, got['h']); self.assertNotIn(home, got['msg']); self.assertIn('x.json', got['msg'])
            self.assertEqual(got['etc'], 'logs go to /tmp on the node'); self.assertEqual(got['api'], '/payments/{id}')


if __name__ == '__main__':
    unittest.main()
