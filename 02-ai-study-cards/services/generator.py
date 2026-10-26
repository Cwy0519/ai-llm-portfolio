"""业务编排层：把"分段 → 拼提示词 → 调模型 → 解析 → 合并"串成一条流水线，
并且让多种卡片同时生成。

这是整个项目的中枢。它不认识 Gradio，也不认识 openai 的具体细节，
只依赖 config / prompts / llm_client / utils 这几个更底层的模块。

两个关键设计（答辩重点）：
    1. 分段：材料长就按段落切开，避免超上下文，也避免模型"顾头不顾尾"；
    2. 并行：5 种卡片互不依赖，用线程池同时请求。
       大模型请求是网络 IO，Python 线程在等网络时会释放 GIL，
       所以用线程池就够了，不需要 asyncio 也不会被 GIL 卡住。
       总耗时约等于最慢的那一个，而不是五个相加。

本文件用到的 Python 知识（答辩时指着某一行，先报名字再解释）：
    1.  @dataclass / 字段类型提示      —— 自动生成 __init__ 的数据类
    2.  field(default_factory=list)    —— 给可变默认值（列表）的正确写法
    3.  X | None 联合类型 / 默认值参数  —— 类型提示 + "可以不传"
    4.  time.perf_counter()            —— 高精度计时，用来算耗时
    5.  生成器函数 yield               —— 函数变成"可以边算边交结果"的生成器
    6.  typing.Iterator[...]           —— 标注"这是一个迭代器/生成器"
    7.  ThreadPoolExecutor 线程池       —— 同时跑多个"等网络"的任务
    8.  pool.submit(...) / Future      —— 把任务丢进池子，拿到"提货单"
    9.  as_completed(futures)          —— 谁先完成先交谁
    10. 字典推导式 {k: v for ...}       —— 一边遍历一边建字典
    11. enumerate(可迭代对象, 起始值)   —— 同时拿到序号和元素
    12. try / except 具体异常           —— 只接住自己认识的错误
    13. break / return / continue      —— 跳出循环 / 结束函数 / 跳过本轮
    14. 字符串 += 拼接 / str.join      —— 把多段文字接起来
    15. max() / min() 嵌套             —— 把数值"夹"在区间里
"""

# 【import 导入模块】导入 time，用 time.perf_counter() 精确测一段代码跑了多久
import time
# 【from ... import ...】从标准库 concurrent.futures 里拿两个东西：
#   ThreadPoolExecutor —— 线程池，负责"同时跑多个任务"
#   as_completed       —— 迭代器，负责"按完成先后把结果交出来"
from concurrent.futures import ThreadPoolExecutor, as_completed
# 【from ... import ...】dataclass 是装饰器，field 用来给字段设置更细的规则
from dataclasses import dataclass, field
# 【typing 模块】Iterator 是类型提示用的"迭代器"类型，只给人看/给 IDE 看
from typing import Iterator

# 【项目内导入】Settings 是配置对象（dataclass），一路往下传
from config import Settings
# 【项目内导入】CARD_TYPES 是"卡片名 → CardType 说明书"的字典；
#   CardType 是卡片说明书的数据类；build_messages 负责拼提示词
from prompts import CARD_TYPES, CardType, build_messages
# 【项目内导入】LLMClient 是网络层，LLMError 是它抛出的"人话版"异常
from services.llm_client import LLMClient, LLMError
# 【from ... import (...) 小括号多行导入】一次导入多个名字，括号让它们可以分行写
from utils.cards import (
    CardsParseError,
    extract_json,
    merge_parts,
    normalize,
    render_markdown,
)
# 【项目内导入】split_text 负责把长材料切成不超过 max_chars 的小段
from utils.text_split import split_text


