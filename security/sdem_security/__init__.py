"""sdem security — the security architecture, as an SDEM metamodel extension (security/docs/security-aspect-spec.md).

    sdem security catalogue <words>                         search NIST SP 800-53 Rev. 5 controls (id, title, family)
    sdem security coverage --workspace DIR                  per A1–A4 record: its controls, what enforces them, its threats
    sdem security threats  --workspace DIR                  a STRIDE checklist per record — prompts for a person, never records
    sdem security review   --workspace DIR                  what the security design still lacks, weakest first
    sdem security propose FILE --workspace DIR --person P   controls, threats and boundaries as a change set (a person accepts)

Switch it on in a workspace first — a person's decision: sdem profile include ext:security --workspace DIR --person P, then
sdem profile adopt --workspace DIR --person P (adds security.json). It uses SDEM only through its commands and the workspace's
documented files (EXT-02), writes nothing itself (EXT-07), and checks SDEM's version against its manifest (EXT-04).
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
MANIFEST = json.loads((HERE / 'sdem-extension.json').read_text(encoding='utf-8'))
LAYERS = (('A1', 'a1-business.json'), ('A2', 'a2-service-domain.json'), ('A3', 'a3-application.json'), ('A4', 'a4-technology.json'))
SEC_FILE = 'security.json'
S_NAMES = {'S1': 'Business security', 'S2': 'Service domain security', 'S3': 'Data security', 'S4': 'Application security', 'S5': 'Technology security'}
LINKS = ('PROTECTS', 'ENFORCED_BY', 'THREATENS', 'BOUNDS')
# STRIDE per element (the classic table): which threat categories a person should consider for each kind of record
STRIDE = {'A1.BusinessRole': 'SR', 'A1.BusinessActor': 'SR', 'A1.BusinessProcess': 'TRE', 'A1.BusinessObject': 'TID', 'A2.ServiceDomain': 'STRIDE', 'A2.ControlRecord': 'TRID',
          'A3.DataEntity': 'TRID', 'A3.ApplicationComponent': 'STRIDE', 'A3.ApplicationInterface': 'STRIDE', 'A3.APIOperation': 'STIDE', 'A4.Path': 'TID',
          'A4.Node': 'TDE', 'A4.NetworkZone': 'D', 'A4.SystemSoftware': 'TIDE', 'A4.Deployment': 'TE'}
STRIDE_WORDS = {'S': 'Spoofing', 'T': 'Tampering', 'R': 'Repudiation', 'I': 'Information disclosure', 'D': 'Denial of service', 'E': 'Elevation of privilege'}
SECURITY_LAYER_OF = {'A1': 'S1', 'A2': 'S2', 'A4': 'S5'}   # A3: data entities and their fields S3, the rest S4


def sdem(*args):
    """SDEM's command line — the one beside this Python (installed in SDEM's environment), else the one on the PATH."""
    exe = shutil.which('sdem', path=str(Path(sys.executable).parent)) or shutil.which('sdem') or 'sdem'
    return subprocess.run([exe, *map(str, args)], capture_output=True, text=True)


def supported(version, spec):
    v = tuple(int(x) for x in re.findall(r'\d+', version)[:3])
    for clause in spec.split(','):
        op, want = re.match(r'\s*(>=|<)\s*([\d.]+)', clause).groups()
        w = tuple(int(x) for x in want.split('.')); w += (0,) * (3 - len(w))
        if not (v >= w if op == '>=' else v < w): return False
    return True


def manifest():
    """The manifest, with where this installation keeps its pack (MX-01) — SDEM reads it to fold the pack into a workspace's profile."""
    return {**MANIFEST, 'pack': str((HERE / 'pack.json').resolve())}


def catalogue():
    return json.loads((HERE / 'catalogue.json').read_text(encoding='utf-8'))


def _j(p):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError): return None


def workspace(ws):
    """The workspace as SDEM documents it: each layer's records and links, the security layer's, and the approved connections."""
    ws = Path(ws); recs, layer_of = {}, {}
    for code, f in LAYERS + (('S', SEC_FILE),):
        d = _j(ws / f) or {}
        for r in d.get('instances', []): recs[r['id']] = r; layer_of[r['id']] = code
    rels = [x for code, f in LAYERS + (('S', SEC_FILE),) for x in ((_j(ws / f) or {}).get('relationships') or [])]
    maps = [m for m in ((_j(ws / 'mappings.json') or {}).get('mappings') or []) if m.get('status') == 'approved']
    if not (ws / SEC_FILE).exists():
        raise SystemExit(f"sdem security: {ws} has no {SEC_FILE} — switch the extension on first: sdem profile include ext:security --workspace {ws} --person <you>, then sdem profile adopt --workspace {ws} --person <you>")
    return recs, layer_of, rels, maps


def security_layer(r, layer):
    if layer == 'A3': return 'S3' if r['type'] in ('A3.DataEntity', 'A3.DataAttribute') else 'S4'
    return SECURITY_LAYER_OF.get(layer)


