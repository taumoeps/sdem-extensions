"""sdem-bian infer — BIAN's inference for SDEM (MX-45…MX-52; the SDEM 0.22 plan, step 3b).

    sdem-bian infer --workspace DIR --step link --json

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
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.step == 'aid':   # step 3c: AID's BIAN steps move here next; until then SDEM's own run (the manifest says "infers": ["link"])
        print(json.dumps({'format': FORMAT})); return 0
    print(json.dumps(link(a.workspace))); return 0   # ASCII JSON: the same bytes on every platform and console


if __name__ == '__main__':
    sys.exit(main())
