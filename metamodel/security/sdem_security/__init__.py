"""sdem security — the security architecture, as an SDEM metamodel extension (security/docs/security-aspect-spec.md).

    sdem security catalogue <words>                         search NIST SP 800-53 Rev. 5 controls (id, title, family)
    sdem security coverage --workspace DIR                  per record of every layer: its controls, what enforces them, its threats
    sdem security threats  --workspace DIR                  a STRIDE checklist per record — prompts for a person, never records
    sdem security review   --workspace DIR                  what the security design still lacks, weakest first
    sdem security document --workspace DIR [-o FILE]        the review as a readable document (Markdown)
    sdem security remove  --workspace DIR --person P --reason R   switch security off again — archived, not lost (a person's decision)
    sdem security restore --archive F --workspace DIR --person P --reason R   switch it back on from that archive
    sdem security purge   --workspace DIR --person P --reason R [--archive F]   delete the archived data — never the default
    sdem security propose FILE --workspace DIR --person P   controls, threats and boundaries as a change set (a person accepts)

Switch it on in a workspace first — a person's decision: sdem profile include ext:security --workspace DIR --person P, then
sdem profile adopt --workspace DIR --person P (adds security.json). It uses SDEM only through its commands and the workspace's
documented files (EXT-02), writes nothing itself (EXT-07), and checks SDEM's version against its manifest (EXT-04).
"""
import argparse, datetime, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
MANIFEST = json.loads((HERE / 'sdem-extension.json').read_text(encoding='utf-8'))
LAYERS = (('A1', 'a1-business.json'), ('A2', 'a2-service-domain.json'), ('A3', 'a3-application.json'), ('A4', 'a4-technology.json'))
SEC_FILE = 'security.json'
S_NAMES = {'S1': 'Business security', 'S2': 'Service domain security', 'S3': 'Data security', 'S4': 'Application security', 'S5': 'Technology security'}
LINKS = ('PROTECTS', 'ENFORCED_BY', 'THREATENS', 'BOUNDS')
# STRIDE per element (the classic table): which threat categories a person should consider for each kind of record
# (spec §7: an actor S·R; a process or component all six; data T·R·I·D; a flow or path T·I·D). Every type the pack lets a threat
# THREATEN has an entry — a test holds the two together (AUD-04, AUD-07).
STRIDE = {'A1.BusinessRole': 'SR', 'A1.BusinessActor': 'SR', 'A1.BusinessProcess': 'STRIDE', 'A1.BusinessObject': 'TRID', 'A2.ServiceDomain': 'STRIDE',
          'A2.ControlRecord': 'TRID', 'A2.BusinessObject': 'TRID', 'A3.DataEntity': 'TRID', 'A3.DataAttribute': 'TRID', 'A3.ApplicationComponent': 'STRIDE',
          'A3.ApplicationInterface': 'STRIDE', 'A3.APIOperation': 'STRIDE', 'A4.Path': 'TID', 'A4.CommunicationNetwork': 'TID', 'A4.Node': 'STDE',
          'A4.InfrastructureComponent': 'STDE', 'A4.NetworkZone': 'D', 'A4.SystemSoftware': 'TIDE', 'A4.Deployment': 'TE'}
PACK = json.loads((HERE / 'pack.json').read_text(encoding='utf-8'))
PROTECTABLE = sorted({l['target_type'] for l in PACK['link_types'] if l['relationship'] == 'PROTECTS'})    # coverage's scope: what a control can protect
THREATENABLE = sorted({l['target_type'] for l in PACK['link_types'] if l['relationship'] == 'THREATENS'})  # the checklist's scope: what a threat can threaten
INACTIVE = {'retired', 'deprecated'}
STRIDE_WORDS = {'S': 'Spoofing', 'T': 'Tampering', 'R': 'Repudiation', 'I': 'Information disclosure', 'D': 'Denial of service', 'E': 'Elevation of privilege'}
SECURITY_LAYER_OF = {'A1': 'S1', 'A2': 'S2', 'A4': 'S5'}   # A3: data entities and their fields S3, the rest S4


def sdem(*args):
    """SDEM's command line — the one beside this Python (installed in SDEM's environment), else the one on the PATH."""
    exe = shutil.which('sdem', path=str(Path(sys.executable).parent)) or shutil.which('sdem') or 'sdem'
    return subprocess.run([exe, *map(str, args)], capture_output=True, text=True, encoding='utf-8', errors='replace')   # SDEM writes UTF-8 (AUD-10)


