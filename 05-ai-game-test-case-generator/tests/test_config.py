# -*- coding: utf-8 -*-
"""配置层测试：默认值、环境变量覆盖、非法值校验、Key 脱敏。"""
from __future__ import annotations

from pathlib import Path

import pytest

from config import DEFAULTS, ConfigError, load_settings

NO_ENV_FILE = Path("__不存在的_env_文件__")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """每个用例都从干净的环境变量开始，避免受本机 .env 影响。"""
    for key in list(DEFAULTS) + ["LLM_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    yield


def test_defaults_when_nothing_configured():
    s = load_settings(env_file=NO_ENV_FILE)
    assert s.model == "deepseek-chat"
    assert s.base_url == "https://api.deepseek.com/v1"
    assert s.temperature == pytest.approx(0.3)
    assert s.max_cases == 30
    assert s.app_port == 7862
    assert s.json_mode is True
    assert s.api_key == ""


def test_env_overrides_model_and_base_url(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "glm-4-flash")
    monkeypatch.setenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
    s = load_settings(env_file=NO_ENV_FILE)
    assert s.model == "glm-4-flash"
    assert s.base_url.endswith("/v4")  # 结尾斜杠被去掉


@pytest.mark.parametrize("bad", ["3.5", "-1", "abc"])
def test_temperature_out_of_range(monkeypatch, bad):
    monkeypatch.setenv("LLM_TEMPERATURE", bad)
    with pytest.raises(ConfigError) as exc:
        load_settings(env_file=NO_ENV_FILE)
    assert "LLM_TEMPERATURE" in str(exc.value)


def test_max_cases_must_be_positive(monkeypatch):
    monkeypatch.setenv("MAX_CASES", "0")
    with pytest.raises(ConfigError):
        load_settings(env_file=NO_ENV_FILE)


def test_invalid_port_rejected(monkeypatch):
    monkeypatch.setenv("APP_PORT", "70000")
    with pytest.raises(ConfigError) as exc:
        load_settings(env_file=NO_ENV_FILE)
    assert "APP_PORT" in str(exc.value)


@pytest.mark.parametrize("raw,expected", [("1", True), ("true", True), ("0", False), ("off", False)])
def test_json_mode_flag(monkeypatch, raw, expected):
    monkeypatch.setenv("JSON_MODE", raw)
    assert load_settings(env_file=NO_ENV_FILE).json_mode is expected


def test_masked_key_hides_middle(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-abcdefghijklmnop")
    masked = load_settings(env_file=NO_ENV_FILE).masked_key()
    assert masked.startswith("sk-abc")
    assert masked.endswith("mnop")
    assert "*" in masked
    assert "defghijkl" not in masked


def test_masked_key_empty():
    assert load_settings(env_file=NO_ENV_FILE).masked_key() == "（未配置）"


def test_check_ready_rejects_missing_key():
    s = load_settings(env_file=NO_ENV_FILE)
    with pytest.raises(ConfigError) as exc:
        s.check_ready()
    assert "API Key" in str(exc.value)


def test_check_ready_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-你的密钥")
    s = load_settings(env_file=NO_ENV_FILE)
    with pytest.raises(ConfigError):
        s.check_ready()


def test_check_ready_accepts_real_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-1234567890abcdef1234")
    load_settings(env_file=NO_ENV_FILE).check_ready()  # 不抛异常即通过


def test_summary_contains_model_and_masked_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-1234567890abcdef")
    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    summary = load_settings(env_file=NO_ENV_FILE).summary()
    assert "deepseek-chat" in summary
    assert "sk-1234567890abcdef" not in summary
