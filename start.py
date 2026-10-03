"""一键启动：检查环境 → 装依赖 → 建库 → 启 API。

用法：
  python start.py              # 默认 127.0.0.1:8000
  python start.py --port 9000  # 指定端口
"""

import argparse
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, check=True):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=HERE)
    if check and r.returncode != 0:
        sys.exit(f"命令失败: {' '.join(cmd)}")
    return r

def main():
    parser = argparse.ArgumentParser(description="珠科百事通一键启动")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print("[1/4] 检查 Python 环境...")
    print(f"  Python {sys.version.split()[0]}")

    print("[2/4] 安装依赖...")
    run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"])

    print("[3/4] 初始化数据库...")
    db_path = os.path.join(HERE, "data", "zcst.db")
    if os.path.exists(db_path):
        print(f"  数据库已存在: {db_path}")
    else:
        print("  首次构建，从 JSONL 入库...")
        run([sys.executable, "-m", "retrieval.index"])

    print("[4/4] 启动 API 服务...")
    print(f"  地址: http://{args.host}:{args.port}")
    print(f"  健康检查: http://{args.host}:{args.port}/health")
    print(f"  问答接口: POST http://{args.host}:{args.port}/ask")
    print("  按 Ctrl+C 停止\n")
    run([sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", args.host, "--port", str(args.port)])

if __name__ == "__main__":
    main()
