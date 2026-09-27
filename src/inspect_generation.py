"""Print the saved structure of generation attempts: where reasoning and final response live."""
import argparse, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--show", type=int, default=0, help="chars of reasoning/final to print")
a = ap.parse_args()
d = ROOT / "raw" / "generations" / a.tag
rows = [json.loads(x) for x in (d / "manifest.jsonl").read_text().splitlines() if x.strip()]
print(f"{'attempt_id':22} {'valid':5} {'finish':6} {'rfield':18} {'reas_ch':7} {'fin_ch':6} {'ctok':5} {'lat_s':6}")
for r in rows:
    print(f"{r['attempt_id']:22} {str(r['valid']):5} {str(r['finish_reason']):6} "
          f"{str(r.get('reasoning_field_used')):18} {r['reasoning_chars']:7} {r['final_chars']:6} "
          f"{(r.get('usage') or {}).get('completion_tokens', -1):5} {r['latency_s']:6.1f}")
print(f"\ntruncated: {sum(1 for r in rows if r['truncated'])}/{len(rows)}  "
      f"valid: {sum(1 for r in rows if r['valid'])}/{len(rows)}  "
      f"max completion_tokens: {max((r.get('usage') or {}).get('completion_tokens', 0) for r in rows)}")
for r in rows:
    print(f"\nRAW FILE: {r['raw_path']}  sha256={r['raw_file_sha256'][:16]}...")
    print(f"  reasoning     -> JSON key 'reasoning_content'  (raw_response.choices[0].message.{r.get('reasoning_field_used')})")
    print(f"  final response-> JSON key 'final_content'       (raw_response.choices[0].message.content)")
    if a.show:
        full = json.loads((ROOT / r["raw_path"]).read_text())
        print("  --- reasoning head ---"); print("   " + (full["reasoning_content"] or "")[: a.show].replace("\n", "\n   "))
        print("  --- final head ---"); print("   " + (full["final_content"] or "")[: a.show].replace("\n", "\n   "))