def supported(version, spec):
    """EXT-04: is `version` in `spec` (clauses >=, >, <=, <, ==, joined by commas)? An unreadable clause is a ValueError, never a pass."""
    tup = lambda x: (tuple(int(n) for n in re.findall(r'\d+', x)[:3]) + (0, 0, 0))[:3]
    v = tup(version)
    for clause in spec.split(','):
        m = re.match(r'\s*(>=|<=|==|>|<)\s*([\d.]+)\s*$', clause)
        if not m: raise ValueError(f'version range {spec!r}: cannot read {clause.strip()!r}')
        op, w = m.group(1), tup(m.group(2))
        if not {'>=': v >= w, '<=': v <= w, '==': v == w, '>': v > w, '<': v < w}[op]: return False
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


_CORE = {}
def type_parents(ws):
    """Each record type's parents, as SDEM reports them (`sdem types <layer> --json`: extends) — for the types the workspace's profile and
    its extensions add as well as SDEM's own. Empty when SDEM cannot be asked; then only exact types match."""
    out = {}
    for code, _ in LAYERS:
        try: d = json.loads(sdem('types', code, '--workspace', ws, '--json').stdout or '{}')
        except (ValueError, OSError): continue
        for t in d.get('types') or []: out[t['type']] = list(t.get('extends') or [])
    return out


def core_type(ws, t):
    """MX-32a: the type as security's scope sees it. SDEM's own types (A4.Node) match exactly; a type a profile or another extension adds
    inside a layer (NET.A4.Firewall extends A4.Node) is placed by its nearest SDEM ancestor — so coverage, the checklist and SEC-S08 reach it.
    Core types are not widened by inheritance (A4.Artifact stays itself, though it extends A4.InfrastructureComponent)."""
    if str(t).count('.') == 1: return t   # an SDEM type: A4.Node
    key = str(Path(ws).resolve())
    if key not in _CORE: _CORE[key] = type_parents(ws)
    par, seen, todo = _CORE[key], set(), [t]
    while todo:
        x = todo.pop(0)
        if x in seen: continue
        seen.add(x)
        if x != t and x.count('.') == 1: return x
        todo += par.get(x, [])
    return t


def active_control(recs, cid):
    """AUD-03: a control counts only while it can act — not retired or deprecated, and not marked not_applicable."""
    c = recs.get(cid) or {}
    return bool(c) and c.get('lifecycle_status') not in INACTIVE and (c.get('attributes') or {}).get('implementation_status') != 'not_applicable'


def exceptions(ws, today=None):
    """A person's exceptions in force today (sdem exception grant, PR-18): {(rule, record): exception id}."""
    today = today or datetime.date.today(); out = {}
    for e in ((_j(Path(ws) / 'exceptions.json') or {}).get('exceptions') or []):
        try:
            if datetime.date.fromisoformat(e['expires']) < today: continue
        except (KeyError, ValueError): continue
        for rec in e.get('records') or []: out[(e.get('rule'), rec)] = e.get('id')
    return out


def security_layer(r, layer):
    if layer == 'A3': return 'S3' if r['type'] in ('A3.DataEntity', 'A3.DataAttribute') else 'S4'
    return SECURITY_LAYER_OF.get(layer)


def cmd_catalogue(a):
    words = [w.lower() for w in a.words]; cat = catalogue()
    hits = [c for c in cat['controls'] if not c.get('withdrawn') and all(re.search(r'(?<![\w-])' + re.escape(w) + r'(?![\w])', (c['id'] + ' ' + c['title'] + ' ' + c['family_title']).lower()) for w in words)]   # AUD-08: 'IA-2(1)' finds IA-2(1)
    hits = hits[:a.limit]
    if a.json: print(json.dumps({'source': cat['source'], 'count': len(hits), 'items': hits}, indent=2)); return 0
    if not hits: print(f"no NIST SP 800-53 Rev. 5 control matches {' '.join(a.words)!r}"); return 0
    for c in hits: print(f"  {c['id']:<10} {c['title']}  ·  {c['family_title']}")
    print(f"\nNIST SP 800-53 Rev. 5 ({cat['source']['version']}), public domain — the full text: {cat['source']['url']}")
    return 0


