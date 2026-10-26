"""不联网的自测脚本。

作用：用"假的模型"跑一遍完整流水线，验证提示词拼装、JSON 解析、渲染、
分段合并、并行生成、复习计划、导出、界面构建都对。

答辩前跑一次，能证明"我的程序逻辑是经过测试的"，比空口说可靠。
而且它不需要 API Key、不消耗额度。

运行方式（在项目根目录）：
    .venv\\Scripts\\python.exe tests\\selftest.py

本文件用到的 Python 知识（答辩时随便指一处，先报名字再解释）：
    1.  sys.path 模块搜索路径              —— 让 tests/ 里的脚本能 import 到上一层的模块
    2.  import / from ... import ...        —— 导入被测函数
    3.  global 全局变量                    —— check() 里累加"通过了几项"
    4.  def 函数 / 默认参数 / 类型提示       —— 测试函数和断言工具
    5.  try / except + raise               —— expect_error 反过来验证"这里应该报错"
    6.  class 类 / __init__ / self         —— 用类造一个"假模型客户端"
    7.  ** 双星号解包                      —— make_settings(**overrides) 覆盖默认配置
    8.  lambda 匿名函数                    —— 把"一段代码"当参数传给 expect_error
    9.  列表 / 字典 / 集合推导式             —— 造测试数据、比较结果
    10. 临时目录 tempfile + shutil.rmtree   —— 测导出功能，跑完把临时文件删干净
    11. pathlib.Path 读写文件               —— write_text / write_bytes / read_text
    12. try / finally                      —— 不管成功失败都要恢复全局变量、删临时目录
    13. f-string                           —— 打印测试结果
    14. if __name__ == "__main__"          —— 程序入口
"""

# 【import 导入模块】shutil 用来删临时目录（rmtree）
import shutil
# 【import 导入模块】sys 用来改终端编码、改模块搜索路径
import sys
# 【import 导入模块】tempfile 用来创建"临时目录"，测试完就删，不弄脏项目
import tempfile
# 【from ... import ...】只从 datetime 里拿 date 类，用来固定一个"今天"
from datetime import date
# 【from ... import ...】拿 Path，用它拼路径、读写文件
from pathlib import Path

# 让脚本能 import 到上一级目录里的模块
# 【Path + __file__ + parent】找到本文件 → 它的父目录 tests/ → 再父目录就是项目根
#   连续两个 .parent，等价于"上一级目录"
ROOT = Path(__file__).resolve().parent.parent
# 【sys.path 模块搜索路径】sys.path 是一个列表，Python 按顺序在里面找模块
#   insert(0, ...) 把项目根插到最前面，这样 import config 才找得到
#   str(ROOT) 是因为 sys.path 里必须是字符串，不能放 Path 对象
sys.path.insert(0, str(ROOT))

# Windows 控制台默认不是 UTF-8，中文输出会乱码，这里强制一下
# 【hasattr】判断 sys.stdout 有没有 reconfigure 方法（老版本 Python 没有）
if hasattr(sys.stdout, "reconfigure"):
    # 【方法调用 + 关键字参数】强制 UTF-8；errors="replace" 表示编不了的字符替换掉
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 【多行 from ... import】下面这些 import 写在 sys.path 改动之后，
#   所以要让代码检查工具别报"import 不在文件顶部"（E402），于是加 noqa 注释
from config import Settings, config_problem                                    # noqa: E402
# 【from ... import ...】拿"卡片类型字典"和"拼提示词"函数
from prompts import CARD_TYPES, build_messages                                 # noqa: E402
# 【括号多行 import】一次从 services/generator.py 拿三个名字，写不下就用括号换行
from services.generator import (                                               # noqa: E402
    # 结果对象：带 key / ok / markdown / items / error 等字段
    GenerationResult,
    # 并行生成多种卡片（生成器，谁先完成先给谁）
    generate_many,
    # 只生成一种卡片
    generate_one,
)
# 【from ... import ...】拿自定义异常 LLMError，测试"网络失败"时要用
from services.llm_client import LLMError                                       # noqa: E402
# 【括号多行 import】从 utils/cards.py 一次拿 5 个函数/异常
from utils.cards import (                                                      # noqa: E402
    # 解析卡片时专用的异常类型
    CardsParseError,
    # 从模型返回文本里抠 JSON
    extract_json,
    # 合并分段生成的多个结果
    merge_parts,
    # 校验并补全 title / summary / items
    normalize,
    # 把字典渲染成 Markdown
    render_markdown,
)
# 【from ... import ...】拿"生成复习计划"的函数
from utils.review_plan import build_plan                                       # noqa: E402
# 【from ... import ...】拿"数字数"和"长文切分"两个函数
from utils.text_split import count_chars, split_text                           # noqa: E402
# 【import ... as 别名】整个导入 exporter 模块，因为下面要临时改它的模块级变量
import utils.exporter as exporter                                              # noqa: E402

