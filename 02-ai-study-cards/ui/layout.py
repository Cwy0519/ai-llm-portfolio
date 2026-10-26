"""界面层：界面布局 + 事件绑定。

这一层是"最薄"的一层：它不写任何业务逻辑，只做三件事：
    1. 摆组件（左边输入 / 右边输出）；
    2. 把按钮接到业务函数上；
    3. 把异常变成界面上的中文提示，绝不让页面白屏。

本文件用到的 Python 知识（答辩时随便指一处，先报名字再解释）：
    1.  import / from ... import ...      —— 导入别的文件里的类和函数
    2.  模块级常量 + 类型标注 list[str]    —— 定义"全文件共用、顺序固定"的数据
    3.  三引号字符串                       —— 写多行文本（CSS / 说明文字）
    4.  def 函数 / 参数 / 类型提示           —— 把一段逻辑包起来复用
    5.  嵌套函数 + 闭包                     —— on_generate 直接用到外层的 settings
    6.  生成器函数 yield                   —— 一边算一边把进度推给界面
    7.  dict 字典 / get / 字典推导式          —— "卡片类型 → 内容"的对应关系
    8.  列表推导式 / 生成器表达式             —— 一行生成一个新列表
    9.  元组 + * 星号解包                   —— 一次返回 9 个值（_pack）
    10. 条件表达式 a if 条件 else b          —— 行内的 if
    11. try / except 两层                   —— 先接"预料之中"，再接"意料之外"
    12. raise 主动抛异常                    —— 出问题时把原因说清楚
    13. lambda 匿名函数                     —— 只包含一个表达式的小函数
    14. with 语句 + gr.Blocks/Row/Tabs      —— 收集界面组件、自动管理上下文
    15. 事件绑定 .click / .upload / .change —— 把组件事件接到函数上
    16. pathlib.Path / read_bytes / decode  —— 读文件、看大小
    17. str.join / sum / len                —— 拼接字符串、求和、取长度
    18. None 空值                           —— 表示"没有文件 / 没有内容"
"""

# 【import 导入模块】导入 time，用 time.time() 取"当前时间戳"来算耗时
import time
# 【from ... import ...】从 pathlib 里只拿 Path 这个类，用它表示文件路径
from pathlib import Path

# 【import ... as 起别名】导入 gradio 起短名 gr，后面写 gr.Blocks / gr.Textbox 更省事
import gradio as gr

# 【from ... import ...】从 config.py 拿 Settings 类型（只用来写类型提示）和检查配置的函数
from config import Settings, config_problem
# 【from ... import ...】从 prompts.py 拿"卡片类型字典"和"难度列表"
from prompts import CARD_TYPES, LEVELS
# 【from ... import ...】从 services/generator.py 拿结果类型和"并行生成"函数
from services.generator import GenerationResult, generate_many
# 【from ... import ...】从 services/llm_client.py 拿自定义异常 LLMError
#   拿到它是为了下面能单独接住"调模型失败"这一类错误
from services.llm_client import LLMError
# 【from ... import ...】从 utils/exporter.py 拿"拼整份 Markdown"和"存文件"两个函数
from utils.exporter import build_bundle_markdown, save_bundle
# 【from ... import ...】从 utils/review_plan.py 拿"生成复习计划"的函数
from utils.review_plan import build_plan
# 【from ... import ...】从 utils/text_split.py 拿"数字数"的函数
from utils.text_split import count_chars

# 五种卡片的固定顺序：界面 Tab 顺序、输出顺序都按这个来
# 【模块级变量 + 类型标注】"变量名: 类型 = 值" 只是标注，运行时不会检查
#   list(CARD_TYPES) 把字典的键（qa/cloze/...）按原顺序转成一个列表
TAB_KEYS: list[str] = list(CARD_TYPES)

# 少量自定义样式：
# Gradio 6 默认把页面内容限制在 768px，左右两栏会挤成上下两行，
# 所以这里把几层容器的宽度限制统一放开，再给一个舒服的最大宽度。
# 【三引号多行字符串】三个引号包起来的内容可以换行，原样保存成一段字符串
#   注意：这里面的内容会原封不动交给浏览器，所以在字符串里不能加 # 注释
CSS = """
gradio-app { display: block !important; width: 100% !important; }
.gradio-container { width: 100% !important; max-width: 1280px !important; margin: 0 auto !important; }
.gradio-container .main.fillable { width: 100% !important; max-width: 1280px !important; }
.gradio-container .app { width: 100% !important; }
#status-box { min-height: 1.6em; }
"""

