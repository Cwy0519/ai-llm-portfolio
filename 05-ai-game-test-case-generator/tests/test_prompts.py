# -*- coding: utf-8 -*-
"""提示词层测试：场景库、方法库、消息组装。"""
from __future__ import annotations

import pytest

from prompts import (
    DESIGN_METHODS,
    GAME_SCENES,
    build_messages,
    build_user_prompt,
    get_scene,
    method_names,
    scene_names,
)


def test_scene_library_has_expected_size():
    assert len(scene_names()) == len(GAME_SCENES) == 8


def test_method_library_has_expected_size():
    assert len(method_names()) == len(DESIGN_METHODS) == 5


def test_get_scene_unknown_raises():
    with pytest.raises(KeyError):
        get_scene("不存在的场景")


def test_scene_brief_joins_focus_points():
    scene = get_scene("充值付费")
    assert "充值" in scene.brief()
    assert isinstance(scene.risks, tuple) and scene.risks


def test_build_messages_roles():
    messages = build_messages("充值付费", "购买月卡后立即到账", ["场景法"], 5)
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "测试工程师" in messages[0]["content"]


def test_user_prompt_contains_feature_methods_and_count():
    prompt = build_user_prompt(get_scene("战斗与技能"), "释放大招后进入冷却", ["边界值分析", "错误推测法"], 8)
    assert "释放大招后进入冷却" in prompt
    assert "边界值分析" in prompt and "错误推测法" in prompt
    assert "8 条" in prompt
    assert "P0" in prompt


def test_user_prompt_requires_abnormal_cases():
    prompt = build_user_prompt(get_scene("登录与注册"), "手机号验证码登录", ["场景法"], 10)
    assert "异常" in prompt and "边界" in prompt


def test_build_user_prompt_without_methods_raises():
    with pytest.raises(ValueError):
        build_user_prompt(get_scene("登录与注册"), "登录", [], 5)


def test_system_prompt_forbids_extra_output():
    system = build_messages("登录与注册", "验证码登录", ["等价类划分"], 3)[0]["content"]
    assert "JSON" in system
    assert "不要输出任何解释" in system
