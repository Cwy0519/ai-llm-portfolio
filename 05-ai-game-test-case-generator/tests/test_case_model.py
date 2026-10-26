# -*- coding: utf-8 -*-
"""用例模型测试：编号、排序、去重、统计、表格行。"""
from __future__ import annotations

from utils.case_model import (
    HEADERS,
    build_cases,
    dedupe,
    sort_cases,
    stats,
    stats_markdown,
    to_rows,
)


def raw(title="用例", priority="P2", expected="预期", **kwargs):
    item = {
        "title": title,
        "priority": priority,
        "type": kwargs.get("type", "功能"),
        "method": kwargs.get("method", "场景法"),
        "preconditions": kwargs.get("preconditions", "前置"),
        "steps": kwargs.get("steps", ["步骤一", "步骤二"]),
        "expected": expected,
    }
    return item


def test_build_cases_assigns_sequential_ids():
    cases = build_cases([raw("A"), raw("B"), raw("C")], module="充值付费")
    assert [c.id for c in cases] == ["TC-001", "TC-002", "TC-003"]
    assert all(c.module == "充值付费" for c in cases)


def test_build_cases_sorts_by_priority():
    cases = build_cases([raw("低", "P3"), raw("高", "P0"), raw("中", "P1")], module="m")
    assert [c.priority for c in cases] == ["P0", "P1", "P3"]
    assert cases[0].title == "高"


def test_build_cases_empty():
    assert build_cases([], module="m") == []


def test_dedupe_same_title_and_expected():
    kept, removed = dedupe([raw("A"), raw("A")])
    assert (len(kept), removed) == (1, 1)


def test_dedupe_keeps_different_expected():
    kept, removed = dedupe([raw("A", expected="成功"), raw("A", expected="失败")])
    assert (len(kept), removed) == (2, 0)


def test_dedupe_ignores_punctuation_and_case():
    kept, removed = dedupe([raw("背包已满，领取道具"), raw("背包已满 领取道具")])
    assert (len(kept), removed) == (1, 1)


def test_sort_cases_keeps_stable_order():
    items = [raw("a", "P1"), raw("b", "P1"), raw("c", "P0")]
    assert [c["title"] for c in sort_cases(items)] == ["c", "a", "b"]


def test_stats_counts_every_dimension():
    cases = build_cases(
        [
            raw("A", "P0", type="功能"),
            raw("B", "P0", type="边界", method="边界值分析"),
            raw("C", "P1", type="异常", method="错误推测法"),
            raw("D", "P2", type="功能"),
        ],
        module="m",
    )
    s = stats(cases)
    assert s["total"] == 4
    assert s["by_priority"] == {"P0": 2, "P1": 1, "P2": 1, "P3": 0}
    assert s["by_type"]["功能"] == 2
    assert s["by_method"]["场景法"] == 2
    assert s["method_covered"] == 3


def test_stats_flags_too_many_p0():
    cases = build_cases([raw("A", "P0"), raw("B", "P0"), raw("C", "P2")], module="m")
    s = stats(cases)
    assert s["p0_ratio_ok"] is False
    assert "复核优先级" in stats_markdown(cases)


def test_stats_markdown_empty():
    assert stats_markdown([]) == "还没有生成用例。"


def test_stats_markdown_contains_total():
    cases = build_cases([raw("A")], module="充值付费")
    text = stats_markdown(cases, requested=10)
    assert "共生成 1 条" in text
    assert "目标 10 条" in text


def test_to_rows_matches_headers():
    cases = build_cases([raw("A")], module="m")
    rows = to_rows(cases)
    assert len(rows) == 1
    assert len(rows[0]) == len(HEADERS)


def test_steps_text_is_numbered():
    case = build_cases([raw("A", steps=["打开商城", "点击购买"])], module="m")[0]
    assert case.steps_text() == "1. 打开商城\n2. 点击购买"


def test_preconditions_default_when_blank():
    case = build_cases([raw("A", preconditions="")], module="m")[0]
    assert case.preconditions == "无特殊前置条件"
