"""评测运行器：对 questions.csv 每题跑 /ask，输出命中率。

用法：
  python -m evaluation.runner --api http://127.0.0.1:8000
  python -m evaluation.runner --api http://127.0.0.1:8000 --csv evaluation/questions.csv
  python -m evaluation.runner --api http://127.0.0.1:8000 --save
"""

import argparse
import csv
import datetime
import json
import os
import re
import shutil
import sys

try:
    import requests
except ImportError:
    sys.exit("需要 requests：pip install requests")

_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


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
            timeout=60,
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


def save_results(rate, details):
    """将评测结果落盘到 evaluation/results/，返回写入的文件路径列表。"""
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []

    # JSON 全量明细
    json_path = os.path.join(_RESULTS_DIR, f"eval_{ts}.json")
    payload = {
        "timestamp": ts,
        "total": len(details),
        "hits": sum(1 for d in details if d["hit"]),
        "accuracy": round(rate, 1),
        "details": details,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    paths.append(json_path)

    # CSV 汇总（每题一行）
    csv_path = os.path.join(_RESULTS_DIR, f"eval_{ts}.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "question", "category", "hit", "confidence", "top_title", "expected"])
        for d in details:
            writer.writerow([
                d.get("id", ""), d.get("question", ""), d.get("category", ""),
                d.get("hit", False), d.get("confidence", 0),
                d.get("top_title", ""), d.get("expected", ""),
            ])
    paths.append(csv_path)

    # latest 副本（覆盖，Windows 无需管理员权限）
    for ext, src in ((".json", json_path), (".csv", csv_path)):
        latest = os.path.join(_RESULTS_DIR, f"latest{ext}")
        shutil.copy2(src, latest)
        paths.append(latest)

    return paths


def main():
    parser = argparse.ArgumentParser(description="珠科百事通评测运行器")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="API 地址")
    parser.add_argument("--csv", default="evaluation/questions.csv", help="评测集 CSV")
    parser.add_argument("--save", action="store_true", help="结果落盘到 evaluation/results/")
    args = parser.parse_args()

    rate, details = run_eval(args.api, args.csv)
    if rate < 85:
        print(f"\n⚠️  当前准确率 {rate:.1f}% < 85% 目标，需优化检索或补充数据")
    else:
        print(f"\n🎉 达标！准确率 {rate:.1f}% ≥ 85%")

    if args.save:
        paths = save_results(rate, details)
        print(f"\n📁 结果已落盘：")
        for p in paths:
            print(f"   {p}")


if __name__ == "__main__":
    main()