def coverage_rows(ws):
    ws = as_019(ws)   # DL-22: a 0.20 workspace read as 0.19 held it
    recs, layer_of, rels, maps = workspace(ws)
    by = lambda rel, key: [m for m in maps if m['relationship'] == rel]
    rows = []
    for rid, r in sorted(recs.items(), key=lambda kv: (layer_of[kv[0]], kv[0])):
        L = layer_of[rid]
        ct = core_type(ws, r['type'])
        if L == 'S' or ct not in PROTECTABLE: continue
        named = [m['source']['id'] for m in by('PROTECTS', 0) if m['target']['id'] == rid]
        controls = [c for c in named if active_control(recs, c)]
        threats = [m['source']['id'] for m in by('THREATENS', 0) if m['target']['id'] == rid]
        enforced = {c: [m['target']['id'] for m in by('ENFORCED_BY', 0) if m['source']['id'] == c] for c in controls}
        at = r.get('attributes') or {}
        rows.append({'id': rid, 'name': r.get('name'), 'type': r['type'], **({'kind_of': ct} if ct != r['type'] else {}), 'layer': L, 'security_layer': security_layer({**r, 'type': ct}, L),
                     'classification': at.get('access_classification') or r.get('access_classification'), 'personal_information': at.get('personal_information'),
                     'controls': [{'id': c, 'control_id': ((recs.get(c) or {}).get('attributes') or {}).get('control_id'), 'enforced_by': enforced[c]} for c in controls],
                     'threats': threats, 'protected': bool(controls), 'inactive_controls': [c for c in named if c not in controls]})
    by_id = {x['id']: x for x in rows}   # a field is protected by what protects its data entity (the same store, the same controls)
    for x in rows:
        if x.get('kind_of', x['type']) == 'A3.DataAttribute' and not x['protected']:
            ent = lambda i: (by_id.get(i) or {}).get('kind_of', (by_id.get(i) or {}).get('type')) == 'A3.DataEntity'
            ents = sorted({l['source'] for l in rels if l.get('target') == x['id'] and ent(l['source'])} | {l['target'] for l in rels if l.get('source') == x['id'] and ent(l['target'])})
            via = [e for e in ents if by_id[e]['protected']]
            if via: x['protected'] = True; x['protected_through'] = via
    return rows


def cmd_coverage(a):
    rows = coverage_rows(a.workspace)
    if a.json: print(json.dumps(numbered({'workspace': str(a.workspace), 'count': len(rows), 'protected': sum(r['protected'] for r in rows), 'protected_means': MANIFEST.get('protected_means'), 'items': rows}, getattr(a, 'design', a.workspace), a.workspace), indent=2)); return 0
    for s in S_NAMES:
        mine = [r for r in rows if r['security_layer'] == s]
        if not mine: continue
        print(f"\n{s} {S_NAMES[s]} — {sum(r['protected'] for r in mine)} of {len(mine)} records protected")
        for r in mine:
            ctl = ', '.join(f"{c['control_id'] or c['id']}" + (f" by {'/'.join(c['enforced_by'])}" if c['enforced_by'] else '') for c in r['controls']) or '— no control'
            print(f"  {r['id']:<28} {ctl}" + (f"   threats: {', '.join(r['threats'])}" if r['threats'] else '') + ('   [personal data]' if r['personal_information'] else ''))
    return 0


def threats_data(ws):
    ws = as_019(ws)   # DL-22: a 0.20 workspace read as 0.19 held it
    recs, layer_of, rels, maps = workspace(ws)
    stated = {}
    for m in maps:
        if m['relationship'] == 'THREATENS':
            t = recs.get(m['source']['id']) or {}
            stated.setdefault(m['target']['id'], set()).update(((t.get('attributes') or {}).get('stride') or []))
    out = []
    for rid, r in sorted(recs.items(), key=lambda kv: (layer_of[kv[0]], kv[0])):
        ct = core_type(ws, r['type'])
        cats = STRIDE.get(ct) if ct in THREATENABLE else None
        if not cats or layer_of[rid] == 'S': continue
        open_ = [c for c in cats if c not in stated.get(rid, set())]
        out.append({'id': rid, 'name': r.get('name'), 'type': r['type'], **({'kind_of': ct} if ct != r['type'] else {}), 'security_layer': security_layer({**r, 'type': ct}, layer_of[rid]), 'consider': list(cats), 'stated': sorted(stated.get(rid, set())), 'not_yet_considered': open_})
    return out


def cmd_threats(a):
    out = threats_data(a.workspace)
    if a.json: print(json.dumps(numbered({'note': 'a checklist for a person (STRIDE per element) — not records; a threat is added only with sdem security propose', 'items': out}, getattr(a, 'design', a.workspace), a.workspace), indent=2)); return 0
    print('STRIDE per element — a checklist for a person; nothing here is a record.')
    for x in out:
        if x['not_yet_considered']: print(f"  {x['security_layer']} {x['id']:<28} consider: {', '.join(STRIDE_WORDS[c] for c in x['not_yet_considered'])}")
    return 0


