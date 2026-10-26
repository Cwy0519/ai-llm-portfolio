"""config.py 的单元测试。

约定：所有用例都通过 `isolated_config` fixture 运行——`.env` 被指向不存在的
临时文件、相关环境变量被清空，配置完全由显式传入的 env 映射驱动。因此测试
不依赖真实 `.env` 内容，也不会读取或使用真实 API Key。

新契约：应用只走真实 API，Key 必填；演示模式（MOCK_MODE / use_mock /
mode_label）已移除。
"""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError

import pytest

import config
from config import DEFAULT_BASE_URL, DEFAULT_MODEL, Settings

# ---------------------------------------------------------------------------
# load_settings：默认值与显式覆盖
# ---------------------------------------------------------------------------


def test_load_settings_defaults(isolated_config):
    settings = isolated_config.load_settings(env={})

    assert settings.api_key == ""
    assert settings.base_url == DEFAULT_BASE_URL
    assert settings.model == DEFAULT_MODEL
    assert settings.temperature == 0.8
    assert settings.max_tokens == 2048
    assert settings.timeout == 60.0
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 7860
    assert settings.app_inbrowser is True
    assert settings.issues == ()
    assert settings.has_api_key is False
    assert settings.is_ready is False


def test_explicit_env_overrides_all_fields(isolated_config):
    settings = isolated_config.load_settings(
        env={
            "LLM_API_KEY": "  sk-unit-test-key-123456  ",
            "LLM_BASE_URL": "  https://example.com/v1  ",
            "LLM_MODEL": "  test-model  ",
            "LLM_TEMPERATURE": "1.25",
            "LLM_MAX_TOKENS": "512",
            "LLM_TIMEOUT": "12.5",
            "APP_HOST": "0.0.0.0",
            "APP_PORT": "8080",
            "APP_INBROWSER": "0",
        }
    )

    assert settings.api_key == "sk-unit-test-key-123456"
    assert settings.base_url == "https://example.com/v1"
    assert settings.model == "test-model"
    assert settings.temperature == 1.25
    assert settings.max_tokens == 512
    assert settings.timeout == 12.5
    assert settings.app_host == "0.0.0.0"
    assert settings.app_port == 8080
    assert settings.app_inbrowser is False
    assert settings.has_api_key is True
    assert settings.validate() == []
    assert settings.is_ready is True


def test_env_argument_overrides_process_environment(isolated_config, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "from-process")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.1")

    with_process_env = isolated_config.load_settings(env={})
    assert with_process_env.model == "from-process"
    assert with_process_env.temperature == 0.1

    overridden = isolated_config.load_settings(
        env={"LLM_MODEL": "from-argument", "LLM_TEMPERATURE": "0.9"}
    )
    assert overridden.model == "from-argument"
    assert overridden.temperature == 0.9


def test_non_string_env_values_are_coerced(isolated_config):
    settings = isolated_config.load_settings(env={"LLM_MAX_TOKENS": 1024, "APP_INBROWSER": 0})

    assert settings.max_tokens == 1024
    assert settings.app_inbrowser is False


# ---------------------------------------------------------------------------
# API Key：只读 LLM_API_KEY，缺失时 validate() 必须报错
# ---------------------------------------------------------------------------


def test_api_key_reads_only_llm_api_key(isolated_config):
    """新版只认 LLM_API_KEY，不再回退 DEEPSEEK_API_KEY / OPENAI_API_KEY。"""
    deepseek_only = isolated_config.load_settings(env={"DEEPSEEK_API_KEY": "deepseek-key"})
    assert deepseek_only.api_key == ""
    assert deepseek_only.has_api_key is False

    openai_only = isolated_config.load_settings(env={"OPENAI_API_KEY": "openai-key"})
    assert openai_only.api_key == ""
    assert openai_only.has_api_key is False

    explicit = isolated_config.load_settings(
        env={"LLM_API_KEY": "llm-key", "DEEPSEEK_API_KEY": "deepseek-key"}
    )
    assert explicit.api_key == "llm-key"


def test_missing_key_reports_problem(isolated_config):
    settings = isolated_config.load_settings(env={})

    problems = settings.validate()
    assert any("未配置 API Key" in problem for problem in problems)
    assert any("LLM_API_KEY" in problem for problem in problems)
    assert settings.is_ready is False


def test_blank_key_counts_as_missing(isolated_config):
    settings = isolated_config.load_settings(env={"LLM_API_KEY": "   "})

    assert settings.has_api_key is False
    assert any("未配置 API Key" in problem for problem in settings.validate())


def test_with_key_is_ready():
    settings = Settings(api_key="sk-test")

    assert settings.has_api_key is True
    assert settings.validate() == []
    assert settings.is_ready is True


# ---------------------------------------------------------------------------
# 已移除的演示模式：契约层面确认不存在（防止回归时残留）
# ---------------------------------------------------------------------------


def test_mock_mode_contract_removed():
    field_names = {item.name for item in dataclasses.fields(Settings)}

    assert "mock_mode" not in field_names
    assert not hasattr(Settings, "use_mock")
    assert not hasattr(Settings, "mode_label")
    assert not hasattr(config, "MODE_LABEL")


# ---------------------------------------------------------------------------
# 非法数字 / 非法布尔值：回退默认值并记录 issues
# ---------------------------------------------------------------------------


