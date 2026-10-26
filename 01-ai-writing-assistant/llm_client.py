"""大模型调用封装（OpenAI 兼容接口）。

只做一件事：把对话消息流式地变成文本增量，并把底层异常翻译成
用户看得懂的提示。业务代码不需要 import openai。
"""

from __future__ import annotations

from typing import Iterator, Sequence

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    OpenAI,
)

from config import Settings


class LLMError(RuntimeError):
    """可直接展示给用户的调用错误。"""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    @property
    def friendly(self) -> str:
        return f"{self.message} {self.hint}".strip()


def _status_detail(exc: APIStatusError) -> str:
    """尽量从异常里挖出服务端返回的错误描述（截断，避免刷屏）。"""
    try:
        body = exc.response.json()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])[:200]
            if body.get("message"):
                return str(body["message"])[:200]
    except Exception:  # noqa: BLE001 - 解析失败时退回原始文本
        pass
    return str(exc)[:200]


def translate_error(exc: Exception) -> LLMError:
    """把 openai SDK / 网络异常翻译成中文可读提示。"""
    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, AuthenticationError):
        return LLMError(
            "API Key 无效或已过期（HTTP 401）。",
            "请检查 .env 中的 LLM_API_KEY 是否填写正确、是否与 LLM_BASE_URL 匹配。",
        )
    if isinstance(exc, PermissionDeniedError):
        return LLMError(
            "当前 API Key 没有调用该模型的权限（HTTP 403）。",
            "请确认账号已开通对应模型，或在 .env 中更换 LLM_MODEL。",
        )
    if isinstance(exc, NotFoundError):
        return LLMError(
            "接口地址或模型不存在（HTTP 404）。",
            "请检查 LLM_BASE_URL 是否以 /v1 结尾、LLM_MODEL 名称是否正确。",
        )
    if isinstance(exc, RateLimitError):
        return LLMError(
            "请求过于频繁或额度不足（HTTP 429）。",
            "请稍后重试，或检查账号余额与限流设置。",
        )
    if isinstance(exc, APITimeoutError):
        return LLMError(
            "请求超时，模型响应过慢。",
            "可稍后重试，或在 .env 中调大 LLM_TIMEOUT、减小 LLM_MAX_TOKENS。",
        )
    if isinstance(exc, APIConnectionError):
        return LLMError(
            "无法连接到模型服务。",
            "请检查网络、代理设置，以及 LLM_BASE_URL 是否可访问。",
        )
    if isinstance(exc, BadRequestError):
        return LLMError(
            f"请求参数不被服务端接受（HTTP 400）：{_status_detail(exc)}",
            "请检查模型名称与参数配置。",
        )
    if isinstance(exc, APIStatusError):
        return LLMError(
            f"模型服务返回错误（HTTP {exc.status_code}）：{_status_detail(exc)}",
            "请稍后重试；若持续出现，请核对服务商状态与配置。",
        )
    if isinstance(exc, APIError):
        return LLMError(f"调用模型失败：{str(exc)[:200]}", "请稍后重试。")
    return LLMError(f"生成失败：{type(exc).__name__}: {str(exc)[:200]}", "请稍后重试。")


class LLMClient:
    """流式对话客户端（OpenAI 兼容协议）。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
            max_retries=1,
        )

    def stream_chat(self, messages: Sequence[dict[str, str]]) -> Iterator[str]:
        """逐段产出模型输出（增量文本，不是累积文本）。"""
        try:
            stream = self._client.chat.completions.create(
                model=self._settings.model,
                messages=list(messages),
                temperature=self._settings.temperature,
                max_tokens=self._settings.max_tokens,
                stream=True,
            )
            for chunk in stream:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                piece = getattr(delta, "content", None) if delta else None
                if piece:
                    yield piece
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - 统一翻译为可读错误
            raise translate_error(exc) from exc

    def chat(self, messages: Sequence[dict[str, str]]) -> str:
        """非流式调用：把增量拼成完整文本。"""
        return "".join(self.stream_chat(messages))
