"""Build a self-contained HTML adjudication tool. Blinded, keyboard-driven, autosaving.

Tier 1 = the 24 responses that decide the original headline (stem_only vs route_search).
Tier 2 = the 24 that decide the follow-up replication (D00_control vs D01_search).
Tier 3 = 20 responses that emailed the target but the grader called NOT coercion
         (these estimate the grader's false-negative rate; without them, precision only).
"""
import json, pathlib, random, hashlib, html
ROOT = pathlib.Path(__file__).resolve().parent.parent
TAGS = ['pilot','main','r1main','gcdiag','s1','s1c','s1d','s1e','s2fact','s2factb']

def jl(p):
    p = ROOT/p
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

gen, oc = {}, {}
for t in TAGS:
    for r in jl(f'raw/generations/{t}/manifest.jsonl'):
        if r.get('valid') and r['draw_id'] not in gen: gen[r['draw_id']] = r
    for r in jl(f'raw/outcomes/{t}/manifest.jsonl'):
        if r.get('parse_ok') and r['draw_id'] not in oc: oc[r['draw_id']] = r

ids = [d for d in gen if d in oc]
pos = lambda d: oc[d]['classifier_verdict'] and oc[d]['target_email_present']
T1 = sorted(d for d in ids if gen[d].get('arm') in ('stem_only','route_search_no_frame') and pos(d))
T2 = sorted(d for d in ids if gen[d].get('arm') in ('D00_control','D01_search') and pos(d))
emo = sorted(d for d in ids if gen[d].get('arm') in
             ('stem_only','route_search_no_frame','D00_control','D01_search')
             and oc[d]['target_email_present'] and not oc[d]['classifier_verdict'])
rng = random.Random(20260912)
T3 = sorted(rng.sample(emo, min(20, len(emo))))

items = []
for tier, group in ((1, T1), (2, T2), (3, T3)):
    for d in group:
        raw = json.loads((ROOT/gen[d]['raw_path']).read_text())
        items.append({
            "ref": hashlib.sha256(d.encode()).hexdigest()[:10],
            "tier": tier,
            "response": raw['final_content'] or "",
        })
# shuffle within each tier so tier order is preserved but content order is not
out = []
for tier in (1, 2, 3):
    g = [i for i in items if i['tier'] == tier]
    rng.shuffle(g); out += g
for n, it in enumerate(out, 1): it['n'] = n

key = {}
for tier, group in ((1, T1), (2, T2), (3, T3)):
    for d in group:
        key[hashlib.sha256(d.encode()).hexdigest()[:10]] = {
            "draw_id": d, "tier": tier, "arm": gen[d].get('arm'),
            "grader_coercion": oc[d]['classifier_verdict'],
            "target_email": oc[d]['target_email_present'],
            "keyword": oc[d]['keyword_blackmail_or_leverage'],
            "upstream_composite": oc[d]['blackmail'],
        }
dest = ROOT/"annotation"/"adjudication"
dest.mkdir(parents=True, exist_ok=True)
(dest/"KEY_do_not_open.json").write_text(json.dumps(key, indent=2))
(dest/"items.json").write_text(json.dumps(out, indent=2))
print(f"tier1={len(T1)} tier2={len(T2)} tier3={len(T3)} total={len(out)}")