def test_invalid_numbers_fall_back_and_are_recorded(isolated_config):
    settings = isolated_config.load_settings(
        env={
            "LLM_TEMPERATURE": "not-a-number",
            "LLM_MAX_TOKENS": "abc",
            "LLM_TIMEOUT": "??",
            "APP_PORT": "80x0",
        }
    )

    assert settings.temperature == 0.8
    assert settings.max_tokens == 2048
    assert settings.timeout == 60.0
    assert settings.app_port == 7860
    assert len(settings.issues) == 4
    joined = "\n".join(settings.issues)
    for key in ("LLM_TEMPERATURE", "LLM_MAX_TOKENS", "LLM_TIMEOUT", "APP_PORT"):
        assert key in joined
    assert "回退为默认值" in joined
    # issues 会被透传到 validate()，界面能提示用户
    validate_text = "\n".join(settings.validate())
    for issue in settings.issues:
        assert issue in validate_text
    assert "未配置 API Key" in validate_text


def test_invalid_bool_falls_back_and_is_recorded(isolated_config):
    settings = isolated_config.load_settings(env={"APP_INBROWSER": "maybe"})

    assert settings.app_inbrowser is True
    assert len(settings.issues) == 1
    assert "APP_INBROWSER" in settings.issues[0]
    assert "回退为默认值" in settings.issues[0]


def test_bool_true_false_spellings(isolated_config):
    for raw in ("1", "true", "TRUE", "yes", "y", "on"):
        assert isolated_config.load_settings(env={"APP_INBROWSER": raw}).app_inbrowser is True
    for raw in ("0", "false", "No", "n", "off"):
        assert isolated_config.load_settings(env={"APP_INBROWSER": raw}).app_inbrowser is False


# ---------------------------------------------------------------------------
# validate()：范围与格式校验
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("temperature", [-0.1, 2.1, 100])
def test_validate_temperature_out_of_range(temperature):
    problems = Settings(api_key="sk-test", temperature=temperature).validate()

    assert any("LLM_TEMPERATURE" in problem for problem in problems)


@pytest.mark.parametrize("temperature", [0.0, 0.8, 2.0])
def test_validate_temperature_boundaries_ok(temperature):
    assert Settings(api_key="sk-test", temperature=temperature).validate() == []


@pytest.mark.parametrize("base_url", ["ftp://example.com/v1", "example.com/v1", "", "https://"])
def test_validate_base_url_invalid(base_url):
    problems = Settings(api_key="sk-test", base_url=base_url).validate()

    assert any("LLM_BASE_URL" in problem for problem in problems)


@pytest.mark.parametrize("base_url", ["https://api.deepseek.com/v1", "http://127.0.0.1:11434/v1"])
def test_validate_base_url_valid(base_url):
    assert Settings(api_key="sk-test", base_url=base_url).validate() == []


@pytest.mark.parametrize("port", [-1, 0, 65536, 70000])
def test_validate_app_port_out_of_range(port):
    problems = Settings(api_key="sk-test", app_port=port).validate()

    assert any("APP_PORT" in problem for problem in problems)


@pytest.mark.parametrize("port", [1, 7860, 65535])
def test_validate_app_port_boundaries_ok(port):
    assert Settings(api_key="sk-test", app_port=port).validate() == []


@pytest.mark.parametrize("max_tokens", [0, -5])
def test_validate_max_tokens_must_be_positive(max_tokens):
    problems = Settings(api_key="sk-test", max_tokens=max_tokens).validate()

    assert any("LLM_MAX_TOKENS" in problem for problem in problems)


@pytest.mark.parametrize("timeout", [0, -1.5])
def test_validate_timeout_must_be_positive(timeout):
    problems = Settings(api_key="sk-test", timeout=timeout).validate()

    assert any("LLM_TIMEOUT" in problem for problem in problems)


def test_validate_empty_model_is_reported():
    problems = Settings(api_key="sk-test", model="   ").validate()

    assert any("LLM_MODEL" in problem for problem in problems)


def test_validate_propagates_issues():
    settings = Settings(api_key="sk-test", issues=("自定义加载问题",))

    assert "自定义加载问题" in settings.validate()
    assert settings.is_ready is False


# ---------------------------------------------------------------------------
# 展示相关：masked_key / has_api_key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("api_key", ["", "   "])
def test_masked_key_when_not_configured(api_key):
    assert Settings(api_key=api_key).masked_key() == "未配置"


@pytest.mark.parametrize("api_key", ["short", "12345678"])
def test_masked_key_short_keys_fully_masked(api_key):
    assert Settings(api_key=api_key).masked_key() == "****"


def test_masked_key_twelve_chars_fully_masked():
    assert Settings(api_key="123456789012").masked_key() == "****"


def test_masked_key_long_key_keeps_prefix_and_suffix():
    masked = Settings(api_key="  sk-test-dummy-0000  ").masked_key()

    assert masked == "sk-1****cdef"
    assert "234567890ab" not in masked


def test_masked_key_thirteen_chars_keeps_prefix_and_suffix():
    assert Settings(api_key="1234567890123").masked_key() == "1234****0123"


def test_has_api_key_strips_whitespace():
    assert Settings(api_key="  sk-test  ").has_api_key is True
    assert Settings(api_key="\n\t ").has_api_key is False


# ---------------------------------------------------------------------------
# 不可变性与单例缓存
# ---------------------------------------------------------------------------


def test_settings_is_frozen():
    settings = Settings(api_key="sk-test")

    with pytest.raises(FrozenInstanceError):
        settings.temperature = 1.0  # type: ignore[misc]


def test_get_settings_is_cached_and_reset(monkeypatch):
    calls: list[int] = []

    def fake_load_settings() -> Settings:
        calls.append(len(calls) + 1)
        return Settings(api_key=f"sk-{len(calls)}")

    config.get_settings.cache_clear()
    monkeypatch.setattr(config, "load_settings", fake_load_settings)

    first = config.get_settings()
    second = config.get_settings()
    assert first is second
    assert len(calls) == 1

    third = config.reset_settings()
    assert third is not first
    assert third.api_key == "sk-2"
    assert len(calls) == 2
