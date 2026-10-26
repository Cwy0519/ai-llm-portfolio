"""和大模型说话的唯一出口。

这一层只做三件事：
    1. 发请求（流式，边生成边返回）；
    2. 网络抖动时自动重试；
    3. 把各种异常翻译成"人话"，交给界面去提示。

把所有网络细节关在这个文件里，好处是：换平台只改这里，换界面不用改这里。
"""

from typing import Iterator

import openai
from openai import OpenAI

from config import Settings


class LLMError(Exception):
    """我们自己定义的错误类型，界面只认识它，不需要认识 openai 的一堆异常。"""


def stream_chat(settings: Settings, messages: list[dict],
                temperature: float | None = None) -> Iterator[str]:
    """流式调用大模型，每收到一小块文字就 yield 出来。

    流式（stream=True）的作用：用户不用等整段生成完，字是一个一个"流"出来的，
    体验好很多，也顺便解决了"长文本等待焦虑"。
    """
    # max_retries=0：关掉 SDK 自带的自动重试，重试逻辑我们自己控制，方便加提示
    client = OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.timeout,
        max_retries=0,
    )
    temp = settings.temperature if temperature is None else temperature

    attempt = 0
    produced = False          # 是否已经吐出过内容

    while True:
        try:
            stream = client.chat.completions.create(
                model=settings.model,
                messages=messages,
                temperature=temp,
                stream=True,
            )
            for chunk in stream:
                # 有些平台会发"空包"（choices 为空），直接跳过
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    produced = True
                    yield delta
            return            # 正常结束

        except Exception as e:  # noqa: BLE001 —— 这里就是要兜住所有异常再翻译成提示
            # 只有"还没输出任何内容"时才重试；
            # 否则重试会让界面上出现重复的半截文字，比报错更难看。
            can_retry = (
                isinstance(e, (openai.APIConnectionError, openai.APITimeoutError,
                               openai.RateLimitError))
                and not produced
                and attempt < settings.max_retries
            )
            if can_retry:
                attempt += 1
                continue
            raise LLMError(_friendly(e, settings.timeout)) from e


def _friendly(e: Exception, timeout: int) -> str:
    """把异常翻译成用户能看懂、能自己解决的一句话。"""
    if isinstance(e, openai.AuthenticationError):
        return "API Key 无效或已过期（401）。请检查 .env 里的 LLM_API_KEY 是否填对。"
    if isinstance(e, openai.PermissionDeniedError):
        return "当前 Key 没有权限调用这个模型（403）。请确认账号已开通该模型。"
    if isinstance(e, openai.NotFoundError):
        return "接口地址或模型名不存在（404）。请检查 LLM_BASE_URL 和 LLM_MODEL。"
    if isinstance(e, openai.RateLimitError):
        return "请求太频繁或余额不足（429）。等几秒再试，或检查账户余额。"
    if isinstance(e, openai.APITimeoutError):
        return f"请求超时（{timeout} 秒）。可以把 .env 里的 LLM_TIMEOUT 调大，或把单段字数调小。"
    if isinstance(e, openai.APIConnectionError):
        return "连不上服务器。请检查网络，以及 LLM_BASE_URL 是否写错。"
    if isinstance(e, openai.BadRequestError):
        return "请求被模型拒绝了（400）。常见原因是文本太长，或该模型不支持当前参数。"
    return f"调用失败（{type(e).__name__}）：{e}"