def computed_findings(ws, today=None):
    """SEC-S07, SEC-S08 and SEC-LAYER — checks along paths SDEM's rule language cannot express (the requirements registry; a component's
    or an operation's access to personal data). Reported in the standard's shape. As the standard's own rules (PR-11a): a check that is
    not yet decidable — its subject still planned, its requirement only proposed — is `unresolved`, not `non_compliant` (AUD-02); a
    person's exception (sdem exception grant --rule SEC-S08 …) holds it as `exception_approved` (MX-17); only controls that can act count
    (AUD-03)."""
    ws = as_019(ws)   # DL-22: a 0.20 workspace read as 0.19 held it
    recs, layer_of, rels, maps = workspace(ws)
    out, attrs = [], lambda i: (recs.get(i) or {}).get('attributes') or {}
    planned = lambda i: (recs.get(i) or {}).get('lifecycle_status') == 'planned'
    def add(rule, rec, decided, msg):
        out.append({'rule': rule, 'record': rec, 'outcome': 'non_compliant' if decided else 'unresolved', 'message': msg, 'computed': True})
    reqs = (_j(Path(ws) / 'requirements.json') or {}).get('requirements') or []
    known_req = {q.get('id') for q in reqs}
    met = set()
    for i, r in recs.items():
        if r['type'].endswith('.SecurityControl') and active_control(recs, i):
            ids = attrs(i).get('meets_requirements') or []
            met.update(ids)
            for q in ids:   # SEC-S07: a control names a requirement the registry does not hold (AUD-05)
                if q not in known_req: add('SEC-S07', i, True, f'meets_requirements names {q}, which is not in requirements.json — PL-8, GV.PO')
    for q in reqs:   # SEC-S07: retired and superseded requirements ask nothing any more (AUD-05)
        if q.get('category') == 'security' and q.get('status') not in ('retired', 'superseded') and q.get('id') not in met:
            add('SEC-S07', q.get('id'), q.get('status') == 'confirmed', 'a security requirement that no control meets (meets_requirements) — PL-8, GV.PO'
                + ('' if q.get('status') == 'confirmed' else f" — not decidable while the requirement is {q.get('status') or 'unconfirmed'}"))
    # SEC-S08: personal data held by an entity, or by one of its fields (AUD-12); accessed by a component or an API operation
    kt = lambda i: core_type(ws, (recs.get(i) or {}).get('type', ''))   # MX-32a: a subtype counts as its SDEM type
    pfield = {i for i in recs if kt(i) == 'A3.DataAttribute' and attrs(i).get('personal_information') is True}
    pii = {i for i in recs if kt(i) == 'A3.DataEntity' and attrs(i).get('personal_information') is True}
    pii |= {l['source'] for l in rels if l.get('target') in pfield and kt(l['source']) == 'A3.DataEntity'}
    pii |= {l['target'] for l in rels if l.get('source') in pfield and kt(l['target']) == 'A3.DataEntity'}
    users = sorted({l['source'] for l in rels if l.get('kind') == 'access' and l.get('target') in pii and kt(l['source']) in ('A3.ApplicationComponent', 'A3.APIOperation')})
    audit = lambda i: any(m['relationship'] == 'PROTECTS' and m['target']['id'] == i and active_control(recs, m['source']['id'])
                          and re.match(r'AU-(2|12)\b', str(attrs(m['source']['id']).get('control_id') or '')) for m in maps)
    near = lambda i: {l['target'] for l in rels if l.get('source') == i} | {l['source'] for l in rels if l.get('target') == i}
    for c in users:
        is_op = kt(c) == 'A3.APIOperation'
        holders = {c} | ({x for x in near(c) if kt(x) in ('A3.ApplicationComponent', 'A3.ApplicationInterface')} if is_op else set())
        if not any(audit(x) for x in holders):   # an operation is audited by its own control, or by the interface or component that serves it
            add('SEC-S08', c, not planned(c), f"{'an API operation' if is_op else 'a component'} that accesses personal data has no audit control (AU-2 or AU-12) protecting it — DE.CM"
                + (' — not decidable while it is planned' if planned(c) else ''))
    for L in S_NAMES:   # a security layer this design leaves empty — said, not hidden
        if L == 'S2' and str(ws) in _NO_BIAN: continue   # a design without BIAN has no service domains to secure (DL-22)
        if not any(r['type'].endswith(('.SecurityControl', '.Threat')) and attrs(i).get('security_layer') == L for i, r in recs.items()):
            add('SEC-LAYER', L, False, f'{S_NAMES[L]} has no controls or threats in this design')
    held = exceptions(ws, today)
    for f in out:
        if (f['rule'], f['record']) in held: f['outcome'] = 'exception_approved'; f['exception'] = held[(f['rule'], f['record'])]
    return out


class ReviewError(Exception): pass


