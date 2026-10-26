# -*- coding: utf-8 -*-
"""编排层测试：输入校验、分批调用、解析失败兜底、跨批去重。

全部使用假客户端，不联网、不消耗额度。
"""
from __future__ import annotations

import json

import pytest

from services.generator import Generator, GenerationError, InputError

FEATURE = "购买月卡后立即到账并解锁每日领取"


def make_payload(n: int, prefix: str = "用例") -> str:
    cases = [
        {
            "title": f"{prefix}{i}",
            "priority": ["P0", "P1", "P2"][i % 3],
            "type": ["功能", "边界", "异常"][i % 3],
            "method": ["场景法", "边界值分析", "错误推测法"][i % 3],
            "preconditions": "已登录",
            "steps": ["打开商城", "点击购买"],
            "expected": f"结果{i}",
        }
        for i in range(1, n + 1)
    ]
    return json.dumps({"cases": cases}, ensure_ascii=False)


class FakeClient:
    """按顺序吐出预设响应的假客户端。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_json(self, messages):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("假客户端响应不够用了")
        return self.responses.pop(0)


def test_generate_basic():
    client = FakeClient([make_payload(3)])
    result = Generator(client).generate("充值付费", FEATURE, ["场景法"], 3)
    assert result.count == 3
    assert [c.id for c in result.cases] == ["TC-001", "TC-002", "TC-003"]
    assert result.warnings == []


def test_generate_splits_into_batches():
    client = FakeClient([make_payload(12, "甲"), make_payload(8, "乙")])
    result = Generator(client, batch_size=12).generate("充值付费", FEATURE, ["场景法"], 20)
    assert len(client.calls) == 2
    assert result.count == 20


def test_generate_caps_to_requested_count():
    client = FakeClient([make_payload(10)])
    result = Generator(client, batch_size=20).generate("充值付费", FEATURE, ["场景法"], 4)
    assert result.count == 4


def test_generate_warns_when_less_than_requested():
    client = FakeClient([make_payload(3)])
    result = Generator(client, batch_size=10).generate("充值付费", FEATURE, ["场景法"], 8)
    assert any("实际生成" in w for w in result.warnings)


def test_parse_error_in_one_batch_continues():
    client = FakeClient(["模型这轮没按格式输出", make_payload(1)])
    result = Generator(client, batch_size=1).generate("充值付费", FEATURE, ["场景法"], 2)
    assert result.count == 1
    assert any("无法解析" in w for w in result.warnings)


def test_all_batches_fail_raises():
    client = FakeClient(["坏数据一", "坏数据二"])
    with pytest.raises(GenerationError):
        Generator(client, batch_size=1).generate("充值付费", FEATURE, ["场景法"], 2)


def test_duplicate_cases_removed_across_batches():
    client = FakeClient([make_payload(2, "重复"), make_payload(2, "重复")])
    result = Generator(client, batch_size=2).generate("充值付费", FEATURE, ["场景法"], 4)
    assert result.count == 2
    assert any("去重" in w for w in result.warnings)


@pytest.mark.parametrize(
    "scene,feature,methods,count",
    [
        ("不存在的场景", FEATURE, ["场景法"], 5),
        ("充值付费", "太短", ["场景法"], 5),
        ("充值付费", FEATURE, [], 5),
        ("充值付费", FEATURE, ["瞎写的方法"], 5),
        ("充值付费", FEATURE, ["场景法"], 0),
        ("充值付费", FEATURE, ["场景法"], 999),
    ],
)
def test_invalid_inputs_raise(scene, feature, methods, count):
    client = FakeClient([make_payload(1)])
    with pytest.raises(InputError):
        Generator(client).generate(scene, feature, methods, count)


def test_client_failure_propagates():
    class Boom:
        def chat_json(self, messages):
            raise RuntimeError("接口挂了")

    with pytest.raises(RuntimeError):
        Generator(Boom()).generate("充值付费", FEATURE, ["场景法"], 1)
