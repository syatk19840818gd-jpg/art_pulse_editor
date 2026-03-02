import glob
import json

files = sorted(glob.glob(r"data/phase1_seed10/logs/debug_exhibitions_listing_triage_*.json"))
if not files:
    raise FileNotFoundError("debug_exhibitions_listing_triage_*.json が見つかりません")

p = files[-1]
print("using:", p)

with open(p, encoding="utf-8") as f:
    data = json.load(f)

for x in data:
    print("\n---")
    print("gallery_name_en:", x.get("gallery_name_en"))
    print("provisional_root_cause:", x.get("provisional_root_cause"))
    print("accepted_candidate_count:", x.get("accepted_candidate_count"))
    print("accepted_detail_urls_top20:", x.get("accepted_detail_urls_top20"))
    print("evidence_summary_ja:", x.get("evidence_summary_ja"))