def cmd_catalogue(a):
    words = [w.lower() for w in a.words]; cat = catalogue()
    hits = [c for c in cat['controls'] if not c.get('withdrawn') and all(re.search(r'\b' + re.escape(w) + r'\b', (c['id'] + ' ' + c['title'] + ' ' + c['family_title']).lower()) for w in words)]
    hits = hits[:a.limit]
    if a.json: print(json.dumps({'source': cat['source'], 'count': len(hits), 'items': hits}, indent=2)); return 0
    if not hits: print(f"no NIST SP 800-53 Rev. 5 control matches {' '.join(a.words)!r}"); return 0
    for c in hits: print(f"  {c['id']:<10} {c['title']}  ·  {c['family_title']}")
    print(f"\nNIST SP 800-53 Rev. 5 ({cat['source']['version']}), public domain — the full text: {cat['source']['url']}")
    return 0


def coverage_rows(ws):
    recs, layer_of, rels, maps = workspace(ws)
    by = lambda rel, key: [m for m in maps if m['relationship'] == rel]
    rows = []
    for rid, r in sorted(recs.items(), key=lambda kv: (layer_of[kv[0]], kv[0])):
        L = layer_of[rid]
        if L == 'S' or r['type'] not in STRIDE: continue
        controls = [m['source']['id'] for m in by('PROTECTS', 0) if m['target']['id'] == rid]
        threats = [m['source']['id'] for m in by('THREATENS', 0) if m['target']['id'] == rid]
        enforced = {c: [m['target']['id'] for m in by('ENFORCED_BY', 0) if m['source']['id'] == c] for c in controls}
        at = r.get('attributes') or {}
        rows.append({'id': rid, 'name': r.get('name'), 'type': r['type'], 'layer': L, 'security_layer': security_layer(r, L),
                     'classification': at.get('access_classification') or r.get('access_classification'), 'personal_information': at.get('personal_information'),
                     'controls': [{'id': c, 'control_id': ((recs.get(c) or {}).get('attributes') or {}).get('control_id'), 'enforced_by': enforced[c]} for c in controls],
                     'threats': threats, 'protected': bool(controls)})
    return rows


def cmd_coverage(a):
    rows = coverage_rows(a.workspace)
    if a.json: print(json.dumps({'workspace': str(a.workspace), 'count': len(rows), 'protected': sum(r['protected'] for r in rows), 'items': rows}, indent=2)); return 0
    for s in S_NAMES:
        mine = [r for r in rows if r['security_layer'] == s]
        if not mine: continue
        print(f"\n{s} {S_NAMES[s]} — {sum(r['protected'] for r in mine)} of {len(mine)} records protected")
        for r in mine:
            ctl = ', '.join(f"{c['control_id'] or c['id']}" + (f" by {'/'.join(c['enforced_by'])}" if c['enforced_by'] else '') for c in r['controls']) or '— no control'
            print(f"  {r['id']:<28} {ctl}" + (f"   threats: {', '.join(r['threats'])}" if r['threats'] else '') + ('   [personal data]' if r['personal_information'] else ''))
    return 0


def cmd_threats(a):
    recs, layer_of, rels, maps = workspace(a.workspace)
    stated = {}
    for m in maps:
        if m['relationship'] == 'THREATENS':
            t = recs.get(m['source']['id']) or {}
            stated.setdefault(m['target']['id'], set()).update(((t.get('attributes') or {}).get('stride') or []))
    out = []
    for rid, r in sorted(recs.items(), key=lambda kv: (layer_of[kv[0]], kv[0])):
        cats = STRIDE.get(r['type'])
        if not cats or layer_of[rid] == 'S': continue
        open_ = [c for c in cats if c not in stated.get(rid, set())]
        out.append({'id': rid, 'name': r.get('name'), 'type': r['type'], 'security_layer': security_layer(r, layer_of[rid]), 'consider': list(cats), 'stated': sorted(stated.get(rid, set())), 'not_yet_considered': open_})
    if a.json: print(json.dumps({'note': 'a checklist for a person (STRIDE per element) — not records; a threat is added only with sdem security propose', 'items': out}, indent=2)); return 0
    print('STRIDE per element — a checklist for a person; nothing here is a record.')
    for x in out:
        if x['not_yet_considered']: print(f"  {x['security_layer']} {x['id']:<28} consider: {', '.join(STRIDE_WORDS[c] for c in x['not_yet_considered'])}")
    return 0


