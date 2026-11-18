# A made-up security design for SDEM's payment-initiation-v3

Synthetic data only — a fictional bank's payment initiation, the security design added on top of SDEM's
`examples/payment-initiation-v3/sdem` workspace (the sdem-security spec §9).

- `security-design.json` — a change set for the security layer: 9 controls (NIST SP 800-53 Rev. 5: IA-2, IA-8, SC-8, SC-28,
  SC-12, SC-7, SI-10, AU-12, AC-5), 5 threats (STRIDE) and the internet-edge trust boundary, with which control mitigates which threat.
- `security-links.json` — 36 links into A1–A4 (`PROTECTS`, `ENFORCED_BY`, `THREATENS`, `BOUNDS`), each approved by a person with evidence.

```
cp -r <bian-sdem-framework>/examples/payment-initiation-v3/sdem /tmp/secws
sdem profile include ext:security --workspace /tmp/secws --person <you> --reason "security design"
sdem profile adopt --workspace /tmp/secws --person <you> --reason "the security layer"
sdem security propose security-design.json --workspace /tmp/secws --person <you>
python - <<'PY'   # each link, approved by a person with its evidence
import json, subprocess
for x in json.load(open('security-links.json')):
    subprocess.run(['sdem', 'connect', x['source'], x['relationship'], x['target'], '--workspace', '/tmp/secws', '--person', '<you>',
                    '--evidence', 'design_document:security-design.md#5', '--rationale', 'the made-up security design'], check=True)
PY
sdem security coverage --workspace /tmp/secws
sdem security review --workspace /tmp/secws
```

`review` then shows what this made-up design still lacks — two personal-data entities with no classification, two paths
whose encryption is not given, four zones with no control: the gaps a security reviewer would raise.

## S2 — the service domains' own security (added 2026-11-19)

`security-design-s2.json` and `security-links-s2.json` add the security of the BIAN service domains themselves — proposed security responsibilities, not controls BIAN specifies: six controls and four threats for Payment Order Initiation (AC-3, SI-7, AU-10), Party Authentication (IA-5) and Fraud Evaluation (SI-7, AC-6), each PROTECTS a service domain or its control record and is ENFORCED_BY the application that carries it out (S4/S5 controls stay where they are — no control is copied into S2 to fill the layer). Load them after the first two files, the same way:

```
sdem security propose security-design-s2.json --workspace <ws> --person <you>
# each link in security-links-s2.json: sdem connect <source> <relationship> <target> --workspace <ws> --person <you> --evidence design_document:security-design.md#6 --rationale "…"
```

Made-up data, like everything here.