# 【模块级全局变量】记录"一共通过了多少项检查"，每个 check() 成功就加 1
#   注意：函数里要改它，必须先写 global，否则会被当成一个新的局部变量
PASSED = 0


# 【def 函数 + 默认参数】极简断言函数
#   name 是检查项的名字；condition 是要判断的真/假；detail 是失败时的补充信息
#   detail: str = "" 是"默认参数"：调用时不传就用空字符串
def check(name: str, condition: bool, detail: str = "") -> None:
    """一个极简的断言函数：打印结果，失败就抛异常。"""
    # 【global 声明】告诉 Python："下面要改的是外面那个全局 PASSED"
    #   不写这一句，PASSED += 1 会被理解成"新建一个局部变量"，全局变量永远不变
    global PASSED
    # 【if 真值判断】condition 为 True 表示这项检查通过
    if condition:
        # 【增量赋值】PASSED += 1 等价于 PASSED = PASSED + 1
        PASSED += 1
        # 【print + f-string】打印带缩进的"通过"，看起来像测试报告
        print(f"  [通过] {name}")
    # 【else】条件为 False
    else:
        # 【print + f-string】把失败项和补充信息一起打印出来
        print(f"  [失败] {name}  {detail}")
        # 【raise 抛异常】主动抛 AssertionError 让测试"立刻停下并报错"
        #   为什么不在失败时继续跑？测试要"发现问题就停"，否则错误会越滚越多
        raise AssertionError(name)


# 【def 函数 + 函数作为参数】验证"某段代码应该报错"
#   fn 是一个函数（或 lambda）；error_type 是期望的异常类型，默认 Exception（所有异常）
def expect_error(name: str, fn, error_type=Exception) -> None:
    """期待某段代码报错；没报错就算测试失败。"""
    # 【try/except】故意执行 fn()，期待它抛异常
    try:
        # 【调用传进来的函数】fn 是参数，加括号就是"执行它"
        #   这种"把函数当参数传"的写法叫"高阶函数"
        fn()
    # 【except 变量类型】except 后面可以直接跟一个变量，表示"接住这类异常"
    except error_type:
        # 【函数调用】真的抛了预期的异常，说明测试通过，记一笔
        check(name, True)
        # 【return】结束本函数，不再执行下面那句"失败"的检查
        return
    # 【函数调用】能走到这里说明 fn() 没报错，测试失败
    #   error_type.__name__ 取异常类的名字，比如 "CardsParseError"
    check(name, False, f"应该抛出 {error_type.__name__}，但没抛")


# ---------------------------------------------------------------- 测试替身

# 【三引号字符串 + 相邻字符串拼接】`_FAKE_JSON` 是一段"假模型会返回的 JSON 文本"
#   为什么用括号包起来？为了把长字符串拆成多行写，相邻字符串会自动拼成一个
_FAKE_JSON = (
    '{"title": "光合作用", "summary": "材料讲了光合作用的两个阶段", "items": ['
    '{"front": "光合作用的原料是什么？", "back": "二氧化碳和水", "tip": ""},'
    '{"front": "光反应的场所在哪里？", "back": "类囊体薄膜", "tip": "记：光在膜上"}'
    "]}"
)


