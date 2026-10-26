"""generator.py 的单元测试。

应用只走真实 API：所有生成用例都用假的 LLMClient（monkeypatch
`generator._client_for`）验证流式转发与异常翻译，不发起任何网络请求。
"""

from __future__ import annotations

import pytest

import generator
from config import Settings
from generator import GenerationError, InputError, generate, prepare, stream_generate
from llm_client import LLMError
from prompts import SCENARIOS


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api_key="sk-unit-test",
        base_url="https://api.example.invalid/v1",
        model="test-model",
    )


def _values(scenario_key: str = "email") -> dict[str, str]:
    scenario = SCENARIOS[scenario_key]
    return {field.key: f"{field.label}的示例内容" for field in scenario.fields}


class FakeClient:
    """模拟 LLMClient：可以产出若干增量，也可以抛异常。"""

    def __init__(self, chunks=("你好", "，世界"), error: Exception | None = None) -> None:
        self.chunks = list(chunks)
        self.error = error
        self.received_messages: list[dict[str, str]] | None = None
        self.calls = 0

    def stream_chat(self, messages):
        self.calls += 1
        self.received_messages = list(messages)
        if self.error is not None:
            raise self.error
        yield from self.chunks


# ---------------------------------------------------------------------------
# prepare()
# ---------------------------------------------------------------------------


def test_prepare_returns_scenario_settings_and_messages(settings):
    values = _values()

    scenario, config, messages = prepare("email", values, tone="幽默", settings=settings)

    assert scenario is SCENARIOS["email"]
    assert config is settings
    assert [message["role"] for message in messages] == ["system", "user"]
    assert all(message["content"].strip() for message in messages)
    for value in values.values():
        assert value in messages[1]["content"]
    assert "【语气要求】幽默" in messages[1]["content"]


def test_prepare_uses_default_tone_when_none(settings):
    scenario, _, messages = prepare("novel", _values("novel"), settings=settings)

    assert f"【语气要求】{scenario.default_tone}" in messages[1]["content"]


def test_prepare_missing_required_field_raises_input_error(settings):
    values = _values()
    values["purpose"] = ""

    with pytest.raises(InputError) as excinfo:
        prepare("email", values, settings=settings)

    assert "邮件目的" in str(excinfo.value)
    assert isinstance(excinfo.value, ValueError)


def test_prepare_unknown_scenario_raises_input_error(settings):
    with pytest.raises(InputError, match="未知写作场景"):
        prepare("不存在的场景", {}, settings=settings)


# ---------------------------------------------------------------------------
# 输入 / 配置错误：调用时立即抛出（eager）
# ---------------------------------------------------------------------------


def test_input_errors_are_raised_eagerly(settings):
    with pytest.raises(InputError, match="未知写作场景"):
        stream_generate("不存在的场景", {}, settings=settings)

    values = _values()
    values["purpose"] = ""
    with pytest.raises(InputError, match="邮件目的"):
        stream_generate("email", values, settings=settings)


def test_no_api_key_raises_generation_error_eagerly():
    settings = Settings(api_key="")

    with pytest.raises(GenerationError) as excinfo:
        stream_generate("email", _values(), settings=settings)

    message = str(excinfo.value)
    assert "配置有误" in message
    assert "未配置 API Key" in message
    assert settings.is_ready is False


def test_other_invalid_settings_raise_generation_error():
    settings = Settings(api_key="sk-unit-test", temperature=5.0)

    with pytest.raises(GenerationError, match="LLM_TEMPERATURE"):
        generate("email", _values(), settings=settings)


# ---------------------------------------------------------------------------
# 真实模式：用假客户端验证编排与异常转换（不触网）
# ---------------------------------------------------------------------------


def test_stream_generate_forwards_client_chunks(monkeypatch, settings):
    fake = FakeClient()
    monkeypatch.setattr(generator, "_client_for", lambda _settings: fake)
    values = _values()

    chunks = list(stream_generate("email", values, tone="正式", settings=settings))

    assert chunks == ["你好", "，世界"]
    assert fake.calls == 1
    assert fake.received_messages is not None
    assert [message["role"] for message in fake.received_messages] == ["system", "user"]
    for value in values.values():
        assert value in fake.received_messages[1]["content"]
    assert "【语气要求】正式" in fake.received_messages[1]["content"]


def test_generate_equals_joined_stream(monkeypatch, settings):
    fake = FakeClient(chunks=("第一段", "第二段"))
    monkeypatch.setattr(generator, "_client_for", lambda _settings: fake)
    values = _values()

    result = generate("email", values, settings=settings)
    streamed = "".join(stream_generate("email", values, settings=settings))

    assert result == streamed == "第一段第二段"


def test_stream_generate_is_lazy_about_client(monkeypatch, settings):
    """输入/配置校验在调用时完成，但真实客户端到迭代时才构造（便于提前提示错误）。"""
    calls: list[int] = []
    fake = FakeClient()

    def factory(_settings):
        calls.append(1)
        return fake

    monkeypatch.setattr(generator, "_client_for", factory)

    stream = stream_generate("email", _values(), settings=settings)
    assert calls == []
    assert next(stream) == "你好"
    assert calls == [1]


def test_empty_client_output_returns_empty_string(monkeypatch, settings):
    monkeypatch.setattr(generator, "_client_for", lambda _settings: FakeClient(chunks=()))

    assert generate("email", _values(), settings=settings) == ""


def test_llm_error_is_translated_to_generation_error(monkeypatch, settings):
    fake = FakeClient(error=LLMError("模型服务超时了", "请稍后重试"))
    monkeypatch.setattr(generator, "_client_for", lambda _settings: fake)

    with pytest.raises(GenerationError) as excinfo:
        list(stream_generate("email", _values(), settings=settings))

    assert str(excinfo.value) == "模型服务超时了 请稍后重试"
    assert isinstance(excinfo.value.__cause__, LLMError)


def test_unexpected_exception_is_wrapped(monkeypatch, settings):
    fake = FakeClient(error=RuntimeError("boom"))
    monkeypatch.setattr(generator, "_client_for", lambda _settings: fake)

    with pytest.raises(GenerationError) as excinfo:
        list(stream_generate("email", _values(), settings=settings))

    message = str(excinfo.value)
    assert "生成失败" in message
    assert "RuntimeError" in message
    assert "boom" in message


# ---------------------------------------------------------------------------
# 已移除的演示模式：契约层面确认不存在
# ---------------------------------------------------------------------------


def test_demo_mode_helpers_are_gone():
    for name in ("_stream_demo_text", "_DEMO_CHUNK_SIZE", "_DEMO_CHUNK_DELAY"):
        assert not hasattr(generator, name), f"generator 不应再有 {name}"

    with pytest.raises(TypeError):
        # 旧参数 length / extra 已移除
        prepare("email", _values(), length="简短", extra="补充")  # type: ignore[call-arg]
