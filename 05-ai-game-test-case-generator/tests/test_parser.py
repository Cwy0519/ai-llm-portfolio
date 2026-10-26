# -*- coding: utf-8 -*-
"""解析层测试：模型输出抠 JSON、容错修复、字段归一化、脏数据丢弃。"""
from __future__ import annotations

import json

import pytest

from utils.parser import ParseError, extract_json, normalize_cases


def as_text(payload) -> str:
    return json.dumps(payload, ensure_ascii=False)


# ---------------- extract_json ----------------
def test_extract_plain_object():
    assert extract_json('{"cases": []}') == {"cases": []}


def test_extract_from_code_fence():
    text = '好的，结果如下：\n```json\n{"cases": [{"title": "登录成功"}]}\n```\n以上。'
    assert extract_json(text)["cases"][0]["title"] == "登录成功"


def test_extract_from_prose_without_fence():
    text = '根据需求分析，生成结果：{"cases": [{"title": "充值到账"}]} 请复核。'
    assert extract_json(text)["cases"][0]["title"] == "充值到账"


def test_extract_array():
    assert extract_json('[{"title": "a"}]')[0]["title"] == "a"


def test_repair_trailing_comma():
    text = '{"cases": [{"title": "a", "expected": "b",},],}'
    data = extract_json(text)
    assert data["cases"][0]["title"] == "a"


def test_repair_chinese_quotes():
    text = '{"cases": [{"title": “背包已满时领取道具”, "expected": "提示并转为邮件"}]}'
    assert extract_json(text)["cases"][0]["title"] == "背包已满时领取道具"


@pytest.mark.parametrize("bad", ["", "   ", "模型今天不想说话", "###"])
def test_extract_raises_on_garbage(bad):
    with pytest.raises(ParseError):
        extract_json(bad)


# ---------------- normalize_cases ----------------
def test_normalize_wrapped_cases():
    payload = {"cases": [{"title": "A", "steps": ["打开", "点击"], "expected": "成功"}]}
    cases, dropped = normalize_cases(payload)
    assert dropped == 0
    assert len(cases) == 1
    assert cases[0]["steps"] == ["打开", "点击"]


def test_normalize_bare_list():
    cases, dropped = normalize_cases([{"title": "A", "expected": "ok"}, {"title": "B", "expected": "ok"}])
    assert (len(cases), dropped) == (2, 0)


def test_normalize_single_object():
    cases, dropped = normalize_cases({"title": "单条用例", "expected": "ok"})
    assert (len(cases), dropped) == (1, 0)


def test_normalize_steps_string_split():
    payload = {"cases": [{"title": "A", "steps": "1. 打开商城\n2. 购买月卡", "expected": "到账"}]}
    cases, _ = normalize_cases(payload)
    assert cases[0]["steps"] == ["打开商城", "购买月卡"]


def test_normalize_priority_variants():
    payload = {
        "cases": [
            {"title": "a", "priority": "p0", "expected": "ok"},
            {"title": "b", "priority": "P1 高", "expected": "ok"},
            {"title": "c", "priority": "重要", "expected": "ok"},
        ]
    }
    cases, _ = normalize_cases(payload)
    assert [c["priority"] for c in cases] == ["P0", "P1", "P2"]


def test_normalize_type_and_method_keywords():
    payload = {"cases": [{"title": "a", "type": "性能问题", "method": "边界值", "expected": "ok"}]}
    cases, _ = normalize_cases(payload)
    assert cases[0]["type"] == "性能"
    assert cases[0]["method"] == "边界值分析"


def test_normalize_invalid_enum_falls_back():
    payload = {"cases": [{"title": "a", "type": "随便写的", "method": "瞎编方法", "expected": "ok"}]}
    cases, _ = normalize_cases(payload)
    assert cases[0]["type"] == "功能"
    assert cases[0]["method"] == "场景法"


def test_normalize_drops_incomplete_items():
    payload = {
        "cases": [
            {"title": "正常用例", "steps": ["a"], "expected": "ok"},
            {"steps": ["没有标题"], "expected": "ok"},
            {"title": "只有标题"},
            "这根本不是对象",
        ]
    }
    cases, dropped = normalize_cases(payload)
    assert len(cases) == 1
    assert dropped == 3


def test_normalize_defaults_preconditions():
    payload = {"cases": [{"title": "a", "steps": ["x"], "expected": "y"}]}
    cases, _ = normalize_cases(payload)
    assert cases[0]["preconditions"] == "无特殊前置条件"


def test_normalize_raises_on_scalar():
    with pytest.raises(ParseError):
        normalize_cases(123)

