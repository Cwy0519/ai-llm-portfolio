# -*- coding: utf-8 -*-
"""Gradio 界面层：只负责收集参数、展示结果、导出文件，不做业务逻辑。"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import gradio as gr

from config import ConfigError, Settings, load_settings
from prompts import GAME_SCENES, method_names, scene_names
from services.generator import Generator, GenerationError, InputError
from services.llm_client import LLMClient, LLMError
from utils.case_model import HEADERS, TestCase, stats_markdown, to_rows
from utils.exporter import export_xlsx
from utils.parser import ParseError

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"
_settings_cache: dict[str, Settings | None] = {"value": None}

SAMPLE = (
    "月卡充值：玩家在商城购买 30 元月卡后，应立即到账 300 钻石，并解锁连续 30 天的每日 100 钻石领取资格；"
    "同一天不能重复购买月卡；月卡剩余天数可以叠加；跨天时按服务器时间刷新可领取状态。"
)

DISCLAIMER = (
    "> 生成结果是**测试设计草稿**：AI 不熟悉你们项目的真实规则，请测试工程师复核后使用。"
    "重点关注数值配置、状态流转与兼容性场景。"
)


def get_settings(force_reload: bool = False) -> Settings:
    """懒加载配置：界面可以先打开，点击生成时才要求 Key。"""
    if force_reload or _settings_cache["value"] is None:
        _settings_cache["value"] = load_settings()
    return _settings_cache["value"]


def on_generate(scene: str, feature: str, methods: list[str], count: int):
    """点击「生成用例」。"""
    try:
        settings = get_settings(force_reload=True)
        settings.check_ready()
        generator = Generator(LLMClient(settings), settings)
        result = generator.generate(scene, feature, methods, int(count))
    except (ConfigError, InputError, GenerationError, LLMError, ParseError) as exc:
        raise gr.Error(str(exc))

    rows = to_rows(result.cases)
    summary = stats_markdown(result.cases, requested=result.requested)
    warn_text = "\n".join(f"- ⚠️ {w}" for w in result.warnings) if result.warnings else ""
    status = f"✅ 生成完成，共 {result.count} 条用例。"
    if warn_text:
        status += f"\n\n**提醒：**\n{warn_text}"

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = EXPORT_DIR / f"测试用例-{scene}-{stamp}.xlsx"
    try:
        export_xlsx(result.cases, path)
        file_update = gr.update(value=str(path), visible=True, label=f"下载 Excel：{path.name}")
    except Exception as exc:  # noqa: BLE001 - 导出失败不应吞掉已生成的用例
        file_update = gr.update(value=None, visible=False)
        status += f"\n\n⚠️ 导出 Excel 失败：{exc}（用例仍可在表格中查看）"

    return rows, summary, status, file_update, result.cases


def on_export_only(cases: list[TestCase]):
    """不重新生成，直接把当前表格内容导出。"""
    if not cases:
        raise gr.Error("还没有用例可以导出，请先生成。")
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = EXPORT_DIR / f"测试用例-导出-{stamp}.xlsx"
    export_xlsx(cases, path)
    return gr.update(value=str(path), visible=True, label=f"下载 Excel：{path.name}")


def build_ui(settings: Settings | None = None) -> gr.Blocks:
    if settings is not None:
        _settings_cache["value"] = settings

    with gr.Blocks(title="AI 游戏测试用例生成器") as demo:
        gr.Markdown(
            "# 🎮 AI 游戏测试用例生成器\n"
            "填写游戏功能点，自动生成带**优先级 / 用例类型 / 设计方法 / 前置条件 / 操作步骤 / 预期结果**的标准用例表，"
            "一键导出 Excel。"
        )

        with gr.Row():
            with gr.Column(scale=2):
                scene = gr.Dropdown(scene_names(), value="充值付费", label="游戏场景")
                feature = gr.Textbox(
                    label="要测试的功能（越具体越好）",
                    lines=6,
                    value=SAMPLE,
                    placeholder="例如：月卡购买后立即到账，同一天不可重复购买……",
                )
                methods = gr.CheckboxGroup(
                    method_names(),
                    value=["等价类划分", "边界值分析", "场景法", "错误推测法"],
                    label="用例设计方法（至少选一种）",
                )
                count = gr.Slider(5, 30, value=12, step=1, label="生成数量")
                with gr.Row():
                    run_btn = gr.Button("生成用例", variant="primary", scale=3)
                    export_btn = gr.Button("重新导出 Excel", scale=2)
                status = gr.Markdown("填写左侧内容后点击「生成用例」。")
            with gr.Column(scale=3):
                table = gr.Dataframe(
                    headers=list(HEADERS),
                    datatype=["str"] * len(HEADERS),
                    label="用例表（生成后自动填充，可选中复制）",
                    wrap=True,
                    interactive=False,
                    max_height=520,
                )
                summary = gr.Markdown()
                download = gr.File(label="下载 Excel", visible=False)

        cases_state = gr.State([])

        gr.Examples(
            examples=[
                ["充值付费", SAMPLE, ["等价类划分", "边界值分析", "场景法"], 10],
                ["战斗与技能", "角色释放大招后进入 8 秒冷却，冷却期间再次点击应提示且不重复扣蓝。",
                 ["边界值分析", "错误推测法"], 8],
                ["断线重连", "战斗副本中网络中断 10 秒后重连，应恢复到原关卡原血量，且不重复结算掉落。",
                 ["场景法", "错误推测法"], 8],
            ],
            inputs=[scene, feature, methods, count],
        )
        gr.Markdown(DISCLAIMER)

        run_btn.click(
            on_generate,
            inputs=[scene, feature, methods, count],
            outputs=[table, summary, status, download, cases_state],
        )
        export_btn.click(on_export_only, inputs=[cases_state], outputs=[download])

    return demo


