"""提示词模板：整个项目的"大脑"其实就在这里。

提示词的四个要素（答辩可以直接背）：
    1. 角色——你希望模型以什么身份工作（专业译者 / 中文编辑）
    2. 任务——具体要它做什么
    3. 约束——不许做什么（不许解释、不许加前缀、必须按术语表）
    4. 输出格式——只要译文本身

单独放一个文件的好处：调 prompt 是最高频的操作，改这里不用碰界面和网络代码。
"""

# 界面下拉框里可选的目标语言
TARGET_LANGS = ["英文", "中文", "日文", "韩文", "法文", "德文", "西班牙文"]

# 润色时的风格选项
POLISH_STYLES = ["简洁清晰", "书面正式", "口语自然"]


def build_translate_messages(text: str, target_lang: str, glossary: str = "") -> list[dict]:
    """生成"翻译"任务的对话消息。

    返回的是 OpenAI 格式的消息列表：先一条 system（设定身份和规则），
    再一条 user（真正要处理的文本）。这个格式所有兼容 OpenAI 的平台都认。
    """
    # 注意：Gradio 里没有填过的输入框传进来是 None，不是 ""，
    # 所以这里必须用 (glossary or "") 兜一下，否则会报 NoneType 错误。
    glossary_block = (glossary or "").strip() or "（无）"

    system = (
        f"你是一名专业译者，擅长把各种语言准确翻译成{target_lang}。\n"
        "请严格遵守以下规则：\n"
        f"1. 只输出{target_lang}译文，不要输出原文，不要解释，"
        "不要在开头加“译文：”“以下是翻译：”之类的话。\n"
        "2. 保留原文的段落划分和换行位置。\n"
        "3. 术语表里出现的词，必须使用术语表给出的译法。\n"
        f"4. 如果原文本身已经是{target_lang}，请原样返回，不要改写。\n\n"
        "术语表（源词 => 目标词）：\n"
        f"{glossary_block}"
    )

    user = f"请翻译下面的文本：\n\n{text}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_polish_messages(text: str, style: str = "简洁清晰") -> list[dict]:
    """生成"润色"任务的消息：不改变意思，只改表达。"""
    system = (
        "你是一名资深中文编辑，负责润色文字。\n"
        "请严格遵守以下规则：\n"
        "1. 不改变原文意思，不增加原文没有的信息，不删掉关键信息。\n"
        "2. 只输出润色后的正文，不要解释改了什么，不要加“润色后：”之类的前缀。\n"
        "3. 保留原文的段落划分。\n"
        f"4. 语言风格：{style}。\n"
    )
    user = f"请润色下面的文字：\n\n{text}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
