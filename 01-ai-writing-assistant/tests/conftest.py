"""pytest 共享配置。

目标：
1. 让 `pytest tests` 在任意工作目录下都能 import 到项目根目录的核心模块；
2. 为 config 相关测试提供隔离环境：把 `.env` 指向不存在的临时路径并清空相关
   环境变量，避免测试结果受真实 `.env` / 机器环境变量影响，也避免误用真实 Key；
3. 每个用例结束后清理模块级缓存（get_settings 的 lru_cache、生成客户端的缓存），
   防止用例之间互相污染；
4. 临时目录策略：本机 Python 进程无法写入系统 TEMP（PermissionError），
   `tempfile.gettempdir()` 会回退到当前工作目录，导致 `pytest-of-<user>` 出现在
   项目根目录。因此默认把 pytest 的 basetemp 指到 `tests/.pytest-tmp`，并在会话
   结束时删除，保证工作区干净（见文末 hook）。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORKSPACE_TMP = PROJECT_ROOT / "tests" / ".pytest-tmp"

# 与配置相关的全部环境变量（显式 env 覆盖时需要先清空进程环境里的同名变量）
CONFIG_ENV_KEYS: tuple[str, ...] = (
    "LLM_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "LLM_TIMEOUT",
    "APP_HOST",
    "APP_PORT",
    "APP_INBROWSER",
)


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """返回 config 模块，但保证其读取环境时不接触真实 .env 与机器环境变量。"""
    import config as config_module

    monkeypatch.setattr(config_module, "ENV_FILE", tmp_path / "does-not-exist.env")
    for key in CONFIG_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    config_module.get_settings.cache_clear()
    yield config_module
    config_module.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_module_caches():
    """用例结束后清空模块级缓存，避免跨用例污染。"""
    yield
    try:
        import config as config_module

        config_module.get_settings.cache_clear()
    except Exception:  # pragma: no cover - 依赖缺失时不影响其他用例
        pass
    try:
        import generator

        generator._client_for.cache_clear()
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# 临时目录策略（避免 pytest-of-<user> 落在项目根目录）
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """未显式指定 --basetemp 时，把临时目录固定到工作区的 tests/.pytest-tmp。

    背景：本环境下 Python 进程无法写入系统 TEMP（PermissionError），
    `tempfile.gettempdir()` 会回退到当前工作目录（项目根目录），使 pytest 默认
    的 `pytest-of-<user>` 目录出现在项目根目录。显式指定 basetemp 可避免污染。
    """
    if getattr(config.option, "basetemp", None) is None:
        config.option.basetemp = str(WORKSPACE_TMP)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """会话结束后清理本 hook 自己设置的 basetemp（不动用户显式指定的目录）。"""
    basetemp = getattr(session.config.option, "basetemp", None)
    if not basetemp:
        return
    try:
        resolved = Path(basetemp).resolve()
        if resolved.parent == (PROJECT_ROOT / "tests").resolve():
            shutil.rmtree(resolved, ignore_errors=True)
    except OSError:  # pragma: no cover - 清理失败不应影响测试结果
        pass
