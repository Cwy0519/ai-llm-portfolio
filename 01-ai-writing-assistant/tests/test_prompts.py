"""prompts.py 的单元测试：场景元数据、模板填充、校验与场景解析。

新契约：只有 3 种语气（正式 / 活泼 / 幽默）；篇幅、补充要求、示例填充、
演示文本均已移除。
"""

from __future__ import annotations

import dataclasses

import pytest

import prompts
from prompts import (
    DEFAULT_TONE,
    OUTPUT_RULES,
    SCENARIO_LIST,
    SCENARIOS,
    TONES,
    build_messages,
    get_scenario,
    resolve_scenario,
    scenario_choices,
    validate_values,
)

SCENARIO_KEYS = ["email", "xiaohongshu", "weekly", "official", "novel"]


def _sample_values(scenario: prompts.Scenario) -> dict[str, str]:
    """为场景生成合法测试输入：每个字段一个非空值。"""
    return {field.key: f"{field.label}的示例内容" for field in scenario.fields}


# ---------------------------------------------------------------------------
# 语气与已移除功能
# ---------------------------------------------------------------------------


def test_tones_are_exactly_three():
    assert list(TONES) == ["正式", "活泼", "幽默"]
    assert set(TONES) == {"正式", "活泼", "幽默"}
    assert DEFAULT_TONE == "正式"
    assert prompts.tones() == list(TONES)
    for label, description in TONES.items():
        assert label.strip()
        assert description.strip()


def test_removed_features_are_gone():
    """篇幅 / 补充要求 / 示例值 / 演示文本等已按需求移除。"""
    for name in (
        "LENGTHS",
        "DEFAULT_LENGTH",
        "lengths",
        "MAX_EXTRA_CHARS",
        "example_values",
        "empty_values",
        "demo_output",
    ):
        assert not hasattr(prompts, name), f"prompts 不应再有 {name}"


def test_scenario_dataclass_contract():
    field_names = {item.name for item in dataclasses.fields(prompts.Scenario)}

    assert field_names == {
        "key",
        "name",
        "summary",
        "fields",
        "system_prompt",
        "user_template",
        "default_tone",
    }
    assert not hasattr(prompts.Scenario, "display_name")


# ---------------------------------------------------------------------------
# 场景注册与元数据
# ---------------------------------------------------------------------------


def test_five_scenarios_are_registered():
    assert set(SCENARIOS) == set(SCENARIO_KEYS)
    assert len(SCENARIO_LIST) == len(SCENARIOS) == 5
    assert prompts.DEFAULT_SCENARIO in SCENARIOS
    assert [scenario.key for scenario in SCENARIO_LIST] == SCENARIO_KEYS


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_scenario_metadata_is_complete(key):
    scenario = SCENARIOS[key]

    assert scenario.key == key
    assert scenario.name.strip()
    assert scenario.summary.strip()
    assert scenario.fields, "每个场景至少需要一个输入字段"
    assert scenario.system_prompt.strip()
    assert scenario.user_template.strip()
    assert scenario.default_tone in TONES

    field_keys = [field.key for field in scenario.fields]
    assert len(field_keys) == len(set(field_keys)), "字段 key 不能重复"
    for field in scenario.fields:
        assert field.key.strip()
        assert field.label.strip()
        assert field.lines > 0
        assert field.max_chars > 0
        # 每个字段都应该出现在 user 模板里，否则用户输入会被丢弃
        assert f"{{{field.key}}}" in scenario.user_template


def test_scenario_choices_are_plain_names():
    choices = scenario_choices()

    assert choices == [(scenario.name, scenario.key) for scenario in SCENARIO_LIST]
    # 纯名称、无 emoji 前缀
    for scenario, (display, key) in zip(SCENARIO_LIST, choices):
        assert display == scenario.name
        assert key == scenario.key
        assert not any(ord(char) > 0xFFFF for char in display), "显示名不应包含 emoji"


