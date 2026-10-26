# -*- coding: utf-8 -*-
"""大模型客户端：OpenAI 兼容接口 + 重试 + 中文错误翻译。

只对外暴露一个方法 chat_json()，上层不需要知道网络细节。
"""
from __future__ import annotations

import time
from typing import Sequence

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from config import Settings


class LLMError(Exception):
    """调用大模型失败。消息可直接展示给用户。"""


_ERROR_HINTS = {
    400: "请求被拒绝：可能是模型不支持 JSON 模式，或输入过长（试试把 .env 里的 JSON_MODE 改成 0）",
    401: "API Key 无效或已过期，请检查 .env 里的 LLM_API_KEY 与 LLM_BASE_URL 是否匹配",
    403: "没有访问该模型的权限，请确认账号已开通对应模型",
    404: "接口地址或模型名不存在，请检查 LLM_BASE_URL 是否以 /v1 结尾、LLM_MODEL 是否拼写正确",
    429: "请求过于频繁或额度不足，稍后重试或检查账号余额",
    500: "模型服务内部错误，请稍后重试",
    503: "模型服务繁忙，请稍后重试",
}


class LLMClient:
    """封装 OpenAI 兼容接口。测试时可传入假的 client 对象替换掉网络调用。"""

    def __init__(self, settings: Settings, client: object | None = None):
        self.settings = settings
        self._client = client or OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
        )

    # ---------- 对外 ----------
    def chat_json(self, messages: Sequence[dict]) -> str:
        """调用模型并把返回内容取成字符串；失败自动重试。"""
        attempts = self.settings.retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._request(messages)
            except LLMError:
                raise
            except Exception as exc:  # noqa: BLE001 - 统一翻译成中文提示
                last_error = exc
                if isinstance(exc, APITimeoutError):
                    raise LLMError("请求超时：可以调大 .env 里的 LLM_TIMEOUT，或减少一次生成的用例数量") from exc
                if isinstance(exc, APIConnectionError):
                    raise LLMError("无法连接到模型服务：检查网络、代理与 LLM_BASE_URL 是否可达") from exc
                if isinstance(exc, APIStatusError):
                    status = getattr(exc, "status_code", 0) or 0
                    if status in (429, 500, 502, 503, 504) and attempt < attempts:
                        time.sleep(min(2 ** attempt, 8))
                        continue
                    hint = _ERROR_HINTS.get(status, f"接口返回错误状态码 {status}")
                    raise LLMError(hint) from exc
                raise LLMError(f"调用模型失败：{exc}") from exc
        raise LLMError(f"重试 {attempts} 次后仍失败：{last_error}")

    # ---------- 内部 ----------
    def _request(self, messages: Sequence[dict]) -> str:
        kwargs = {
            "model": self.settings.model,
            "messages": list(messages),
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }
        if self.settings.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMError("模型没有返回任何内容")
        message = choices[0].message
        content = getattr(message, "content", "") or ""
        if not content.strip():
            raise LLMError("模型返回了空内容，请重试")
        return content
