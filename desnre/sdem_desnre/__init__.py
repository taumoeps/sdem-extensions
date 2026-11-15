"""sdem desnre — puts a made-up SDEM workspace on your own page of the DESNRE site, as a 3D view.

    sdem desnre login                    once: paste a token from desnre.vercel.app/account (kept in your Keychain)
    sdem desnre create <workspace>       check it, build the 3D model, send it as a draft — not public; opens the preview
    sdem desnre publish <workspace>      make it live on your page: desnre.vercel.app/u/<you>/<name>
    sdem desnre list | whoami | remove <workspace> | logout

The first SDEM extension (SDEM's docs/design/sdem-extensions-spec.md, EXT-01…EXT-15; the DESNRE site's
docs/desnre-publish-design.md and desnre-accounts-design.md). Installed next to SDEM (pip install), it runs as `sdem desnre …`;
on its own as `sdem-desnre …`. It uses SDEM only through its command line with --json and the workspace files — never SDEM's
code. The first `create` of a workspace asks you to confirm it is made-up data, and records who said so. Your token comes from
the environment (DESNRE_TOKEN) or, on a Mac, the Keychain. The hero page is the site owner's (--hero). Standard library only.
"""
import argparse, datetime, json, math, os, re, shlex, shutil, subprocess, sys, urllib.error, urllib.request, webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / 'sdem-extension.json').read_text(encoding='utf-8'))
SCHEMA = json.loads((HERE / 'desnre-model.schema.json').read_text(encoding='utf-8'))
GENERATOR = f"sdem-desnre {MANIFEST['version']}"
SITE = os.environ.get('DESNRE_SITE', 'https://desnre.vercel.app')
MARK = Path('extensions') / 'desnre.json'
NAME = re.compile(SCHEMA['properties']['name']['pattern'])
MAX_BYTES = 4_000_000   # DP-10, DW-41: the 3D model and its workspace together


class PublishError(Exception):
    """Why the workspace cannot be published — said plainly, never half-done."""


# ---------- SDEM, through its public command line only (EXT-02, EXT-03) ----------