def review_data(ws):
    """The security standard's findings (sdem comply) with SEC-S07, SEC-S08 and SEC-LAYER, the exposed records, and personal data with no SC-28."""
    ws = as_019(ws)   # DL-22: a 0.20 workspace read as 0.19 held it
    r = sdem('comply', '--workspace', ws, '--json')
    try: comply = json.loads(r.stdout)
    except ValueError: raise ReviewError(f'sdem comply did not answer (exit {r.returncode}): ' + (r.stderr or r.stdout).strip()[-600:])
    if not isinstance(comply, dict) or not isinstance(comply.get('findings'), list):   # AUD-06: never an empty review from an answer it cannot read
        raise ReviewError(f'sdem comply answered in a form this extension does not know (exit {r.returncode}) — nothing is reported rather than a wrong all-clear')
    std = MANIFEST.get('standard_id', 'SEC')
    if not any((g.get('id') == std and g.get('kind') == 'standard') for g in comply.get('groups') or []):
        raise ReviewError(f"the security standard ({std}) is not in {ws}'s profile — switch the extension on (sdem profile include ext:security), or put the standard back; "
                          'without it the review would report no findings, which is not the same as none')
    ours = [f for f in comply['findings'] if ((f.get('standard') or {}).get('id') == std)]
    findings = [f for f in ours if f.get('outcome') in ('non_compliant', 'unresolved')]
    computed = computed_findings(ws)   # SEC-S07, SEC-S08, SEC-LAYER
    excepted = [f for f in ours + computed if f.get('outcome') == 'exception_approved']
    findings += [f for f in computed if f['outcome'] in ('non_compliant', 'unresolved')]
    rows = coverage_rows(ws)
    unprotected = [x for x in rows if not x['protected'] and (x['personal_information'] or x.get('kind_of', x['type']) in ('A3.ApplicationInterface', 'A4.Path', 'A4.NetworkZone', 'A4.CommunicationNetwork', 'A4.InfrastructureComponent'))]
    no_rest = [x for x in rows if x['personal_information'] and x['protected'] and not any(str(c['control_id'] or '').startswith('SC-28') for c in x['controls'])]   # SEC-S01: at rest, specifically
    order = {'non_compliant': 0, 'unresolved': 1}
    findings.sort(key=lambda f: (order.get(f.get('outcome'), 2), f.get('rule', ''), str(f.get('record', ''))))
    return {'findings': findings, 'excepted': excepted, 'unprotected': unprotected, 'personal_data_without_sc28': no_rest}


def cmd_review(a):
    try: d = review_data(a.workspace)
    except ReviewError as e: print(str(e), file=sys.stderr); return 2
    findings, unprotected, no_rest = d['findings'], d['unprotected'], d['personal_data_without_sc28']
    if a.json: print(json.dumps(numbered(d, getattr(a, 'design', a.workspace), a.workspace), indent=2)); return 0
    print(f"Security review of {a.workspace} — {len(findings)} finding(s) from the security rules (the standard and the extension's own checks), "
          f"{len(d['excepted'])} under a person's exception, {len(unprotected)} exposed record(s) with no control")
    for f in findings: print(f"  {f.get('outcome'):<14} {f.get('rule'):<9} {f.get('record')}  {f.get('message', '')}")
    for x in no_rest: print(f"  no SC-28        {x['security_layer']:<9} {x['id']}  personal data with no protection at rest")
    for x in unprotected: print(f"  no control     {x['security_layer']:<9} {x['id']}  {x['type']}")
    return 0


