"""评测运行器：对 questions.csv 每题跑 /ask，输出 Hit Rate / MRR / Recall@K。

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

# Windows 控制台默认 GBK 编码，打不出 emoji，强制切 UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import requests
except ImportError:
    sys.exit("需要 requests：pip install requests")

_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _point_substrings(point):
    """提取期望要点的中文子串集合（用于模糊匹配）。"""
    if len(point) <= 4:
        return {point}
    subs = set()
    for i in range(len(point)):
        for n in (2, 3, 4):
            if i + n <= len(point):
                sub = point[i:i + n]
                if re.match(r"[\u4e00-\u9fff]+$", sub):
                    subs.add(sub)
    return subs


def _point_matched(point, text):
    """判断单个期望要点是否在 text 中模糊匹配（覆盖率 ≥ 30%）。"""
    if len(point) <= 4:
        return point in text
    subs = _point_substrings(point)
    if not subs:
        return False
    matched = sum(1 for s in subs if s in text)
    return matched / len(subs) >= 0.3


def _matched_points(expected, text):
    """返回 expected 中被 text 命中的要点列表。"""
    if not expected:
        return []
    points = [k.strip() for k in expected.split("、") if k.strip()]
    return [p for p in points if _point_matched(p, text)]


def run_eval(api_url, csv_path, recall_k=5):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    hits = 0
    mrr_sum = 0.0
    recall_sum = 0.0
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
            details.append({"id": qid, "question": q, "hit": False,
                            "mrr": 0.0, "recall_at_k": 0.0,
                            "reason": f"HTTP {resp.status_code}"})
            continue

        data = resp.json()
        answer = data.get("answer", "")
        refs = data.get("references", [])

        # ── 逐引用判定命中位置（MRR）──
        points = [k.strip() for k in expected.split("、") if k.strip()] if expected else []
        first_hit_rank = 0  # 1-based，0 = 未命中
        for rank, r in enumerate(refs, 1):
            ref_text = answer + " " + r.get("title", "")
            if _matched_points(expected, ref_text):
                first_hit_rank = rank
                break

        hit = first_hit_rank > 0
        rr = 1.0 / first_hit_rank if hit else 0.0

        # ── Recall@K：top-K 引用覆盖的期望要点比例 ──
        if points:
            all_ref_text = answer + " " + " ".join(
                r.get("title", "") for r in refs[:recall_k]
            )
            matched = len(_matched_points(expected, all_ref_text))
            recall = matched / len(points)
        else:
            recall = 0.0

        if hit:
            hits += 1
        mrr_sum += rr
        recall_sum += recall

        details.append({
            "id": qid,
            "question": q,
            "category": category,
            "expected": expected,
            "hit": hit,
            "hit_rank": first_hit_rank,
            "mrr": round(rr, 4),
            "recall_at_k": round(recall, 4),
            "confidence": data.get("confidence", 0),
            "top_title": refs[0]["title"] if refs else "",
        })

    rate = hits / total * 100 if total else 0
    mrr = mrr_sum / total if total else 0
    recall_at_k = recall_sum / total if total else 0

    print(f"\n{'='*60}")
    print(f"评测结果：{hits}/{total} 命中")
    print(f"  Hit Rate   : {rate:.1f}%")
    print(f"  MRR        : {mrr:.4f}")
    print(f"  Recall@{recall_k}   : {recall_at_k:.4f}")
    print(f"{'='*60}")

    for d in details:
        mark = "✅" if d["hit"] else "❌"
        rank_str = f"r{d['hit_rank']}" if d["hit"] else "r-"
        print(f"  {mark} [{d['id']}] {d['question'][:20]} | {d['category']} "
              f"| {rank_str} | MRR={d['mrr']:.2f} | R@{recall_k}={d['recall_at_k']:.2f} "
              f"| {d['top_title'][:25]}")

    return rate, mrr, recall_at_k, details


def save_results(rate, mrr, recall_at_k, details, recall_k=5):
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
        "hit_rate": round(rate, 1),
        "mrr": round(mrr, 4),
        f"recall_at_{recall_k}": round(recall_at_k, 4),
        "details": details,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    paths.append(json_path)

    # CSV 汇总（每题一行）
    csv_path = os.path.join(_RESULTS_DIR, f"eval_{ts}.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "question", "category", "hit", "hit_rank",
                         "mrr", f"recall_at_{recall_k}", "confidence", "top_title", "expected"])
        for d in details:
            writer.writerow([
                d.get("id", ""), d.get("question", ""), d.get("category", ""),
                d.get("hit", False), d.get("hit_rank", 0),
                d.get("mrr", 0), d.get("recall_at_k", 0),
                d.get("confidence", 0), d.get("top_title", ""), d.get("expected", ""),
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
    parser.add_argument("--recall-k", type=int, default=5, help="Recall@K 的 K 值（默认 5）")
    args = parser.parse_args()

    rate, mrr, recall_at_k, details = run_eval(args.api, args.csv, recall_k=args.recall_k)
    if rate < 85:
        print(f"\n⚠️  当前 Hit Rate {rate:.1f}% < 85% 目标，需优化检索或补充数据")
    else:
        print(f"\n🎉 Hit Rate 达标！{rate:.1f}% ≥ 85%")

    print(f"   MRR = {mrr:.4f}（越接近 1 越好，1 = 全部 top-1 命中）")
    print(f"   Recall@{args.recall_k} = {recall_at_k:.4f}（越接近 1 越好）")

    if args.save:
        paths = save_results(rate, mrr, recall_at_k, details, recall_k=args.recall_k)
        print(f"\n📁 结果已落盘：")
        for p in paths:
            print(f"   {p}")


if __name__ == "__main__":
    main()