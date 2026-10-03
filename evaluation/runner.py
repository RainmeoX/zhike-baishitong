"""评测运行器：对 questions.csv 每题跑 /ask，输出命中率。

用法：
  python -m evaluation.runner --api http://127.0.0.1:8000
  python -m evaluation.runner --api http://127.0.0.1:8000 --csv evaluation/questions.csv
"""

import argparse
import csv
import json
import sys

try:
    import requests
except ImportError:
    sys.exit("需要 requests：pip install requests")


def run_eval(api_url, csv_path):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    hits = 0
    details = []

    for row in rows:
        qid = row.get("id", row.get("ID", ""))
        q = row.get("问题", row.get("question", ""))
        expected = row.get("期望答案要点", row.get("expected", ""))
        category = row.get("类别", row.get("category", ""))

        resp = requests.post(
            f"{api_url}/ask",
            json={"question": q, "topk": 5},
            timeout=15,
        )
        if resp.status_code != 200:
            details.append({"id": qid, "question": q, "hit": False, "reason": f"HTTP {resp.status_code}"})
            continue

        data = resp.json()
        answer = data.get("answer", "")
        refs = data.get("references", [])

        # 命中判定：期望答案要点按"、"分隔，每个要点提取核心子串做模糊匹配
        hit = False
        if expected:
            import re
            points = [k.strip() for k in expected.split("、") if k.strip()]
            combined = answer + " " + " ".join(r.get("title", "") for r in refs)
            for point in points:
                if len(point) <= 4:
                    if point in combined:
                        hit = True
                        break
                    continue
                subs = set()
                for i in range(len(point)):
                    for n in (2, 3, 4):
                        if i + n <= len(point):
                            sub = point[i:i+n]
                            if re.match(r"[\u4e00-\u9fff]+$", sub):
                                subs.add(sub)
                if not subs:
                    continue
                matched = sum(1 for s in subs if s in combined)
                if matched / len(subs) >= 0.3:
                    hit = True
                    break

        if hit:
            hits += 1

        details.append({
            "id": qid,
            "question": q,
            "category": category,
            "expected": expected,
            "hit": hit,
            "confidence": data.get("confidence", 0),
            "top_title": refs[0]["title"] if refs else "",
        })

    rate = hits / total * 100 if total else 0
    print(f"\n{'='*50}")
    print(f"评测结果：{hits}/{total} 命中，准确率 {rate:.1f}%")
    print(f"{'='*50}")

    for d in details:
        mark = "✅" if d["hit"] else "❌"
        print(f"  {mark} [{d['id']}] {d['question'][:20]} | {d['category']} | conf={d['confidence']:.1f} | {d['top_title'][:25]}")

    return rate, details


def main():
    parser = argparse.ArgumentParser(description="珠科百事通评测运行器")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="API 地址")
    parser.add_argument("--csv", default="evaluation/questions.csv", help="评测集 CSV")
    args = parser.parse_args()

    rate, details = run_eval(args.api, args.csv)
    if rate < 85:
        print(f"\n⚠️  当前准确率 {rate:.1f}% < 85% 目标，需优化检索或补充数据")
    else:
        print(f"\n🎉 达标！准确率 {rate:.1f}% ≥ 85%")


if __name__ == "__main__":
    main()