# 【class 定义类】"假的模型客户端"：不联网，直接返回一段固定的 JSON
#   为什么要有它？真实调用要 API Key、要花钱、还慢；测逻辑时用假的就够了
class FakeClient:
    """假的模型客户端：不联网，直接返回一段固定的 JSON。"""

    # 【__init__ 构造方法 + self】创建对象时自动执行；self 指"这个对象自己"
    #   payload 是要返回的假 JSON；fail=True 表示"模拟一次失败"
    def __init__(self, payload: str = _FAKE_JSON, fail: bool = False):
        # 【实例属性 + self】把参数存到对象上，方法里用 self.calls 就能取到
        #   calls 记录"被调用了几次"，用来验证分段生成有没有真的多调几次
        self.calls = 0
        # 【实例属性】fail 决定 complete() 要不要模拟失败
        self.fail = fail
        # 【实例属性】payload 是 complete() 要返回的那段假 JSON
        self.payload = payload

    # 【实例方法】签名和真实客户端保持一致：收 messages，返回一段字符串
    def complete(self, messages: list[dict]) -> str:
        # 【属性自增】每调用一次就记一笔
        self.calls += 1
        # 【if】如果构造时要求"模拟失败"
        if self.fail:
            # 【raise 自定义异常】抛出项目自己定义的 LLMError，模拟网络问题
            raise LLMError("模拟的网络错误：连不上服务器。")
        # 【return】正常情况下，把那段假 JSON 原样返回
        return self.payload


# 【def 函数 + ** 双星号参数】**overrides 会把所有"关键字参数"收进一个字典
#   例如 make_settings(api_key="x") → overrides == {"api_key": "x"}
def make_settings(**overrides) -> Settings:
    """造一个测试用的配置对象，不读 .env。"""
    # 【dict(...) 构造字典】用"参数名=值"的方式建一个字典，相当于写 {...}
    #   这里给的是测试用的默认值：假的 Key、连不上的地址、超时很短
    base = dict(
        api_key="sk-test", base_url="http://127.0.0.1:1/v1", model="fake",
        timeout=5, max_chars=200, temperature=0.7, max_retries=0, json_mode=True,
    )
    # 【dict.update】用传进来的参数覆盖默认值，这样测试可以只改关心的那一项
    base.update(overrides)
    # 【** 星号解包】把字典再"摊开"成关键字参数，等价于 Settings(api_key=..., ...)
    return Settings(**base)


# ---------------------------------------------------------------- 测试用例

# 【测试函数】第 1 组：验证 extract_json 能把 JSON 从各种"包装"里抠出来
def test_extract_json() -> None:
    # 【print】打印小节标题，让终端输出分段清楚
    print("\n[1] 从模型返回里抠 JSON")
    # 【函数调用 + 比较运算】== 比较两边是否相等，结果 True/False 传给 check
    check("普通 JSON", extract_json('{"a": 1}') == {"a": 1})
    # 【字符串里的 ``` 】测"模型爱把 JSON 包在代码块里"的情况
    check("带代码块", extract_json('```json\n{"a": 1}\n```') == {"a": 1})
    # 【字符串里混中文】测 JSON 前后有废话时还能不能抠出来
    check("带前后废话", extract_json('好的，结果如下：{"a": 1} 希望有帮助') == {"a": 1})
    # 【尾逗号】测"自动修复"逻辑：去掉 } 前多余的逗号
    check("尾逗号自动修复", extract_json('{"a": 1,}') == {"a": 1})
    # 【lambda 匿名函数】lambda: ... 相当于"没名字的一小段函数"
    #   这里只是把"要执行的代码"包一下，交给 expect_error 去调用
    expect_error("完全没有 JSON 要报错", lambda: extract_json("没有 JSON"), CardsParseError)
    # 【lambda】空字符串里当然没有 JSON，也必须抛 CardsParseError
    expect_error("空内容要报错", lambda: extract_json(""), CardsParseError)


# 【测试函数】第 2 组：验证 normalize 会补默认字段、丢掉坏卡
def test_normalize() -> None:
    # 【print】打印小节标题，终端输出更清楚
    print("\n[2] 字段校验")
    # 【函数调用 + 字典参数】传一个"只有 items、没有 title"的字典，测补默认值
    data = normalize({"items": [{"front": "a", "back": "b"}]})
    # 【dict 取值 + ==】data["title"] 用键取"值"，判断是否补成了默认标题
    check("缺 title 用默认值", data["title"] == "学习卡片")
    # 【dict 取值】判断 summary 缺省时补的是空字符串
    check("缺 summary 补空串", data["summary"] == "")

    # 【多行字典字面量】重写一个 data，里面故意放一张"缺反面"的坏卡
    data = normalize({
        "title": "t",
        "items": [{"front": "", "back": "x"}, {"front": "a", "back": "b"}],
    })
    # 【len】两张卡里有一张不合法，校验后应该只剩 1 张
    check("丢掉缺正反面的卡", len(data["items"]) == 1)

    # 【expect_error + 多行调用】测"缺 items 字段"必须报错
    expect_error("缺 items 要报错", lambda: normalize({"title": "t"}), CardsParseError)
    # 【多行参数】参数太多时换行写，括号里的换行不影响语法
    expect_error(
        "没有有效卡片要报错",
        lambda: normalize({"items": [{"front": "", "back": ""}]}),
        CardsParseError,
    )


