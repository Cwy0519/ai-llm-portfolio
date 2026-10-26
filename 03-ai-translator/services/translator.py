"""业务编排层：把"切分 → 拼提示词 → 调模型 → 清洗 → 拼接"串成一条流水线。

这是整个项目的中枢。它不认识 Gradio，也不认识 openai，
只依赖 config / prompts / llm_client / utils 这四个更底层的模块。

为什么 process() 是个"生成器"（yield 而不是 return）？
    因为要边处理边把中间结果显示到界面上。
    每完成一点就 yield 一次，Gradio 收到一次就刷新一次界面——这就是"流式输出"。
"""

from typing import Iterator

from config import Settings
from prompts import build_polish_messages, build_translate_messages
from services.llm_client import stream_chat
from utils.postprocess import clean_output
from utils.text_split import count_chars, split_text

# 三种工作模式（界面上的单选框就是这三项）
MODE_TRANSLATE = "翻译"
MODE_POLISH = "润色"
MODE_BOTH = "翻译 + 润色"
MODES = [MODE_TRANSLATE, MODE_POLISH, MODE_BOTH]


def process(
    text: str,
    target_lang: str,
    mode: str,
    glossary: str,
    bilingual: bool,
    settings: Settings,
    temperature: float | None = None,
    style: str = "简洁清晰",
) -> Iterator[tuple[str, str]]:
    """处理入口。每次 yield 返回 (界面上的正文, 状态栏文字)。

    参数说明：
        text        用户输入的原文
        target_lang 目标语言
        mode        翻译 / 润色 / 翻译 + 润色
        glossary    术语表，每行一条"源词=译词"
        bilingual   是否输出双语对照
        settings    配置对象
        temperature 覆盖配置里的随机性（None 表示用配置值）
        style       润色风格
    """
    text = (text or "").strip()
    glossary = glossary or ""
    style = style or "简洁清晰"
    if not text:
        raise ValueError("输入是空的。请先粘贴一段要处理的文字。")
    if mode not in MODES:
        raise ValueError(f"不认识的模式：{mode}")

    chunks = split_text(text, settings.max_chars)
    total = len(chunks)

    if total > 1:
        yield "", f"文本较长，已按每段不超过 {settings.max_chars} 字切成 {total} 段，开始逐段处理…"

    done: list[tuple[str, str]] = []   # 已完成的段落：(原文, 译文)

    for i, chunk in enumerate(chunks, 1):
        tag = f"[{i}/{total}] " if total > 1 else ""

        # ---------- 第一步：翻译（或直接润色） ----------
        if mode in (MODE_TRANSLATE, MODE_BOTH):
            step = "翻译"
            messages = build_translate_messages(chunk, target_lang, glossary)
        else:
            step = "润色"
            messages = build_polish_messages(chunk, style)

        yield _render(done, chunk, "", bilingual), f"{tag}{step}中…"

        acc = ""
        for delta in stream_chat(settings, messages, temperature):
            acc += delta
            yield _render(done, chunk, acc, bilingual), f"{tag}{step}中… 已生成 {len(acc)} 字"
        result = clean_output(acc)

        # ---------- 第二步：仅"翻译 + 润色"模式，对译文再润色一次 ----------
        if mode == MODE_BOTH:
            yield _render(done, chunk, result, bilingual), f"{tag}润色中…"
            acc2 = ""
            for delta in stream_chat(settings, build_polish_messages(result, style), temperature):
                acc2 += delta
                yield _render(done, chunk, acc2, bilingual), f"{tag}润色中… 已生成 {len(acc2)} 字"
            result = clean_output(acc2)

        done.append((chunk, result))
        yield _render(done, "", "", bilingual), f"{tag}这一段完成（{i}/{total}）"

    yield _render(done, "", "", bilingual), f"完成：共 {total} 段，{count_chars(text)} 字"


def _render(done: list[tuple[str, str]], current_src: str, partial: str,
            bilingual: bool) -> str:
    """把"已完成的结果 + 正在生成的部分"拼成最终显示在界面上的文字。

    done     已经处理完的段落，每项是 (原文, 译文)
    current_src 当前正在处理的原文（双语模式要显示）
    partial  当前这段已经生成的一小部分
    """
    if bilingual:
        blocks = [f"【原文】\n{src}\n\n【译文】\n{dst}" for src, dst in done]
        if current_src:
            blocks.append(f"【原文】\n{current_src}\n\n【译文】\n{partial}")
        return "\n\n---\n\n".join(blocks)

    parts = [dst for _, dst in done]
    if partial:
        parts.append(partial)
    return "\n\n".join(parts)
