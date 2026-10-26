# -*- coding: utf-8 -*-
"""把大模型返回的文本解析成结构化的测试用例。

模型输出不稳定是常态，所以这里做了四层兜底：
1. 直接 json.loads
2. 剥掉 ```json 代码块再解析
3. 从第一个 { 到最后一个 } 截取再解析
4. 修掉尾逗号、中文引号后再解析一次

解析成功后还要做字段校验与归一化，字段缺失的用例会被丢弃并计数，
而不是抛异常让整批作废。
"""
from __future__ import annotations

import json
import re
from typing import Any

from prompts import DESIGN_METHODS

PRIORITIES = ("P0", "P1", "P2", "P3")
CASE_TYPES = ("功能", "边界", "异常", "兼容", "性能", "安全")

_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)
_PRIORITY_RE = re.compile(r"P\s*([0-3])", re.I)
_STEP_PREFIX = re.compile(r"^\s*(?:\d+[.、)]|[-*•])\s*")

_TITLE_KEYS = ("title", "用例标题", "name", "标题")
_STEPS_KEYS = ("steps", "操作步骤", "step", "步骤")
_EXPECTED_KEYS = ("expected", "预期结果", "expect", "期望结果")
_PRE_KEYS = ("preconditions", "前置条件", "precondition", "前提条件")
_PRIORITY_KEYS = ("priority", "优先级")
_TYPE_KEYS = ("type", "用例类型", "类型")
_METHOD_KEYS = ("method", "设计方法")
_LIST_KEYS = ("cases", "test_cases", "testcases", "测试用例", "data", "items")


class ParseError(Exception):
    """模型输出无法解析为 JSON。"""


def _loads(text: str) -> Any:
    return json.loads(text)


def _repair(text: str) -> str:
    """处理常见的模型格式毛病：尾逗号、中文引号、单引号。"""
    fixed = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)          # 尾逗号
    fixed = re.sub(r"'([^'\\]*)'(\s*:)", r'"\1"\2', fixed)  # 单引号 key
    return fixed


def extract_json(text: str) -> Any:
    """从任意文本中抠出 JSON 对象或数组。"""
    if not isinstance(text, str) or not text.strip():
        raise ParseError("模型返回为空")

    candidates: list[str] = [text.strip()]

    for block in _FENCE.findall(text):
        candidates.append(block.strip())

    start_obj, end_obj = text.find("{"), text.rfind("}")
    if start_obj != -1 and end_obj > start_obj:
        candidates.append(text[start_obj:end_obj + 1])
    start_arr, end_arr = text.find("["), text.rfind("]")
    if start_arr != -1 and end_arr > start_arr:
        candidates.append(text[start_arr:end_arr + 1])

    last_error: Exception | None = None
    for candidate in candidates:
        for payload in (candidate, _repair(candidate)):
            try:
                return _loads(payload)
            except json.JSONDecodeError as exc:
                last_error = exc

    raise ParseError(f"无法解析为 JSON：{last_error}")


def _first(item: dict, keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return default


def _as_steps(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[\n；;]+", value)
    elif isinstance(value, (list, tuple)):
        parts = []
        for entry in value:
            if isinstance(entry, str):
                parts.append(entry)
            elif isinstance(entry, dict):
                parts.append(str(_first(entry, ("step", "action", "内容", "描述"), "")))
    else:
        parts = [str(value)]
    cleaned = []
    for part in parts:
        text = _STEP_PREFIX.sub("", str(part)).strip()
        if text:
            cleaned.append(text)
    return cleaned[:10]


def _as_priority(value: Any) -> str:
    if isinstance(value, str):
        match = _PRIORITY_RE.search(value)
        if match:
            return f"P{match.group(1)}"
        if value.strip().upper() in PRIORITIES:
            return value.strip().upper()
    return "P2"


def _as_type(value: Any) -> str:
    text = str(value or "").strip()
    for candidate in CASE_TYPES:
        if candidate in text:
            return candidate
    return "功能"


_METHOD_KEYWORDS = (
    ("等价", "等价类划分"),
    ("边界", "边界值分析"),
    ("场景", "场景法"),
    ("错误推测", "错误推测法"),
    ("推测", "错误推测法"),
    ("正交", "正交实验法"),
)


def _as_method(value: Any) -> str:
    """模型可能只写「边界值」这种简写，这里做关键字兜底。"""
    text = str(value or "").strip()
    for candidate in DESIGN_METHODS:
        if candidate in text:
            return candidate
    for keyword, candidate in _METHOD_KEYWORDS:
        if keyword in text:
            return candidate
    return "场景法"


def normalize_cases(payload: Any) -> tuple[list[dict], int]:
    """把模型返回的任意结构归一化成用例字典列表。

    返回 (用例列表, 被丢弃的条数)。
    """
    if isinstance(payload, dict):
        found = None
        for key in _LIST_KEYS:
            if isinstance(payload.get(key), list):
                found = payload[key]
                break
        if found is None:
            found = [payload] if _first(payload, _TITLE_KEYS) else []
        raw_items = found
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raise ParseError("模型返回的 JSON 不是对象或数组")

    cases: list[dict] = []
    dropped = 0
    for item in raw_items:
        if not isinstance(item, dict):
            dropped += 1
            continue
        title = str(_first(item, _TITLE_KEYS, "") or "").strip()
        steps = _as_steps(_first(item, _STEPS_KEYS))
        expected = str(_first(item, _EXPECTED_KEYS, "") or "").strip()
        if not title or (not steps and not expected):
            dropped += 1
            continue
        cases.append(
            {
                "title": title,
                "priority": _as_priority(_first(item, _PRIORITY_KEYS)),
                "type": _as_type(_first(item, _TYPE_KEYS)),
                "method": _as_method(_first(item, _METHOD_KEYS)),
                "preconditions": str(_first(item, _PRE_KEYS, "") or "").strip() or "无特殊前置条件",
                "steps": steps or ["按用例标题描述执行操作"],
                "expected": expected or "按需求文档校验结果",
            }
        )
    return cases, dropped