# 【测试函数】第 3 组：验证 Markdown 渲染的格式
def test_render() -> None:
    # 【print】打印小节标题
    print("\n[3] 渲染 Markdown")
    # 【嵌套字典】外层是"一份卡片数据"，items 里每项是一张卡
    data = {
        "title": "T",
        "summary": "一句话总结",
        "items": [
            # 第一张：tip 有内容，应该渲染出"💡 提示"
            {"front": "问题一", "back": "答案一", "tip": "小提示"},
            # 第二张：tip 是空串，不应该渲染提示
            {"front": "问题二", "back": "答案二", "tip": ""},
        ],
    }
    # 【字典取值 + 函数调用】CARD_TYPES["qa"] 取出"问答卡"的定义，交给渲染函数
    md = render_markdown(CARD_TYPES["qa"], data, "入门")
    # 【in 成员判断 + and】两个子串都在 md 里才算通过；and 表示"两边都真才真"
    check("带类型和难度", "🃏 问答卡" in md and "入门" in md)
    # 【in】判断渲染结果里有没有"引用块"格式的总结
    check("带一句话总结", "> 一句话总结" in md)
    # 【in + and】判断两张卡都按"**1. 问：**"这种格式编了号
    check("有编号", "**1. 问：** 问题一" in md and "**2. 问：** 问题二" in md)
    # 【in】判断答案前面有"答："标签
    check("有正反面标签", "**答：** 答案一" in md)
    # 【str.count】数一数"💡"出现了几次；只有一张卡有提示，所以应该等于 1
    check("只渲染有内容的提示", md.count("💡") == 1)


# 【测试函数】第 4 组：验证分段结果能正确合并
def test_merge() -> None:
    # 【print】打印小节标题
    print("\n[4] 分段结果合并")
    # 【字典字面量】第一段材料生成的假结果：1 张卡
    part1 = {"title": "第一段主题", "summary": "总结1",
             "items": [{"front": "a", "back": "b", "tip": ""}]}
    # 【字典字面量】第二段材料生成的假结果：2 张卡
    part2 = {"title": "第二段主题", "summary": "总结2",
             "items": [{"front": "c", "back": "d", "tip": ""},
                       {"front": "e", "back": "f", "tip": ""}]}
    # 【函数调用 + 传列表】把两段结果按顺序传进去，让程序合并
    data = merge_parts([part1, part2])
    # 【len】1 + 2 = 3，卡片应该全部保留
    check("卡片全部拼起来", len(data["items"]) == 3)
    # 【dict 取值】合并后标题只取第一段的（整份资料的主题以开头为准）
    check("标题取第一段", data["title"] == "第一段主题")


# 【测试函数】第 5 组：验证长文切分的边界情况
def test_split() -> None:
    # 【print】打印小节标题
    print("\n[5] 长文本切分")
    # 【字符串乘法】"一句话" * 6 表示把这句重复 6 遍，快速造一段长文本
    text = "第一句话在这里。第二句话稍长一点点。第三句话也不短。" * 6
    # 【关键字参数】max_chars=60 表示"每段最多 60 个字"
    chunks = split_text(text, max_chars=60)
    # 【len + check 的 detail 参数】第三个参数会在失败时打印实际值，方便排查
    check("切出了多段", len(chunks) > 1, f"实际 {len(chunks)} 段")
    # 【all + 生成器表达式】all(...) 要求括号里每一项都为真，才返回 True
    #   这里检查"每一段长度都 ≤ 60"
    check("每段都不超过上限", all(len(c) <= 60 for c in chunks))
    # 【all + str.strip】c.strip() 非空表示"这一段不是空字符串/纯空白"
    check("没有空段", all(c.strip() for c in chunks))
    # 【切片 chunks[:-1]】除最后一段外，每段都应该以句号/感叹号/问号结尾
    check("尽量按句切分", all(c[-1] in "。！？" for c in chunks[:-1]))

    # 【函数调用】造一段"200 个啊、中间没有标点"的超长单句，测"硬切"
    hard = split_text("啊" * 200, max_chars=50)
    # 【and】两个条件都满足：每段 ≤ 50 字，且正好切成 4 段（200 / 50）
    check("超长单句能硬切", all(len(c) <= 50 for c in hard) and len(hard) == 4)
    # 【== 列表比较】空输入应该返回空列表 []，而不是抛异常
    check("空输入返回空列表", split_text("") == [])
    # 【count_chars】数字数时会忽略空格和换行："a b\nc" 算 3 个字
    check("count_chars 忽略空白", count_chars("a b\nc") == 3)


