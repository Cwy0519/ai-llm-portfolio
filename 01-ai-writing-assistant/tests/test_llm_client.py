"""llm_client.py 的单元测试。

不发起真实请求：所有 stream_chat 用例都把 `LLMClient._client` 替换成假的
OpenAI 兼容客户端；只保留 openai 异常类型用于验证错误翻译。
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AuthenticationError, NotFoundError, RateLimitError

from config import Settings
from llm_client import LLMClient, LLMError, translate_error


def _settings() -> Settings:
    return Settings(
        api_key="sk-unit-test",
        base_url="https://api.example.invalid/v1",
        model="test-model",
        temperature=0.7,
        max_tokens=123,
    )


def _delta_chunk(content: str | None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def _empty_choices_chunk():
    return SimpleNamespace(choices=[])


def _no_delta_chunk():
    return SimpleNamespace(choices=[SimpleNamespace()])


class FakeCompletions:
    def __init__(self, chunks=(), error: Exception | None = None) -> None:
        self.chunks = list(chunks)
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return iter(self.chunks)


class FakeClient:
    def __init__(self, chunks=(), error: Exception | None = None) -> None:
        self.completions = FakeCompletions(chunks=chunks, error=error)
        self.chat = SimpleNamespace(completions=self.completions)


def _client_with(fake: FakeClient) -> LLMClient:
    """构造真实 LLMClient（只做本地对象初始化，不联网），再换掉底层客户端。"""
    client = LLMClient(_settings())
    client._client = fake
    return client


# ---------------------------------------------------------------------------
# 初始化与 stream_chat 正常路径
# ---------------------------------------------------------------------------


def test_client_initializes_without_network():
    client = LLMClient(_settings())

    assert client._settings.model == "test-model"
    assert hasattr(client._client, "chat")


def test_stream_chat_yields_delta_content_and_skips_empty_choices():
    fake = FakeClient(
        chunks=[
            _delta_chunk("你"),
            _empty_choices_chunk(),
            _delta_chunk("好"),
            _delta_chunk(None),
            _no_delta_chunk(),
            _delta_chunk("！"),
        ]
    )
    client = _client_with(fake)
    messages = [{"role": "user", "content": "hi"}]

    assert list(client.stream_chat(messages)) == ["你", "好", "！"]
    assert client.chat(messages) == "你好！"


def test_stream_chat_passes_expected_parameters():
    fake = FakeClient(chunks=[_delta_chunk("ok")])
    client = _client_with(fake)
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ]

    list(client.stream_chat(messages))

    assert len(fake.completions.calls) == 1
    call = fake.completions.calls[0]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0.7
    assert call["max_tokens"] == 123
    assert call["stream"] is True
    assert call["messages"] == messages
    assert call["messages"] is not messages  # 传入的是副本，不暴露内部可变对象


def test_stream_chat_empty_stream_yields_nothing():
    client = _client_with(FakeClient(chunks=()))

    assert list(client.stream_chat([{"role": "user", "content": "x"}])) == []
    assert client.chat([{"role": "user", "content": "x"}]) == ""


# ---------------------------------------------------------------------------
# stream_chat 异常路径：统一翻译成 LLMError
# ---------------------------------------------------------------------------


def test_stream_chat_translates_create_exception():
    client = _client_with(FakeClient(error=RuntimeError("socket exploded")))

    with pytest.raises(LLMError) as excinfo:
        list(client.stream_chat([{"role": "user", "content": "x"}]))

    error = excinfo.value
    assert "生成失败" in error.message
    assert "RuntimeError" in error.message
    assert "socket exploded" in error.message
    assert error.friendly


def test_stream_chat_translates_mid_stream_exception():
    class BrokenIterator:
        def __init__(self) -> None:
            self.sent = False

        def __iter__(self):
            return self

        def __next__(self):
            if not self.sent:
                self.sent = True
                return _delta_chunk("先")
            raise ValueError("流中断")

    fake = FakeClient()
    fake.completions = type(
        "BrokenCompletions",
        (FakeCompletions,),
        {
            "create": lambda self, **kwargs: (
                self.calls.append(kwargs) or BrokenIterator()  # type: ignore[func-returns-value]
            )
        },
    )()
    fake.chat = SimpleNamespace(completions=fake.completions)
    client = _client_with(fake)
    stream = client.stream_chat([{"role": "user", "content": "x"}])

    assert next(stream) == "先"
    with pytest.raises(LLMError) as excinfo:
        next(stream)
    assert "ValueError" in excinfo.value.message
    assert "流中断" in excinfo.value.message


def test_stream_chat_llm_error_passes_through():
    original = LLMError("已经翻译过了", "提示")
    client = _client_with(FakeClient(error=original))

    with pytest.raises(LLMError) as excinfo:
        list(client.stream_chat([{"role": "user", "content": "x"}]))

    assert excinfo.value is original


# ---------------------------------------------------------------------------
# translate_error / LLMError.friendly
# ---------------------------------------------------------------------------


def test_llm_error_friendly_combines_message_and_hint():
    assert LLMError("只有消息").friendly == "只有消息"
    assert LLMError("消息", "提示").friendly == "消息 提示"


def test_translate_error_generic_exception():
    error = translate_error(RuntimeError("boom"))

    assert isinstance(error, LLMError)
    assert "生成失败" in error.message
    assert "RuntimeError" in error.message
    assert error.friendly


def test_translate_error_timeout():
    request = httpx.Request("POST", "https://api.example.invalid/v1/chat/completions")

    error = translate_error(APITimeoutError(request=request))

    assert isinstance(error, LLMError)
    assert "超时" in error.message
    assert error.friendly
    assert "LLM_TIMEOUT" in error.friendly


def test_translate_error_connection():
    request = httpx.Request("POST", "https://api.example.invalid/v1")

    error = translate_error(APIConnectionError(request=request))

    assert isinstance(error, LLMError)
    assert "无法连接" in error.message
    assert error.friendly


def test_translate_error_llm_error_passthrough():
    original = LLMError("自定义错误", "自定义提示")

    assert translate_error(original) is original


def _make_status_error(error_cls, status_code: int):
    """构造 openai 的 HTTP 状态异常；不同 openai 版本签名不同时跳过用例。"""
    request = httpx.Request("POST", "https://api.example.invalid/v1")
    response = httpx.Response(
        status_code,
        request=request,
        json={"error": {"message": "upstream detail"}},
    )
    try:
        return error_cls("server said no", response=response, body=None)
    except TypeError:  # pragma: no cover - 取决于 openai 版本
        pytest.skip(f"{error_cls.__name__} 构造签名与本测试不兼容")


@pytest.mark.parametrize(
    ("error_cls", "status_code", "expected"),
    [
        (AuthenticationError, 401, "401"),
        (RateLimitError, 429, "429"),
        (NotFoundError, 404, "404"),
    ],
)
def test_translate_error_http_statuses(error_cls, status_code: int, expected: str):
    error = translate_error(_make_status_error(error_cls, status_code))

    assert isinstance(error, LLMError)
    assert "HTTP" in error.message or expected in error.message
    assert error.friendly