def document_md(ws):
    """The security review as a readable document (Markdown): SDEM's security findings, coverage per S1–S5, the threats and what mitigates
    them, and the STRIDE checklist — generated, deterministic, nothing invented; every record named with its id."""
    ws = as_019(ws)   # DL-22: a 0.20 workspace read as 0.19 held it
    recs, layer_of, rels, maps = workspace(ws)
    rev, rows, chk = review_data(ws), coverage_rows(ws), threats_data(ws)
    def safe(t):   # AUD-11: a record's own text cannot make a heading, a list item, a table row or HTML in the document
        t = re.sub(r'\s+', ' ', str(t)).strip()
        t = re.sub(r'&(?!(?:amp|lt|gt|quot|#\d+);)', '&amp;', t).replace('<', '&lt;').replace('>', '&gt;')   # safe to apply twice
        return re.sub(r'^([#>*+-]|\d+\.)', r'\\\1', t)
    nm = lambda i: f"{safe((recs.get(i) or {}).get('name') or i)} ({i})"
    cell = lambda t: safe(t).replace('|', '\\|')
    sec = {i: r for i, r in recs.items() if layer_of[i] == 'S'}
    kind = lambda t: str(t).split('.')[-1]
    def count(k, one, many): n = sum(1 for r in sec.values() if kind(r['type']) == k); return f"{n} {one if n == 1 else many}"
    L = [f"# Security review — {Path(ws).resolve().name}", '',
         f"> Generated by `sdem security document` (sdem-security {MANIFEST['version']}) from the workspace and its security standard. Read-only: it shows what "
         "the design holds and what SDEM's security rules find — nothing added, nothing decided. Controls are NIST SP 800-53 Rev. 5; threats are STRIDE.", '',
         '## Summary', '',
         f"{len(rows)} records in scope across every layer of a design; {sum(r['protected'] for r in rows)} protected by a control of their own. "
         f"{count('SecurityControl', 'control', 'controls')}, {count('Threat', 'threat', 'threats')}, {count('TrustBoundary', 'trust boundary', 'trust boundaries')}. "
         f"{sum(1 for f in rev['findings'] if f.get('outcome') == 'non_compliant')} finding(s) not compliant, {sum(1 for f in rev['findings'] if f.get('outcome') == 'unresolved')} unresolved"
         f"{(', ' + str(len(rev['excepted'])) + ' under a person' + chr(39) + 's exception') if rev['excepted'] else ''}.", '',
         '| Security layer | Records | Protected | Controls | Threats |', '|---|---|---|---|---|']
    for c, n in S_NAMES.items():
        mine = [x for x in rows if x['security_layer'] == c]
        own = lambda k: sum(1 for r in sec.values() if kind(r['type']) == k and (r.get('attributes') or {}).get('security_layer') == c)
        L.append(f"| {c} {n} | {len(mine)} | {sum(x['protected'] for x in mine)} | {own('SecurityControl')} | {own('Threat')} |")
    L += ['', '## 1. Findings from the security rules', '']
    if not rev['findings']: L.append('None — every security rule is met or does not apply.')
    by = {}
    for f in rev['findings']: by.setdefault(f.get('rule', ''), []).append(f)
    for rule in sorted(by):
        fs = by[rule]
        L += [f"### {rule} — {fs[0].get('message', '')}", '']
        for f in fs:
            rid = f.get('record'); L.append(f"- **{f.get('outcome', '').replace('_', ' ')}** — " + (nm(rid) if rid in recs else str(rid)))
        L.append('')
    L += ['## 2. Records no control protects', '', 'Interfaces, paths, network zones and personal data with no control of their own:', '']
    L += [f"- {x['security_layer']} · {nm(x['id'])} — {kind(x['type'])}" for x in rev['unprotected']] or ['None.']
    L += [f"- personal data with no protection at rest (SC-28): {nm(x['id'])}" for x in rev['personal_data_without_sc28']]
    L += ['', '## 3. Coverage by security layer', '']
    for c, n in S_NAMES.items():
        mine = [x for x in rows if x['security_layer'] == c]
        if not mine: continue
        L += [f"### {c} {n} — {sum(x['protected'] for x in mine)} of {len(mine)} protected", '', '| Record | Kind | Controls (enforced by) | Threats |', '|---|---|---|---|']
        for x in mine:
            ctl = '; '.join(f"{c2['control_id'] or c2['id']} {nm(c2['id'])}" + (f" — by {', '.join(nm(e) for e in c2['enforced_by'])}" if c2['enforced_by'] else '') for c2 in x['controls']) or '—'
            L.append(f"| {cell(nm(x['id']))}{' · personal data' if x['personal_information'] else ''} | {kind(x['type'])} | {cell(ctl)} | {cell(', '.join(nm(t) for t in x['threats']) or '—')} |")
        L.append('')
    L += ['## 4. Threats and what mitigates them', '', '| Threat | STRIDE | Likelihood · impact | Threatens | Mitigated by |', '|---|---|---|---|---|']
    thr = [i for i, r in sorted(sec.items()) if kind(r['type']) == 'Threat']
    for t in thr:
        at = sec[t].get('attributes') or {}
        hits = [m['target']['id'] for m in maps if m['relationship'] == 'THREATENS' and m['source']['id'] == t]
        mit = [l['source'] for l in rels if l.get('kind') == 'mitigates' and l.get('target') == t]
        L.append(f"| {cell(nm(t))} | {cell(''.join(at.get('stride') or [])) or '—'} | {at.get('likelihood') or '—'} · {at.get('impact') or '—'} | {cell(', '.join(nm(h) for h in hits) or '—')} | {cell(', '.join(nm(c2) for c2 in mit) or '— not mitigated')} |")
    if not thr: L.append('| — | | | | |')
    L += ['', '## 5. STRIDE checklist — not yet considered', '', 'A prompt for a person, per record: the STRIDE categories that apply to its kind and that no threat in the design states yet. These are not threats the design holds.', '']
    open_ = [x for x in chk if x['not_yet_considered']]
    L += [f"- {x['security_layer']} · {nm(x['id'])} — {', '.join(STRIDE_WORDS[c2] for c2 in x['not_yet_considered'])}" for x in open_] or ['Every category is considered.']
    return '\n'.join(L) + '\n'


def cmd_document(a):
    try: md = document_md(a.workspace)
    except ReviewError as e: print(str(e), file=sys.stderr); return 2
    if a.out: Path(a.out).write_text(md, encoding='utf-8'); print(f"written: {a.out}")
    else: sys.stdout.write(md)
    return 0