# 【测试函数】第 6 组：验证提示词里该有的信息都拼进去了
def test_prompt() -> None:
    # 【print】打印小节标题
    print("\n[6] 提示词拼装")
    # 【函数调用】拼一次提示词，参数依次是：材料、卡片类型、难度、数量
    messages = build_messages("这是一段材料。", CARD_TYPES["cloze"], "挑战", 6)
    # 【下标索引 + 链式取值】messages[1] 是第二条消息，["content"] 取它的正文
    user = messages[1]["content"]
    # 【len】一条 system（定身份）+ 一条 user（下任务），正好 2 条
    check("有 system 和 user 两条", len(messages) == 2)
    # 【in】检查 user 正文里确实带上了卡片类型
    check("带上卡片类型", "填空题" in user)
    # 【in】检查带上了难度
    check("带上难度", "挑战" in user)
    # 【in】检查带上了数量（"6 张"）
    check("带上数量", "6 张" in user)
    # 【in】检查带上了输出格式要求里的 '"items"' 字段名
    check("带上 JSON 结构", '"items"' in user)

    # 【关键字参数 + 链式取值】分段生成时要告诉模型"这是第几段/共几段"
    #   这里演示一个常见写法：函数调用后直接 [1]["content"] 继续取
    part_user = build_messages("x", CARD_TYPES["qa"], part_index=2, part_total=5)[1]["content"]
    # 【in】检查提示词里出现了"第 2/5 段"
    check("分段时告诉模型第几段", "第 2/5 段" in part_user)


# 【测试函数】第 7 组：用假模型验证"生成一种卡片"的完整流程
def test_generate_one() -> None:
    # 【print】打印小节标题
    print("\n[7] 单类型生成（假模型）")
    # 【创建对象】造一个假客户端，它每次调用都返回 _FAKE_JSON
    fake = FakeClient()
    # 【关键字参数】client=fake 把假客户端塞进去，覆盖真实的网络调用
    #   这就是"依赖注入"：要测的逻辑不变，只把"外部依赖"换成假的
    result = generate_one(make_settings(), "一段材料。", CARD_TYPES["qa"], "进阶", 2, client=fake)
    # 【属性访问】result.ok 是布尔值，表示这次生成成功没有
    check("生成成功", result.ok)
    # 【len】假 JSON 里正好 2 张卡
    check("拿到 2 张卡", len(result.items) == 2)
    # 【in】渲染出来的 Markdown 里应该有标题"光合作用"
    check("markdown 非空", "光合作用" in result.markdown)
    # 【属性比较】材料不长，只需要调用模型 1 次
    check("只调用一次", fake.calls == 1)

    # 长材料：应该分段多次调用，最后合并
    # 【创建对象】再建一个新的假客户端，重新从 0 计数
    fake2 = FakeClient()
    # 【字符串乘法】造一段约 4 句的长材料
    long_text = "第一句话在这里。第二句话稍微长一点点。第三句话也不短。" * 4
    # 【关键字参数】这次把 max_chars 改小，逼程序分段
    result2 = generate_one(make_settings(max_chars=30), long_text,
                           CARD_TYPES["qa"], "进阶", 2, client=fake2)
    # 【比较运算 + detail】调用次数 > 1 说明真的分段了；detail 会打印实际次数
    check("长材料分段调用", fake2.calls > 1, f"实际调用 {fake2.calls} 次")
    # 【len】分段合并后卡片数一定比单次生成的 2 张多
    check("合并后卡片变多", len(result2.items) > 2)
    # 【str.count】合并时重新统一编号，所以"**1. 问：**"只应该出现 1 次
    check("编号连续", result2.markdown.count("**1. 问：**") == 1)

    # 模型没按 JSON 返回：不能直接失败，要把原文降级显示出来
    # 【关键字参数】payload=... 让假客户端返回一段"根本不是 JSON"的文字
    bad = FakeClient(payload="抱歉，我这次只能给你一段普通文字，不是 JSON。")
    # 【函数调用】这次应该"不崩溃"，而是把原文降级显示出来
    result3 = generate_one(make_settings(), "一段材料。", CARD_TYPES["qa"], "进阶", 2, client=bad)
    # 【and】ok 为真（没崩）并且 markdown 里标注了"原始文本"，才算降级成功
    check("格式不对时降级显示原文", result3.ok and "原始文本" in result3.markdown)