# ---------------------------------------------------------------------------
# build_messages：结构、占位符替换、语气要求
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_build_messages_returns_system_and_user(key):
    scenario = SCENARIOS[key]
    values = _sample_values(scenario)

    messages = build_messages(scenario, values)

    assert [message["role"] for message in messages] == ["system", "user"]
    assert all(message["content"].strip() for message in messages)
    system_content = messages[0]["content"]
    user_content = messages[1]["content"]

    assert scenario.system_prompt in system_content
    assert OUTPUT_RULES in system_content
    for field in scenario.fields:
        assert f"{{{field.key}}}" not in user_content, "占位符必须全部被替换"
        assert values[field.key] in user_content, "用户输入应完整出现在 user 消息中"


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_user_message_contains_tone_requirements(key):
    scenario = SCENARIOS[key]

    user_content = build_messages(scenario, _sample_values(scenario), tone="活泼")[1]["content"]

    assert "【语气要求】" in user_content
    assert "活泼" in user_content
    assert TONES["活泼"] in user_content
    assert user_content.rstrip().endswith(f"活泼（{TONES['活泼']}）")


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_none_tone_uses_scenario_default(key):
    scenario = SCENARIOS[key]

    user_content = build_messages(scenario, _sample_values(scenario), tone=None)[1]["content"]

    assert f"【语气要求】{scenario.default_tone}" in user_content


def test_invalid_tone_falls_back_to_scenario_default():
    scenario = SCENARIOS["email"]

    user_content = build_messages(
        scenario, _sample_values(scenario), tone="阴阳怪气"
    )[1]["content"]

    assert f"【语气要求】{scenario.default_tone}" in user_content
    assert "阴阳怪气" not in user_content


def test_values_are_stripped():
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    values["purpose"] = "  说明交付延期  "

    user_content = build_messages(scenario, values)[1]["content"]

    assert "- 邮件目的：说明交付延期" in user_content


def test_user_input_with_braces_is_not_replaced_twice():
    """模板填充是一次性 re.sub：字段值里的 {其他字段} 不应被二次替换。"""
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    values["recipient"] = "王经理 {purpose}"

    user_content = build_messages(scenario, values)[1]["content"]

    assert "{purpose}" in user_content


def test_unknown_braces_remain_untouched():
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    values["recipient"] = "王经理 {未定义字段}"

    user_content = build_messages(scenario, values)[1]["content"]

    assert "{未定义字段}" in user_content


# ---------------------------------------------------------------------------
# validate_values
# ---------------------------------------------------------------------------


def test_validate_values_detects_missing_required_field():
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    values["purpose"] = "   "

    problems = validate_values(scenario, values)

    assert len(problems) == 1
    assert "邮件目的" in problems[0]
    assert "请填写" in problems[0]


def test_validate_values_detects_multiple_missing_fields():
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    del values["recipient"]
    del values["action"]

    problems = validate_values(scenario, values)

    assert any("收件人与身份" in problem for problem in problems)
    assert any("期望对方做什么" in problem for problem in problems)


def test_validate_values_allows_empty_optional_fields():
    scenario = SCENARIOS["weekly"]
    values = _sample_values(scenario)
    for optional_key in ("role", "results", "problems"):
        assert next(f for f in scenario.fields if f.key == optional_key).required is False
        values[optional_key] = ""

    assert validate_values(scenario, values) == []


def test_validate_values_detects_overlong_input():
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    values["recipient"] = "字" * 2001

    problems = validate_values(scenario, values)

    assert any("收件人与身份" in problem and "过长" in problem for problem in problems)


def test_validate_values_exact_limit_is_ok():
    scenario = SCENARIOS["email"]
    values = _sample_values(scenario)
    values["recipient"] = "字" * 2000

    assert validate_values(scenario, values) == []


def test_validate_values_accepts_sample_values():
    for scenario in SCENARIO_LIST:
        assert validate_values(scenario, _sample_values(scenario)) == []


# ---------------------------------------------------------------------------
# 场景解析
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_resolve_scenario_accepts_key_and_name(key):
    scenario = SCENARIOS[key]

    assert resolve_scenario(scenario.key) is scenario
    assert resolve_scenario(scenario.name) is scenario


def test_resolve_scenario_falls_back_to_default():
    default = SCENARIOS[prompts.DEFAULT_SCENARIO]

    assert resolve_scenario(None) is default
    assert resolve_scenario("") is default


def test_resolve_scenario_unknown_raises_key_error():
    with pytest.raises(KeyError):
        resolve_scenario("不存在的场景")


def test_get_scenario():
    assert get_scenario("email") is SCENARIOS["email"]
    with pytest.raises(KeyError):
        get_scenario("nope")
