"""输出清洗：模型经常"不听话"。

即使提示词写了"只输出译文"，模型还是会时不时加一句
"译文：""以下是翻译结果："，或者把结果用引号/代码块包起来。
这一层就是兜底——它不改变译文内容，只把多余的包装剥掉。

这也是答辩里"遇到的困难"的好素材：
提示词约束是第一道防线，代码清洗是第二道防线，两道都要有。

注意：包装可能层层嵌套，比如 `译文：```...``` `，
所以这里用"循环剥壳"，而不是只剥一次。
"""

import re

# 模型最爱加的开头。长串放前面，避免"翻译结果："被"翻译："提前截断
_PREFIXES = (
    "以下是翻译结果：", "以下是译文：", "以下是翻译：", "翻译结果：",
    "润色结果：", "润色后：", "修改后：", "结果：",
    "译文：", "翻译：", "润色：",
    "以下是翻译结果:", "以下是译文:", "以下是翻译:", "翻译结果:",
    "润色结果:", "润色后:", "修改后:", "结果:",
    "译文:", "翻译:", "润色:",
)

# 成对的引号，只有首尾同时出现时才剥掉
_QUOTE_PAIRS = (("“", "”"), ("「", "」"), ("『", "』"), ('"', '"'))


def clean_output(text: str) -> str:
    """把模型返回的原始文本清洗成可以直接展示的正文。"""
    if not text:
        return ""

    t = text.strip()

    # 1) 循环剥壳：前缀和代码块可能互相嵌套，最多剥 3 层，防止死循环
    for _ in range(3):
        before = t
        t = _strip_prefix(t)
        t = _strip_fence(t)
        if t == before:
            break

    # 2) 去掉整体包裹的引号
    for left, right in _QUOTE_PAIRS:
        if len(t) >= 2 and t.startswith(left) and t.endswith(right):
            t = t[1:-1].strip()
            break

    # 3) 去掉每行末尾多余的空格（只去右边，不动行首缩进）
    t = "\n".join(line.rstrip() for line in t.splitlines())

    # 4) 连续 3 个以上换行压成 2 个，避免输出一大片空白
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()


def _strip_prefix(t: str) -> str:
    """去掉开头那句"译文："，只去一个，防止误伤正文。"""
    for prefix in _PREFIXES:
        if t.startswith(prefix):
            return t[len(prefix):].lstrip()
    return t


def _strip_fence(t: str) -> str:
    """去掉 markdown 代码块围栏：开头的 ``` 和结尾的 ```。"""
    t = re.sub(r"^```[A-Za-z]*[ \t]*\n?", "", t)   # ``` 或 ```python 加换行
    t = re.sub(r"\n?```\s*$", "", t)               # 结尾的 ```
    return t.strip()