# 【测试函数】第 8 组：验证多种卡片"并行"生成的结果收集
def test_generate_many() -> None:
    # 【print】打印小节标题
    print("\n[8] 多类型并行生成（假模型）")
    # 【创建对象】假的客户端，三个类型共用它
    fake = FakeClient()
    # 【列表字面量】要生成的三个卡片 key
    keys = ["qa", "cloze", "mnemonic"]
    # 【list() 把生成器一次性取完】generate_many 返回的是生成器，
    #   用 list() 才能拿到全部结果，也才能用 len() 数个数
    results = list(generate_many(make_settings(), "一段材料。" * 30, keys,
                                 "入门", 3, client=fake))
    # 【len】三种类型应该各返回一个结果
    check("三种都返回", len(results) == 3)
    # 【集合推导式 + set】把每个结果的 key 收成集合，和 set(keys) 比较
    #   集合比较"不看顺序"，很适合检查"内容是否一致"
    check("key 能对上", {r.key for r in results} == set(keys))
    # 【all】要求"每一个结果都 ok"
    check("全部成功", all(r.ok for r in results))
    # 【all + len】要求每种卡片至少有 2 张
    check("每种都有卡片", all(len(r.items) >= 2 for r in results))

    # 【expect_error + 多行】空材料（只有空格）必须报错，而且要是 ValueError
    expect_error(
        "空材料要报错",
        lambda: list(generate_many(make_settings(), "  ", keys, client=FakeClient())),
        ValueError,
    )
    # 【expect_error】不认识的卡片 key 也必须报错，而不是悄悄跳过
    expect_error(
        "不认识的类型要报错",
        lambda: list(generate_many(make_settings(), "材料", ["不存在"], client=FakeClient())),
        ValueError,
    )


# 【测试函数】第 9 组：验证"调用失败"被包装成结果而不是崩溃
def test_failure() -> None:
    # 【print】打印小节标题
    print("\n[9] 失败兜底")
    # 【关键字参数】fail=True：这个假客户端每次调用都会抛 LLMError
    fake = FakeClient(fail=True)
    # 【函数调用】生成一种卡片，预期"失败但不崩溃"
    result = generate_one(make_settings(), "材料", CARD_TYPES["qa"], client=fake)
    # 【not】ok 应该是 False，说明程序把失败包装成了结果对象
    check("失败时 ok=False", not result.ok)
    # 【in】error 字段里应该保留原始的中文原因，方便用户判断
    check("错误原因是人话", "模拟的网络错误" in result.error)

    # 【list()】两种类型 + 全部失败：应该返回 2 条"失败结果"，而不是抛异常
    results = list(generate_many(make_settings(), "材料", ["qa", "cloze"],
                                 client=FakeClient(fail=True)))
    # 【len + all】两种都返回了，且都是失败的——"一种失败不影响其它"
    check("一种失败不影响其它", len(results) == 2 and all(not r.ok for r in results))


# 【测试函数】第 10 组：验证复习计划的日期和轮次
def test_plan() -> None:
    # 【print】打印小节标题
    print("\n[10] 复习计划")
    # 【创建对象】固定"今天"是 2026-10-22，这样测试结果永远稳定（不依赖真实日期）
    today = date(2026, 10, 22)
    # 【关键字参数】按 12 张卡、5 种形式、进阶难度生成计划
    plan = build_plan(n_items=12, n_types=5, level="进阶", today=today)
    # 【str.count】计划是 Markdown 表格，数"| 第 "出现了几次 → 应该有 5 轮复习
    check("有 5 轮", plan.count("| 第 ") == 5)
    # 【in】第 1 轮是"明天"，也就是 10-23
    check("第一次复习是明天", "2026-10-23" in plan)
    # 【in】最后一轮是 15 天后，10-22 加 15 天 = 11-06
    check("最后一次是 15 天后", "2026-11-06" in plan)
    # 【in】**12** 是 Markdown 加粗的数字，检查卡片数量有没有写进去
    check("显示卡片数量", "**12**" in plan)


