"""大模型生成接入（智谱 GLM-4-Flash / 华为云 MaaS 均可）。

环境变量（在项目 .env 中配置）：
  LLM_API_KEY=xxx          # 智谱 API Key
  LLM_MODEL=glm-4-flash    # 模型名
  LLM_ENDPOINT=https://open.bigmodel.cn/api/paas/v4/chat/completions

  # 向后兼容：若未设 LLM_* 则回退到 HWMAAS_*
  HWMAAS_API_KEY / HWMAAS_MODEL / HWMAAS_ENDPOINT

未设置 key 时自动降级为抽取式回答。
"""

import os

from api.log import get_logger
from retrieval.maas_env import load
load()

logger = get_logger(__name__)

try:
    import requests
except ImportError:
    requests = None

# 优先读 LLM_*，回退 HWMAAS_*（向后兼容）
_API_KEY = os.getenv("LLM_API_KEY", "") or os.getenv("HWMAAS_API_KEY", "")
_MODEL = os.getenv("LLM_MODEL", "") or os.getenv("HWMAAS_MODEL", "deepseek-v4-flash")
_ENDPOINT = os.getenv("LLM_ENDPOINT", "") or os.getenv("HWMAAS_ENDPOINT", "https://api.modelarts-maas.com/v1/chat/completions")

SYSTEM_PROMPT = (
    "你是「珠科百事通」校务问答助手，服务珠海科技学院 3.1 万在校生。\n"
    "回答规则：\n"
    "1. 用口语化、简洁的方式回答，像学长学姐给同学解答一样自然\n"
    "2. 严格基于【参考内容】回答，不编造、不补充参考内容以外的信息\n"
    "3. 回答末尾标注来源，格式：「（来源：部门-通知标题）」\n"
    "4. 如果参考内容与问题主题不匹配或不足以回答，必须拒答：明确说明「暂未检索到相关通知」，并建议联系相关部门，不要强行作答\n"
    "5. 涉及电话、时间、金额等关键信息，逐字引用原文，不改写"
)


def is_available():
    return bool(_API_KEY) and requests is not None


def generate(question, references, max_tokens=512):
    """调用华为云 MaaS 生成回答。

    Args:
        question: 学生问题
        references: list[dict]，每项含 title/department/content 键
        max_tokens: 最大生成长度

    Returns:
        str: 生成的回答，或 None（调用失败时）
    """
    if not is_available():
        return None

    # 构建多文档编号 context
    parts = []
    for i, ref in enumerate(references, 1):
        dept = ref.get("department", "")
        title = ref.get("title", "")
        content = (ref.get("content", "") or "")[:800]  # 每篇截取 800 字
        parts.append(f"[{i}] 部门：{dept} | 标题：{title}\n{content}")
    context_block = "\n\n".join(parts)

    prompt = f"【参考内容】\n{context_block}\n\n【学生问题】\n{question}\n\n请根据参考内容回答；若参考内容与问题主题不匹配或不足以回答，请直接说明「暂未检索到相关通知」："

    try:
        resp = requests.post(
            _ENDPOINT,
            headers={
                "Authorization": f"Bearer {_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.warning("LLM 返回非 200: status=%s", resp.status_code)
    except Exception as e:
        logger.warning("LLM 调用失败，降级抽取式: %s", e)
    return None
