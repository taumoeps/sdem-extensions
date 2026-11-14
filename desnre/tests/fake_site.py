"""A stand-in for the DESNRE site's API, for this extension's tests: the same routes, answers and rules (DP-10…DP-14, DA-20…DA-40)
— accounts with personal tokens and their own pages, the owner's hero page, drafts not public, the made-up mark and the schema
checked — with a store in memory. The real handlers live with the
site (desnre-site: api/_lib/models.js) and are tested there; this checks the extension speaks the same contract."""
import json, re, secrets, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import sdem_desnre as X

NAME = re.compile(X.SCHEMA['properties']['name']['pattern'])


class Site:
    def __init__(self, publish_token='', approve_token='', people=None):
        self.tokens = {'publish': publish_token, 'approve': approve_token}
        self.people = dict(people or {})   # personal token -> (username, admin)
        self.store = {}   # path -> text
        site = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def answer(self, code, body):
                data = (body if isinstance(body, str) else json.dumps(body)).encode()
                self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data)

            def person(self):
                return site.people.get(self.headers.get('Authorization', '')[7:])

            def allowed(self, which):   # the hero page: the shared tokens, or an admin's personal token
                p = self.person()
                return (p and p[1]) or (bool(site.tokens[which]) and self.headers.get('Authorization', '') == 'Bearer ' + site.tokens[which])

            def route(self):
                u = urlparse(self.path); q = parse_qs(u.query)
                m = re.match(r'^/api/models(?:/([^/]+))?(/approve)?$', u.path)
                if m: return (m.group(1), bool(m.group(2)), q)
                m = re.match(r'^/api/u/([^/]+)/([^/]+)(/approve)?$', u.path)
                return (m.group(1) + '/' + m.group(2), bool(m.group(3)), q) if m else (None, None, None)

            def mine(self, name):   # a person's own page: only its owner
                p = self.person()
                return '/' not in name or (p and name.split('/')[0] == p[0])

            def do_GET(self):
                path = urlparse(self.path).path
                if path == '/api/me':
                    p = self.person()
                    if not p: return self.answer(401, {'error': 'not allowed — wrong or missing token'})
                    return self.answer(200, {'username': p[0], 'admin': p[1], 'page': f'http://{self.headers["Host"]}/u/{p[0]}'})
                m = re.match(r'^/api/u/([^/]+)$', path)
                if m:
                    items = [json.loads(v) for k, v in sorted(site.store.items()) if k.startswith(f'meta/{m.group(1)}/')]
                    return self.answer(200, {'owner': m.group(1), 'count': len(items), 'items': items})
                name, _, q = self.route()
                if name is None and path == '/api/models':
                    items = [json.loads(v) for k, v in sorted(site.store.items()) if k.startswith('meta/') and k.count('/') == 1]
                    return self.answer(200, {'count': len(items), 'items': items})
                if not name: return self.answer(400, {'error': 'bad name'})
                if 'draft' in q:
                    t = site.store.get(f"draft/{name}/{q['draft'][0]}.json")
                else:
                    t = site.store.get(f'live/{name}.json')
                return self.answer(200, t) if t else self.answer(404, {'error': 'not found'})

            def do_POST(self):
                name, approve, _ = self.route()
                if not name: return self.answer(400, {'error': 'bad name'})
                body = self.rfile.read(int(self.headers.get('Content-Length') or 0)).decode()
                theirs = '/' in name
                if theirs and not self.mine(name): return self.answer(403, {'error': 'you can send drafts only to your own page'})
                if not theirs and not self.allowed('approve' if approve else 'publish'):
                    return self.answer(403 if self.person() else 401, {'error': "the hero page is the site owner's — send your model to your own page"})
                if approve:
                    ds = [k for k in site.store if k.startswith(f'draft/{name}/')]
                    if not ds: return self.answer(404, {'error': f'no draft called {name}'})
                    text = site.store.pop(ds[0]); m = json.loads(text)
                    kept = f'live/{name}.json' in site.store
                    if kept: site.store[f'previous/{name}.json'] = site.store[f'live/{name}.json']
                    site.store[f'live/{name}.json'] = text
                    site.store[f'meta/{name}.json'] = json.dumps({'name': name, 'workspace': m['source']['workspace'], 'sdem': m['source']['sdem'],
                                                                  'metamodel': m['source']['metamodel'], 'records': m['counts']['records'], 'published': 'today'})
                    url = f'http://{self.headers["Host"]}/u/{name}' if theirs else f'http://{self.headers["Host"]}/?model={name}'
                    return self.answer(200, {'name': name, 'url': url, 'previous_kept': kept, **({'page': url.rsplit('/', 1)[0]} if theirs else {})})
                m = json.loads(body)
                if m.get('data') != 'synthetic': return self.answer(422, {'error': 'only made-up models'})
                if m.get('name') != name.split('/')[-1] or X.validate(m): return self.answer(422, {'error': 'the model does not match its schema'})
                for k in [k for k in site.store if k.startswith(f'draft/{name}/')]: del site.store[k]
                key = secrets.token_hex(16); site.store[f'draft/{name}/{key}.json'] = json.dumps(m)
                prev = f'/u/{name}?draft={key}' if theirs else f'/?model={name}&draft={key}'
                return self.answer(201, {'name': name, 'draft': key, 'preview': f'http://{self.headers["Host"]}{prev}', 'public': False})

            def do_DELETE(self):
                name, _, _ = self.route()
                if ('/' in name and not (self.mine(name) or (self.person() or ('', False))[1])) or ('/' not in name and not self.allowed('approve')):
                    return self.answer(403, {'error': 'not yours to remove'})
                gone = [k for k in site.store if k in (f'live/{name}.json', f'meta/{name}.json', f'previous/{name}.json') or k.startswith(f'draft/{name}/')]
                if not gone: return self.answer(404, {'error': f'nothing called {name}'})
                for k in gone: del site.store[k]
                return self.answer(200, {'name': name, 'removed': True})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.server.shutdown(); self.server.server_close()
