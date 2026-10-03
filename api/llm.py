"""华为云 MaaS 大模型生成接入（预留）。

当拿到华为云 MaaS API key 后，设置环境变量即可启用：
  export HWMAAS_API_KEY="your-key"
  export HWMAAS_MODEL="DeepSeek-V4-Flash"  # 或其他模型

未设置 key 时自动降级为抽取式回答（当前模式）。
"""

import os

try:
    import requests
except ImportError:
    requests = None

_API_KEY = os.getenv("HWMAAS_API_KEY", "")
_MODEL = os.getenv("HWMAAS_MODEL", os.getenv("HWMAAS_MODEL", "DeepSeek-V4-Flash"))
_ENDPOINT = os.getenv("HWMAAS_ENDPOINT", "https://maas.cn-north-4.myhuaweicloud.com/v1/inferences")

SYSTEM_PROMPT = (
    "你是「珠科百事通」校务问答助手。根据检索到的官方通知内容回答学生问题。"
    "要求：1) 答案简洁准确；2) 必须基于提供的参考内容，不编造；"
    "3) 如果参考内容不足以回答，说明并建议联系相关部门。"
)


def is_available():
    return bool(_API_KEY) and requests is not None


def generate(question, context, max_tokens=512):
    """调用华为云 MaaS 生成回答。

    Args:
        question: 学生问题
        context: 检索到的参考内容（拼接的标题+摘要）
        max_tokens: 最大生成长度

    Returns:
        str: 生成的回答，或 None（调用失败时）
    """
    if not is_available():
        return None

    prompt = f"参考内容：\n{context}\n\n学生问题：{question}\n\n请根据参考内容回答："

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
    except Exception:
        pass
    return None