# 【三引号字符串】页面顶部的标题区，写的是 Markdown 语法（# 是标题，** 是加粗）
_HEADER = """
# 📚 AI 学习卡片生成器

输入一段学习材料，一键生成 **问答卡 / 填空题 / 记忆口诀 / 知识要点 / 类比解释** 五种复习资料。
支持难度分级、长文自动分段、多类型并行生成、一键导出 Markdown。
"""

# 【三引号字符串】"使用说明"折叠面板里的内容，纯 Markdown 文本
_HELP = """
1. 把学习材料粘贴到左边「学习材料」框；也可以上传一个 `.txt` / `.md` 文件，内容会自动填进去。
2. 选择**难度**和**每种形式要几张卡**，再勾选要做哪几种形式（**至少 2 种**）。
3. 点「🚀 开始生成」。几种卡片会**同时**生成，完成一种就在右边对应的 Tab 里显示一种。
4. 每个结果框右上角有复制按钮；「复习与导出」Tab 里可以下载整份 Markdown。
5. 生成的文件会自动保存到项目的 `exports/` 目录，文件名带时间戳。

**小贴士**
- 材料越具体、越成体系，生成的卡片越好；只有标题没有内容的材料效果很差。
- 材料很长时会自动分段，调用次数变多、速度变慢，属于正常现象。
- 生成会消耗 API 额度，先用一小段材料试通再加大。
"""

# 【模块级常量】"没选这个类型"时 Tab 里显示的占位文字，多处复用所以提出来
_PLACEHOLDER_TEXT = "（本次没有选择这个类型）"


# 【def 定义函数】给"还没生成"的 Tab 拼一句引导文字
#   参数 card 是 prompts.py 里的一张"卡片定义"对象（带 emoji / label / intro）
def _tab_placeholder(card) -> str:
    """还没生成时，Tab 里显示一句引导，告诉用户这个 Tab 是干什么的。

    注意：这里是纯文本框（不是 Markdown），所以不要写 ** 之类的语法。
    """
    # 【return + 括号续行】return 后面跟圆括号，括号里的相邻字符串会自动拼成一个
    #   这正是"多行写一个长字符串"的标准写法：不会多出换行，也不用 + 号
    return (
        # 【f-string + 属性访问】card.emoji / card.label / card.intro 都是对象属性
        #   \n\n 表示两个换行，让引导语和下一句之间空一行
        f"{card.emoji} {card.label}：{card.intro}\n\n"
        # 【f-string】第二句同样用 f 前缀，把卡片名字嵌进去
        f"点「🚀 开始生成」后，{card.label}会显示在这里。"
    )


# 【def 定义函数 + 类型提示】把多个输出打包成一个元组
#   参数里的 dict[str, str] 表示"键是字符串、值也是字符串的字典"
def _pack(status: str, tab_values: dict[str, str], plan: str, md: str, file):
    """把 9 个输出按固定顺序打包，顺序必须和 outputs=[...] 一致。"""
    # 【元组 + 星号解包】括号里用逗号隔开就是元组，一共 9 个元素：
    #   1 个 status + 5 个 Tab 内容 + plan + md + file
    #   * 把后面的生成器"摊开"成一个个元素，等价于手写 5 个 tab_values[key]
    #   为什么顺序必须对？Gradio 是按"位置"把返回值塞进 outputs 列表的组件里的
    return (status, *(tab_values[key] for key in TAB_KEYS), plan, md, file)