def cmd_remove(a):
    """AUD-01: switch security off in a workspace — a person's decision. SDEM archives the security layer and every connection that
    touches it (archive/ext-security-<date>.json), keeps their ids retired, and takes ext:security out of the profile (MX-16)."""
    if sdem('profile', 'exclude', '--help').returncode != 0:
        print('sdem security remove: this SDEM cannot switch an extension off (sdem profile exclude, MX-16) — reinstall SDEM 0.19.0 from its tag (2026-11-19 or later)', file=sys.stderr); return 2
    args = ['profile', 'exclude', 'ext:security', '--workspace', a.workspace, '--person', a.person, '--reason', a.reason] + (['--dry-run'] if a.dry_run else []) + (['--json'] if a.json else [])
    r = sdem(*args); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)
    if r.returncode == 0 and not a.json: print('The DESNRE site still shows Security for this design until you publish it again; then it shows that Security was switched off, when and by whom (EL-05): sdem desnre create <name> && sdem desnre publish <name>')
    return r.returncode


def cmd_restore(a):
    """EL-06: switch security back on from an archive `remove` wrote — its layer, its connections with their old ids, its exceptions."""
    if sdem('profile', 'restore', '--help').returncode != 0:
        print('sdem security restore: this SDEM cannot restore from an archive (sdem profile restore, EL-06) — reinstall SDEM 0.19.0 from its tag', file=sys.stderr); return 2
    args = ['profile', 'restore', '--archive', a.archive, '--workspace', a.workspace, '--person', a.person, '--reason', a.reason] + (['--skip-unfit'] if a.skip_unfit else []) \
           + (['--dry-run'] if a.dry_run else []) + (['--json'] if a.json else [])
    r = sdem(*args); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)
    if r.returncode == 0 and not a.json: print('The DESNRE site shows Security for this design again after you publish it (EL-04): sdem desnre create <name> && sdem desnre publish <name>')
    return r.returncode


def cmd_purge(a):
    """EL-16: delete security's archived data when a person decides to — never part of remove. The link ids stay retired."""
    if sdem('profile', 'purge', '--help').returncode != 0:
        print('sdem security purge: this SDEM cannot purge archived data (sdem profile purge, EL-16) — reinstall SDEM 0.19.0 from its tag', file=sys.stderr); return 2
    args = ['profile', 'purge'] + (['--archive', a.archive] if a.archive else ['ext:security']) + ['--workspace', a.workspace, '--person', a.person, '--reason', a.reason] \
           + (['--dry-run'] if a.dry_run else []) + (['--json'] if a.json else [])
    r = sdem(*args); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); return r.returncode


def cmd_propose(a):
    args = ['change', 'propose', a.file, '--workspace', a.workspace, '--agent', 'sdem-layer-s', '--person', a.person] + (['--dry-run'] if a.dry_run else []) + (['--json'] if a.json else [])
    r = sdem(*args); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); return r.returncode


STABLE_OF_019 = {'A1': 'business', 'A2': 'bian', 'A4': 'technology'}   # A3: data or application, by the record's type
NUMBERING = ("'layer' and the types are in the numbering this extension's rules are written in (SDEM 0.19's: A1 business, A2 BIAN, "
             "A3 application and data, A4 technology). design_layer is the record's layer as this design names and numbers it — quote that (XA-10).")


def design_layers(ws, copy=None):
    """XA-10: {record id: {'id', 'code', 'name'}} — each record's layer by its stable id (business, bian, data, application,
    technology) and as this design numbers it (SDEM's layers_in_use), so a reader never translates a number."""
    try:
        from sdem.api import layers_in_use
        use = {l['id']: l for l in layers_in_use(ws)}
    except ImportError: use = {}   # an SDEM without it: the stable id alone
    w = copy or as_019(ws); recs, layer_of, _, _ = workspace(w); out = {}
    for rid, r in recs.items():
        L = layer_of.get(rid)
        sid = ('data' if core_type(w, r['type']) in ('A3.DataEntity', 'A3.DataAttribute') else 'application') if L == 'A3' else STABLE_OF_019.get(L)
        if sid: out[rid] = {'id': sid, **({'code': use[sid]['code'], 'name': use[sid]['name']} if sid in use else {})}
    return out


def numbered(d, ws, copy=None):
    """XA-10: a report with each record's design_layer beside the fields it already has."""
    m = design_layers(ws, copy)
    def walk(x):
        if isinstance(x, list): return [walk(v) for v in x]
        if not isinstance(x, dict): return x
        y = {k: walk(v) for k, v in x.items()}
        rid = x.get('id') if isinstance(x.get('id'), str) else x.get('record') if isinstance(x.get('record'), str) else None
        if rid in m and 'design_layer' not in y: y['design_layer'] = m[rid]
        return y
    return {**walk(d), 'numbering': NUMBERING}