def sdem_command(ws=None):
    """How to run SDEM: $SDEM_CMD; else the `sdem` beside this Python; else `sdem` on the PATH; else `python -m sdem` from an SDEM checkout above the workspace."""
    if os.environ.get('SDEM_CMD'):
        return shlex.split(os.environ['SDEM_CMD']), {}
    beside = shutil.which('sdem', path=str(Path(sys.executable).parent))   # installed next to SDEM (the same environment): that SDEM
    if beside:
        return [beside], {}
    if shutil.which('sdem'):
        return ['sdem'], {}
    root = next((p for p in [Path(ws or '.').resolve(), *Path(ws or '.').resolve().parents] if (p / 'sdem' / '__init__.py').exists()), None)
    if not root:
        raise PublishError('SDEM is not installed (pip install sdem), and no SDEM checkout was found above the workspace — or set SDEM_CMD')
    return [sys.executable, '-m', 'sdem'], {'PYTHONPATH': str(root) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def run_sdem(ws, args):
    cmd, env = sdem_command(ws)
    return subprocess.run(cmd + args, capture_output=True, text=True, env={**os.environ, **env}, timeout=300)


def version_tuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', v)[:3])


def in_range(v, spec):
    """'>=0.18,<0.19' — every clause must hold."""
    for clause in spec.split(','):
        op, want = re.match(r'\s*(>=|<=|==|<|>)\s*([\d.]+)', clause).groups()
        a, b = version_tuple(v), version_tuple(want)
        b = b + (0,) * (len(a) - len(b))
        if not {'>=': a >= b, '<=': a <= b, '==': a == b, '<': a < b, '>': a > b}[op]:
            return False
    return True


def sdem_version(ws):
    r = run_sdem(ws, ['--version'])
    m = re.search(r'(\d+\.\d+\.\d+)', r.stdout + r.stderr)
    if r.returncode != 0 or not m:
        raise PublishError(f'could not read SDEM\'s version: {(r.stderr or r.stdout).strip()[-200:]}')
    return m.group(1)


def metamodel_version(ws):
    found = set()
    for f in FILES:
        with open(os.path.join(ws, f), encoding='utf-8') as fh:
            found.add(json.load(fh).get('metamodel_version', ''))
    if len(found) != 1 or not next(iter(found)):
        raise PublishError(f'the four layer files do not name one metamodel version: {sorted(found)}')
    return found.pop()


# ---------- the gates (DP-01, DP-02) ----------

def read_mark(ws):
    p = Path(ws) / MARK
    try:
        m = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise PublishError(f'{p} is missing — a person marks a made-up workspace with: sdem-desnre mark {ws} --by "<name>" --synthetic (EXT-11)')
    if m.get('data') != 'synthetic' or not m.get('marked_by'):
        raise PublishError(f'{p} does not say "data": "synthetic" with who marked it — only made-up workspaces go on the public site (EXT-10)')
    return m


def gates(ws, need_mark=True):
    """Everything that must hold before a model is built: SDEM and metamodel versions, the synthetic mark, a clean check."""
    v = sdem_version(ws)
    if not in_range(v, MANIFEST['sdem']):
        raise PublishError(f"SDEM {v} is outside the versions this extension supports ({MANIFEST['sdem']}) — update sdem-desnre (EXT-04)")
    mm = metamodel_version(ws)
    if not in_range(mm, MANIFEST['metamodel']):
        raise PublishError(f"metamodel {mm} is outside the versions this extension supports ({MANIFEST['metamodel']}) (EXT-04)")
    if need_mark: read_mark(ws)
    r = run_sdem(ws, ['check', '--workspace', str(ws), '--json'])
    try:
        c = json.loads(r.stdout)
    except ValueError:
        raise PublishError(f'sdem check gave no JSON: {(r.stderr or r.stdout).strip()[-300:]}')
    if not c.get('ok'):
        errs = [f'{k}: {e}' for k, v in (c.get('report') or {}).items() for e in v][:5]
        raise PublishError('sdem check found errors — fix them first (EXT-09):\n  ' + '\n  '.join(errs))
    return v, mm


# ---------- the model's format (DP-04): a small validator for the schema's keywords ----------

def validate(value, schema=SCHEMA, at='model'):
    errs = []
    t = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'number': (int, float), 'integer': int}
    if t and not (isinstance(value, types[t]) and not (t in ('number', 'integer') and isinstance(value, bool))):
        return [f'{at}: should be {t}']
    if 'const' in schema and value != schema['const']:
        errs.append(f'{at}: should be {schema["const"]!r}')
    if 'pattern' in schema and isinstance(value, str) and not re.search(schema['pattern'], value):
        errs.append(f'{at}: does not match {schema["pattern"]}')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0): errs.append(f'{at}: needs at least {schema["minItems"]} item(s)')
        if len(value) > schema.get('maxItems', 10**9): errs.append(f'{at}: at most {schema["maxItems"]} item(s)')
        if 'items' in schema:
            for i, x in enumerate(value):
                errs += validate(x, schema['items'], f'{at}[{i}]')
                if len(errs) > 20: break
    if isinstance(value, dict):
        errs += [f'{at}: {k} is missing' for k in schema.get('required', []) if k not in value]
        for k, s in schema.get('properties', {}).items():
            if k in value: errs += validate(value[k], s, f'{at}.{k}')
    if at == 'model' and not errs:   # every edge joins two nodes
        n = len(value['nodes'])
        errs += [f'model.edges[{i}]: names a node that is not there' for i, e in enumerate(value['edges']) if not (0 <= e[0] < n and 0 <= e[1] < n)][:5]
    return errs


FILES = ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json']

# record type -> shape key in the page's SH table
SHAPE = {
    'A1.BusinessCapability': 'cap', 'A1.ValueStream': 'proc', 'A1.ValueStreamStage': 'proc',
    'A1.BusinessProcess': 'proc', 'A1.BusinessActivity': 'proc', 'A1.BusinessObject': 'doc',
    'A1.BusinessRole': 'role',
    'A2.BusinessDomain': 'obj', 'A2.ServiceDomain': 'svc', 'A2.AssetType': 'obj',
    'A2.FunctionalPattern': 'art', 'A2.ControlRecord': 'doc', 'A2.BehaviorQualifier': 'art',
    'A2.ServiceGroup': 'obj', 'A2.ServiceOperation': 'op', 'A2.BusinessScenario': 'proc',
    'A2.BusinessObject': 'doc', 'A2.BusinessObjectAttribute': 'tbl',
    'A3.ApplicationComponent': 'comp', 'A3.ApplicationService': 'rbox', 'A3.ApplicationInterface': 'dep',
    'A3.APIOperation': 'api', 'A3.DataEntity': 'tbl', 'A3.Event': 'evt',
    'A4.SystemSoftware': 'node', 'A4.TechnologyService': 'rbox', 'A4.DeploymentEnvironment': 'obj',
    'A4.Deployment': 'dep', 'A4.CommunicationNetwork': 'net', 'A4.Artifact': 'img',
}
DATABASE = re.compile(r'postgres|mysql|oracle|sql server|database|\bdb\b', re.I)   # system software drawn as a database