# 【装饰器 @dataclass】写在 class 上一行，作用是"自动生成 __init__"
#   只要在类里写"字段名: 类型"，dataclass 就会帮你生成
#   __init__(self, key, ok, markdown="", ...)，不用自己一行行赋值
@dataclass
class GenerationResult:
    """一种卡片的生成结果。界面拿到它就知道该填哪个 Tab、要不要报错。"""

    # 【带类型提示的字段】key: str 就是"这个字段叫 key，类型是字符串"
    #   dataclass 会按"从上到下"的顺序把这些字段做成构造参数，所以顺序有意义
    key: str
    # 【bool 字段】ok=True 表示这类卡片生成成功，False 表示失败
    ok: bool
    # 【字段默认值】= "" 表示不传就用空字符串；有默认值的字段必须排在没默认值的后面
    markdown: str = ""
    # 【字段默认值】标题，模型没给就用空串
    title: str = ""
    # 【field(default_factory=list)】这是给"可变默认值"的正确写法
    #   如果写成 items: list[dict] = []，这个列表会被所有实例共用（Python 的著名坑），
    #   一个对象往里 append，其它对象也跟着变；default_factory=list 表示
    #   "每次创建对象时调用一次 list() 造一个新列表"，各用各的
    items: list[dict] = field(default_factory=list)
    # 【字段默认值】错误提示文字，成功时是空串
    error: str = ""
    # 【字段默认值】耗时秒数，0.0 是浮点数写法（0.0 比 0 更明确表达"这是秒"）
    seconds: float = 0.0


# 【def 函数 + 多行参数】参数太多时，可以用小括号把参数列表拆成多行，更好读
def generate_one(
    # 【参数 + 类型提示】settings：配置对象；text：这段学习材料
    settings: Settings,
    text: str,
    # 【参数】card：CardType 对象，里面有 key/label/rules 等写作要求
    card: CardType,
    # 【默认参数】level="进阶"：调用时不传就用"进阶"
    level: str = "进阶",
    # 【默认参数】count=4：每种卡片默认生成 4 张
    count: int = 4,
    # 【X | None 联合类型】表示"要么是 LLMClient，要么是 None"
    #   默认 None 的意思是"没传就自己新建一个"（见函数体第一行）
    client: LLMClient | None = None,
# 【返回值类型提示】-> GenerationResult：返回一个 GenerationResult 对象
) -> GenerationResult:
    """生成一种卡片。材料太长时自动分段，最后合并成一份结果。"""
    # 【time.perf_counter】返回一个高精度的时间点（秒），专门用来算"过了多久"
    #   为什么不用 time.time()？perf_counter 不受系统改时间影响，测耗时更准
    start = time.perf_counter()
    # 【or 短路技巧】client or LLMClient(settings)：
    #   如果 client 不是 None（真值），就直接用它；是 None 才新建一个
    #   好处：调用方想复用同一个客户端就传进来，不想管就让它自己建
    client = client or LLMClient(settings)
    # 【函数调用】把材料切成若干段，每段不超过 max_chars 字；返回字符串列表
    chunks = split_text(text, settings.max_chars)

    # 【带类型提示的变量】parts 存每段解析出来的卡片数据（每个元素是字典）
    #   这里必须先赋值再用，Python 不会自动声明变量
    parts: list[dict] = []
    # 【列表】warnings 存"某一段失败了"的提示，最后拼进 Markdown
    warnings: list[str] = []

    # 【for + enumerate】enumerate(chunks, 1)：同时拿到"第几段 i"（从 1 开始）和"这一段内容"
    #   起始值写 1，是因为提示词里要告诉模型"这是第 1/3 段"，人读着更自然
    for i, chunk in enumerate(chunks, 1):
        # 【函数调用】拼提示词：材料 + 卡片要求 + 难度 + 数量 + 第几段/共几段
        #   build_messages 返回 OpenAI 格式的消息列表
        messages = build_messages(chunk, card, level, count, i, len(chunks))

        # 第一步：请求模型（这里出问题通常是网络、Key、限流）
        # 【try/except 具体异常】只包住"可能失败的那一行"，范围小才好定位问题
        try:
            # 【调用对象方法】client.complete(messages) 发请求，返回模型输出的纯文本
            raw = client.complete(messages)
        # 【except 具体异常 as e】只接住 LLMClient 抛的 LLMError，别的异常继续往上冒
        except LLMError as e:
            # 【if 真值判断】空列表 [] 在 Python 里算"假"，not parts 就是"一张还没生成出来"
            if not parts:            # 第一段就失败：这种卡片整体算失败
                # 【提前 return】直接造一个"失败结果"返回；注意这里没有 raise，
                #   因为上层是并行执行的，抛出去会把整批都搞崩
                return GenerationResult(
                    # 【关键字参数】构造对象时写明参数名，比按位置传更好读
                    key=card.key, ok=False, error=str(e),
                    # 【算耗时】当前时间 - 开始时间 = 这段代码花了多少秒
                    seconds=time.perf_counter() - start,
                )
            # 后面某段失败：保留已经生成的部分，提示一下就好，别让用户白等
            # 【f-string + 列表 append】把"第几段失败、原因是什么"记进 warnings
            warnings.append(f"第 {i}/{len(chunks)} 段失败：{e}")
            # 【break 跳出循环】后面的段落不再尝试，直接去合并"已经拿到的部分"
            #   为什么是 break 不是 continue？因为对长材料来说，后面的段通常也连不上，
            #   硬试只会让用户等更久
            break

        # 第二步：解析 JSON（这里出问题说明模型没按格式返回）
        # 【嵌套 try/except】再包一层，是因为"网络失败"和"格式不对"要区别对待
        try:
            # 【函数嵌套调用】先把文本抠成字典（extract_json），再校验收拢（normalize），
            #   最后 append 到 parts；一行里套了三层调用，从里往外读
            parts.append(normalize(extract_json(raw)))
        # 【except CardsParseError】只接住"解析不了"这种异常
        except CardsParseError as e:
            # 【if 真值判断】还是一张都没成功，走降级分支
            if not parts:
                # 降级：内容可能仍有价值，直接显示原文，比让用户白等一次好
                # 【关键设计】注意这里 ok=True：虽然格式不对，但"拿到了内容"，
                #   所以仍然把它显示出来，只是把 error 一起带上，界面可以提示
                return GenerationResult(
                    key=card.key,
                    ok=True,
                    # 【调用本文件的私有函数】把模型原文包成一段 Markdown
                    markdown=_fallback_markdown(card, raw, level, e),
                    error=str(e),
                    seconds=time.perf_counter() - start,
                )
            # 【f-string】已经有部分成功了：记一条警告，保留现有结果
            warnings.append(f"第 {i}/{len(chunks)} 段格式不对：{e}")
            # 【break】同样不再尝试后面的段，先保住已有的成果
            break

    # 【函数调用】把多段结果合并成一份：标题取第一段的，items 全部拼起来
    data = merge_parts(parts)
    # 【函数调用】把结构化数据渲染成 Markdown 文本
    markdown = render_markdown(card, data, level)
    # 【if 真值判断】warnings 非空说明前面有段落失败了
    if warnings:
        # 【+= 累加赋值 + str.join】markdown += ... 等价于 markdown = markdown + ...
        #   "；".join(warnings) 用中文分号把多条警告连成一句
        markdown += "\n> ⚠️ " + "；".join(warnings) + "，已保留前面生成的部分。\n"

    # 【return 构造对象】成功结果：把标题、卡片列表、耗时一起交回给上层
    return GenerationResult(
        key=card.key,
        ok=True,
        markdown=markdown,
        # 【字典取值】data["title"] 一定能取到，因为 merge_parts 保证了有默认值
        title=data["title"],
        items=data["items"],
        seconds=time.perf_counter() - start,
    )


