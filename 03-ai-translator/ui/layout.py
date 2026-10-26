"""界面布局 + 事件绑定。

这一层是"最薄"的一层：它不写任何业务逻辑，
只做三件事——摆组件、把按钮接到函数上、把异常变成提示条。
"""

import gradio as gr

from config import Settings, config_problem
from prompts import POLISH_STYLES, TARGET_LANGS
from services.llm_client import LLMError
from services.translator import MODE_TRANSLATE, MODES, process
from utils.text_split import count_chars

# 少量自定义样式：
# Gradio 6 默认把页面内容限制在 768px，左右两栏会挤成上下两行，
# 所以这里把几层容器的宽度限制统一放开，再给一个舒服的最大宽度。
CSS = """
gradio-app { display: block !important; width: 100% !important; }
.gradio-container { width: 100% !important; max-width: 1180px !important; margin: 0 auto !important; }
.gradio-container .main.fillable { width: 100% !important; max-width: 1180px !important; }
.gradio-container .app { width: 100% !important; }
#status-box { min-height: 1.6em; }
"""

_HELP = """
1. 把要处理的文字粘贴到左上角的「原文」框。
2. 选目标语言和模式：
   - **翻译**：把原文翻成目标语言；
   - **润色**：不改意思，只让表达更通顺（不需要选语言）；
   - **翻译 + 润色**：先翻译，再把译文润色一遍（最慢，效果通常最好）。
3. 需要固定译法时，展开「高级选项」，在术语表里一行写一条 `源词=译词`。
4. 点「开始」，结果会边生成边出现在右边；状态栏会显示进度。
"""


def build_ui(settings: Settings) -> gr.Blocks:
    """搭建界面。settings 从外面传进来，界面自己不去读环境变量。"""

    def on_run(text, target_lang, mode, glossary, bilingual, style, temperature):
        """点击「开始」后执行的生成器。

        它把 process() 吐出来的每一小块直接转交给界面，
        所以用户能看到文字一段一段地流出来。
        """
        # 第一道检查：没配 key 就不要发请求，直接给一句人话提示
        problem = config_problem(settings)
        if problem:
            gr.Warning(problem)
            yield "", "⚠️ " + problem
            return

        last_output = ""
        try:
            for output, status in process(
                text=text,
                target_lang=target_lang,
                mode=mode,
                glossary=glossary,
                bilingual=bilingual,
                settings=settings,
                temperature=temperature,
                style=style,
            ):
                last_output = output
                yield output, status

        except (LLMError, ValueError) as e:
            # 这两类是"预料之中的错误"，把原话显示给用户
            gr.Warning(str(e))
            yield last_output, "❌ " + str(e)

        except Exception as e:  # noqa: BLE001 —— 兜底，绝不让界面白屏
            gr.Warning("出现意外错误，详情见启动程序的终端窗口。")
            yield last_output, f"❌ 意外错误：{type(e).__name__}: {e}"

    def on_clear():
        return "", "", "就绪"

    # fill_width=True：Gradio 6 默认把内容限制在 768px 宽，
    # 左右两栏会挤成上下两行；打开它才能铺满，再配合 CSS 限制最大宽度。
    with gr.Blocks(title="AI 翻译与润色工具", fill_width=True) as demo:
        gr.Markdown(
            "# AI 翻译与润色工具\n"
            "粘贴原文 → 选语言和模式 → 点「开始」。"
            "支持长文本自动分段、术语表固定译法、双语对照。"
        )

        with gr.Row():
            # ---------------- 左：输入区 ----------------
            with gr.Column(scale=5, min_width=360):
                src = gr.Textbox(
                    label="原文",
                    lines=10,
                    max_lines=24,
                    placeholder="在这里粘贴要翻译或润色的文字…",
                    buttons=["copy"],
                )
                counter = gr.Markdown("字数：0")

                with gr.Row():
                    lang = gr.Dropdown(
                        choices=TARGET_LANGS, value="英文",
                        label="目标语言", scale=1,
                    )
                    mode = gr.Radio(
                        choices=MODES, value=MODE_TRANSLATE,
                        label="模式", scale=2,
                    )

                with gr.Accordion("高级选项（术语表 / 风格 / 随机性）", open=False):
                    glossary = gr.Textbox(
                        label="术语表：每行一条，格式为「源词=译词」",
                        lines=3,
                        placeholder="大模型=large language model\n提示词=prompt",
                    )
                    style = gr.Dropdown(
                        choices=POLISH_STYLES, value="简洁清晰",
                        label="润色风格（仅在润色时生效）",
                    )
                    bilingual = gr.Checkbox(label="输出双语对照", value=False)
                    temp = gr.Slider(
                        minimum=0.0, maximum=1.0, step=0.1, value=0.3,
                        label="temperature：越低越稳定，越高越发散",
                    )

                with gr.Row():
                    run_btn = gr.Button("开始", variant="primary", scale=3)
                    clear_btn = gr.Button("清空", scale=1)

                with gr.Accordion("使用说明", open=False):
                    gr.Markdown(_HELP)

                gr.Examples(
                    label="点一下试试",
                    examples=[
                        ["Gradio is a Python library that lets you build web apps "
                         "for machine learning with just a few lines of code.", "中文", "翻译"],
                        ["我们这个项目主要是想解决，就是那个，长文本翻译的时候，"
                         "前后用语不一致的这么一个问题。", "中文", "润色"],
                    ],
                    inputs=[src, lang, mode],
                )

            # ---------------- 右：输出区 ----------------
            with gr.Column(scale=6, min_width=380):
                dst = gr.Textbox(
                    label="结果", lines=22, max_lines=40, buttons=["copy"],
                )
                status = gr.Markdown("就绪", elem_id="status-box")

        # ---------------- 事件绑定 ----------------
        run_btn.click(
            fn=on_run,
            inputs=[src, lang, mode, glossary, bilingual, style, temp],
            outputs=[dst, status],
        )
        clear_btn.click(fn=on_clear, inputs=None, outputs=[src, dst, status])
        src.change(fn=lambda s: f"字数：{count_chars(s)}", inputs=src, outputs=counter)

    return demo
