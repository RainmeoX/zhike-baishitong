"""评测运行器：对 questions.csv 每题跑 /ask，输出 Hit Rate / MRR / Recall@K / 引用正确率。

题型约定（100 问 = 60 普通 + 30 拒答 + 10 陷阱）：
  - 普通/陷阱题：期望答案要点非空，按要点命中判定（陷阱题含错误前提，要点为正确纠正内容）
  - 拒答题：期望答案要点为空，答案含拒答标记即算拒答成功
    （库内无相关信息时正确拒答，而非编造；拒答成功不计入 Hit Rate 分母，单独统计拒答成功率）

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

# 引用正确性抽检需要读库（retrieval.db 仅依赖标准库，无额外负担）
from retrieval.db import get_conn, DB_PATH

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


def _ref_text(r):
    """引用自身判定文本：标题+部门+栏目。

    不拼 LLM answer——answer 由引用内容生成，拼入判定文本会让
    rank-1 恒命中，MRR/Recall 失真为 1.0，测不出真实检索排序。
    """
    return " ".join(r.get(key, "") for key in ("title", "department", "column"))


# ── 引用正确性抽检 ──
# LLM 答案末尾标注「（来源：部门-通知标题）」，兜底答案形如「根据「标题」：摘要」
_CITE_PATTERNS = (
    re.compile(r"[（(]来源[：:]\s*([^）)]+)[）)]"),
    re.compile(r"根据[「『]([^」』]+)[」』]"),
)

# ── 拒答判定 ──
# 拒答题（期望要点为空）的正确行为是明确说明库内无相关信息，而非编造。
# 标记覆盖兜底答案「暂未检索到…建议联系…」与 LLM 说明不足类回答的常见措辞。
_REFUSAL_MARKS = (
    "暂未检索到", "未检索到", "未能检索到", "无法回答",
    "不足以回答", "建议联系", "暂无相关", "抱歉，",
)


def _is_refusal(answer):
    """判断答案是否为拒答（库内无相关信息时的正确行为）。"""
    return any(m in answer for m in _REFUSAL_MARKS)


def _cited_sources(answer):
    """从答案文本提取被引出处字符串（去重保序）。"""
    if not answer:
        return []
    seen, sources = set(), []
    for pat in _CITE_PATTERNS:
        for m in pat.finditer(answer):
            s = m.group(1).strip()
            if s and s not in seen:
                seen.add(s)
                sources.append(s)
    return sources


def _load_title_content(db_path=None):
    """从库建 title→content 映射；库缺失、无文档表或无数据时返回 None（跳过抽检）。"""
    path = str(db_path) if db_path else str(DB_PATH)
    if not os.path.exists(path):
        return None
    try:
        conn = get_conn(db_path)
        rows = conn.execute("SELECT title, content FROM documents").fetchall()
        conn.close()
    except Exception:
        return None
    if not rows:
        return None
    return {r["title"]: r["content"] for r in rows}


def _resolve_cited_doc(source, title_content):
    """把「部门-标题」出处解析为库内文档标题，未命中返回 None。

    精确匹配 → 标题包含于出处串 → 取「-」后缀匹配，选最长命中减少误配。
    """
    if source in title_content:
        return source
    tail = source.rsplit("-", 1)[-1].strip()
    candidates = [t for t in title_content if t and (t in source or (tail and tail in t))]
    return max(candidates, key=len) if candidates else None


def _citation_check(answer, expected, title_content):
    """引用正确性抽检：每条被引出处解析到文档后，正文含 ≥1 个期望要点即算对。

    返回 (被引总数, 正确数)；title_content 为 None 时返回 None（跳过）。
    出处解析不到库内文档计为不正确（无法验证即不可信）。
    """
    if title_content is None:
        return None
    total = ok = 0
    for s in _cited_sources(answer):
        total += 1
        title = _resolve_cited_doc(s, title_content)
        if title and _matched_points(expected, title_content[title]):
            ok += 1
    return total, ok


def run_eval(api_url, csv_path, recall_k=5):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # 引用抽检前置：库缺失则整场跳过（不阻塞评测主流程）
    title_content = _load_title_content()
    if title_content is None:
        print("⚠️  未找到爬取数据（data/zcst.db），本轮跳过引用正确性抽检")

    total = len(rows)
    hits = 0
    mrr_sum = 0.0
    recall_sum = 0.0
    cite_total = 0
    cite_ok = 0
    refusal_total = 0
    refusal_ok = 0
    details = []

    for row in rows:
        qid = row.get("id", row.get("ID", ""))
        q = row.get("问题", row.get("question", ""))
        expected = row.get("期望答案要点", row.get("expected", ""))
        category = row.get("类别", row.get("category", ""))

        try:
            resp = requests.post(
                f"{api_url}/ask",
                json={"question": q, "topk": 5},
                timeout=60,
            )
        except Exception as e:
            # 连接失败等异常：单题跳过，不中断整场评测
            details.append({"id": qid, "question": q, "hit": False,
                            "mrr": 0.0, "recall_at_k": 0.0,
                            "reason": f"请求失败 {e}"})
            print(f"[跳过] {qid}: 请求失败 {e}")
            continue
        if resp.status_code != 200:
            details.append({"id": qid, "question": q, "hit": False,
                            "mrr": 0.0, "recall_at_k": 0.0,
                            "reason": f"HTTP {resp.status_code}"})
            continue

        data = resp.json()
        refs = data.get("references", [])
        answer = data.get("answer", "")

        # ── 拒答题（期望要点为空）：答案含拒答标记即算拒答成功 ──
        # 库内无相关信息时正确拒答而非编造；不计入 Hit Rate 分母，单独统计
        if not expected:
            refusal_total += 1
            refused = _is_refusal(answer)
            if refused:
                refusal_ok += 1
            details.append({
                "id": qid,
                "question": q,
                "category": category,
                "expected": expected,
                "type": "refusal",
                "hit": refused,
                "hit_rank": 0,
                "mrr": 0.0,
                "recall_at_k": 0.0,
                "confidence": data.get("confidence", 0),
                "top_title": refs[0]["title"] if refs else "",
                "cite_ok": 0,
                "cite_total": 0,
                "refusal_ok": refused,
            })
            continue

        # ── 逐引用判定命中位置（MRR）──
        points = [k.strip() for k in expected.split("、") if k.strip()] if expected else []
        first_hit_rank = 0  # 1-based，0 = 未命中
        for rank, r in enumerate(refs, 1):
            if _matched_points(expected, _ref_text(r)):
                first_hit_rank = rank
                break

        hit = first_hit_rank > 0
        rr = 1.0 / first_hit_rank if hit else 0.0

        # ── Recall@K：top-K 引用覆盖的期望要点比例 ──
        if points:
            all_ref_text = " ".join(_ref_text(r) for r in refs[:recall_k])
            matched = len(_matched_points(expected, all_ref_text))
            recall = matched / len(points)
        else:
            recall = 0.0

        # ── 引用正确性抽检：被引文档正文是否含期望要点 ──
        cite = _citation_check(answer, expected, title_content)
        if cite is not None:
            cite_total += cite[0]
            cite_ok += cite[1]

        if hit:
            hits += 1
        mrr_sum += rr
        recall_sum += recall

        details.append({
            "id": qid,
            "question": q,
            "category": category,
            "expected": expected,
            "type": "normal",
            "hit": hit,
            "hit_rank": first_hit_rank,
            "mrr": round(rr, 4),
            "recall_at_k": round(recall, 4),
            "confidence": data.get("confidence", 0),
            "top_title": refs[0]["title"] if refs else "",
            "cite_ok": cite[1] if cite is not None else 0,
            "cite_total": cite[0] if cite is not None else 0,
        })

    # 指标分母只算可答题（普通+陷阱）；拒答题单独统计拒答成功率
    answerable = total - refusal_total
    rate = hits / answerable * 100 if answerable else 0
    mrr = mrr_sum / answerable if answerable else 0
    recall_at_k = recall_sum / answerable if answerable else 0
    refusal_rate = refusal_ok / refusal_total * 100 if refusal_total else None
    cite_prec = cite_ok / cite_total * 100 if cite_total else None

    print(f"\n{'='*60}")
    print(f"评测结果：{hits}/{answerable} 命中（另拒答题 {refusal_ok}/{refusal_total} 正确说明）")
    print(f"  Hit Rate   : {rate:.1f}%")
    print(f"  MRR        : {mrr:.4f}")
    print(f"  Recall@{recall_k}   : {recall_at_k:.4f}")
    if refusal_rate is not None:
        print(f"  拒答成功率 : {refusal_rate:.1f}%（{refusal_ok}/{refusal_total} 道无答案题正确说明而非编造）")
    if cite_prec is not None:
        print(f"  引用正确率 : {cite_prec:.1f}%（{cite_ok}/{cite_total} 条引用验证通过）")
    elif title_content is not None:
        print(f"  引用正确率 : 无引用可校验")
    else:
        print(f"  引用正确率 : 跳过（未找到爬取数据）")
    print(f"{'='*60}")

    for d in details:
        mark = "✅" if d.get("hit") else "❌"
        if d.get("type") == "refusal":
            rank_str = "拒答" if d.get("refusal_ok") else "编造"
        else:
            rank_str = f"r{d['hit_rank']}" if d.get("hit") else "r-"
        print(f"  {mark} [{d.get('id', '')}] {d.get('question', '')[:20]} | {d.get('category', '')} "
              f"| {rank_str} | MRR={d.get('mrr', 0):.2f} | R@{recall_k}={d.get('recall_at_k', 0):.2f} "
              f"| {d.get('top_title', '')[:25]}")

    return rate, mrr, recall_at_k, cite_prec, refusal_rate, details


def save_results(rate, mrr, recall_at_k, details, recall_k=5):
    """将评测结果落盘到 evaluation/results/，返回写入的文件路径列表。"""
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []

    # 引用正确率：从明细微平均（Σok/Σtotal），无引用则记 null
    c_total = sum(d.get("cite_total", 0) for d in details)
    c_ok = sum(d.get("cite_ok", 0) for d in details)

    # 拒答成功率：从明细统计（type=refusal 的题）
    ref_rows = [d for d in details if d.get("type") == "refusal"]
    r_total = len(ref_rows)
    r_ok = sum(1 for d in ref_rows if d.get("refusal_ok"))

    # JSON 全量明细
    json_path = os.path.join(_RESULTS_DIR, f"eval_{ts}.json")
    payload = {
        "timestamp": ts,
        "total": len(details),
        "hits": sum(1 for d in details if d["hit"]),
        "hit_rate": round(rate, 1),
        "mrr": round(mrr, 4),
        f"recall_at_{recall_k}": round(recall_at_k, 4),
        "citation_precision": round(c_ok / c_total * 100, 1) if c_total else None,
        "refusal_total": r_total,
        "refusal_ok": r_ok,
        "refusal_rate": round(r_ok / r_total * 100, 1) if r_total else None,
        "details": details,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    paths.append(json_path)

    # CSV 汇总（每题一行）
    csv_path = os.path.join(_RESULTS_DIR, f"eval_{ts}.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "question", "category", "type", "hit", "hit_rank",
                         "mrr", f"recall_at_{recall_k}", "confidence", "top_title", "expected",
                         "cite_ok", "cite_total", "refusal_ok"])
        for d in details:
            writer.writerow([
                d.get("id", ""), d.get("question", ""), d.get("category", ""),
                d.get("type", "normal"),
                d.get("hit", False), d.get("hit_rank", 0),
                d.get("mrr", 0), d.get("recall_at_k", 0),
                d.get("confidence", 0), d.get("top_title", ""), d.get("expected", ""),
                d.get("cite_ok", 0), d.get("cite_total", 0),
                d.get("refusal_ok", ""),
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

    rate, mrr, recall_at_k, cite_prec, refusal_rate, details = run_eval(args.api, args.csv, recall_k=args.recall_k)
    if rate < 85:
        print(f"\n⚠️  当前 Hit Rate {rate:.1f}% < 85% 目标，需优化检索或补充数据")
    else:
        print(f"\n🎉 Hit Rate 达标！{rate:.1f}% ≥ 85%")

    print(f"   MRR = {mrr:.4f}（越接近 1 越好，1 = 全部 top-1 命中）")
    print(f"   Recall@{args.recall_k} = {recall_at_k:.4f}（越接近 1 越好）")
    if refusal_rate is not None:
        print(f"   拒答成功率 = {refusal_rate:.1f}%（无答案题需正确说明而非编造）")
    if cite_prec is not None:
        print(f"   引用正确率 = {cite_prec:.1f}%（被引文档需含期望要点才算验证通过）")

    if args.save:
        paths = save_results(rate, mrr, recall_at_k, details, recall_k=args.recall_k)
        print(f"\n📁 结果已落盘：")
        for p in paths:
            print(f"   {p}")


if __name__ == "__main__":
    main()