# zones per layer: (label, [types], x0, z0, x1, z1) on the 6 x 6 plate (-3..3)
ZONES = [
    [('Capabilities', ['A1.BusinessCapability'], -2.8, -2.7, -0.9, -1.2),
     ('Value stream', ['A1.ValueStream', 'A1.ValueStreamStage'], -0.6, -2.7, 2.8, -1.2),
     ('Processes', ['A1.BusinessProcess', 'A1.BusinessActivity'], -2.8, -0.9, 2.8, 1.0),
     ('Actors', ['A1.BusinessRole'], -2.8, 1.3, -0.9, 2.7),
     ('Information', ['A1.BusinessObject'], -0.6, 1.3, 2.8, 2.7)],
    [('Service domains', ['A2.BusinessDomain', 'A2.ServiceDomain'], -2.8, -2.7, 2.8, -1.7),
     ('Asset types and patterns', ['A2.AssetType', 'A2.FunctionalPattern'], -2.8, -1.4, 0.0, 0.0),
     ('Control record', ['A2.ControlRecord', 'A2.BehaviorQualifier'], 0.3, -1.4, 2.8, 0.0),
     ('Operations', ['A2.ServiceGroup', 'A2.ServiceOperation'], -2.8, 0.3, 0.9, 2.7),
     ('Scenario and objects', ['A2.BusinessScenario', 'A2.BusinessObject', 'A2.BusinessObjectAttribute'], 1.2, 0.3, 2.8, 2.7)],
    [('Components', ['A3.ApplicationComponent'], -2.8, -2.7, 2.8, -1.6),
     ('Service and interface', ['A3.ApplicationService', 'A3.ApplicationInterface'], -2.8, -1.3, -0.9, 0.2),
     ('APIs', ['A3.APIOperation'], -0.6, -1.3, 2.8, 0.9),
     ('Data and events', ['A3.DataEntity', 'A3.Event'], -2.8, 1.2, 2.8, 2.7)],
    [('Platforms', ['A4.SystemSoftware'], -2.8, -2.7, 0.4, -1.3),
     ('Technology services', ['A4.TechnologyService'], 0.7, -2.7, 2.8, -1.3),
     ('Environments and deployments', ['A4.DeploymentEnvironment', 'A4.Deployment'], -2.8, -1.0, 2.8, 0.9),
     ('Network and artifacts', ['A4.CommunicationNetwork', 'A4.Artifact'], -2.8, 1.2, 2.8, 2.7)],
]
LAYER = {'A1': 0, 'A2': 1, 'A3': 2, 'A4': 3}
SHOWN = ('approved', 'proposed')   # mapping statuses drawn: approved solid, proposed dashed; others (rejected, superseded …) left out


def readable(t):
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', t.split('.', 1)[1]).replace('A P I', 'API')
    return s[0] + s[1:].lower()


PLATFORMS = ('A4.Node', 'A4.Device', 'A4.SystemSoftware')
HOSTED_KINDS = ('assignment', 'composition', 'aggregation')


def sdem_containment(ws, layer):
    """A1–A3 drawn by what owns what (`sdem layout --layer <L> --json`). None if SDEM has no hierarchy for the layer: then it is grouped by record type."""
    r = run_sdem(ws, ['layout', '--layer', layer, '--workspace', str(ws), '--json'])
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip().startswith('{') else None


def sdem_layout(ws, environment):
    """A4 by its network zones (`sdem zones --layout --json`). Coordinates come as fractions of the plate."""
    r = run_sdem(ws, ['zones', '--layout', '--environment', environment or 'all', '--workspace', str(ws), '--json'])
    if r.returncode != 0:
        raise PublishError(f"sdem zones --layout failed: {(r.stderr or r.stdout).strip()[-400:]} — A4 needs network zones")
    return json.loads(r.stdout)


X0, X1, Z0, Z1 = -2.8, 2.8, -2.7, 2.7   # the A4 plate in the hero's units
def plate(fx, fz): return X0 + fx * (X1 - X0), Z0 + fz * (Z1 - Z0)


