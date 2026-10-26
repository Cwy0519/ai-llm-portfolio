"""长文本切分：把一整篇材料切成若干"不超过 max_chars 字"的小段。

为什么要切？——这是本项目最关键的技术点之一，答辩必讲：
    1. 模型有上下文长度上限，材料太长会直接报错或截断；
    2. 就算没超限，长材料一次生成也容易"顾头不顾尾"，后面的内容被忽略；
    3. 切成小段后，每段单独出卡，最后把卡片合并起来，稳定性好很多。

切分策略是"从粗到细，能不分就不分"：
    先按空行分段  →  段还是太长就按句子切  →  单句还超长才硬切
    这样做的好处是尽量不把一句话拦腰截断。

本文件用到的 Python 知识（答辩时随便指一处，先报名字再解释）：
    1. re.compile 预编译正则           —— 正则编译一次，后面反复用
    2. 零宽断言 (?<=...)               —— 只"要求前面是标点"，不消耗任何字符
    3. f-string 拼出正则字符组 [...]    —— 把一串标点放进字符组当"任选其一"
    4. 函数默认参数                    —— max_chars: int = 2500
    5. str.split("分隔符")             —— 按分隔符把字符串切成列表
    6. 列表推导式 + if 过滤            —— [x for x in ... if 条件]
    7. list.append / list.extend       —— 追加一个 vs 批量追加
    8. while 循环 + 切片               —— 单句超长时反复硬切
    9. 字符串 += 累加（缓冲区思想）      —— buf 攒够一段再收走
    10. or 兜底 + 提前 return           —— 空输入直接返回空列表
    11. re.sub 删除字符 + len           —— 去掉空白后数"字数"
    12. 类型提示 list[str]              —— 声明"返回的是字符串列表"
"""

# 【import 导入模块】re 正则库：既要 split（按模式切），也要 sub（按模式替换）
import re

# 【模块级常量】全大写命名是"约定"（不是语法强制），表示这段程序别去改它；
#   这个字符串里的每一个字符都算一种"句末标点"。
# 这些符号出现在句尾，可以在它们后面断开
_SENT_END = "。！？!?；;…"
# 【re.compile + f-string 拼正则】这一行是本文件的技术核心。
#   f"(?<=[{_SENT_END}])" 拼出来是 (?<=[。！？!?；;…]) —— 一个字符组。
#   (?<=...) 叫"零宽断言（后顾断言）"：它只检查"当前位置的前面是不是这些标点"，
#   匹配到的长度是 0，所以按它切分时标点不会被扔掉，会留在前一句的结尾。
#   如果直接把标点丢进字符组去 split，标点会被当成分隔符删掉，句子就"断头"了。
# 正则里的 (?<=...) 是"零宽断言"：只在标点之后切，标点本身留在前一句里
_SENT_SPLIT = re.compile(f"(?<=[{_SENT_END}])")


# 【def 函数 + 默认参数】max_chars 不传就按 2500 字切；返回"字符串组成的列表"
def split_text(text: str, max_chars: int = 2500) -> list[str]:
    """把 text 切成若干段，每段长度尽量不超过 max_chars。

    返回字符串列表；空输入返回空列表。
    """
    # 【or 兜底 + strip】text 可能是 None，先用空串顶上，再去掉首尾空白
    text = (text or "").strip()
    # 【真值判断 + 提前 return】空字符串算"假"，没内容就返回空列表，不再往下走
    if not text:
        # 【提前 return】没有内容就返回空列表，不再往下切
        return []
    # 【边界处理】配成 0 或负数表示"不切分"，整篇当成一段
    if max_chars <= 0:            # 配置成 0 或负数表示不切分
        # 【返回单元素列表】注意返回 [text] 而不是 text，类型要始终是"列表"
        return [text]

    # 【类型提示 + 空列表】结果容器：里面装切好的每一段
    chunks: list[str] = []
    # 【str.split 按空行切】"\n\n"（两个换行）就是空行，这是最粗的第一层切分
    for block in text.split("\n\n"):        # 第一层：按空行分段
        # 【strip("\n")】带参数表示"只去掉首尾这些字符"，这里只去换行、保留段内换行
        block = block.strip("\n")
        # 【strip + 真值判断】只有空白字符的块（比如连敲好几个回车）直接跳过
        if not block.strip():
            # 【continue 跳过】这一块只有空白字符，不参与切分
            continue
        # 【len + 数值比较】这一段本来就不长，不用再切
        if len(block) <= max_chars:
            # 【append】原样放进结果：能不分就不分，尽量保持段落完整
            chunks.append(block)            # 这一段不长，直接用
        else:
            # 【extend + 函数调用】把 _split_block 返回的多个小段逐个并进来；
            #   这里必须用 extend 而不是 append，否则会变成"列表里套列表"。
            chunks.extend(_split_block(block, max_chars))   # 太长，进第二层
    # 【return】返回切好的段落列表（可能一段，也可能很多段）
    return chunks


