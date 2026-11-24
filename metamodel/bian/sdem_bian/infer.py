"""sdem-bian infer — BIAN's inference for SDEM (MX-45…MX-52; the SDEM 0.22 plan, step 3b).

    sdem-bian infer --workspace DIR --step link --json
    sdem-bian infer --workspace DIR --step aid --phase NAME --state FILE --json

The second is BIAN's part of `sdem aid` (MX-54; the plan's step 3c): SDEM calls it at each of its phases — projection, patterns,
existing, information, access, direct — with the state so far in FILE, and reads back {"format", "phase", "result"}. The code is
aid_bian.py, generated from SDEM's own copy (BP-11), so SDEM keeps everything between the phases (marking, zones, numbering) its own.

SDEM runs this for `sdem link` on a workspace that uses BIAN (it never imports this package — R-D5). It runs SDEM's rules engine (its
core rules, through sdem.api) with BIAN's own steps (rules_bian.py, the code SDEM split out of its engine), so BIAN's rules see the core's
proposals as they always did (S29 reads DEPLOYED_AS), and answers sdem-inference/1 with what BIAN's rules found — each proposal and
candidate exactly as the engine records it, and any target design (no application layer yet: BIAN's container pattern). SDEM checks it
and lists it with its own core rules' proposals.
"""
import argparse, json, sys

FORMAT = 'sdem-inference/1'


def _rule_of(rec):
    ev = (rec.get('evidence') or [''])[0]
    return ev.split(':', 1)[1].split(' ', 1)[0] if ev.startswith('engine_rationale:') else None


def link(workspace):
    from sdem import api
    from .rules_bian import BianSteps
    api.activate(workspace)
    own = {r['id'] for r in json.loads((api.catalogue_dir().parent / 'inference-rules.json').read_text(encoding='utf-8'))} \
        if (api.catalogue_dir().parent / 'inference-rules.json').exists() else None

    class BianRun(BianSteps, api.CoreRun):
        pass

    reader = api.GraphReader.from_exports(api.estate_files(workspace))   # the workspace read as `sdem link` reads it — every layer file
    out = BianRun(reader, 'RUN').run()
    design = lambda r: ' stepdesign ' in ((r.get('evidence') or [''])[0] + ' ')   # the target design's links (BIAN's container pattern), whatever rule names them
    mine = lambda r: design(r) or ((_rule_of(r) in own) if own is not None else True)
    return {'format': FORMAT,
            'proposals': [{'record': r} for r in out['proposals'] if mine(r)],
            'candidates': [r for r in out.get('candidates', []) if mine(r)],
            'design': out.get('design') or []}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-bian infer', description=__doc__.strip().split('\n')[0])
    ap.add_argument('--workspace', required=True)
    ap.add_argument('--step', required=True, choices=['link', 'aid'])
    ap.add_argument('--phase', help='MX-54: one phase of BIAN\'s part of sdem aid')
    ap.add_argument('--state', help='MX-54: the file holding the state SDEM sends for the phase')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.step == 'aid':
        if not a.phase:   # MX-47's one answer at the end of sdem aid: BIAN gives its part at the phases instead ("aid-phases")
            print(json.dumps({'format': FORMAT})); return 0
        from sdem import api
        from .aid_bian import answer
        import contextlib
        api.activate(a.workspace)
        with open(a.state, encoding='utf-8') as f: state = json.load(f)
        with (api.view_019() if api.parts.migrated() else contextlib.nullcontext()):   # DL-12: AID runs in a migrated workspace's 0.19 view, as SDEM's own run does
            result = answer(a.phase, state, a.workspace)
        print(json.dumps({'format': FORMAT, 'phase': a.phase, 'result': result})); return 0   # ASCII JSON
    print(json.dumps(link(a.workspace))); return 0   # ASCII JSON: the same bytes on every platform and console


if __name__ == '__main__':
    sys.exit(main())