def build(ws, scale, topology=True, environment='production'):
    nodes, idx, rtype, inner, implied = [], {}, {}, [], set()
    dropped = set(); zone_links = []; zone_links_by_layer = {}; laid_out = set()
    zones = [[[z[0], z[2], z[3], z[4], z[5]] for z in ZONES[l]] for l in range(4)]
    for l, f in enumerate(FILES):
        with open(os.path.join(ws, f), encoding='utf-8') as fh:
            d = json.load(fh)
        recs = d.get('instances', [])
        cl = sdem_containment(ws, 'A' + str(l + 1)) if topology and l in (0, 1, 2) else None
        if cl:   # A1–A3 by what owns what (SDEM's containment layout) — A2 first: BIAN's service landscape
            zones[l] = [[z['label'], *[round(c, 3) for c in (*plate(z['rect'][0], z['rect'][1]), *plate(z['rect'][2], z['rect'][3]))], z['id'], z['part_of']] for z in cl['zones']]
            if cl.get('strip'):
                q = cl['strip']['rect']; zones[l].append([cl['strip']['label'], *[round(c, 3) for c in (*plate(q[0], q[1]), *plate(q[2], q[3]))]])
            for sh in cl['shapes']:
                k = SHAPE.get(sh['type'], 'obj')
                x, z = plate(*sh['at'])
                idx[sh['id']] = len(nodes); rtype[sh['id']] = sh['type']
                nodes.append([sh['id'], sh['name'], l, round(x, 3), round(z, 3), k, readable(sh['type'])] + ([sh['zone']] if sh['zone'] else []))
            inner += [(x['source'], x['target'], 2, x['kind'], 2 if x['shown_by'] == 'position' else 0) for x in cl['links']]   # 2: a faint "part of" line — nesting shown as a line too (the owner, 2026-11-15)
            zone_links_by_layer[l] = [[c['from'], c['to']] for c in cl['connections']]
            laid_out.add(l)
            continue
        if l == 3 and topology:   # A4 laid out by SDEM's deployment-zones viewpoint (one environment; default production)
            lay = sdem_layout(ws, environment)
            dropped = set(lay['left_out'])
            zones[3] = [[z['label'], *[round(c, 3) for c in (*plate(z['rect'][0], z['rect'][1]), *plate(z['rect'][2], z['rect'][3]))], z['id'], z['part_of']] for z in lay['zones']]
            zones[3] += [[f"runs on {g['platform']}", *[round(c, 3) for c in (*plate(g['rect'][0], g['rect'][1]), *plate(g['rect'][2], g['rect'][3]))]] for g in lay['runs_on']]
            if lay['not_in_a_zone']:
                q = lay['not_in_a_zone']; zones[3].append([lay['strip']['label'], *[round(c, 3) for c in (*plate(q[0], q[1]), *plate(q[2], q[3]))]])
            one_env = (environment or 'all').lower() != 'all'   # one environment shown: its block and lines say nothing the view does not (the owner, 2026-11-14)
            skip = {sh['id'] for sh in lay['shapes'] if one_env and sh['type'] == 'A4.DeploymentEnvironment'}
            # a network is shown by its zone, not as a shape (the owner, 2026-11-14 — the 3D view only; the data keeps both records):
            # its address range goes in its zone's heading
            nets = [sh for sh in lay['shapes'] if sh['type'] == 'A4.CommunicationNetwork']
            skip |= {sh['id'] for sh in nets}
            at4 = {r['id']: (r.get('attributes') or {}) for r in recs}
            ranges = {}
            for sh in nets:
                rng = at4.get(sh['id'], {}).get('address_range')
                if sh['zone'] and rng: ranges.setdefault(sh['zone'], []).extend(rng if isinstance(rng, list) else [rng])
            for z in zones[3]:
                if len(z) > 5 and z[5] in ranges: z[0] = z[0] + ' · ' + ', '.join(ranges[z[5]])
            dropped |= skip
            for sh in lay['shapes']:
                if sh['id'] in skip: continue
                k = SHAPE.get(sh['type'], 'obj')
                if sh['type'] == 'A4.SystemSoftware' and DATABASE.search(sh['name']): k = 'db'
                x, z = plate(*sh['at'])
                idx[sh['id']] = len(nodes); rtype[sh['id']] = sh['type']
                nodes.append([sh['id'], sh['name'], l, round(x, 3), round(z, 3), k, readable(sh['type'])] + ([sh['zone']] if sh['zone'] else []))
            inner += [(x['source'], x['target'], 2, x['kind'], 1 if x['shown_by'] == 'position' else 0) for x in lay['links'] if x['source'] not in skip and x['target'] not in skip]
            zone_links = [[c['from'], c['to']] for c in lay['connections']]   # arrows between the regions (ZC-01, ZC-02); nesting is one region inside another
            continue
        for zl, types, x0, z0, x1, z1 in ZONES[l]:
            zr = [r for t in types for r in recs if r['type'] == t]
            if not zr:
                continue
            w, h = x1 - x0, z1 - z0
            cols = max(1, min(len(zr), round(math.sqrt(len(zr) * w / h))))
            rows = math.ceil(len(zr) / cols)
            for i, r in enumerate(zr):
                c, rw = i % cols, i // cols
                in_row = min(cols, len(zr) - rw * cols)
                x = x0 + w * (c + 0.5 + (cols - in_row) / 2) / cols
                z = z0 + h * (rw + 0.5) / rows + 0.12
                k = SHAPE.get(r['type'], 'obj')
                if r['type'] == 'A4.SystemSoftware' and DATABASE.search(r.get('name', '')):
                    k = 'db'
                idx[r['id']] = len(nodes)
                rtype[r['id']] = r['type']
                nodes.append([r['id'], r['name'], l, round(x, 3), round(z, 3), k, readable(r['type'])])
        missing = [r['id'] for r in recs if r['id'] not in idx]
        if missing:
            raise PublishError(f'{f}: records of a type the 3D view cannot place: {", ".join(missing)}')
        inner += [(rel['source'], rel['target'], 2, rel['kind'], 0) for rel in d.get('relationships', [])]

    with open(os.path.join(ws, 'mappings.json'), encoding='utf-8') as fh:
        maps = json.load(fh).get('mappings', [])
    cross = []
    for m in maps:
        if m.get('status') not in SHOWN:
            continue
        a, b = m['source']['id'], m['target']['id']
        if a in dropped or b in dropped: continue   # a connection to another environment's record
        if a in idx and b in idx and nodes[idx[a]][2] > nodes[idx[b]][2]:
            a, b = b, a   # drawn from the upper layer down
        cross.append((a, b, 1 if m['status'] == 'approved' else 0, m['relationship'], 0))

    edges = []
    for a, b, ok, rel, imp in inner + cross:
        if a not in idx or b not in idx:
            raise PublishError(f'link {a} → {b} ({rel}) names a record not in the workspace')
        edges.append([idx[a], idx[b], ok, rel] + ([imp] if imp else []))

    # inside each zone, swap records between grid slots while that shortens their lines
    # (links inside the layer count fully; mappings count half — they pull blocks under each other)
    zone_of = {}
    for i, n in enumerate(nodes):
        if topology and n[2] == 3: continue                      # A4 by topology: placed, not shuffled
        if n[2] in laid_out:                                       # a layer SDEM laid out by what owns what: records swap only inside their own region,
            if len(n) > 7 and n[7] != 'R:' + n[0]: zone_of[i] = (n[2], n[7])   # and a region's own record (its anchor on the heading) never moves
            continue
        zone_of[i] = (n[2], next(zi for zi, z in enumerate(ZONES[n[2]]) if rtype[n[0]] in z[1]))
    touching = {i: [e for e in edges if i in (e[0], e[1])] for i in range(len(nodes))}

    def cost(i):
        return sum((1.0 if e[2] == 2 else 0.5) * math.hypot(nodes[e[0]][3] - nodes[e[1]][3], nodes[e[0]][4] - nodes[e[1]][4]) for e in touching[i])

    def swap(i, j):
        nodes[i][3], nodes[j][3] = nodes[j][3], nodes[i][3]
        nodes[i][4], nodes[j][4] = nodes[j][4], nodes[i][4]

    for _ in range(50):
        improved = False
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if i not in zone_of or zone_of.get(i) != zone_of.get(j):
                    continue
                before = cost(i) + cost(j)
                swap(i, j)
                if cost(i) + cost(j) < before - 1e-6:
                    improved = True
                else:
                    swap(i, j)
        if not improved:
            break

    return {
        'source': {'workspace': os.path.basename(os.path.normpath(ws)), 'generator': GENERATOR},
        'counts': {'records': len(nodes), 'inner': len(inner), 'mappings': len(cross)},
        'environment': environment,
        'zone_links': zone_links + [x for ls in zone_links_by_layer.values() for x in ls],
        'scale': scale,
        'zones': zones,
        'nodes': nodes,
        'edges': edges,
    }




