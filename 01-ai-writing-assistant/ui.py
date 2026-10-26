"""Gradio 界面：AI 智能写作助手。

界面只负责「渲染 + 交互」：场景、字段、语气等元数据来自 prompts.py，
生成逻辑委托给 generator.stream_generate()，样式使用 Gradio 默认主题。
"""

from __future__ import annotations

from typing import Any, Iterator

import gradio as gr

import config
import prompts
from generator import GenerationError, InputError, stream_generate

TITLE = "AI 智能写作助手"
DESCRIPTION = (
    "选择写作场景、填写关键信息，AI 会生成对应风格的中文文案。"
    "生成结果可直接编辑，点击右上角按钮复制。"
)
STATUS_IDLE = "填写左侧信息后点击「生成」。"
OUTPUT_PLACEHOLDER = "生成的内容会显示在这里，可直接编辑后再复制。"


def _config_hint() -> str:
    """配置缺失时在页面顶部给出提示，避免用户点击生成后才看到错误。"""
    problems = config.get_settings().validate()
    if not problems:
        return ""
    return "**配置提示**：" + "；".join(problems)


def _run_generate(
    scenario_key: str | None,
    values: dict[str, str],
    tone: str | None,
) -> Iterator[tuple[str, str]]:
    """流式生成：逐段累积文本，同时产出（结果文本, 状态说明）。"""
    try:
        scenario = prompts.resolve_scenario(scenario_key)
    except KeyError:
        yield "", "错误：未知的写作场景，请刷新页面后重试。"
        return

    cleaned = {
        item.key: (values.get(item.key) or "").strip() for item in scenario.fields
    }
    yield "", "生成中…"

    chunks: list[str] = []
    try:
        for delta in stream_generate(scenario.key, cleaned, tone=tone):
            if not delta:
                continue
            chunks.append(delta)
            text = "".join(chunks)
            yield text, f"生成中…（已输出 {len(text)} 字）"
    except InputError as exc:
        yield "", f"请检查输入：{exc}"
        return
    except GenerationError as exc:
        yield "".join(chunks), f"生成失败：{exc}"
        return
    except Exception as exc:  # noqa: BLE001 - 兜底，不把堆栈暴露到界面
        yield "".join(chunks), f"生成失败：{type(exc).__name__}"
        return

    text = "".join(chunks).strip()
    if not text:
        yield "", "模型没有返回内容，请调整输入后重试。"
        return
    yield text, f"生成完成，共 {len(text)} 字。"


def _make_generate_fn(field_keys: list[str]) -> Any:
    """按场景字段动态生成回调签名。

    Gradio 按位置传入各输入组件，字段由 prompts.py 动态决定、数量不固定，
    因此运行时生成一个参数与输入一一对应的函数（字段名会出现在接口文档中）。
    """
    names = ["scenario_key", *field_keys, "tone"]
    for name in names:
        if not name.isidentifier():
            raise ValueError(f"场景字段名必须是合法标识符：{name!r}")

    assignments = "\n".join(f"        {key!r}: {key}," for key in field_keys)
    source = (
        f"def _generate({', '.join(names)}):\n"
        f"    values = {{\n{assignments}\n    }}\n"
        f"    yield from _run_generate(scenario_key, values, tone)\n"
    )
    namespace: dict[str, Any] = {"_run_generate": _run_generate}
    exec(compile(source, "<ui-generate>", "exec"), namespace)  # noqa: S102
    return namespace["_generate"]


def build_ui() -> gr.Blocks:
    """构建 Gradio Blocks 界面（只构建，不启动服务）。"""
    default_scenario = prompts.resolve_scenario(prompts.DEFAULT_SCENARIO)

    entries = [
        (scenario.key, item)
        for scenario in prompts.SCENARIO_LIST
        for item in scenario.fields
    ]
    field_keys = [item.key for _, item in entries]
    if len(set(field_keys)) != len(field_keys):
        raise ValueError("不同场景的字段 key 不能重复，否则无法按位置收集输入值")

    with gr.Blocks(title=TITLE) as demo:
        gr.Markdown(f"# {TITLE}\n\n{DESCRIPTION}")
        hint = _config_hint()
        if hint:
            gr.Markdown(hint)

        with gr.Row():
            # ---------- 左栏：场景 + 输入 + 生成 ----------
            with gr.Column():
                scenario_dropdown = gr.Dropdown(
                    choices=prompts.scenario_choices(),
                    value=default_scenario.key,
                    label="写作场景",
                    interactive=True,
                )

                # 所有场景的字段组一次创建，切换场景时只切换 visible
                field_boxes: dict[str, gr.Textbox] = {}
                field_groups: dict[str, gr.Column] = {}
                for scenario in prompts.SCENARIO_LIST:
                    with gr.Column(
                        visible=(scenario.key == default_scenario.key)
                    ) as group:
                        for item in scenario.fields:
                            label = item.label + (" *" if item.required else "")
                            field_boxes[item.key] = gr.Textbox(
                                label=label,
                                placeholder=item.placeholder,
                                lines=item.lines,
                                interactive=True,
                            )
                    field_groups[scenario.key] = group

                tone_radio = gr.Radio(
                    choices=prompts.tones(),
                    value=default_scenario.default_tone,
                    label="语气",
                    interactive=True,
                )
                generate_btn = gr.Button("生成", variant="primary")

            # ---------- 右栏：结果 ----------
            with gr.Column():
                output_box = gr.Textbox(
                    label="生成结果（可编辑、可复制）",
                    placeholder=OUTPUT_PLACEHOLDER,
                    lines=20,
                    max_lines=40,
                    show_copy_button=True,
                    interactive=True,
                )
                output_status = gr.Markdown(STATUS_IDLE)

        field_inputs = [field_boxes[key] for key in field_keys]

        # ---- 场景切换：显示对应字段，并同步该场景的默认语气 ----
        def on_scenario_change(value: str) -> list[Any]:
            try:
                scenario = prompts.resolve_scenario(value)
            except KeyError:
                scenario = prompts.resolve_scenario(prompts.DEFAULT_SCENARIO)
            visibility = [
                gr.update(visible=(scenario.key == key)) for key in field_groups
            ]
            return [*visibility, gr.update(value=scenario.default_tone)]

        scenario_dropdown.change(
            fn=on_scenario_change,
            inputs=[scenario_dropdown],
            outputs=[*field_groups.values(), tone_radio],
            api_name="scenario_change",
            show_progress="hidden",
        )

        # ---- 流式生成 ----
        generate_btn.click(
            fn=_make_generate_fn(field_keys),
            inputs=[scenario_dropdown, *field_inputs, tone_radio],
            outputs=[output_box, output_status],
            api_name="generate",
        )

    return demo