# 【私有函数】_ 开头表示"只在本文件用"，外部不要依赖它
def _fallback_markdown(card: CardType, raw: str, level: str, reason: Exception) -> str:
    """模型没按 JSON 返回时的降级输出：至少把它说的话原样交给用户。"""
    # 【or 兜底 + strip】raw 可能是 None，先换成 ""，再去掉首尾空白
    snippet = (raw or "").strip()
    # 【len 判断】太长的原文直接显示会把界面撑爆，所以要截断
    if len(snippet) > 3000:
        # 【切片 + 拼接】snippet[:3000] 取前 3000 个字符，后面加一句说明
        #   注意：这里会给用户看到"内容被截断了"，比悄悄丢内容更诚实
        snippet = snippet[:3000] + "\n……（内容太长，已截断）"
    # 【return 括号续行 + 隐式字符串拼接】圆括号里的多段字符串会自动接成一段
    #   f 开头的段会替换 {} 里的变量，没有 f 的段就是原样文字
    return (
        f"### {card.emoji} {card.label} · {level}\n\n"
        f"> ⚠️ 模型这次没有按 JSON 格式返回（{reason}）。"
        "下面直接显示它的原始文本，可以手动整理，或者再生成一次。\n\n"
        f"---\n\n{snippet}\n"
    )