LAYERS = ('A1', 'A2', 'A3', 'A4')
WS_FILES = FILES + ['mappings.json', 'requirements.json', 'sdem-profile.json']


def workspace_bundle(ws, v, mm):
    """DW-40: what the workbench shows — the workspace's own files, and what SDEM says about them: the check report, each layer's
    document, the kinds of record each layer allows (with the profile's), and how each layer is drawn. All through SDEM's commands."""
    def js(args):
        r = run_sdem(ws, args)
        try: return json.loads(r.stdout)
        except ValueError: return None
    files = {}
    for f in WS_FILES:
        p = Path(ws) / f
        if p.exists():
            files[f] = json.loads(p.read_text(encoding='utf-8'))
    docs = {}
    for L in LAYERS:
        r = run_sdem(ws, ['document', '--workspace', str(ws), '--layer', L])
        if r.returncode == 0: docs[L] = r.stdout
    return {
        'sdem': v, 'metamodel': mm, 'files': files,
        'check': js(['check', '--workspace', str(ws), '--json']),
        'documents': docs,
        'types': {L: (js(['types', L, '--workspace', str(ws), '--json']) or {}).get('types', []) for L in LAYERS},
        'layouts': {L: js(['layout', '--layer', L, '--workspace', str(ws), '--json']) for L in LAYERS},
    }