def computed_findings(ws):
    """SEC-S07 and SEC-S08 (security-aspect-spec §6): checks along paths SDEM's rule language cannot express — the requirements
    registry, and a component's access to personal data. Reported with the standard's own findings, in the same shape."""
    recs, layer_of, rels, maps = workspace(ws)
    out, attrs = [], lambda i: (recs.get(i) or {}).get('attributes') or {}
    met = set()
    for r in recs.values():
        if r['type'].endswith('.SecurityControl'): met.update(attrs(r['id']).get('meets_requirements') or [])
    for q in ((_j(Path(ws) / 'requirements.json') or {}).get('requirements') or []):   # SEC-S07
        if q.get('category') == 'security' and q.get('status') != 'retired' and q.get('id') not in met:
            out.append({'rule': 'SEC-S07', 'record': q.get('id'), 'outcome': 'non_compliant', 'message': 'a security requirement that no control meets (meets_requirements) — PL-8, GV.PO'})
    pii = {i for i, r in recs.items() if r['type'] == 'A3.DataEntity' and attrs(i).get('personal_information') is True}
    users = sorted({l['source'] for l in rels if l.get('kind') == 'access' and l.get('target') in pii and (recs.get(l['source']) or {}).get('type') == 'A3.ApplicationComponent'})
    for c in users:   # SEC-S08
        audited = any(m['relationship'] == 'PROTECTS' and m['target']['id'] == c and re.match(r'AU-(2|12)\b', str(attrs(m['source']['id']).get('control_id') or '')) for m in maps)
        if not audited:
            out.append({'rule': 'SEC-S08', 'record': c, 'outcome': 'non_compliant', 'message': 'a component that accesses personal data has no audit control (AU-2 or AU-12) protecting it — DE.CM'})
    for L in S_NAMES:   # a security layer this design leaves empty — said, not hidden
        if not any(r['type'].endswith(('.SecurityControl', '.Threat')) and attrs(i).get('security_layer') == L for i, r in recs.items()):
            out.append({'rule': 'SEC-LAYER', 'record': L, 'outcome': 'unresolved', 'message': f'{S_NAMES[L]} has no controls or threats in this design'})
    return out


def cmd_review(a):
    r = sdem('comply', '--workspace', a.workspace, '--json')
    try: comply = json.loads(r.stdout)
    except ValueError: print(r.stdout + r.stderr, file=sys.stderr); return 2
    findings = [f for f in (comply.get('findings') or comply.get('items') or []) if str(f.get('rule', '')).startswith('SEC-') and f.get('outcome') in ('non_compliant', 'unresolved')]
    findings += computed_findings(a.workspace)   # SEC-S07, SEC-S08
    rows = coverage_rows(a.workspace)
    unprotected = [x for x in rows if not x['protected'] and (x['personal_information'] or x['type'] in ('A3.ApplicationInterface', 'A4.Path', 'A4.NetworkZone'))]
    no_rest = [x for x in rows if x['personal_information'] and x['protected'] and not any(str(c['control_id'] or '').startswith('SC-28') for c in x['controls'])]   # SEC-S01: at rest, specifically
    order = {'non_compliant': 0, 'unresolved': 1}
    findings.sort(key=lambda f: (order.get(f.get('outcome'), 2), f.get('rule', ''), str(f.get('record', ''))))
    if a.json: print(json.dumps({'findings': findings, 'unprotected': unprotected, 'personal_data_without_sc28': no_rest}, indent=2)); return 0
    print(f"Security review of {a.workspace} — {len(findings)} finding(s) from the security standard, {len(unprotected)} exposed record(s) with no control")
    for f in findings: print(f"  {f.get('outcome'):<14} {f.get('rule'):<9} {f.get('record')}  {f.get('message', '')}")
    for x in no_rest: print(f"  no SC-28        {x['security_layer']:<9} {x['id']}  personal data with no protection at rest")
    for x in unprotected: print(f"  no control     {x['security_layer']:<9} {x['id']}  {x['type']}")
    return 0


def cmd_propose(a):
    args = ['change', 'propose', a.file, '--workspace', a.workspace, '--agent', 'sdem-layer-s', '--person', a.person] + (['--dry-run'] if a.dry_run else []) + (['--json'] if a.json else [])
    r = sdem(*args); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); return r.returncode


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['--manifest']:   # how SDEM recognises an extension (EXT-05, EXT-15), and where its pack is (MX-01)
        print(json.dumps(manifest(), indent=2)); return 0
    ap = argparse.ArgumentParser(prog='sdem security', description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('catalogue', help='search NIST SP 800-53 Rev. 5 controls'); p.add_argument('words', nargs='+'); p.add_argument('--limit', type=int, default=25); p.add_argument('--json', action='store_true')
    for name, h in (('coverage', 'per record: its controls, what enforces them, its threats'), ('threats', 'a STRIDE checklist per record (prompts, never records)'), ('review', 'what the security design still lacks')):
        p = sub.add_parser(name, help=h); p.add_argument('--workspace', required=True); p.add_argument('--json', action='store_true')
    p = sub.add_parser('propose', help='controls, threats and boundaries into the security layer, as a change set a person accepts')
    p.add_argument('file'); p.add_argument('--workspace', required=True); p.add_argument('--person', required=True); p.add_argument('--dry-run', action='store_true'); p.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    v = re.search(r'\d+\.\d+\.\d+', sdem('--version').stdout or '')
    if v and not supported(v.group(0), MANIFEST['sdem']):
        print(f"sdem security: SDEM {v.group(0)} is not one this extension supports ({MANIFEST['sdem']})", file=sys.stderr); return 1
    return {'catalogue': cmd_catalogue, 'coverage': cmd_coverage, 'threats': cmd_threats, 'review': cmd_review, 'propose': cmd_propose}[a.command](a)


def entry():
    sys.exit(main())
