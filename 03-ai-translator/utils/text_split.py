"""长文本切分：把一整篇文字切成若干"不超过 max_chars 字"的小段。

为什么要切？——这是本项目最关键的技术点，答辩必讲：
    1. 模型有上下文长度上限，输入太长会直接报错；
    2. 就算没超限，长文本翻译到后面会"忘掉"前面的风格，术语前后不一致；
    3. 切成小段后可以边翻边显示，用户不用干等。

切分策略是"从粗到细，能不分就不分"：
    先按空行分段  →  段还是太长就按句子切  →  单句还超长才硬切
    这样做的好处是尽量不把一句话拦腰截断，译文不会断头断尾。
"""

import re

# 这些符号出现在句尾，可以在它们后面断开
_SENT_END = "。！？!?；;…"
# 正则里的 (?<=...) 是"零宽断言"：只在标点之后切，标点本身留在前一句里
_SENT_SPLIT = re.compile(f"(?<=[{_SENT_END}])")


def split_text(text: str, max_chars: int = 1200) -> list[str]:
    """把 text 切成若干段，每段长度尽量不超过 max_chars。

    返回的是字符串列表；空输入返回空列表。
    """
    text = (text or "").strip()
    if not text:
        return []
    if max_chars <= 0:            # 配置成 0 或负数表示不切分
        return [text]

    chunks: list[str] = []
    for block in text.split("\n\n"):        # 第一层：按空行分段
        block = block.strip("\n")
        if not block.strip():
            continue
        if len(block) <= max_chars:
            chunks.append(block)            # 这一段不长，直接用
        else:
            chunks.extend(_split_block(block, max_chars))   # 太长，进第二层
    return chunks


def _split_block(block: str, max_chars: int) -> list[str]:
    """段内切分：先按句子切成小片，再把小片贪心地拼到不超过上限。"""
    pieces = [p for p in _SENT_SPLIT.split(block) if p.strip()]

    out: list[str] = []
    buf = ""
    for piece in pieces:
        # 单句就超过上限：只能硬切，保证任何一段都不超限
        while len(piece) > max_chars:
            if buf:
                out.append(buf)
                buf = ""
            out.append(piece[:max_chars])
            piece = piece[max_chars:]

        if len(buf) + len(piece) <= max_chars:
            buf += piece               # 还装得下，继续往当前段里塞
        else:
            if buf:
                out.append(buf)        # 装不下了，把当前段收走
            buf = piece

    if buf:
        out.append(buf)

    return [c for c in out if c.strip()] or [block]


def count_chars(text: str) -> int:
    """统计字数：去掉所有空白字符后再数，比 len() 更符合直觉。"""
    return len(re.sub(r"\s", "", text or ""))
