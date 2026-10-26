"""配置管理模块。

所有密钥与运行参数统一从「环境变量 + 项目根目录下的 .env 文件」读取，
代码中不出现任何硬编码的 API Key。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"

_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "no", "n", "off"}


@dataclass(frozen=True)
class Settings:
    """一次运行生效的全部配置，加载后只读。"""

    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.8
    max_tokens: int = 2048
    timeout: float = 60.0
    app_host: str = "127.0.0.1"
    app_port: int = 7860
    app_inbrowser: bool = True
    # 解析环境变量时产生的问题（如数字格式错误），供界面提示
    issues: tuple[str, ...] = ()

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key.strip())

    def masked_key(self) -> str:
        """脱敏后的 Key，用于界面 / 启动日志展示。"""
        key = self.api_key.strip()
        if not key:
            return "未配置"
        if len(key) <= 12:
            return "****"
        return f"{key[:4]}****{key[-4:]}"

    def validate(self) -> list[str]:
        """返回所有配置问题；空列表表示可以正常生成。"""
        problems = list(self.issues)

        if not self.has_api_key:
            problems.append(
                "未配置 API Key：请复制 .env.example 为 .env，并填写 LLM_API_KEY"
            )
        if not self.model.strip():
            problems.append("LLM_MODEL 未配置，无法确定要调用的模型")

        parsed = urlparse(self.base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            problems.append(f"LLM_BASE_URL 不是合法的 http(s) 地址：{self.base_url!r}")

        if not 0.0 <= self.temperature <= 2.0:
            problems.append(f"LLM_TEMPERATURE 应在 0-2 之间，当前为 {self.temperature}")
        if self.max_tokens <= 0:
            problems.append(f"LLM_MAX_TOKENS 应为正整数，当前为 {self.max_tokens}")
        if self.timeout <= 0:
            problems.append(f"LLM_TIMEOUT 应为正数（秒），当前为 {self.timeout}")
        if not 0 < self.app_port < 65536:
            problems.append(f"APP_PORT 应为 1-65535 之间的整数，当前为 {self.app_port}")

        return problems

    @property
    def is_ready(self) -> bool:
        return not self.validate()


def _read_float(env: Mapping[str, str], key: str, default: float, issues: list[str]) -> float:
    raw = (env.get(key) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        issues.append(f"{key}={raw!r} 不是合法数字，已回退为默认值 {default}")
        return default


def _read_int(env: Mapping[str, str], key: str, default: int, issues: list[str]) -> int:
    raw = (env.get(key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        issues.append(f"{key}={raw!r} 不是合法整数，已回退为默认值 {default}")
        return default


def _read_bool(env: Mapping[str, str], key: str, default: bool, issues: list[str]) -> bool:
    raw = (env.get(key) or "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    issues.append(f"{key}={raw!r} 无法识别（应为 0/1/true/false），已回退为默认值 {default}")
    return default


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """读取 .env 与进程环境变量，构造 Settings。

    显式传入 env 时，其键值会覆盖 .env / 进程环境（便于测试）。
    """
    load_dotenv(dotenv_path=ENV_FILE, override=False)

    merged: dict[str, str] = {k: str(v) for k, v in os.environ.items()}
    if env:
        merged.update({k: str(v) for k, v in env.items()})

    issues: list[str] = []
    settings = Settings(
        api_key=(merged.get("LLM_API_KEY") or "").strip(),
        base_url=(merged.get("LLM_BASE_URL") or DEFAULT_BASE_URL).strip(),
        model=(merged.get("LLM_MODEL") or DEFAULT_MODEL).strip(),
        temperature=_read_float(merged, "LLM_TEMPERATURE", 0.8, issues),
        max_tokens=_read_int(merged, "LLM_MAX_TOKENS", 2048, issues),
        timeout=_read_float(merged, "LLM_TIMEOUT", 60.0, issues),
        app_host=(merged.get("APP_HOST") or "127.0.0.1").strip(),
        app_port=_read_int(merged, "APP_PORT", 7860, issues),
        app_inbrowser=_read_bool(merged, "APP_INBROWSER", True, issues),
        issues=tuple(issues),
    )
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """进程内缓存的配置单例。"""
    return load_settings()


def reset_settings() -> Settings:
    """清除缓存并重新加载 .env。"""
    get_settings.cache_clear()
    return get_settings()