def as_019(ws):
    """DL-22: a workspace in SDEM 0.20's form read as 0.19 held it — Data's records in the Application file, each approved ACCESSED_BY as
    access inside it — the form this extension's rules are written in (SEC-S01…, MX-32a). A copy SDEM writes (export_019; proven record by
    record, P2), read and thrown away; a workspace in 0.19's form is read as it is. Records keep their ids, so security's own links hold."""
    try: form = (_j(Path(ws) / 'workspace.json') or {}).get('names')
    except OSError: form = None
    if form != 'ids': return ws
    import tempfile
    from sdem.migrate20 import export_019   # only an SDEM that writes the 0.20 form has it
    out = Path(tempfile.mkdtemp(prefix='sdem-security-')) / (Path(ws).resolve().name or 'workspace')   # '.' has no name of its own
    export_019(ws, out)
    try:
        from sdem.api import layers_in_use
        if not any(l['id'] == 'bian' for l in layers_in_use(ws)): _NO_BIAN.add(str(out))   # the copy has 0.19's empty A2 file; the design has no BIAN
    except ImportError: pass
    return str(out)


_NO_BIAN = set()   # copies (as_019) of designs without BIAN


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['--manifest']:   # how SDEM recognises an extension (EXT-05, EXT-15), and where its pack is (MX-01)
        print(json.dumps(manifest(), indent=2)); return 0
    ap = argparse.ArgumentParser(prog='sdem security', description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('catalogue', help='search NIST SP 800-53 Rev. 5 controls'); p.add_argument('words', nargs='+'); p.add_argument('--limit', type=int, default=25); p.add_argument('--json', action='store_true')
    for name, h in (('coverage', 'per record: its controls, what enforces them, its threats'), ('threats', 'a STRIDE checklist per record (prompts, never records)'), ('review', 'what the security design still lacks')):
        p = sub.add_parser(name, help=h); p.add_argument('--workspace', required=True); p.add_argument('--json', action='store_true')
    p = sub.add_parser('document', help='the security review as a readable document (Markdown): findings, coverage, threats, the STRIDE checklist')
    p.add_argument('--workspace', required=True); p.add_argument('-o', '--out', help='a file; without it, the document is printed')
    p = sub.add_parser('remove', help="switch security off in a workspace — its layer and connections are archived, not lost (a person's decision)")
    p.add_argument('--workspace', required=True); p.add_argument('--person', required=True); p.add_argument('--reason', required=True)
    p.add_argument('--dry-run', action='store_true'); p.add_argument('--json', action='store_true')
    p = sub.add_parser('restore', help="switch security back on from an archive — layer, connections (old ids) and exceptions, checked first (a person's decision)")
    p.add_argument('--archive', required=True); p.add_argument('--workspace', required=True); p.add_argument('--person', required=True); p.add_argument('--reason', required=True)
    p.add_argument('--skip-unfit', action='store_true'); p.add_argument('--dry-run', action='store_true'); p.add_argument('--json', action='store_true')
    p = sub.add_parser('purge', help="delete security's archived data — never the default; --dry-run lists what it would delete and what it cannot reach")
    p.add_argument('--archive', help='one archive; without it, every security archive in the workspace'); p.add_argument('--workspace', required=True)
    p.add_argument('--person', required=True); p.add_argument('--reason', required=True); p.add_argument('--dry-run', action='store_true'); p.add_argument('--json', action='store_true')
    p = sub.add_parser('propose', help='controls, threats and boundaries into the security layer, as a change set a person accepts')
    p.add_argument('file'); p.add_argument('--workspace', required=True); p.add_argument('--person', required=True); p.add_argument('--dry-run', action='store_true'); p.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.command != 'catalogue':   # the catalogue needs no SDEM; everything else is checked against the versions it supports (EXT-04)
        try: out = sdem('--version').stdout or ''
        except OSError: print('sdem security: SDEM is not installed in this environment — install it first (see the README)', file=sys.stderr); return 2
        v = re.search(r'\d+\.\d+\.\d+', out)
        if not v: print(f'sdem security: cannot read SDEM\'s version from {out.strip()[:80]!r} — refusing rather than guessing', file=sys.stderr); return 2
        if not supported(v.group(0), MANIFEST['sdem']):
            print(f"sdem security: SDEM {v.group(0)} is not one this extension supports ({MANIFEST['sdem']})", file=sys.stderr); return 1
    if a.command in ('coverage', 'threats', 'review', 'document'): a.design = a.workspace; a.workspace = as_019(a.workspace)   # read-only: the analysis in its own form
    return {'catalogue': cmd_catalogue, 'coverage': cmd_coverage, 'threats': cmd_threats, 'review': cmd_review, 'document': cmd_document, 'remove': cmd_remove, 'restore': cmd_restore, 'purge': cmd_purge, 'propose': cmd_propose}[a.command](a)


def entry():
    sys.exit(main())