# 【测试函数】第 11 组：验证导出 Markdown 和写文件
def test_export() -> None:
    # 【print】打印小节标题
    print("\n[11] 导出 Markdown")
    # 【创建对象 + 关键字参数】手工造一个"生成结果"对象，当作导出模块的输入
    result = GenerationResult(
        key="qa", ok=True, markdown="### 🃏 问答卡\n\n**1. 问：** a\n\n**答：** b\n",
        title="测试", items=[{"front": "a", "back": "b", "tip": ""}],
    )
    # 【模块名.函数名】用 exporter. 前缀调用，因为上面是 import 整个模块
    md = exporter.build_bundle_markdown([result], "进阶", "材料" * 10)
    # 【str.startswith】检查整份文档是不是以总标题开头
    check("有总标题", md.startswith("# 学习卡片"))
    # 【in】检查"难度"这一行写进去了
    check("有难度信息", "- 难度：进阶" in md)
    # 【in】"材料" * 10 = 20 个字，检查字数统计对不对
    check("有材料字数", "- 材料字数：20 字" in md)
    # 【in】检查卡片正文确实被包含进去了
    check("包含卡片内容", "**1. 问：** a" in md)

    # 【tempfile.mkdtemp】创建一个临时目录，prefix 是名字前缀，方便识别
    #   为什么用临时目录？测试会写文件，不能弄脏项目里的 exports/
    tmp = Path(tempfile.mkdtemp(prefix="study-cards-test-"))
    # 【保存旧值】先把导出模块原来的目录存起来，测完要还原
    old_export_dir = exporter.EXPORT_DIR
    # 【修改模块级变量】把导出目录临时改成 tmp（monkeypatch 的简化版）
    exporter.EXPORT_DIR = tmp
    # 【try/finally】不管测试成功还是失败，finally 里的代码都一定会执行
    try:
        # 【函数调用】真正写文件，返回写入的路径
        path = exporter.save_bundle([result], "进阶", "材料")
        # 【and + Path.exists】path 不是 None，而且磁盘上真的存在
        check("文件真的写出来了", path is not None and path.exists())
        # 【Path.suffix】取文件扩展名，应该是 ".md"
        check("文件名是 .md", path.suffix == ".md")
        # 【Path.read_text】读回文件内容，确认里面真的有"问答卡"三个字
        check("文件内容有卡片", "问答卡" in path.read_text(encoding="utf-8"))
        # 【is None】全部失败时 save_bundle 应该返回 None，不写空文件
        check("全部失败时不写文件", exporter.save_bundle(
            [GenerationResult(key="qa", ok=False, error="x")], "进阶", "材料") is None)
    # 【finally】收尾：恢复原来的导出目录，并删掉临时目录
    finally:
        # 【赋值还原】把模块变量改回去，避免影响别的测试
        exporter.EXPORT_DIR = old_export_dir
        # 【shutil.rmtree】递归删除整个临时目录；ignore_errors=True 表示删不掉也不报错
        shutil.rmtree(tmp, ignore_errors=True)


# 【测试函数】第 12 组：验证配置检查能识别常见的填错
def test_config() -> None:
    # 【print】打印小节标题
    print("\n[12] 配置检查")
    # 【is not None】没填 Key 时应该返回一句提示（不是 None）
    check("没填 Key 时给出提示", config_problem(make_settings(api_key="")) is not None)
    # 【** 覆盖】"sk-xxx" 这种模板占位符也要被当成"没填"
    check("占位 Key 也算没填", config_problem(make_settings(api_key="sk-xxx")) is not None)
    # 【is None】填了正常 Key，检查应该通过（返回 None，表示没问题）
    check("填了 Key 就通过", config_problem(make_settings()) is None)
    # 【多行调用】地址少了 https:// 时应该给出提示
    check("地址写错会提示", config_problem(
        make_settings(base_url="api.deepseek.com")) is not None)


