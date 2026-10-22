"""关键词检索：FTS5 精确命中数字/英文 + LIKE 中文子串 + 同义词扩展。"""

import re

from api.log import get_logger
from retrieval.db import get_conn, init_db

logger = get_logger(__name__)

SYNONYMS = {
    # ── 交通 ──
    "校巴": ["班车", "巴士", "校车", "校园巴士"],
    "校车": ["班车", "巴士", "校园巴士"],
    "班车": ["校巴", "校车", "巴士"],
    "通勤": ["上下班", "通勤车"],
    "单车": ["自行车", "共享单车", "青桔"],
    # ── 餐饮 ──
    "饭堂": ["食堂", "餐厅"],
    "食堂": ["饭堂", "餐厅"],
    "外卖": ["配送", "送餐", "餐食"],
    # ── 住宿 ──
    "宿舍": ["公寓", "住宿"],
    "公寓": ["宿舍", "住宿"],
    "门禁": ["出入", "刷卡进门"],
    # ── 缴费 ──
    "缴费": ["收费", "交费", "水费", "电费"],
    "收费": ["缴费", "交费"],
    "学费": ["缴费", "收费"],
    "退费": ["退款", "退还"],
    # ── 报修/故障 ──
    "报修": ["维修", "保修", "故障"],
    "维修": ["报修", "保修"],
    "报修电话": ["服务电话", "联系电话", "后勤电话", "日常服务"],
    "停水": ["断水", "没水"],
    "停电": ["断电", "没电", "停电检修"],
    # ── 教务-选课/考试 ──
    "选课": ["退课", "改选", "选修"],
    "重修": ["补考", "重修报名"],
    "四六级": ["四、六级", "四级", "六级", "CET"],
    "四级": ["四、六级", "CET"],
    "六级": ["四、六级", "CET"],
    "准考证": ["考试证", "打印准考证"],
    "挂科": ["不及格", "没过", "挂了"],
    # ── 教务-学籍/毕业 ──
    "学籍": ["注册", "学籍信息"],
    "毕业": ["离校", "预毕业", "毕业图像"],
    "论文": ["毕设", "毕业设计", "毕业论文"],
    "实习": ["实践", "实训"],
    "学分": ["绩点", "GPA", "学分绩"],
    "绩点": ["学分", "GPA", "学分绩"],
    "转专业": ["转系", "专业调整"],
    "请假": ["销假", "假条"],
    # ── 招生 ──
    "分数线": ["录取线", "录取分数", "投档线"],
    "录取": ["分数线", "录取分"],
    "奖学金": ["助学金", "奖助"],
    "助学金": ["奖学金", "奖助"],
    "新生": ["入学", "迎新", "新生入学"],
    "军训": ["国防教育", "军事训练"],
    "招生章程": ["招生简章", "招生计划"],
    # ── 后勤-生活 ──
    "空调": ["风扇", "空调清洗"],
    "网络": ["校园网", "wifi", "WiFi", "上网"],
    "快递": ["驿站", "取件", "菜鸟"],
    "消杀": ["灭虫", "除虫", "绿化消杀"],
    "垃圾分类": ["分类垃圾", "分类投放"],
    "控烟": ["禁烟", "吸烟"],
    # ── 安全/应急 ──
    "消防": ["防火", "消防安全"],
    "应急": ["预案", "应急处理"],
    "防台": ["台风", "防暴雨", "防风"],
    "食品安全": ["食品卫生", "食物中毒"],
    # ── 体测 ──
    "体测": ["体质测试", "体能测试"],
}


def _extract_keywords(query):
    keywords = set()
    for kw, syns in SYNONYMS.items():
        if kw.lower() in query.lower():
            keywords.add(kw)
            keywords.update(syns)
    # 滑动窗口提取 2-4 字中文子串（避免长查询被当一个 token）
    for i in range(len(query)):
        for n in (2, 3, 4):
            if i + n <= len(query):
                sub = query[i:i+n]
                if re.match(r"[\u4e00-\u9fff]+$", sub):
                    keywords.add(sub)
    return keywords


def search(query, topk=10, db_path=None, conn=None):
    own = conn is None
    conn = conn or get_conn(db_path)
    init_db(conn)
    cur = conn.cursor()

    scored = {}

    tokens = [t for t in re.findall(r"[0-9A-Za-z]+", query) if len(t) >= 2]
    if tokens:
        fts_query = " OR ".join(f'"{t}"' for t in tokens)
        try:
            rows = cur.execute(
                "SELECT doc_id, bm25(documents_fts) AS r FROM documents_fts"
                " WHERE documents_fts MATCH ? ORDER BY r LIMIT ?",
                (fts_query, topk * 3),
            ).fetchall()
            for row in rows:
                scored[row["doc_id"]] = scored.get(row["doc_id"], 0) + 10
        except Exception as e:
            logger.warning("FTS5 查询失败，跳过全文索引路: %s", e)

    for kw in _extract_keywords(query):
        like = f"%{kw}%"
        rows = cur.execute(
            "SELECT doc_id, title, content FROM documents"
            " WHERE title LIKE ? OR content LIKE ? LIMIT 60",
            (like, like),
        ).fetchall()
        for row in rows:
            base = 0
            in_title = kw in row["title"]
            in_content = kw in (row["content"] or "")
            if in_title:
                base += 6
            if in_content:
                base += 1
            if in_title and not (row["content"] or "").strip():
                base += 4
            if base:
                scored[row["doc_id"]] = scored.get(row["doc_id"], 0) + base

    results = []
    for doc_id, score in sorted(scored.items(), key=lambda x: -x[1])[:topk]:
        row = cur.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if row:
            results.append({
                "doc_id": row["doc_id"],
                "title": row["title"],
                "department": row["department"],
                "column_name": row["column_name"],
                "source_url": row["source_url"],
                "publish_time": row["publish_time"],
                "score": score,
            })
    if own:
        conn.close()
    return results