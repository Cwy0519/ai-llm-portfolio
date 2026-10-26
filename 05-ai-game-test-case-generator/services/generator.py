# -*- coding: utf-8 -*-
"""生成编排层：校验输入 → 分批调用模型 → 解析 → 去重 → 编号 → 汇总提醒。

为什么要分批：一次让模型吐 30 条用例，质量会明显下降（后面几条开始敷衍），
而且容易超出输出长度限制。所以按 BATCH_SIZE 拆分，每批单独校验。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from config import Settings
from prompts import DESIGN_METHODS, GAME_SCENES, build_messages
from utils.case_model import TestCase, build_cases, dedupe
from utils.parser import ParseError, extract_json, normalize_cases

BATCH_SIZE = 12
MAX_COUNT = 50


class InputError(Exception):
    """用户输入不合法。消息可直接展示。"""


class GenerationError(Exception):
    """生成失败。消息可直接展示。"""


@dataclass
class Result:
    cases: list[TestCase]
    requested: int
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.cases)


def validate_input(scene_name: str, feature: str, methods: Sequence[str], count: int,
                   max_cases: int = MAX_COUNT) -> tuple[str, list[str], int]:
    """校验并清洗输入，返回 (功能描述, 方法列表, 数量)。"""
    if scene_name not in GAME_SCENES:
        raise InputError(f"请选择一个游戏场景（当前：{scene_name!r} 无效）")

    feature_text = (feature or "").strip()
    if len(feature_text) < 5:
        raise InputError("请填写要测试的功能描述，至少 5 个字。例如：充值月卡后应立刻到账并解锁每日领取。")

    method_list = [m for m in (methods or []) if m in DESIGN_METHODS]
    if not method_list:
        raise InputError("请至少勾选一种用例设计方法。")

    if not isinstance(count, int) or count < 1:
        raise InputError("生成数量必须是大于 0 的整数。")
    if count > max_cases:
        raise InputError(f"一次最多生成 {max_cases} 条用例，请调小数量。")
    return feature_text, method_list, count


class Generator:
    """把 LLMClient 和解析、编号流程串起来。"""

    def __init__(self, client, settings: Settings | None = None, batch_size: int = BATCH_SIZE):
        self.client = client
        self.settings = settings
        self.batch_size = max(1, batch_size)

    def generate(self, scene_name: str, feature: str, methods: Sequence[str], count: int) -> Result:
        max_cases = self.settings.max_cases if self.settings else MAX_COUNT
        feature_text, method_list, count = validate_input(scene_name, feature, methods, count, max_cases)

        warnings: list[str] = []
        raw: list[dict] = []
        dropped_total = 0
        remaining = count
        batch_index = 0

        while remaining > 0:
            batch_index += 1
            size = min(self.batch_size, remaining)
            remaining -= size
            messages = build_messages(scene_name, feature_text, method_list, size)
            try:
                text = self.client.chat_json(messages)
                payload = extract_json(text)
                batch_cases, dropped = normalize_cases(payload)
            except ParseError as exc:
                warnings.append(f"第 {batch_index} 批返回格式无法解析，已跳过（{exc}）")
                continue
            if dropped:
                dropped_total += dropped
                warnings.append(f"第 {batch_index} 批有 {dropped} 条用例字段缺失，已丢弃")
            if not batch_cases:
                warnings.append(f"第 {batch_index} 批没有解析出有效用例")
            raw.extend(batch_cases)

        if not raw:
            raise GenerationError("没有生成任何有效用例，请调整功能描述或重试。")

        raw, removed = dedupe(raw)
        if removed:
            warnings.append(f"合并时有 {removed} 条重复用例被去重")

        cases = build_cases(raw, module=scene_name)
        if len(cases) > count:
            cases = cases[:count]
        if len(cases) < count:
            warnings.append(f"目标 {count} 条，实际生成 {len(cases)} 条，可再生成一次补足")

        return Result(cases=cases, requested=count, warnings=warnings)