# 【测试函数】第 13 组：验证文件读取（UTF-8 / GBK）和界面构建
def test_upload_and_ui() -> None:
    # 【print】打印小节标题
    print("\n[13] 文件读取与界面构建")
    # 【函数内 import】写在函数里也可以，这样只有跑到这个测试时才导入 gradio 界面
    #   好处：测别的功能时不用等界面库加载
    from ui.layout import _read_uploaded, build_ui

    # 【临时目录】再建一个临时目录，这次用来放测试用的 txt 文件
    tmp = Path(tempfile.mkdtemp(prefix="study-cards-upload-"))
    # 【try/finally】测完必须把临时文件删掉
    try:
        # 【Path 的 / 运算符】Path 对象重载了 "/"，这里不是除法，而是"拼接路径"
        utf8_file = tmp / "材料.txt"
        # 【Path.write_text】把字符串写进文件，encoding 指定编码
        utf8_file.write_text("光合作用。", encoding="utf-8")
        # 【str() 转字符串 + 元组解包】被测函数要字符串路径，所以先 str()
        name, content = _read_uploaded(str(utf8_file))
        # 【and】文件名和内容都要对
        check("读 UTF-8 文件", content == "光合作用。" and name == "材料.txt")

        # 【拼路径】再建一个 GBK 编码的文件，测兼容分支
        gbk_file = tmp / "gbk.txt"
        # 【str.encode + write_bytes】先把字符串按 gbk 编成字节，再按字节写文件
        gbk_file.write_bytes("中文材料".encode("gbk"))
        # 【下划线占位】"_" 是约定俗成的"这个值我不用"，这里只要内容不要文件名
        _, content = _read_uploaded(str(gbk_file))
        # 【==】用 GBK 存的文件也能正确读出来
        check("读 GBK 文件", content == "中文材料")

        # 【lambda】传 None 进去，应该抛 ValueError
        expect_error("空文件参数要报错", lambda: _read_uploaded(None), ValueError)
    # 【finally】删除临时目录
    finally:
        # 【清理】ignore_errors=True：删不掉也不报错，避免最后一步把测试搞崩
        shutil.rmtree(tmp, ignore_errors=True)

    # 【函数调用】用假配置真的搭一次界面；能建出来就说明组件和事件绑定没写错
    demo = build_ui(make_settings())
    # 【is not None】返回了对象就说明构建成功
    check("界面能正常构建", demo is not None)


# 【def 定义函数】自测入口：按顺序把所有测试跑一遍
def main() -> None:
    # 【字符串乘法】"=" * 50 打印 50 个等号，当分隔线
    print("=" * 50)
    # 【print】一句说明，告诉用户这次测试不需要联网
    print("自测开始（不联网，不需要 API Key）")
    # 【print】再打一条分隔线，把标题夹在中间
    print("=" * 50)
    # 【逐个调用测试函数】任何一个 check 失败都会抛异常，整个脚本立刻停下
    # 【调用测试 1】从模型返回文本里抠 JSON
    test_extract_json()
    # 【调用测试 2】校验字段、补默认值
    test_normalize()
    # 【调用测试 3】渲染 Markdown
    test_render()
    # 【调用测试 4】合并分段结果
    test_merge()
    # 【调用测试 5】长文本切分
    test_split()
    # 【调用测试 6】拼装提示词
    test_prompt()
    # 【调用测试 7】单类型生成
    test_generate_one()
    # 【调用测试 8】多类型并行生成
    test_generate_many()
    # 【调用测试 9】失败兜底
    test_failure()
    # 【调用测试 10】复习计划
    test_plan()
    # 【调用测试 11】导出 Markdown
    test_export()
    # 【调用测试 12】配置检查
    test_config()
    # 【调用测试 13】文件读取与界面构建
    test_upload_and_ui()
    # 【"\n" + 字符串】先打印一个空行，再打印分隔线
    print("\n" + "=" * 50)
    # 【f-string】把所有检查的通过数量打印出来
    print(f"全部通过：{PASSED} 项检查")
    # 【print】最后一条分隔线，测试报告结束
    print("=" * 50)


# 【if __name__ == "__main__"】直接运行本文件时才执行 main()
#   被别的脚本 import 时不会自动开始跑测试
if __name__ == "__main__":
    # 【函数调用】执行自测入口，开始跑全部测试
    main()