# 【def 定义函数】这是并行版的"生成多种卡片"
# 【生成器函数】函数体里一旦出现 yield，这个函数就变成"生成器函数"：
#   调用它不会立刻执行，而是返回一个生成器对象，用 for / next() 才会一段段往下跑
def generate_many(
    settings: Settings,
    text: str,
    # 【参数类型】card_keys 是"卡片名"组成的列表，比如 ["qa", "cloze"]
    card_keys: list[str],
    level: str = "进阶",
    count: int = 4,
    client: LLMClient | None = None,
# 【返回类型 Iterator[...]】提示"这是一个迭代器"，每次 next() 交出一个 GenerationResult
) -> Iterator[GenerationResult]:
    """并行生成多种卡片，谁先完成就先 yield 谁。

    界面收到一个就填一个 Tab，用户不用等全部做完才看到结果。
    """
    # 【or 兜底 + strip】text 可能是 None，先换空串；去掉首尾空白
    text = (text or "").strip()
    # 【if 真值判断】空字符串算"假"，直接报错让界面提示用户
    if not text:
        # 【raise ValueError】参数不合法就抛内置的 ValueError，上层用 try 接住
        raise ValueError("学习材料是空的。请先粘贴一段材料，或上传一个 .txt 文件。")

    # 【函数嵌套 + 夹逼】int(count or 4)：count 是 None/0 就先用 4；
    #   min(10, x) 把上限压到 10，max(1, x) 把下限抬到 1——保证在 1~10 之间
    count = max(1, min(10, int(count or 4)))
    # 【列表推导式】从 card_keys 里挑出"真的存在"的卡片名，再去 CARD_TYPES 取说明书
    #   写成 if key in CARD_TYPES 是为了防止界面传来不认识的键，直接 KeyError
    cards = [CARD_TYPES[key] for key in card_keys if key in CARD_TYPES]
    # 【if 真值判断】一个有效卡片都没选，报错
    if not cards:
        # 【raise 抛异常】一个有效类型都没选，提前拦住，不浪费模型调用
        raise ValueError("请至少选择一种卡片类型。")

    # 【or 兜底】没传客户端就自己建一个；建好后所有线程共用同一个（省重复握手）
    client = client or LLMClient(settings)
    # 【min()】并发数取"4"和"卡片数"里的小值
    workers = min(4, len(cards))     # 并发别开太大，否则容易触发平台限流

    # 【with 语句 + 线程池】with 会在代码块结束时自动调用 pool.shutdown() 收尾
    #   为什么用线程池而不是多进程？因为瓶颈是"等网络"，线程足够；
    #   Python 线程在等网络 IO 时会释放 GIL，所以能真正并发，不会被 GIL 卡住
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # 【字典推导式】{键: 值 for ...} 一边遍历一边建字典
        #   键是 pool.submit(...) 返回的 Future（"提货单"，代表未来才会有结果）；
        #   值是这张卡片对象——这样拿到 Future 就能知道它对应哪种卡片
        future_to_card = {
            # 【submit 提交任务】pool.submit(函数, 参数1, 参数2, ...)：
            #   把 generate_one 丢给线程池去跑，位置参数按顺序传进去
            pool.submit(generate_one, settings, text, card, level, count, client): card
            # 【字典推导式的 for】遍历每一种卡片，各提交一个任务
            for card in cards
        }
        # 【as_completed】传入一堆 Future，它"谁先完成就先交出谁"，
        #   所以用户会先看到最快的那类卡片，而不是按提交顺序干等
        for future in as_completed(future_to_card):
            # 【字典取值】用 Future 反查它对应哪种卡片（Future 对象可哈希，能当键）
            card = future_to_card[future]
            # 【try/except】单个卡片崩了不能拖垮整批，所以这里再兜一层
            try:
                # 【yield 交出结果】future.result() 取出任务的返回值（或者重新抛出任务里的异常）；
                #   yield 把它交给调用方，然后函数在这里"暂停"，等下一次迭代再继续
                yield future.result()
            # 【except Exception 兜底】连"意料之外的错误"也接住，转成失败结果
            except Exception as e:  # noqa: BLE001 —— 一种卡片崩了不能拖垮其它卡片
                # 【yield】失败也交出一个结果对象，界面照样能显示"这一类失败了"
                # 【type(e).__name__】取出异常类名（比如 KeyError），便于排查
                yield GenerationResult(
                    key=card.key,
                    ok=False,
                    error=f"意外错误：{type(e).__name__}: {e}",
                )