# 【def 定义函数 + 元组类型提示】读取上传的文本文件
#   -> tuple[str, str] 表示返回"两个字符串"组成的元组：(文件名, 文件内容)
def _read_uploaded(file) -> tuple[str, str]:
    """读取上传的文本文件，返回 (文件名, 内容)。

    先按 UTF-8 读，读不出来再试 GBK——Windows 上另存为的 txt 经常是 GBK。
    """
    # 【if 真值判断】file 是 None 或空字符串时算"假"，说明用户没上传
    if not file:
        # 【raise 主动抛异常】主动抛 ValueError，并且把原因写成中文
        #   调用方（on_file_upload）会用 try/except 接住，变成界面上的提示
        raise ValueError("没有检测到文件。")

    # 【变量赋值】先把参数复制给 path，后面可能要改它，不动原参数更清楚
    path = file
    if isinstance(file, (list, tuple)):     # 有些版本会把结果包成列表
        # 【isinstance + 类型元组】第二个参数传 (list, tuple)，表示"是其中任意一种"
        # 【嵌套 if】列表也可能是空的，空列表同样要报错
        if not file:
            # 【raise 主动抛异常】列表是空的，等于还是没上传
            raise ValueError("没有检测到文件。")
        # 【下标索引】取列表第 0 个元素，也就是第一个上传的文件
        path = file[0]
    if hasattr(path, "name"):               # 兼容传进来的是文件对象
        # 【hasattr + 属性访问】文件对象有 .name 属性，里面是它的路径字符串
        path = path.name

    # 【类型转换】把任意形式（字符串 / 文件对象）统一转成 Path 对象，后面才好用
    path = Path(str(path))
    # 【Path 方法】.exists() 判断文件在磁盘上到底存不存在
    if not path.exists():
        # 【raise】路径对，但文件不见了（可能刚被删掉）
        raise ValueError("文件不存在，请重新上传。")
    # 【Path.stat + 大小判断】st_size 是字节数；2 * 1024 * 1024 就是 2MB
    #   先看大小再读，避免有人传一个几百 MB 的文件把程序卡死
    if path.stat().st_size > 2 * 1024 * 1024:
        # 【raise】超过 2MB 直接拒绝，避免一次读进太多内容把界面卡住
        raise ValueError("文件太大（超过 2MB）。请只上传一小段材料。")

    # 【Path.read_bytes】一次性把文件读成 bytes（字节串），此时还不知道是什么编码
    raw = path.read_bytes()
    # 【for 遍历元组】按"最可能成功"的顺序依次尝试三种编码
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        # 【try/except】每次尝试单独包一层：这一种编码失败不影响下一种
        try:
            # 【bytes.decode + 元组返回】用指定编码把字节串变成字符串，成功就立刻返回
            #   utf-8-sig 会顺手去掉 Windows 记事本加的那个隐藏 BOM 头
            return path.name, raw.decode(encoding)
        # 【except 指定异常类型】只接"解码失败"，别的错误照常抛出
        except UnicodeDecodeError:
            # 【continue 跳过本次循环】这种编码不行，直接试下一个
            continue
    # 【raise】三种编码都失败才会走到这里，说明文件可能不是文本文件
    raise ValueError("读不出文件内容，请确认是 UTF-8 编码的 .txt / .md 文件。")