def model_for(ws, name, environment='production', scale=0.5, need_mark=True):
    """DP-01…DP-04: the gates, then the model with its header, validated. The same workspace always gives the same model (EXT-13)."""
    if not NAME.match(name or ''):
        raise PublishError(f'--name must be lower-case letters, digits and dashes, at most 40 (got {name!r})')
    v, mm = gates(ws, need_mark)
    body = build(ws, scale, environment=environment)
    model = {'format': 'desnre-model', 'format_version': 1, 'name': name, 'data': 'synthetic',
             **body, 'source': {**body['source'], 'sdem': v, 'metamodel': mm}}
    errs = validate(model)
    if errs:
        raise PublishError('the model does not match its schema:\n  ' + '\n  '.join(errs[:10]))
    model['workspace'] = workspace_bundle(ws, v, mm)   # DW-40: kept beside the 3D model by the site, for the workbench
    return model


def dumps(model):
    return json.dumps(model, ensure_ascii=False, separators=(',', ':')) + '\n'


# ---------- the site's API (DP-05, DP-10…DP-13; accounts DA-30, DA-40) ----------

def token(key):
    """A token from the environment or, on a Mac, the login Keychain (security find-generic-password -s <key>) — never a file (EXT-12)."""
    if os.environ.get(key):
        return os.environ[key]
    if sys.platform == 'darwin' and shutil.which('security'):
        r = subprocess.run(['security', 'find-generic-password', '-s', key, '-w'], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return ''


def keep_token(value):
    """DA-40: the personal token goes in the Mac's Keychain; elsewhere the person sets DESNRE_TOKEN themselves. True if kept."""
    if sys.platform == 'darwin' and shutil.which('security'):
        user = os.environ.get('USER', 'desnre')
        return subprocess.run(['security', 'add-generic-password', '-U', '-a', user, '-s', 'DESNRE_TOKEN', '-w', value],
                              capture_output=True).returncode == 0
    return False


def forget_token():
    if sys.platform == 'darwin' and shutil.which('security'):
        return subprocess.run(['security', 'delete-generic-password', '-s', 'DESNRE_TOKEN'], capture_output=True).returncode == 0
    return False


def call(method, path, tok=None, body=None, site=None):
    url = (site or SITE).rstrip('/') + path
    headers = {'Content-Type': 'application/json', 'User-Agent': GENERATOR}
    if tok:
        headers['Authorization'] = 'Bearer ' + tok
    req = urllib.request.Request(url, data=body.encode('utf-8') if body is not None else None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        try: why = json.loads(e.read().decode('utf-8')).get('error', '')
        except ValueError: why = ''
        raise PublishError(f'{method} {url}: {e.code} {why or e.reason}')
    except urllib.error.URLError as e:
        raise PublishError(f'{method} {url}: {e.reason}')


def signed_in(site):
    """The person's token and who it belongs to — or a plain instruction to sign in (DA-40)."""
    tok = token('DESNRE_TOKEN')
    if not tok:
        raise PublishError(f"you are not signed in — create a token on {(site or SITE).rstrip('/')}/account, then: sdem desnre login")
    return tok, call('GET', '/api/me', tok, None, site)


class Target:
    """Where a model goes: the person's own page (/u/<username>/<name>, the default) or — for the site's owner — the hero page."""
    def __init__(self, a):
        self.site, self.hero = a.site, getattr(a, 'hero', False)
        if self.hero:   # the owner's personal token (an admin), else the two shared tokens while they last (DA-42)
            mine = token('DESNRE_TOKEN')
            self.send_tok, self.live_tok = (mine, mine) if mine else (token('DESNRE_PUBLISH_TOKEN'), token('DESNRE_APPROVE_TOKEN'))
            if not self.send_tok:
                raise PublishError('the hero page is the site owner\'s — sign in with an admin account (sdem desnre login)')
            self.user = ''
        else:
            tok, me = signed_in(a.site)
            self.send_tok = self.live_tok = tok
            self.user = me['username']

    def path(self, name):
        return f'/api/models/{name}' if self.hero else f'/api/u/{self.user}/{name}'


# ---------- the commands ----------

def slug(folder):
    n = re.sub(r'[^a-z0-9-]+', '-', Path(folder).resolve().name.lower()).strip('-')[:40].strip('-')
    return n or 'model'


def who():
    r = subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True) if shutil.which('git') else None
    return (r.stdout.strip() if r and r.returncode == 0 else '') or os.environ.get('USER', '')


def name_of(target):
    """A workspace folder (its recorded name, else its folder name) or a model name."""
    p = Path(target)
    if p.is_dir():
        try:
            return json.loads((p / MARK).read_text(encoding='utf-8')).get('name') or slug(p)
        except (OSError, ValueError):
            return slug(p)
    if not NAME.match(target):
        raise PublishError(f'{target!r} is neither a workspace folder nor a model name')
    return target


def confirm_made_up(ws, by, yes):
    """EXT-11: the mark is a person's statement. Asked once, recorded with who said it."""
    p = Path(ws) / MARK
    try:
        m = json.loads(p.read_text(encoding='utf-8'))
        if m.get('data') == 'synthetic' and m.get('marked_by'):
            return m
    except (OSError, ValueError):
        m = {}
    if not yes:
        if not sys.stdin.isatty():
            raise PublishError(f'{ws} is not yet confirmed as made-up data — run create in a terminal to answer, or add --yes to confirm it')
        print(f'The DESNRE site is public. Is {ws} made-up data only — no real organisation\'s architecture? [y/N] ', end='', flush=True)
        if input().strip().lower() not in ('y', 'yes'):
            raise PublishError('not confirmed — nothing was sent')
    by = (by or who()).strip()
    if not by:
        raise PublishError('who is confirming? add --by "<your name>"')
    m = {**m, 'data': 'synthetic', 'marked_by': by, 'on': datetime.date.today().isoformat()}
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')
    print(f'recorded: made-up data, confirmed by {by} → {p}')
    return m


def remember_name(ws, name):
    p = Path(ws) / MARK
    m = json.loads(p.read_text(encoding='utf-8'))
    if m.get('name') != name:
        m['name'] = name; p.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')


def cmd_login(a):
    import getpass
    site = (a.site or SITE).rstrip('/')
    if sys.stdin.isatty():
        print(f'Create a token on {site}/account, then paste it here.')
        tok = getpass.getpass('Token: ').strip()
    else:
        tok = sys.stdin.readline().strip()
    if not tok.startswith('desnre_'):
        raise PublishError('that is not a DESNRE token — tokens start with desnre_')
    me = call('GET', '/api/me', tok, None, a.site)
    if keep_token(tok):
        print(f"signed in as @{me['username']} — the token is kept in your Keychain (DESNRE_TOKEN)")
    else:
        print(f"signed in as @{me['username']} — keep the token as the environment variable DESNRE_TOKEN (it is not stored on this computer)")
    print(f"your page: {me.get('page')}")


def cmd_logout(a):
    print('signed out — the token is removed from your Keychain' if forget_token() else 'no token was kept on this computer (unset DESNRE_TOKEN if you set it)')
    print(f"to stop the token working anywhere, revoke it on {(a.site or SITE).rstrip('/')}/account")


def cmd_whoami(a):
    _, me = signed_in(a.site)
    print(f"@{me['username']}" + (' (admin)' if me.get('admin') else '') + f" — your page: {me.get('page')}")


def cmd_create(a):
    ws = a.workspace
    if not Path(ws, 'a1-business.json').exists():
        raise PublishError(f'{ws} is not an SDEM workspace (no a1-business.json)')
    name = a.name or name_of(ws)
    target = None if a.dry_run else Target(a)   # signed in before anything is built
    if a.dry_run:
        model = model_for(ws, name, a.environment, a.scale, need_mark=False)
    else:
        confirm_made_up(ws, a.by, a.yes)
        model = model_for(ws, name, a.environment, a.scale)
    text = dumps(model)
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise PublishError(f'the model is {len(text.encode("utf-8"))} bytes; the site takes at most {MAX_BYTES}')
    c = model['counts']
    print(f"checked: SDEM {model['source']['sdem']}, metamodel {model['source']['metamodel']}, sdem check clean")
    print(f"built:   {name} — {c['records']} records · {c['inner']} links inside layers · {c['mappings']} mappings")
    if a.dry_run or a.out:
        out = Path(a.out or f'desnre-model-{name}.json'); out.write_text(text, encoding='utf-8')
        print(f'written: {out}')
        if a.dry_run:
            print('dry run: nothing sent'); return
    r = call('POST', target.path(name), target.send_tok, text, a.site)
    remember_name(ws, name)
    print(f"sent:    a draft — not public\npreview: {r.get('preview')}")
    if not a.no_open and sys.stdout.isatty():
        webbrowser.open(r.get('preview') or '')
    print(f"\nLook at every layer, then make it live:  sdem desnre publish {ws}" + (' --hero' if target.hero else ''))


def cmd_publish(a):
    t = Target(a)
    name = name_of(a.target)
    r = call('POST', t.path(name) + '/approve', t.live_tok, '{}', a.site)
    print(f"live:    {r.get('url')}" + ('  (the version it replaces is kept)' if r.get('previous_kept') else ''))
    if r.get('page'):
        print(f"your page: {r['page']}")


def cmd_list(a):
    if a.hero:
        r = call('GET', '/api/models', None, None, a.site)
    else:
        user = a.user or signed_in(a.site)[1]['username']
        r = call('GET', f'/api/u/{user}', None, None, a.site)
    rows = r.get('items', [])
    if a.json:
        print(json.dumps(r, indent=2)); return
    print(f'{len(rows)} live model(s)' + (':' if rows else ''))
    for m in rows:
        when = str(m.get('published_at') or m.get('published') or '?')[:10]
        print(f"  {m['name']:<24} {m.get('workspace', '')}  SDEM {m.get('sdem', '?')}  {m.get('records', '?')} records  published {when}")


def cmd_remove(a):
    t = Target(a)
    name = name_of(a.target)
    call('DELETE', t.path(name), t.live_tok, None, a.site)
    print(f'{name} taken off ' + ('the hero page' if t.hero else 'your page'))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['--manifest']:   # EXT-05: how SDEM (sdem extensions) recognises it
        print(json.dumps(MANIFEST, indent=2)); return 0
    ap = argparse.ArgumentParser(prog='sdem desnre', description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n')[1])
    ap.add_argument('--version', action='version', version=GENERATOR)
    sub = ap.add_subparsers(dest='command', required=True, metavar='{login,create,publish,list,remove,whoami,logout}')
    p = sub.add_parser('login', help='sign in with a token from your account page (kept in your Keychain)'); p.add_argument('--site'); p.set_defaults(fn=cmd_login)
    p = sub.add_parser('create', help='check, build and send a workspace as a draft (not public)')
    p.add_argument('workspace')
    p.add_argument('--name', help="the model's name on the site (default: the workspace folder's name)")
    p.add_argument('--by', help='who confirms it is made-up data (default: your git user name)')
    p.add_argument('--yes', action='store_true', help='confirm it is made-up data without being asked')
    p.add_argument('--dry-run', action='store_true', help='check and build; write the model; send nothing')
    p.add_argument('-o', '--out', help='also write the model here (default for --dry-run: desnre-model-<name>.json)')
    p.add_argument('--no-open', action='store_true', help='do not open the preview in the browser')
    p.add_argument('--environment', default='production', help="the deployment environment A4 shows (default production; 'all' for every one)")
    p.add_argument('--scale', type=float, default=0.5, help='shape size; 0.5 fits about 70 records')
    p.add_argument('--hero', action='store_true', help="the hero page, not your own (the site owner only)")
    p.add_argument('--site', help=f'the site (default $DESNRE_SITE or {SITE})'); p.set_defaults(fn=cmd_create)
    for name, fn, h in (('publish', cmd_publish, 'make the draft live on your page'), ('remove', cmd_remove, 'take a model off your page')):
        p = sub.add_parser(name, help=h); p.add_argument('target', help='the workspace folder, or the model name')
        p.add_argument('--hero', action='store_true', help='the hero page (the site owner only)'); p.add_argument('--site'); p.set_defaults(fn=fn)
    p = sub.add_parser('list', help='your live models'); p.add_argument('--user', help="someone else's page"); p.add_argument('--hero', action='store_true', help="the hero page's")
    p.add_argument('--json', action='store_true'); p.add_argument('--site'); p.set_defaults(fn=cmd_list)
    p = sub.add_parser('whoami', help='who you are signed in as'); p.add_argument('--site'); p.set_defaults(fn=cmd_whoami)
    p = sub.add_parser('logout', help='remove the token from this computer'); p.add_argument('--site'); p.set_defaults(fn=cmd_logout)
    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except PublishError as e:
        print(f'sdem desnre: {e}', file=sys.stderr)
        return 1
    return 0


def entry():   # the installed command, sdem-desnre
    sys.exit(main())


if __name__ == '__main__':
    entry()
