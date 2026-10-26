"""生成流程编排。

UI 只调用 stream_generate()：它负责校验输入与配置、组装提示词、流式产出文本，
并把可预期的失败转换为 InputError / GenerationError，便于界面展示友好提示。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator, Mapping

from config import Settings, get_settings
from llm_client import LLMClient, LLMError
from prompts import (
    Scenario,
    build_messages,
    resolve_scenario,
    validate_values,
)


class InputError(ValueError):
    """用户输入不合法，消息可直接展示给用户。"""


class GenerationError(RuntimeError):
    """生成失败（配置、网络、模型服务等原因），消息可直接展示。"""


@lru_cache(maxsize=4)
def _client_for(settings: Settings) -> LLMClient:
    """按配置缓存客户端（Settings 不可变，配置变化后会生成新实例）。"""
    return LLMClient(settings)


def prepare(
    scenario_key: str,
    values: Mapping[str, str],
    tone: str | None = None,
    settings: Settings | None = None,
) -> tuple[Scenario, Settings, list[dict[str, str]]]:
    """校验并组装本次生成所需的全部材料。"""
    try:
        scenario = resolve_scenario(scenario_key)
    except KeyError as exc:
        raise InputError(f"未知写作场景：{scenario_key!r}") from exc

    problems = validate_values(scenario, values)
    if problems:
        raise InputError("；".join(problems))

    config = settings or get_settings()
    issues = config.validate()
    if issues:
        raise GenerationError("配置有误：" + "；".join(issues))

    messages = build_messages(scenario, values, tone=tone)
    return scenario, config, messages


def _stream_remote(config: Settings, messages: list[dict[str, str]]) -> Iterator[str]:
    """真实模型调用：把底层异常统一转换为 GenerationError。"""
    try:
        client = _client_for(config)
        yield from client.stream_chat(messages)
    except LLMError as exc:
        raise GenerationError(exc.friendly) from exc
    except Exception as exc:  # noqa: BLE001 - 兜底，避免界面抛出原始堆栈
        raise GenerationError(f"生成失败：{type(exc).__name__}: {str(exc)[:200]}") from exc


def stream_generate(
    scenario_key: str,
    values: Mapping[str, str],
    tone: str | None = None,
    settings: Settings | None = None,
) -> Iterator[str]:
    """流式生成文本，逐段产出模型增量（调用方负责累积）。

    输入/配置错误在调用时立刻抛出，便于界面直接提示；只有模型输出是逐步迭代的。
    """
    _scenario, config, messages = prepare(scenario_key, values, tone=tone, settings=settings)
    return _stream_remote(config, messages)


def generate(
    scenario_key: str,
    values: Mapping[str, str],
    tone: str | None = None,
    settings: Settings | None = None,
) -> str:
    """非流式生成，返回完整文本（便于脚本调用与测试）。"""
    return "".join(stream_generate(scenario_key, values, tone=tone, settings=settings))