# 【def 定义函数 + 类型提示】搭建整个界面；"-> gr.Blocks" 表示返回一个界面对象
def build_ui(settings: Settings) -> gr.Blocks:
    """搭建界面。settings 从外面传进来，界面自己不去读环境变量。"""

    # 【嵌套函数（闭包）】在 build_ui 内部再定义一个函数，它叫"内部函数"
    #   关键点：它能直接用到外层 build_ui 的参数 settings —— 这叫"闭包"
    #   为什么这么写？Gradio 的 inputs 只能传组件里的值，传不了配置对象；
    #   把函数定义在这里，settings 就"被包进来了"，不用占一个输入框
    def on_generate(text, level, count, selected):
        """点击「开始生成」后执行的生成器函数。

        它一边等 generate_many() 的结果，一边把当前进度 yield 给界面，
        所以用户能看到几个 Tab 陆续被填满，而不是干等半分钟。
        """
        # 【字典推导式】一行生成 {"qa": "", "cloze": "", ...}
        #   语法：{键: 值 for 变量 in 可迭代对象}，等价于先建空字典再 for 里赋值
        empty = {key: "" for key in TAB_KEYS}

        # 第一道检查：没配 Key 就不发请求，直接给一句人话提示
        # 【函数调用】用外层闭包里的 settings 检查配置，看 Key / 地址有没有填对
        problem = config_problem(settings)
        # 【if 真值判断】有问题时 problem 是一句非空字符串（真），没问题时是 None（假）
        if problem:
            # 【gradio 的提示气泡】在页面右上角弹一个黄色小提示，不会打断程序
            gr.Warning(problem)
            # 【生成器 yield】把这一组输出"交出去"，界面立刻刷新
            #   注意：这里用 yield 而不是 return，是因为函数要做成生成器：
            #   每 yield 一次，Gradio 就更新一次界面，用户才看得到进度
            yield _pack("❌ " + problem, empty, "", "", None)
            # 【return 结束生成器】yield 之后不再有输出，Gradio 就认为这次任务结束
            return

        # 【or 短路 + strip】text 是 None 就换成空串，再去掉首尾空白（空格 / 换行）
        text = (text or "").strip()
        # 【if 真值判断】空字符串算"假"
        if not text:
            # 【gradio 的提示气泡】告诉用户"材料是空的"
            gr.Warning("请先输入学习材料。")
            # 【多行函数调用】参数太多时可以换行写，括号里的换行不影响语法
            yield _pack(
                "❌ 学习材料是空的：请粘贴一段文字，或上传 .txt / .md 文件。",
                empty, "", "", None,
            )
            # 【return】材料为空，这次生成到此结束
            return

        # 【列表推导式】从 TAB_KEYS 里筛出用户勾选的类型
        #   为什么要过一遍 TAB_KEYS？为了强制按固定顺序输出，而不是按用户点击顺序
        #   小技巧：(selected or []) 防止 selected 是 None 时 in 报错
        selected = [key for key in TAB_KEYS if key in (selected or [])]
        # 【len + if】少于 2 种就拦下：调用次数太少没意义，界面也会太空
        if len(selected) < 2:
            # 【gradio 的提示气泡】提示至少要选 2 种
            gr.Warning("至少要选择 2 种卡片形式。")
            # 【yield 刷新界面】把"没选够"的错误状态送回界面
            yield _pack(
                # 【f-string 表达式】{} 里可以直接算 len(selected)
                f"❌ 请至少选择 2 种卡片形式（现在只选了 {len(selected)} 种）。",
                empty, "", "", None,
            )
            # 【return】类型数量不够，结束生成器
            return

        # 【or 兜底】用户没选难度时用"进阶"，保证后面一定有值
        level = level or "进阶"
        # 【字典推导式 + 条件表达式】给 5 个 Tab 先各放一段文字：
        #   选中的显示"生成中…"，没选中的显示"本次没有选择这个类型"
        tab_values = {
            # 【a if 条件 else b】这是"行内 if"，整个表达式就是它的值
            key: ("⏳ 生成中…" if key in selected else _PLACEHOLDER_TEXT)
            for key in TAB_KEYS
        }
        # 【time.time()】取当前时间戳（秒），最后用它算总耗时
        start = time.time()
        # 先 yield 一次"正在生成"，让用户马上看到反应，而不是点完没动静
        yield _pack(
            f"⏳ 正在并行生成 {len(selected)} 种卡片，请稍等…",
            tab_values, "生成中…", "", None,
        )

        # 【变量标注 + 空字典】先准备一个字典，存"卡片类型 → 生成结果对象"
        results: dict[str, GenerationResult] = {}
        # 【try/except 第一层】把"生成过程"包起来，业务上的失败在这里接住
        try:
            # 【for 遍历生成器】generate_many 本身也是生成器：
            #   哪种卡片先算完就先交出哪个 result，而不是等全部算完才一起给
            #   这就是"界面上的 Tab 一个接一个亮起来"的原因
            for result in generate_many(settings, text, selected, level, count):
                # 【字典赋值】键是 result.key（如 "qa"），值是整个结果对象
                results[result.key] = result
                # 【字典取值】用 key 取出这张卡的"定义"（emoji / label / intro）
                card = CARD_TYPES[result.key]
                # 【多行赋值 + 条件表达式】成功就填 Markdown，失败就拼一段红色错误说明
                tab_values[result.key] = (
                    result.markdown
                    if result.ok
                    else f"❌ **{card.label}生成失败**\n\n{result.error}"
                )

                # 状态栏：已选类型的完成情况，一眼看出还差哪几个
                # 【str.join + 生成器表达式】用 " / " 把每个类型的进度拼成一行
                #   里面是"三层条件表达式"：先判成功✅，再判失败❌，否则还在等⏳
                marks = " / ".join(
                    f"{CARD_TYPES[key].emoji}{CARD_TYPES[key].label}"
                    + ("✅" if results.get(key) and results[key].ok
                       else "❌" if key in results
                       else "⏳")
                    for key in selected
                )
                # 【yield 进度】每完成一种就推一次界面，状态栏数字和 Tab 内容同时更新
                yield _pack(
                    f"⏳ 已完成 {len(results)}/{len(selected)}：{marks}",
                    tab_values, "", "", None,
                )

        # 【except 元组】一个 except 可以同时接住好几种异常：(LLMError, ValueError)
        #   这两类是"预料之中的错误"——模型调不通、材料不合法，原因能直接告诉用户
        except (LLMError, ValueError) as e:
            # 这两类是"预料之中的错误"，把原话显示给用户
            # 【str(e)】把异常对象转成字符串，就是 raise 时写的那句话
            gr.Warning(str(e))
            # 【yield】把错误原因写进状态栏，界面显示红字而不是白屏
            yield _pack("❌ " + str(e), tab_values, "", "", None)
            # 【return】错误已经交给界面，结束本次生成器
            return
        # 【except Exception 兜底（第二层）】接住所有"意料之外"的异常
        #   为什么要分两层？第一层给用户看得懂的原因；第二层保证界面绝不白屏
        except Exception as e:  # noqa: BLE001 —— 兜底，绝不让界面白屏
            # 【gradio 的提示气泡】只给用户一句"看终端"，细节不往界面抛
            gr.Warning("出现意外错误，详情见启动程序的终端窗口。")
            # 【type(e).__name__】取异常类的名字（如 KeyError），方便排查又不泄露细节
            yield _pack(
                f"❌ 意外错误：{type(e).__name__}: {e}",
                tab_values, "", "", None,
            )
            # 【return】兜底处理完，结束生成器，界面保持可用
            return

        # 【列表推导式 + results.get】收集真正成功的那些结果
        #   results.get(key) 取不到返回 None，配合 and 短路就不会报 KeyError
        ok_results = [results[key] for key in selected if results.get(key) and results[key].ok]
        # 【时间相减】用"现在"减"开始"，得到这次生成花了多少秒
        elapsed = time.time() - start

        # 【if 真值判断】空列表算"假"，说明一种都没成功
        if not ok_results:
            # 【yield 刷新界面】把"全部失败"的状态送回界面
            yield _pack(
                "❌ 全部生成失败，请看每个 Tab 里的错误提示。",
                tab_values, "", "", None,
            )
            # 【return】全部失败，不用再算复习计划和导出了
            return

        # 【sum + 生成器表达式】把每个成功结果的卡片数加起来，得到总卡片数
        n_items = sum(len(result.items) for result in ok_results)
        # 【关键字参数】生成复习计划：只要"总卡数 / 成功类型数 / 难度"三个信息
        plan = build_plan(n_items=n_items, n_types=len(ok_results), level=level)
        # 【位置参数】把结果列表、难度、原文交给导出模块，拼成一整份 Markdown
        md = build_bundle_markdown(ok_results, level, text)
        # 【函数调用】把结果存成 .md 文件，返回文件路径（全部失败时返回 None）
        path = save_bundle(ok_results, level, text)

        # 【多行字符串拼接 + f-string】状态栏文案分三段写，相邻字符串自动拼接
        #   {elapsed:.1f} 表示"保留 1 位小数"的格式化写法
        status = (
            f"✅ 生成完成：{len(ok_results)} 种形式、共 {n_items} 张卡，"
            f"用时 {elapsed:.1f} 秒（并行）。\n\n"
            "每个 Tab 的结果可以直接复制；点「📅 复习与导出」下载整份 Markdown。"
        )
        # 【最后一次 yield + 条件表达式】这是最终结果：状态、5 个 Tab、复习计划、
        #   完整 Markdown、文件路径。file 组件要么给它路径字符串，要么给 None
        yield _pack(status, tab_values, plan, md, str(path) if path else None)

    # 【嵌套函数】"清空"按钮的处理函数：没有参数，直接返回所有组件的初始值
    def on_clear():
        """清空所有输入输出，回到初始状态。"""
        # 【列表推导式 + 函数调用】给 5 种卡片各生成一句初始引导文字
        tabs = [_tab_placeholder(CARD_TYPES[key]) for key in TAB_KEYS]
        # 【元组返回 + 星号解包】返回 12 个值，顺序对应下面 clear_btn 的 outputs：
        #   输入框、文件框、字数、状态、5 个 Tab、复习计划、完整 Markdown、下载文件
        return ("", None, "字数：0", "就绪", *tabs, "", "", None)

    # 【嵌套函数】"上传文件"事件的处理函数，返回 3 个值
    def on_file_upload(file):
        """上传文件后：读出内容填进输入框，并显示字数。"""
        # 【if 真值判断】没上传文件就把界面恢复成初始值
        if not file:
            # 【元组返回】输入框清空、字数归零、状态写"就绪"
            return "", "字数：0", "就绪"
        # 【try/except】读文件可能失败（编码不对、文件太大），要接住变成提示
        try:
            # 【元组解包】_read_uploaded 返回 (文件名, 内容)，一次赋给两个变量
            name, content = _read_uploaded(file)
        # 【except 捕获】接住可预期的输入错误：文件不存在、太大、编码不对
        except ValueError as e:
            # 【as 别名】把异常对象叫 e，用 str(e) 取出中文原因
            gr.Warning(str(e))
            # 【元组返回】清空输入框，并把"读不出来的原因"写进状态栏
            return "", "字数：0", "❌ " + str(e)
        # 【return 元组】成功时一次返回：填进输入框的内容、字数、状态提示
        #   这三个值按顺序填到 outputs=[src, counter, status] 对应的组件里
        return (
            content,
            # 【f-string + 函数调用】{} 里可以调用函数，先把结果算出来再拼进字符串
            f"字数：{count_chars(content)}",
            f"📄 已读取文件：{name}（{count_chars(content)} 字），可以直接点「开始生成」。",
        )

    # fill_width=True：Gradio 6 默认把内容限制在 768px 宽，
    # 左右两栏会挤成上下两行；打开它才能铺满，再配合 CSS 限制最大宽度。
    # 【with 语句 + gr.Blocks】with 会把"里面创建的组件"自动收集到这个界面对象里
    #   as demo 给界面起名 demo，最后 return demo 交给 app.py 去启动
    with gr.Blocks(title="AI 学习卡片生成器", fill_width=True) as demo:
        # 【组件：Markdown】把 _HEADER 那段文字按 Markdown 渲染成标题区
        gr.Markdown(_HEADER)

        # 【布局：Row 一行】Row 表示"横着一行"，里面再放 Column 就是左右分栏
        with gr.Row():
            # ---------------- 左：输入区 ----------------
            # 【布局：Column 一列 + 参数】scale=5 占宽度的权重，min_width 是最小宽度
            #   左边 5 份、右边 6 份，加起来差不多是 5:6 的分栏
            with gr.Column(scale=5, min_width=380):
                # 【组件：多行文本框】用于粘贴学习材料
                #   label 是标题，lines 是显示高度，max_lines 是最多能拉多高
                src = gr.Textbox(
                    label="学习材料",
                    lines=12,
                    max_lines=26,
                    # 【相邻字符串自动拼接】placeholder 太长，分两行写，拼起来还是一句
                    placeholder="把要复习的一小段教材、笔记、知识点说明粘贴到这里…\n"
                                "（也可以点下面的「上传文件」）",
                    # 【列表参数】buttons 控制文本框右上角的小按钮，copy = 复制
                    buttons=["copy"],
                )
                # 【组件：文件上传】file_types 限定只能选 .txt / .md
                #   type="filepath" 表示交给函数的是"文件路径字符串"，而不是文件对象
                file_in = gr.File(
                    label="或者上传 .txt / .md 文件（内容会自动填到上面的输入框）",
                    file_types=[".txt", ".md"],
                    type="filepath",
                    height=130,
                )
                # 【组件：Markdown】用来实时显示"字数：N"，初始是 0
                counter = gr.Markdown("字数：0")

                # 【布局：Row】难度和数量放同一行，左右并排
                with gr.Row():
                    # 【组件：单选】choices 是选项列表，value 是默认选中项
                    #   scale=1 表示这一栏占 1 份宽度
                    level = gr.Radio(
                        choices=LEVELS, value="进阶", label="难度", scale=1,
                    )
                    # 【组件：滑块】minimum / maximum / step / value 四个参数缺一不可
                    #   scale=2 表示滑块占 2 份宽度，比难度那一栏宽一点
                    count = gr.Slider(
                        minimum=3, maximum=8, step=1, value=4,
                        label="每种形式生成几张卡", scale=2,
                    )

                # 【组件：多选框】choices 里放"元组 (显示文字, 真正的值)"
                #   列表推导式把每张卡拼成 "(🃏 问答卡, qa)"，界面上显示 emoji+名字，
                #   但传给函数的是干净的 key（qa），这样代码里不用处理表情符号
                selected = gr.CheckboxGroup(
                    choices=[(f"{card.emoji} {card.label}", key)
                             for key, card in CARD_TYPES.items()],
                    # 【变量引用】默认 5 种全选：TAB_KEYS 就是那 5 个 key
                    value=TAB_KEYS,
                    label="要生成哪几种形式？（至少 2 种）",
                    info="每种形式会单独调用一次模型，选得越多越慢、越费额度。",
                )

                # 【布局：Row】两个按钮放一行
                with gr.Row():
                    # 【组件：按钮】variant="primary" 让它变成醒目的主色按钮
                    run_btn = gr.Button("🚀 开始生成", variant="primary", scale=3)
                    # 【组件：按钮】清空按钮，scale=1 比主按钮窄
                    clear_btn = gr.Button("清空", scale=1)

                # 【组件：折叠面板】Accordion 是"点一下展开"的折叠区
                #   open=False 表示默认收起，不占地方
                with gr.Accordion("使用说明 / 小贴士", open=False):
                    # 【组件：Markdown】里面渲染 _HELP 那段使用说明
                    gr.Markdown(_HELP)

                # 【组件：示例】Examples 会显示几个可点的例子，点一下自动填进输入框
                #   为什么有用？答辩演示时不用现场打字，点一下就能跑
                gr.Examples(
                    label="没有材料？点一个例子上手试试",
                    # 【列表套列表】examples 是"二维列表"：每个内层列表 = 一次填值
                    examples=[
                        # 示例 1：生物（光合作用）
                        ["光合作用是绿色植物利用光能，把二氧化碳和水转化成储存着能量的"
                         "有机物，并且释放出氧气的过程。光合作用分为光反应和暗反应两个阶段。"
                         "光反应在类囊体薄膜上进行，需要光，产生 ATP 和 NADPH，并释放氧气；"
                         "暗反应在叶绿体基质中进行，不需要光，利用 ATP 和 NADPH 把二氧化碳"
                         "固定并还原成糖类。影响光合作用速率的因素有光照强度、二氧化碳浓度、"
                         "温度和水分等。"],
                        # 示例 2：计算机网络（HTTP / HTTPS）
                        ["HTTP 是超文本传输协议，默认端口 80，传输内容是明文，容易被窃听和篡改。"
                         "HTTPS 是 HTTP 加上 TLS/SSL 加密层，默认端口 443，能保证传输的机密性、"
                         "完整性和身份认证。HTTPS 在建立连接时会先进行 TLS 握手，协商加密套件"
                         "并验证服务器证书，之后才用对称加密传输数据。使用 HTTPS 会增加少量"
                         "性能开销，但现代硬件下几乎可以忽略。"],
                        # 示例 3：物理（牛顿第三定律）
                        ["牛顿第三定律：两个物体之间的作用力和反作用力总是大小相等、方向相反、"
                         "作用在同一条直线上，并且分别作用在两个不同的物体上。作用力和反作用力"
                         "同时产生、同时消失，不能相互抵消。需要注意的是，作用力和反作用力"
                         "与平衡力不同：平衡力作用在同一个物体上，可以抵消；作用力和反作用力"
                         "作用在两个物体上，不能抵消。"],
                    ],
                    # 【组件引用】点某个例子时，把它的内容填进 src 这个输入框
                    inputs=[src],
                )

            # ---------------- 右：输出区 ----------------
            # 【布局：Column】右栏比左栏略宽（scale=6），因为要放长文本
            with gr.Column(scale=6, min_width=420):
                # 【组件：Markdown + elem_id】elem_id 给这个组件一个 HTML id，
                #   上面 CSS 里的 #status-box 就是靠它选中这里来设最小高度
                status = gr.Markdown("就绪", elem_id="status-box")

                # 【组件：标签页容器】Tabs 里面每个 Tab 是一页，点页签切换
                with gr.Tabs():
                    # 【变量标注 + 空字典】准备存"卡片 key → 结果文本框"的对应关系
                    #   后面 _pack 就是按 TAB_KEYS 的顺序从这个字典里取值
                    tab_boxes: dict[str, gr.Textbox] = {}
                    # 【for 遍历字典 items()】一次拿到"键 key"和"值 card"
                    for key, card in CARD_TYPES.items():
                        # 【组件：一个标签页】页签名字显示 emoji + 卡片名
                        with gr.Tab(f"{card.emoji} {card.label}"):
                            # 【字典赋值】把新建的文本框存进字典，键是卡片 key
                            tab_boxes[key] = gr.Textbox(
                                # 【函数调用】初始内容就是那句引导文字
                                value=_tab_placeholder(card),
                                # 【属性访问】label 用 card.intro（一句话介绍）当标题
                                label=card.intro,
                                lines=18,
                                max_lines=40,
                                buttons=["copy"],
                            )

                    # 【组件：额外的一页】最后一页放"复习计划 + 导出"
                    with gr.Tab("📅 复习与导出"):
                        # 【组件：Markdown】复习计划会写到这里，先放一句说明
                        plan_md = gr.Markdown(
                            "生成完成后，这里会按第 1 / 2 / 4 / 7 / 15 天自动排出复习日期。"
                        )
                        # 【组件：Markdown】一条分隔线 + 小标题，纯装饰
                        gr.Markdown("---\n### 导出文件")
                        # 【组件：下载文件】interactive=False 表示用户不能手动传文件，
                        #   只用来"显示一个可下载的文件"（程序把路径填进来）
                        file_out = gr.File(
                            label="下载 Markdown 文件（生成完成后自动出现）",
                            interactive=False,
                        )
                        # 【组件：文本框】放完整 Markdown，方便全选复制
                        md_box = gr.Textbox(
                            label="完整 Markdown（可以全选复制，贴进笔记软件）",
                            lines=10,
                            max_lines=30,
                            buttons=["copy"],
                        )

        # ---------------- 事件绑定 ----------------
        # 【列表字面量 + 星号解包】把所有"输出组件"按固定顺序排成一个列表
        #   1 个状态 + 5 个 Tab 文本框 + 复习计划 + 完整 Markdown + 下载文件 = 9 个
        #   这个顺序必须和 _pack() 返回值的顺序一模一样，否则内容会串到别的组件里
        output_components = [
            # 【列表内星号解包】*[...] 把 5 个文本框展开成 5 个元素，而不是一个列表
            status, *[tab_boxes[key] for key in TAB_KEYS], plan_md, md_box, file_out,
        ]
        # 【事件绑定 .click】按钮被点击时，调用 on_generate
        #   inputs：把哪些组件的当前值按顺序当参数传进去
        #   outputs：把函数 yield 出来的值按顺序填回哪些组件
        run_btn.click(
            fn=on_generate,
            inputs=[src, level, count, selected],
            outputs=output_components,
        )
        # 【事件绑定 .upload】文件框"上传完成"时触发，自动读文件填进输入框
        file_in.upload(
            fn=on_file_upload,
            inputs=file_in,
            outputs=[src, counter, status],
        )
        # 【事件绑定 .click】清空按钮：注意 inputs=None，说明 on_clear 不需要任何输入
        clear_btn.click(
            fn=on_clear,
            inputs=None,
            # 【列表 + 星号解包】输出顺序要和 on_clear 返回值顺序完全一致（共 12 个）
            outputs=[src, file_in, counter, status, *[tab_boxes[key] for key in TAB_KEYS],
                     plan_md, md_box, file_out],
        )
        # 【lambda 匿名函数】输入框内容一变（.change），就算一次字数
        #   lambda s: ... 等价于 def f(s): return ...，只是没有名字、写在一行里
        #   s 是输入框的当前文本；输出只填到 counter 这个组件里
        src.change(fn=lambda s: f"字数：{count_chars(s)}", inputs=src, outputs=counter)

    # 【return】把建好的界面对象交回给 app.py，由它去 queue() + launch()
    return demo
