# -*- coding: utf-8 -*-
"""配置管理：全项目唯一读取环境变量的地方。

设计要点
- Settings 是 frozen dataclass，创建后不可变，避免运行中被意外改掉
- 所有配置都有类型转换与范围校验，配置写错会在启动时给出中文提示
- masked_key() 用于日志/界面展示，永远不打印完整 Key
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # 允许未安装 python-dotenv 时只读环境变量
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ENV_FILE = Path(__file__).with_name(".env")

DEFAULTS = {
    "LLM_BASE_URL": "https://api.deepseek.com/v1",
    "LLM_MODEL": "deepseek-chat",
    "LLM_TEMPERATURE": "0.3",
    "LLM_MAX_TOKENS": "3000",
    "LLM_TIMEOUT": "60",
    "MAX_CASES": "30",
    "RETRIES": "2",
    "JSON_MODE": "1",
    "APP_HOST": "127.0.0.1",
    "APP_PORT": "7862",
}


class ConfigError(Exception):
    """配置缺失或非法。消息可直接展示给用户。"""


def load_env(env_file: Path = ENV_FILE) -> None:
    """把 .env 读进进程环境；同名环境变量优先，不覆盖。"""
    if load_dotenv is not None and env_file.exists():
        load_dotenv(env_file, override=False)


def _env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return DEFAULTS.get(name, "")
    return value.strip()


def _to_int(name: str, low: int, high: int) -> int:
    raw = _env(name)
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        raise ConfigError(f"{name} 必须是数字，当前是 {raw!r}")
    if not (low <= value <= high):
        raise ConfigError(f"{name} 必须在 {low}–{high} 之间，当前是 {value}")
    return value


def _to_float(name: str, low: float, high: float) -> float:
    raw = _env(name)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ConfigError(f"{name} 必须是数字，当前是 {raw!r}")
    if not (low <= value <= high):
        raise ConfigError(f"{name} 必须在 {low}–{high} 之间，当前是 {value}")
    return value


def _to_bool(name: str) -> bool:
    return _env(name).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    max_cases: int
    retries: int
    json_mode: bool
    app_host: str
    app_port: int

    # ---------- 展示 ----------
    def masked_key(self) -> str:
        key = (self.api_key or "").strip()
        if not key:
            return "（未配置）"
        if len(key) <= 10:
            return "*" * len(key)
        return f"{key[:6]}{'*' * (len(key) - 10)}{key[-4:]}"

    def summary(self) -> str:
        return (
            f"模型 {self.model} ｜ 接口 {self.base_url} ｜ Key {self.masked_key()} ｜ "
            f"温度 {self.temperature} ｜ 单次上限 {self.max_cases} 条"
        )

    # ---------- 校验 ----------
    def check_ready(self) -> None:
        """调用大模型前的检查，未通过时抛 ConfigError。"""
        if not self.api_key or self.api_key.strip() == "":
            raise ConfigError(
                "还没有配置 API Key。请把 .env.example 复制为 .env，填入 LLM_API_KEY 后重启程序。"
            )
        if "你的" in self.api_key or self.api_key.startswith("sk-xxx"):
            raise ConfigError("LLM_API_KEY 还是占位符，请填入真实 Key。")
        if not self.base_url.startswith("http"):
            raise ConfigError("LLM_BASE_URL 必须以 http:// 或 https:// 开头。")


def load_settings(env_file: Path = ENV_FILE) -> Settings:
    """读取 .env + 环境变量，构造并校验 Settings。"""
    load_env(env_file)
    settings = Settings(
        api_key=_env("LLM_API_KEY"),
        base_url=_env("LLM_BASE_URL").rstrip("/"),
        model=_env("LLM_MODEL"),
        temperature=_to_float("LLM_TEMPERATURE", 0.0, 2.0),
        max_tokens=_to_int("LLM_MAX_TOKENS", 256, 32000),
        timeout=_to_int("LLM_TIMEOUT", 5, 600),
        max_cases=_to_int("MAX_CASES", 1, 100),
        retries=_to_int("RETRIES", 0, 5),
        json_mode=_to_bool("JSON_MODE"),
        app_host=_env("APP_HOST") or "127.0.0.1",
        app_port=_to_int("APP_PORT", 1, 65535),
    )
    return settings
