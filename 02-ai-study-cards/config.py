"""配置模块：只做一件事——把 .env 文件里的值读成 Python 变量。

为什么单独一个文件？
    配置是"会变的东西"：换模型、换 Key、调超时、调分段长度。
    把它抽出来，其它文件就不用关心配置从哪来；改配置也不用翻业务代码。

本文件用到的 Python 知识（答辩时随便指一处，先报名字再解释）：
    1. import / from ... import ...  —— 导入模块，从标准库或第三方库借工具
    2. Path / __file__ / .parent      —— 用绝对路径定位项目根目录
    3. os.getenv(名字, 默认值)        —— 读环境变量，读不到就用默认值
    4. @dataclass 装饰器              —— 数据类，自动生成 __init__
    5. 类型提示 str / int / float     —— 标注"这个字段应该是什么类型"
    6. str | None 联合类型            —— "要么是字符串，要么是 None"
    7. try / except ValueError        —— 转换失败就退回默认值
    8. str.strip() / str.lower()      —— 去掉首尾空白、转小写
    9. set 集合 + in 成员判断          —— 判断"这个值在不在里面"
    10. 条件表达式 a if 条件 else b     —— 一行写完 if/else
    11. f-string                      —— 字符串里嵌变量
    12. 提前 return + 括号续行          —— 逐条检查、发现错误马上返回
"""

# 【from ... import ...】从标准库 dataclasses 里只拿 dataclass 这个装饰器
#   好处：后面直接写 @dataclass，不用写成 @dataclasses.dataclass
from dataclasses import dataclass
# 【from ... import ...】从标准库 pathlib 里拿 Path 类，用它表示"文件路径"
#   Path 比字符串拼路径安全：Windows 的反斜杠、斜杠问题它自己处理
from pathlib import Path
# 【import 导入模块】导入整个 os 模块，后面用它的 os.getenv() 读环境变量
import os

# 【from ... import ...】从第三方库 python-dotenv 拿 load_dotenv 函数
#   它的工作：读 .env 这个文本文件，把里面的 KEY=VALUE 塞进"环境变量"
from dotenv import load_dotenv

# 【Path + __file__】BASE_DIR 是当前文件所在的目录，也就是项目根目录。
#   __file__：当前脚本的路径字符串；.resolve()：转成绝对路径；
#   .parent：取上一级（去掉文件名，留下目录）。
# 用绝对路径加载 .env，避免"换个目录启动就读不到配置"这种坑。
BASE_DIR = Path(__file__).resolve().parent
# 【函数调用 + / 运算符重载】读 .env 文件，把 KEY=VALUE 装进环境变量。
#   这里的 "/" 不是除法：pathlib 重载了这个运算符，用来"拼接路径"。
load_dotenv(BASE_DIR / ".env")

# 【变量赋值 + Path 拼接】导出文件统一放在这个目录（第一次导出时会自动创建）
#   注意：这里只是"算出路径"，文件夹并没有真的建出来，创建动作在导出代码里。
EXPORT_DIR = BASE_DIR / "exports"


# 【装饰器 @dataclass】给下面的 class 套一层"自动生成 __init__"的壳。
#   不写它的话，要为 8 个字段手写 self.api_key = api_key……很啰嗦还容易漏。
#   括号里不写参数 = 用默认行为：这个类的对象建好之后字段还可以改。
@dataclass
class Settings:
    """一次运行需要的全部配置，集中放在一个对象里往下传。"""

    # 【类型提示 + 字段】"api_key: str" 表示这个字段应该放字符串。
    #   冒号只做标注，运行时并不检查类型，写错类型也不会立刻报错。
    api_key: str          # 大模型平台的密钥，绝不能写死在代码里
    base_url: str         # 接口地址（不同平台不一样）
    model: str            # 模型名
    timeout: int          # 单次请求超时（秒）
    max_chars: int        # 单次最多喂给模型多少字，超过就分段
    temperature: float    # 随机性：0 最稳定，1 最发散
    max_retries: int      # 网络失败时自动重试几次
    json_mode: bool       # 是否要求模型用 JSON 模式返回


# 【def 函数 + 类型提示】"-> Settings" 表示这个函数返回一个 Settings 对象。
#   注意 Settings 后面有括号，说明这里返回的是"对象"而不是类本身。
def load_settings() -> Settings:
    """从环境变量读取配置；读不到就用默认值（默认连 DeepSeek）。"""
    # 【实例化 + 关键字参数】Settings(...) 调用 @dataclass 自动生成的 __init__。
    #   用"字段名=值"的方式传参，顺序可以打乱，也不容易传错位置。
    return Settings(
        # 【os.getenv + str.strip】读环境变量；.strip() 去掉首尾空格，
        #   防止 .env 里手滑多敲一个空格，导致 Key 校验失败。
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        # 【默认参数】第二个参数是"读不到时用哪个值"，这里给 DeepSeek 官方地址
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip(),
        # 【默认参数】模型名同理：没配置就用 deepseek-chat
        model=os.getenv("LLM_MODEL", "deepseek-chat").strip(),
        # 【调用自定义函数】环境变量取出来都是字符串，交给 _to_int 转整数；
        #   转不动就用后面的默认值 90（秒），不让程序崩掉。
        timeout=_to_int(os.getenv("LLM_TIMEOUT"), 90),
        # 【函数调用 + 默认值】单段最多 2500 字，超过就切段（见 text_split.py）
        max_chars=_to_int(os.getenv("MAX_CHARS"), 2500),
        # 【函数调用 + 浮点默认值】temperature 是小数，用 _to_float 转
        temperature=_to_float(os.getenv("TEMPERATURE"), 0.7),
        # 【函数调用】网络失败自动重试次数，默认 2 次
        max_retries=_to_int(os.getenv("MAX_RETRIES"), 2),
        # 【函数调用 + 布尔默认值】JSON 模式默认打开，用 _to_bool 把字符串转 bool
        json_mode=_to_bool(os.getenv("JSON_MODE"), True),
    # 【括号收尾】上面 Settings( 的右括号；这种写法叫"多行函数调用"
    )


