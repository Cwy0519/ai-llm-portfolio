# -*- coding: utf-8 -*-
"""用例数据模型：编号、去重、排序、统计、表格行转换。

把"模型生成的一堆文本"变成"测试团队能直接用的用例表"，靠的就是这一层。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

PRIORITIES = ("P0", "P1", "P2", "P3")
CASE_TYPES = ("功能", "边界", "异常", "兼容", "性能", "安全")

HEADERS = (
    "用例编号",
    "模块",
    "用例标题",
    "优先级",
    "用例类型",
    "设计方法",
    "前置条件",
    "操作步骤",
    "预期结果",
)

_NORMALIZE_RE = re.compile(r"[\s，。,.、；;：:（）()\[\]【】]+")


@dataclass
class TestCase:
    id: str
    module: str
    title: str
    priority: str
    type: str
    method: str
    preconditions: str
    steps: list[str] = field(default_factory=list)
    expected: str = ""

    def steps_text(self) -> str:
        return "\n".join(f"{i}. {step}" for i, step in enumerate(self.steps, 1))

    def row(self) -> tuple:
        return (
            self.id,
            self.module,
            self.title,
            self.priority,
            self.type,
            self.method,
            self.preconditions,
            self.steps_text(),
            self.expected,
        )


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub("", (text or "").lower())


def dedupe(raw_cases: Sequence[dict]) -> tuple[list[dict], int]:
    """按「标题 + 预期结果」去重，保留第一次出现的。"""
    seen: set[str] = set()
    kept: list[dict] = []
    removed = 0
    for case in raw_cases:
        key = _normalize(str(case.get("title", ""))) + "|" + _normalize(str(case.get("expected", "")))
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        kept.append(case)
    return kept, removed


def sort_cases(raw_cases: Sequence[dict]) -> list[dict]:
    """按优先级排序，同级保持模型给出的顺序。"""
    order = {p: i for i, p in enumerate(PRIORITIES)}
    return sorted(raw_cases, key=lambda c: order.get(str(c.get("priority", "P2")), 2))


def build_cases(raw_cases: Iterable[dict], module: str) -> list[TestCase]:
    """去重 → 排序 → 编号，产出最终用例对象。"""
    cases = [dict(c) for c in raw_cases]
    cases, _ = dedupe(cases)
    cases = sort_cases(cases)
    result: list[TestCase] = []
    for index, item in enumerate(cases, 1):
        result.append(
            TestCase(
                id=f"TC-{index:03d}",
                module=module,
                title=str(item.get("title", "")).strip(),
                priority=str(item.get("priority", "P2")),
                type=str(item.get("type", "功能")),
                method=str(item.get("method", "场景法")),
                preconditions=str(item.get("preconditions", "")).strip() or "无特殊前置条件",
                steps=list(item.get("steps") or []),
                expected=str(item.get("expected", "")).strip(),
            )
        )
    return result


def stats(cases: Sequence[TestCase]) -> dict:
    """统计：总数、优先级分布、类型分布、方法覆盖。"""
    total = len(cases)
    by_priority = {p: 0 for p in PRIORITIES}
    by_type = {t: 0 for t in CASE_TYPES}
    by_method: dict[str, int] = {}
    for case in cases:
        by_priority[case.priority] = by_priority.get(case.priority, 0) + 1
        by_type[case.type] = by_type.get(case.type, 0) + 1
        by_method[case.method] = by_method.get(case.method, 0) + 1
    p0_ratio = (by_priority.get("P0", 0) / total) if total else 0.0
    return {
        "total": total,
        "by_priority": by_priority,
        "by_type": by_type,
        "by_method": by_method,
        "p0_ratio": p0_ratio,
        "p0_ratio_ok": p0_ratio <= 0.34,
        "method_covered": len(by_method),
    }


def stats_markdown(cases: Sequence[TestCase], requested: int = 0) -> str:
    """把统计结果渲染成一段 Markdown，给界面展示。"""
    s = stats(cases)
    if s["total"] == 0:
        return "还没有生成用例。"
    prio = " ｜ ".join(f"{p} {s['by_priority'].get(p, 0)}" for p in PRIORITIES)
    types = " ｜ ".join(f"{t} {n}" for t, n in s["by_type"].items() if n)
    methods = " ｜ ".join(f"{m} {n}" for m, n in s["by_method"].items())
    ratio = f"{s['p0_ratio'] * 100:.0f}%"
    warn = "" if s["p0_ratio_ok"] else "（P0 占比偏高，建议复核优先级）"
    target = f"（目标 {requested} 条）" if requested else ""
    return (
        f"**共生成 {s['total']} 条用例**{target}　｜　覆盖率：{len({c.module for c in cases})} 个模块\n\n"
        f"- **优先级分布**：{prio}　｜　P0 占比 {ratio}{warn}\n"
        f"- **用例类型**：{types}\n"
        f"- **设计方法**：{methods}"
    )


def to_rows(cases: Sequence[TestCase]) -> list[list[str]]:
    """转换为界面表格 / Excel 使用的行数据。"""
    return [list(case.row()) for case in cases]