# 【def 函数 + 私有命名】开头的下划线 _ 是约定"只在本模块内部用"，
#   但它只是约定，不是语法限制，别处照样能调用。
def _split_block(block: str, max_chars: int) -> list[str]:
    """段内切分：先按句子切成小片，再把小片贪心地拼到不超过上限。"""
    # 【列表推导式 + if 过滤】用上面编译好的正则把大段切成"一句一句"，
    #   同时丢掉纯空白的碎片（切完常会留下 "" 这种空串）。
    #   等价写法：先 pieces = _SENT_SPLIT.split(block)，再 for + if 筛一遍。
    pieces = [p for p in _SENT_SPLIT.split(block) if p.strip()]

    # 【初始化】out 装最终的小段；buf 是"当前正在攒的那一段"（缓冲区思想）
    out: list[str] = []
    # 【初始化缓冲区】buf 是「当前正在攒的那一段」
    buf = ""
    # 【for 遍历】一句一句地往缓冲区里塞
    for piece in pieces:
        # 单句就超过上限：只能硬切，保证任何一段都不超限
        # 【while 循环】一句可能超好几倍，所以要反复切，直到它短于上限
        while len(piece) > max_chars:
            # 【真值判断】缓冲区里还有内容就先收走，免得和硬切出来的段混在一起
            if buf:
                # 【append】把缓冲区当前这一段存进结果
                out.append(buf)
                # 【重新赋值】清空缓冲区，重新开始攒
                buf = ""
            # 【切片】piece[:max_chars] 取前 max_chars 个字符，作为一整段
            out.append(piece[:max_chars])
            # 【切片 + 重新赋值】剩下的部分留给下一轮 while 继续切
            piece = piece[max_chars:]

        # 【长度判断】"当前缓冲区 + 这一句"还装得下吗？（贪心：能塞就塞）
        if len(buf) + len(piece) <= max_chars:
            # 【+= 字符串拼接】装得下就继续往当前段里塞
            buf += piece               # 还装得下，继续往当前段里塞
        else:
            # 【真值判断】缓冲区非空才收走（第一次进来时它是空的）
            if buf:
                # 【append】把攒满的这一段收走
                out.append(buf)        # 装不下了，把当前段收走
            # 【重新开始】把这一句当成新一段的开头
            buf = piece

    # 【循环收尾】循环结束后，缓冲区里最后那一段还没收走，这里补上
    if buf:
        # 【append 收尾】循环结束后，把最后一段收进结果
        out.append(buf)

    # 【列表推导 + or 兜底】再滤一次空白段；万一全被滤光（理论上的极端情况），
    #   就用 or 兜底返回"整段原文"，保证调用方至少拿到一段内容。
    return [c for c in out if c.strip()] or [block]


# 【def 函数 + 类型提示】统计"字数"：先删掉所有空白字符，再数长度
def count_chars(text: str) -> int:
    """统计字数：去掉所有空白字符后再数，比 len() 更符合直觉。"""
    # 【re.sub 删除 + or 兜底 + len】r"\s" 匹配空格、换行、制表符等所有空白，
    #   替换成 "" 等于全部删掉；text 为 None 时用 "" 兜底，避免 re.sub 报错。
    return len(re.sub(r"\s", "", text or ""))
