"""站点与栏目配置。"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

SITES = {
    "jiaowu": {
        "name": "教务处",
        "base_url": "https://jx.zcst.edu.cn",
        "department": "教务处",
        "columns": [
            {"name": "通知公告", "list_path": "/1319/list.htm"},
            {"name": "考试信息", "list_path": "/ksxx/list.htm"},
            {"name": "选课管理", "list_path": "/1385/list.htm"},
            {"name": "学籍管理", "list_path": "/xjgl/list.htm"},
            {"name": "规章制度-校级文件", "list_path": "/1358/list.htm"},
        ],
    },
    "houqin": {
        "name": "后勤处",
        "base_url": "https://hq.zcst.edu.cn",
        "department": "后勤处",
        "columns": [
            {"name": "通知公告", "list_path": "/249/list.htm"},
            {"name": "服务指南", "list_path": "/hqsp/list.htm"},
            {"name": "后勤服务", "list_path": "/251/list.htm"},
            {"name": "规章制度", "list_path": "/252/list.htm"},
        ],
    },
    "zsb": {
        "name": "招生办",
        "base_url": "https://zsb.zcst.edu.cn",
        "department": "招生办",
        "columns": [
            {"name": "招生信息", "list_path": "/4470/list.htm"},
            {"name": "了解珠科视频", "list_path": "/ljzkwspw/list.htm"},
        ],
        "pages": [
            {"name": "奖学金、助学金", "url": "/2021/0617/c4655a161739/page.htm"},
            {"name": "转专业政策", "url": "/2021/0617/c4655a161740/page.htm"},
            {"name": "招生章程", "url": "/2021/0619/c4655a161844/page.htm"},
        ],
    },
}