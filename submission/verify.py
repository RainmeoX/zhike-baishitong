"""验证打包结果：检查无敏感文件、数据库已包含、评测结果已包含。"""
import zipfile
import sys

zip_path = sys.argv[1] if len(sys.argv) > 1 else r"submission\output\专业组+珠科百事通+RAGGO!!!!!+v1.0+13800138000.zip"

z = zipfile.ZipFile(zip_path)
names = z.namelist()

print(f"总文件数: {len(names)}")

# 检查敏感文件
bad = []
for n in names:
    if n.endswith(".env") or (".env" in n and ".env.example" not in n):
        bad.append(n)
    if "opencode.json" in n:
        bad.append(n)
    if "__pycache__" in n:
        bad.append(n)
    if ".pyc" in n:
        bad.append(n)

print(f"敏感文件: {bad if bad else '无 ✓'}")

# 检查关键内容
db = [n for n in names if n.endswith(".db")]
print(f"数据库: {db}")

jsonl = [n for n in names if n.endswith(".jsonl")]
print(f"JSONL 文件: {len(jsonl)} 个")

eval_r = [n for n in names if "results" in n and n.endswith((".json", ".csv"))]
print(f"评测结果: {eval_r}")

env_example = [n for n in names if ".env.example" in n]
print(f".env.example: {env_example}")

readme = [n for n in names if "readme" in n.lower() and n.endswith(".md")]
print(f"readme 文档: {readme}")

# 检查 .env 是否泄漏
env_leak = [n for n in names if n.rstrip("/").endswith(".env")]
if env_leak:
    print(f"\n⚠️ 警告：.env 文件被打包了！{env_leak}")
else:
    print(f"\n✅ .env 未打包，密钥安全")