# 【联合类型 str | None】参数有两种可能：字符串，或者 None（表示没读到）。
#   "|" 是 Python 3.10+ 的写法，老版本要写 Optional[str]。
#   "default: int" 没有默认值，说明调用时必须把这个参数传进来。
def _to_int(value: str | None, default: int) -> int:
    """把字符串转成整数；转不动就用默认值，不让程序因为一个配置项崩掉。"""
    # 【try/except】try 里的代码"允许出错"，出错就跳到 except，程序不会退出
    try:
        # 【条件表达式】value 有内容才 int(value)，否则直接用 default。
        #   这一行等价于 if value: return int(value) else: return default。
        return int(value) if value else default
    # 【捕获特定异常】int("abc") 会抛 ValueError；只接这一种，接住就返回默认值
    except ValueError:
        # 【except 分支】int() 转换失败时回退默认值，保证函数一定有返回值
        return default


# 【def 函数 + 类型提示】和 _to_int 一个套路，只是转换成 float
def _to_float(value: str | None, default: float) -> float:
    # 【try/except】下面这句可能因为 float("abc") 失败
    try:
        # 【条件表达式】有值才转，转失败交给 except 兜底
        return float(value) if value else default
    # 【捕获异常】接住 ValueError，返回默认值，保证函数一定有返回值
    except ValueError:
        # 【except 分支】float() 转换失败时回退默认值
        return default


# 【def 函数 + 类型提示】把 .env 里的字符串转成 True / False
def _to_bool(value: str | None, default: bool) -> bool:
    """把 "true"/"1"/"yes" 这类字符串转成布尔值。"""
    # 【if + or 短路】没配置（None）或者空字符串，都算"没填"，直接给默认值
    if value is None or value == "":
        # 【if 分支】没配置这一项（None 或空串）就直接给默认值
        return default
    # 【链式方法调用 + set 成员判断】strip() 去空格、lower() 转小写，
    #   再用 in 判断它在不在 {"1","true","yes","on"} 里 —— 结果本身就是 bool。
    #   用 set 而不是 list：判断"在不在"更快，也更能表达"这是一组可选值"。
    return value.strip().lower() in {"1", "true", "yes", "on"}


# 【set 集合字面量】花括号里只有值、没有"键: 值"，那是集合而不是字典。
#   这些明显是占位符，当作"没填"处理；集合判断 in 是 O(1)，很快。
_PLACEHOLDERS = {"", "你的key", "sk-xxx", "your-key", "在这里填你的key", "xxx"}


# 【联合返回类型】"要么返回一句错误提示(str)，要么返回 None 表示没问题"。
#   调用方判断"返回值是不是 None"就知道配置能不能用。
def config_problem(s: Settings) -> str | None:
    """检查配置是否可用。返回一句人话的错误提示；没问题返回 None。

    这个函数让"没配 Key"变成一个友好的提示，而不是一串红色报错。
    """
    # 【in 成员判断】Key 为空、或者还是 .env.example 里的占位符，都算没配
    if s.api_key in _PLACEHOLDERS:
        # 【括号续行 + 隐式拼接】圆括号里的相邻字符串会自动拼成一个长句子，
        #   分两行写只是为了不超出屏幕宽度，不会多出换行符。
        return (
            "还没有配置 API Key。请把 .env.example 复制一份改名为 .env，"
            "在 LLM_API_KEY 后面填入你的密钥，然后重新启动程序。"
        )
    # 【str.startswith】地址必须以 http 开头，否则肯定连不上
    if not s.base_url.startswith("http"):
        # 【f-string】{} 里直接嵌变量，把用户填错的值原样回显，方便排查
        return f"LLM_BASE_URL 看起来不对（{s.base_url}），它应该以 http 开头。"
    # 【数值比较】上限太小分段就没意义了：每段只剩一两句话，出不了卡片
    if s.max_chars < 200:
        # 【返回错误提示】配置值过小，直接告诉用户改哪里
        return "MAX_CHARS 太小了（至少 200），否则每段只有一两句话。"
    # 【return None + 提前返回】所有检查都过了，返回 None 表示"配置没问题"。
    #   这也是一种惯例：检查函数没问题时返回 None，而不是返回 True。
    return None
